"""Reproducible capacity measurements; all database writes use disposable databases."""

import argparse
from copy import deepcopy
import ctypes
import json
import math
from multiprocessing import get_context
import os
from pathlib import Path
import platform
import shutil
from statistics import median
import time
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import event, text

from backend.app.api.app import create_app
from backend.app.application.certificate_extraction import CertificateExtractionService
from backend.app.application.worker import Worker
from backend.app.config import Settings, get_settings
from backend.app.infrastructure.database.session import create_session_factory
from backend.app.infrastructure.files import FileStorage
from backend.app.infrastructure.ocr.hardware import probe_hardware
from backend.app.operations.backup import BackupService
from backend.app.operations.restore import restore_backup
from backend.app.operations.volume_seed import migrate, seed_volume, temporary_database


def summarize(values: list[float]) -> dict:
    if not values:
        return {"samples": 0, "median_ms": None, "p95_ms": None, "max_ms": None}
    ordered = sorted(values)
    return {"samples": len(values), "median_ms": round(median(values), 3),
            "p95_ms": round(ordered[math.ceil(len(values) * .95) - 1], 3), "max_ms": round(max(values), 3)}


def process_metrics() -> dict:
    result = {"cpu_seconds": round(time.process_time(), 3), "peak_rss_mb": None,
              "read_bytes": None, "write_bytes": None}
    if platform.system() == "Windows":
        class Memory(ctypes.Structure):
            _fields_ = [("cb", ctypes.c_ulong), ("faults", ctypes.c_ulong)] + [
                (field, ctypes.c_size_t) for field in ("peak_working", "working", "quota_peak_paged",
                "quota_paged", "quota_peak_nonpaged", "quota_nonpaged", "pagefile", "peak_pagefile")]
        class IO(ctypes.Structure):
            _fields_ = [(field, ctypes.c_ulonglong) for field in
                        ("read_ops", "write_ops", "other_ops", "read_bytes", "write_bytes", "other_bytes")]
        memory, io = Memory(), IO()
        memory.cb = ctypes.sizeof(memory)
        kernel = ctypes.windll.kernel32
        kernel.GetCurrentProcess.restype = ctypes.c_void_p
        handle = ctypes.c_void_p(kernel.GetCurrentProcess())
        if ctypes.windll.psapi.GetProcessMemoryInfo(handle, ctypes.byref(memory), memory.cb):
            result["peak_rss_mb"] = round(memory.peak_working / 1024**2, 2)
        if kernel.GetProcessIoCounters(handle, ctypes.byref(io)):
            result.update(read_bytes=io.read_bytes, write_bytes=io.write_bytes)
    return result


class CapacityExtractor:
    """Controlled normalized fixture for queue/persistence load, never an OCR measurement."""
    def __init__(self, heat_count: int | None = None) -> None:
        fixture = Path(__file__).resolve().parents[3] / "data/samples/molino-1.raw.json"
        self.normalized = CertificateExtractionService.normalize_known_payload(json.loads(fixture.read_text()))
        self.heat_count = heat_count
        self.count = 0

    def analyze_pdf(self, path: Path, **kwargs) -> dict:
        count = self.heat_count or 10 + self.count % 6
        self.count += 1
        normalized = deepcopy(self.normalized)
        normalized["document"]["certificate_no"] = path.stem
        template = normalized["products"][0]
        normalized["products"] = []
        for index in range(count):
            product = deepcopy(template)
            product.update(product_id=f"LOAD-{index}", heat_no=f"HEAT-{index}")
            normalized["products"].append(product)
        return {"status": "extracted", "document": {"page_count": 1},
                "adapter": "capacity-normalized-fixture", "certificate": normalized}


def execute_jobs(settings_data: dict, jobs: int, kind: str, report_path: str) -> None:
    started = time.perf_counter()
    settings = Settings(**settings_data)
    sessions = create_session_factory(settings)
    storage = FileStorage(settings.storage_root, settings.max_pdf_bytes)
    extractor = None if kind in {"export", "ocr"} else CapacityExtractor(15 if kind == "burst" else None)
    try:
        worker = Worker(settings, sessions, storage, extractor=extractor)
        for _ in range(jobs):
            if not worker.run_once():
                raise RuntimeError("La cola terminó antes de consumir todos los trabajos")
        result = {"seconds": round(time.perf_counter() - started, 3), **process_metrics()}
    except Exception as exc:
        result = {"error_type": type(exc).__name__, "seconds": round(time.perf_counter() - started, 3)}
    finally:
        sessions.kw["bind"].dispose()
    Path(report_path).write_text(json.dumps(result), encoding="utf-8")


def observe_worker(client: TestClient, settings: Settings, job_ids: list[int], kind: str, path: Path) -> dict:
    process = get_context("spawn").Process(target=execute_jobs,
        args=(settings.model_dump(), len(job_ids), kind, str(path)))
    process.start()
    timings = []
    try:
        deadline = time.monotonic() + 1800
        while process.is_alive():
            started = time.perf_counter()
            response = client.get("/api/v1/certificates?limit=50")
            if response.status_code != 200:
                raise RuntimeError("La API falló mientras trabajaba el worker")
            timings.append((time.perf_counter() - started) * 1000)
            if time.monotonic() > deadline:
                raise TimeoutError("El worker excedió 30 minutos")
            process.join(timeout=.25)
        process.join()
        if process.exitcode != 0 or not path.is_file():
            raise RuntimeError("El proceso worker no terminó correctamente")
        result = json.loads(path.read_text())
        if "error_type" in result:
            raise RuntimeError(f"El worker falló: {result['error_type']}")
        jobs = [client.get(f"/api/v1/jobs/{identifier}").json()["data"] for identifier in job_ids]
        allowed = {"succeeded", "needs_review"} if kind == "ocr" else {"succeeded"}
        if any(job["status"] not in allowed for job in jobs):
            raise RuntimeError(f"Estado inesperado del worker: {[job['status'] for job in jobs]}")
        return {**result, "api_during_worker": summarize(timings), "job_statuses": [job["status"] for job in jobs]}
    finally:
        if process.is_alive():
            process.terminate()
            process.join()
        process.close()


def measure_queries(client: TestClient, samples: int) -> tuple[dict, dict]:
    engine = client.app.state.sessions.kw["bind"]
    captured = {}
    current = None
    def capture(connection, cursor, statement, parameters, context, executemany):
        if current and statement.startswith("SELECT") and "FROM mill_certificates" in statement and "LIMIT" in statement:
            captured.setdefault(current, (statement, parameters))
    event.listen(engine, "before_cursor_execute", capture)
    paths = {
        "list": "/api/v1/certificates?limit=50",
        "day": "/api/v1/certificates?date_from=2026-10-07&date_to=2026-10-07",
        "week": "/api/v1/certificates?date_from=2026-10-01&date_to=2026-10-07",
        "month": "/api/v1/certificates?date_from=2026-09-08&date_to=2026-10-07",
        "certificate": "/api/v1/certificates?certificate_no=VOLUME-018250",
        "manufacturer": "/api/v1/certificates?manufacturer=Volume%20Maker%201",
        "heat": "/api/v1/certificates?heat_no=HEAT-18250-15",
        "product": "/api/v1/certificates?product_identifier=COIL-273750",
        "classification": "/api/v1/certificates?fraction=72083991&nico=00",
        "approval": "/api/v1/certificates?approval_status=approved",
        "processing": "/api/v1/certificates?processing_status=succeeded",
        "uploaded": "/api/v1/certificates?date_basis=uploaded",
        "certificate_detail": "/api/v1/certificates/1",
        "run_detail": "/api/v1/classification-runs/1",
    }
    initial = client.get(paths["list"]).json()
    cursor = initial["meta"]["next_cursor"]
    if cursor:
        paths["cursor"] = f"/api/v1/certificates?limit=50&cursor={cursor}"
    timings = {}
    try:
        for name, path in paths.items():
            current = name
            values = []
            for _ in range(samples):
                started = time.perf_counter()
                response = client.get(path)
                if response.status_code != 200:
                    raise RuntimeError(f"Consulta fallida: {name}")
                values.append((time.perf_counter() - started) * 1000)
            timings[name] = summarize(values)
    finally:
        event.remove(engine, "before_cursor_execute", capture)
    plans = {}
    with engine.connect() as connection:
        for name, (statement, parameters) in captured.items():
            plans[name] = connection.exec_driver_sql("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + statement, parameters).scalar_one()
    return timings, plans


def run_capacity(output: Path, certificates: int = 18_250, samples: int = 10, ocr_pdf: Path | None = None) -> dict:
    output = output.resolve()
    root = output.parent / f"capacity-{uuid4().hex[:8]}"
    root.mkdir(parents=True)
    report = {"created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
              "hardware": probe_hardware().as_dict(), "cpu": platform.processor(),
              "logical_cpus": os.cpu_count(), "transport": "FastAPI TestClient, sin TCP/Tailscale",
              "agreed_latency_targets": None, "ocr": {"status": "pending", "reason": "No scanned PDF provided"}}
    base = get_settings()
    def save():
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    with temporary_database(base, root / "source") as settings:
        print("Migraciones y siembra", flush=True)
        migrate(settings)
        started = time.perf_counter()
        report["volume"] = seed_volume(settings, certificates=certificates)
        report["seed_seconds"] = round(time.perf_counter() - started, 3)
        save()
        with TestClient(create_app(settings)) as client:
            print("Consultas y planes SQL", flush=True)
            report["queries"], report["sql_plans"] = measure_queries(client, samples)
            save()
            report["exports"] = {}
            for name, count in (("daily", 10), ("burst", 100), ("month", 300)):
                print(f"Exportación {name}", flush=True)
                ids = list(range(max(1, certificates - count + 1), certificates + 1))
                response = client.post("/api/v1/exports", json={"certificate_ids": ids,
                    "official": True, "person_name": "Capacity benchmark"})
                if response.status_code != 202:
                    raise RuntimeError("No se pudo crear la exportación")
                data = response.json()["data"]
                report["exports"][name] = observe_worker(client, settings, [data["job_id"]], "export", root / f"{name}.json")
                exported = client.get(f"/api/v1/exports/{data['export_id']}").json()["data"]
                file_response = client.get(exported["download_url"])
                if file_response.status_code != 200:
                    raise RuntimeError("No se pudo descargar el archivo generado")
                report["exports"][name].update(certificates=len(ids), products=len(ids)*15, size_bytes=len(file_response.content),
                                               sha256=exported["sha256"])
                save()
            report["ingestion"] = {}
            for name, count in (("daily", 10), ("burst", 30)):
                print(f"Cola y persistencia {name}", flush=True)
                jobs = []
                for number in range(count):
                    response = client.post("/api/v1/documents", files={"file": ("capacity.pdf",
                        f"%PDF-1.7\ncapacity-{uuid4().hex}-{number}".encode(), "application/pdf")})
                    if response.status_code != 202:
                        raise RuntimeError("No se pudo cargar el documento sintético")
                    jobs.append(response.json()["data"]["job_id"])
                report["ingestion"][name] = observe_worker(client, settings, jobs, name, root / f"ingest-{name}.json")
                report["ingestion"][name].update(documents=count, heat_range=[10, 15] if name == "daily" else [15, 15],
                                                 extraction="normalized fixture, not OCR")
                save()
            if ocr_pdf:
                print("OCR real en CPU", flush=True)
                with ocr_pdf.open("rb") as stream:
                    response = client.post("/api/v1/documents", files={"file": (ocr_pdf.name, stream, "application/pdf")})
                if response.status_code != 202:
                    raise RuntimeError("No se pudo cargar el PDF OCR")
                ocr_settings = settings.model_copy(update={"ocr_enabled": True, "ocr_device": "cpu"})
                report["ocr"] = observe_worker(client, ocr_settings, [response.json()["data"]["job_id"]], "ocr", root / "ocr.json")
                save()
            with client.app.state.sessions() as session:
                report["database_size_bytes"] = session.scalar(text("SELECT pg_database_size(current_database())"))
        print("Respaldo completo y restauración", flush=True)
        sessions = create_session_factory(settings)
        try:
            started = time.perf_counter()
            backup = BackupService(settings).create_and_record(sessions, "manual")
            report["backup"] = {"seconds": round(time.perf_counter()-started, 3), "path": backup["path"],
                                "sha256": backup["sha256"], "secondary_path": backup["secondary_path"],
                                "size_bytes": Path(backup["path"]).stat().st_size}
            with temporary_database(base, root / "restore") as restored_settings:
                started = time.perf_counter()
                restored = restore_backup(restored_settings, Path(backup["path"]), restored_settings.storage_root, root / "restored-rules")
                report["restore"] = {**restored, "seconds": round(time.perf_counter()-started, 3)}
        finally:
            sessions.kw["bind"].dispose()
        report["disk_free_bytes"] = shutil.disk_usage(root).free
        report["measurement_process"] = process_metrics()
        report["acceptance"] = "pending_server_hardware_latency_targets_and_ocr" if not ocr_pdf else "pending_server_hardware_and_latency_targets"
        save()
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Medir Hito 7 en bases PostgreSQL desechables")
    parser.add_argument("--output", type=Path, default=Path("tmp/hito7/capacity.json"))
    parser.add_argument("--certificates", type=int, default=18_250)
    parser.add_argument("--samples", type=int, default=10)
    parser.add_argument("--ocr-pdf", type=Path)
    arguments = parser.parse_args()
    if arguments.samples < 1:
        parser.error("samples debe ser positivo")
    run_capacity(arguments.output, arguments.certificates, arguments.samples, arguments.ocr_pdf)
    print(str(arguments.output.resolve()))


if __name__ == "__main__":
    main()
