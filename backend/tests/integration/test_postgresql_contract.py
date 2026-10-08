from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import DBAPIError

from backend.app.api.app import create_app
from backend.app.config import Settings


@pytest.fixture(scope="module")
def test_database_url() -> str:
    database_url = os.getenv("HACKTITLAN_TEST_DATABASE_URL") or Settings().test_database_url
    if not database_url:
        pytest.skip("Requires the explicit hacktitlan_test PostgreSQL database")
    assert database_url.rsplit("/", 1)[-1].split("?", 1)[0] == "hacktitlan_test"
    return database_url


def test_postgresql_connection_identity(test_database_url: str):
    engine = create_engine(test_database_url)
    try:
        with engine.connect() as connection:
            identity = connection.execute(
                text(
                    "SELECT current_database(), current_user, "
                    "current_setting('server_version_num')::integer"
                )
            ).one()
    finally:
        engine.dispose()

    assert identity[0] == "hacktitlan_test"
    assert identity[1]
    assert identity[2] >= 180000


def test_migrated_postgresql_contract(test_database_url: str):
    engine = create_engine(test_database_url)
    try:
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT 1")) == 1
            tables = set(inspect(connection).get_table_names())
            migration = connection.scalar(text("SELECT version_num FROM alembic_version"))
    finally:
        engine.dispose()

    assert migration == "0006_rule_set_immutability"
    assert {
        "manufacturers", "stored_files", "documents", "mill_certificates",
        "heats", "products", "observations", "chemical_compositions", "jobs",
        "extraction_runs", "rule_sets", "classification_runs",
        "classification_results", "decision_steps", "corrections",
        "classification_candidates", "classification_selections", "candidate_factors",
        "evidence_links",
        "approval_events", "exports", "backup_runs",
    } <= tables


def test_approved_rule_sets_are_immutable_in_postgresql(test_database_url: str):
    engine = create_engine(test_database_url)
    connection = engine.connect()
    transaction = connection.begin()
    try:
        rule_set_id = connection.scalar(text("""
            INSERT INTO rule_sets (name, version, status, source_hash, manifest_json)
            VALUES ('immutability-test', '1', 'approved', :source_hash, '{}'::json)
            RETURNING id
        """), {"source_hash": "0" * 64})
        savepoint = connection.begin_nested()
        with pytest.raises(DBAPIError, match="immutable"):
            connection.execute(
                text("UPDATE rule_sets SET manifest_json = CAST(:manifest AS json) WHERE id = :id"),
                {"id": rule_set_id, "manifest": '{"changed":true}'},
            )
        savepoint.rollback()
    finally:
        transaction.rollback()
        connection.close()
        engine.dispose()


def test_ready_endpoint_checks_real_postgresql(test_database_url: str, tmp_path):
    settings = Settings(
        database_url=test_database_url,
        storage_root=tmp_path / "storage",
        backup_root=tmp_path / "backups",
    )

    with TestClient(create_app(settings)) as client:
        response = client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "data": {
            "status": "ready",
            "database": "available",
            "storage": "available",
        },
        "meta": {},
        "error": None,
    }
    assert settings.storage_root.is_dir()
