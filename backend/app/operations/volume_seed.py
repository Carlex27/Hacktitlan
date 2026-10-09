"""Disposable PostgreSQL fixtures for the Hito 7 capacity checks."""

from contextlib import contextmanager
from io import BytesIO
import os
from pathlib import Path
import re
import subprocess
import sys
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from backend.app.config import Settings
from backend.app.infrastructure.files import FileStorage


@contextmanager
def temporary_database(base: Settings, root: Path):
    if not base.test_database_url or make_url(base.test_database_url).database != "hacktitlan_test":
        raise ValueError("Se requiere una conexión explícita a hacktitlan_test")
    name = f"hacktitlan_hito7_{uuid4().hex[:12]}"
    assert re.fullmatch(r"hacktitlan_hito7_[a-f0-9]{12}", name)
    url = make_url(base.test_database_url)
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{name}"'))
    settings = base.model_copy(update={"database_url": url.set(database=name).render_as_string(hide_password=False),
        "storage_root": root / "storage", "backup_root": root / "backups", "secondary_backup_root": root / "secondary"})
    try:
        yield settings
    finally:
        # Only the random database created above can be removed; no existing database is reused.
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
        admin.dispose()


def migrate(settings: Settings) -> None:
    environment = os.environ.copy()
    environment["HACKTITLAN_DATABASE_URL"] = settings.database_url
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"],
                   env=environment, check=True, capture_output=True, text=True)


def seed_volume(settings: Settings, certificates: int = 18_250, heats_per_certificate: int = 15) -> dict:
    if not 1 <= certificates <= 18_250 or not 1 <= heats_per_certificate <= 15:
        raise ValueError("Volumen fuera del alcance del Hito 7")
    if not re.fullmatch(r"hacktitlan_hito7_[a-f0-9]{12}", make_url(settings.database_url).database or ""):
        raise ValueError("La siembra sólo admite una base desechable del Hito 7")
    storage = FileStorage(settings.storage_root, settings.max_pdf_bytes)
    artifact = storage.store_pdf(BytesIO(b"%PDF-1.7\nsynthetic capacity fixture"), "capacity.pdf")
    engine = create_engine(settings.database_url)
    try:
        with engine.begin() as connection:
            if connection.scalar(text("SELECT count(*) FROM mill_certificates")):
                raise ValueError("La siembra requiere una base sin actas")
            connection.execute(text("""
                INSERT INTO stored_files (sha256,original_name,storage_name,relative_path,media_type,size_bytes,status)
                VALUES (:hash,'capacity.pdf',:name,:path,'application/pdf',:size,'ready')
            """), {"hash": artifact.sha256, "name": artifact.storage_name,
                   "path": artifact.relative_path, "size": artifact.size_bytes})
            volume_sql = """
                INSERT INTO manufacturers(name,normalized_name)
                SELECT 'Volume Maker ' || i, 'volume maker ' || i FROM generate_series(1,20) i;
                INSERT INTO documents(stored_file_id,processing_status,archived,metadata_json)
                SELECT 1,'succeeded',false,'{}'::json FROM generate_series(1,:count);
                INSERT INTO mill_certificates(document_id,manufacturer_id,certificate_no,certificate_date,
                    uploaded_at,revision_number,approval_status,demo_notice)
                SELECT id,1+(id%20),'VOLUME-' || lpad(id::text,6,'0'),
                    DATE '2021-10-09' + ((id-1)/10)::int,
                    TIMESTAMPTZ '2021-10-09 12:00:00+00' + ((id-1)/10)::int * INTERVAL '1 day',
                    1,'approved','DEMOSTRACIÓN — SIN VALIDEZ ADUANERA' FROM documents;
                INSERT INTO heats(certificate_id,heat_no,standard,grade,properties_json)
                SELECT c.id,'HEAT-' || c.id || '-' || i,'ASTM A36','A36','{}'::json
                FROM mill_certificates c CROSS JOIN generate_series(1,:heats) i;
                INSERT INTO products(certificate_id,heat_id,product_identifier,form,coiled,rolling,
                    width_mm,thickness_mm,weight_kg,properties_json)
                SELECT certificate_id,id,'COIL-' || id,'flat_rolled',true,'hot',1200,3,10000,'{}'::json FROM heats;
                INSERT INTO observations(certificate_id,heat_id,product_id,field_path,raw_value_json,
                    normalized_value_json,unit,confidence,page_number,source_text,inherited,is_current)
                SELECT certificate_id,heat_id,id,'thickness_mm','3'::json,'3'::json,'mm',1,1,'3 mm',false,true FROM products;
                INSERT INTO chemical_compositions(heat_id,element,raw_value_json,percentage,inherited,source_label)
                SELECT id,'C','0.15'::json,0.15,false,'C %' FROM heats;
                INSERT INTO classification_runs(certificate_id,rule_set_id,approval_status,input_snapshot_json,demo_notice)
                SELECT id,(SELECT min(id) FROM rule_sets),'approved','{}'::json,demo_notice FROM mill_certificates;
                INSERT INTO classification_results(classification_run_id,product_id,fraction,nico,outcome,details_json)
                SELECT r.id,p.id,'72083991','00','classified','{}'::json FROM products p
                JOIN classification_runs r ON r.certificate_id=p.certificate_id;
                INSERT INTO classification_candidates(classification_result_id,rank,fraction,nico,description,support_level,details_json)
                SELECT id,1,fraction,nico,'Synthetic load candidate','fully_supported','{}'::json FROM classification_results;
                INSERT INTO candidate_factors(candidate_id,sequence,rule_code,outcome,explanation,required_for_selection,
                    expected_json,observed_json)
                SELECT id,1,'load.thickness','matched','Synthetic load factor',true,'{}'::json,'{}'::json FROM classification_candidates;
                INSERT INTO evidence_links(candidate_factor_id,observation_id,source_type,field_path,source_reference_json)
                SELECT f.id,o.id,'observation','thickness_mm','{}'::json FROM candidate_factors f
                JOIN classification_candidates c ON c.id=f.candidate_id
                JOIN classification_results r ON r.id=c.classification_result_id
                JOIN observations o ON o.product_id=r.product_id;
            """
            for statement in volume_sql.split(";"):
                if statement.strip():
                    connection.execute(text(statement), {"count": certificates, "heats": heats_per_certificate})
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
            connection.execute(text("ANALYZE"))
        return {"certificates": certificates, "heats": certificates * heats_per_certificate,
                "products": certificates * heats_per_certificate,
                "pdf_fixture_sha256": artifact.sha256, "physical_pdf_files": 1}
    finally:
        engine.dispose()
