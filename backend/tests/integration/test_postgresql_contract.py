from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, inspect, text


@pytest.mark.skipif(
    not os.getenv("HACKTITLAN_TEST_DATABASE_URL"),
    reason="Requires the explicit hacktitlan_test PostgreSQL database",
)
def test_migrated_postgresql_contract():
    database_url = os.environ["HACKTITLAN_TEST_DATABASE_URL"]
    assert database_url.rsplit("/", 1)[-1].split("?", 1)[0] == "hacktitlan_test"
    engine = create_engine(database_url)
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT 1")) == 1
        tables = set(inspect(connection).get_table_names())
    assert {
        "manufacturers", "stored_files", "documents", "mill_certificates",
        "heats", "products", "observations", "chemical_compositions", "jobs",
        "extraction_runs", "rule_sets", "classification_runs",
        "classification_results", "decision_steps", "corrections",
        "approval_events", "exports", "backup_runs",
    } <= tables
