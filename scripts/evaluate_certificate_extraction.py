"""Read real PDFs without writing certificates or approvals to the database."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
from time import perf_counter

from backend.app.application.certificate_extraction import CertificateExtractionService
from backend.app.config import Settings
from backend.app.infrastructure.ocr import PaddleStructureReader
from backend.app.infrastructure.ollama import OllamaExtractor


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdfs", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--with-llm", action="store_true")
    parser.add_argument("--layouts", type=Path)
    args = parser.parse_args()
    settings = Settings()
    class RecordingReader(PaddleStructureReader):
        def read(self, path, **kwargs):
            layout = super().read(path, **kwargs)
            if args.layouts:
                args.layouts.mkdir(parents=True, exist_ok=True)
                (args.layouts / (Path(path).stem + ".json")).write_text(
                    json.dumps(asdict(layout), ensure_ascii=False, indent=2), encoding="utf-8")
            return layout

    service = CertificateExtractionService(RecordingReader(settings),
        ollama_extractor=OllamaExtractor(settings) if args.with_llm else None)
    report = []
    for path in args.pdfs:
        start = perf_counter()
        try:
            result = service.analyze_pdf(path)
            products = (result.get("certificate") or {}).get("products", [])
            entry = {"file": str(path.resolve()), "status": result["status"], "adapter": result.get("adapter"),
                     "seconds": round(perf_counter() - start, 2), "product_count": len(products),
                     "llm_assistance": result.get("llm_assistance"), "reasons": result.get("reasons", []),
                     "certificate": result.get("certificate")}
        except Exception as exc:
            entry = {"file": str(path.resolve()), "status": "error", "error_code": type(exc).__name__,
                     "seconds": round(perf_counter() - start, 2)}
        finally:
            service.release()
        report.append(entry)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({k: v for k, v in entry.items() if k not in {"certificate", "llm_assistance"}}, ensure_ascii=True), flush=True)
    return 1 if any(entry["status"] == "error" for entry in report) else 0


if __name__ == "__main__":
    raise SystemExit(main())
