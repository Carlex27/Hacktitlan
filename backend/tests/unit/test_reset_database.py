from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.dialects.postgresql import dialect

from backend.app.config import Settings
from backend.app.operations.reset_database import reset_database


@pytest.mark.parametrize("environment,url,confirmation", [
    ("production", "postgresql+psycopg://localhost/example", "example"),
    ("development", "postgresql+psycopg://remote/example", "example"),
    ("development", "postgresql+psycopg://localhost/example", "wrong"),
    ("development", "sqlite:///example", "example"),
])
def test_rejects_unsafe_targets_before_connecting(environment, url, confirmation):
    with patch("backend.app.operations.reset_database.create_database_engine") as create_engine:
        with pytest.raises(ValueError):
            reset_database(Settings(environment=environment, database_url=url), confirmation)
        create_engine.assert_not_called()


@pytest.mark.parametrize("running", [0, 1])
def test_transaction_preserves_rules_and_migrations_and_rejects_running_jobs(running):
    engine = MagicMock()
    connection = engine.begin.return_value.__enter__.return_value
    connection.dialect = dialect()
    connection.scalar.side_effect = [running, 0, 0]
    with patch("backend.app.operations.reset_database.create_database_engine", return_value=engine), \
         patch("backend.app.operations.reset_database.inspect") as inspect_connection:
        inspect_connection.return_value.get_table_names.return_value = [
            "rule_sets", "alembic_version", "jobs", "documents",
        ]
        settings = Settings(database_url="postgresql+psycopg://localhost/example")
        if running:
            with pytest.raises(ValueError, match="trabajos en ejecución"):
                reset_database(settings, "example")
            assert len(connection.execute.call_args_list) == 1
            assert engine.begin.return_value.__exit__.call_args.args[0] is ValueError
        else:
            assert reset_database(settings, "example") == {"documents": 0, "jobs": 0}
            statements = [str(call.args[0]) for call in connection.execute.call_args_list]
            assert statements == [
                "LOCK TABLE public.documents, public.jobs IN ACCESS EXCLUSIVE MODE NOWAIT",
                "TRUNCATE TABLE public.documents, public.jobs RESTART IDENTITY",
            ]
        engine.dispose.assert_called_once()
