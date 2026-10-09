"""Vaciar datos de desarrollo conservando migraciones y reglas de clasificación."""

import argparse
import json

from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url

from backend.app.config import Settings, get_settings
from backend.app.infrastructure.database.session import create_database_engine


PRESERVED_TABLES = {"alembic_version", "rule_sets"}


def reset_database(settings: Settings, confirmed_database: str) -> dict[str, int]:
    url = make_url(settings.database_url)
    if settings.environment not in {"development", "test"}:
        raise ValueError("El reinicio sólo está permitido en development o test")
    if url.get_backend_name() != "postgresql" or url.host not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("El reinicio requiere PostgreSQL local")
    if not url.database or confirmed_database != url.database:
        raise ValueError("Confirma el nombre exacto de la base configurada con --confirm-database")
    engine = create_database_engine(settings)
    try:
        with engine.begin() as connection:
            names = sorted(set(inspect(connection).get_table_names(schema="public")) - PRESERVED_TABLES)
            if not names:
                return {}
            tables = ", ".join(
                f"public.{connection.dialect.identifier_preparer.quote(name)}" for name in names
            )
            connection.execute(text(f"LOCK TABLE {tables} IN ACCESS EXCLUSIVE MODE NOWAIT"))
            if "jobs" in names and connection.scalar(text(
                "SELECT count(*) FROM public.jobs WHERE status = 'running'"
            )):
                raise ValueError("Hay trabajos en ejecución: detén el worker antes de reiniciar")
            # No CASCADE: una relación externa debe bloquear el borrado, no ampliarlo.
            connection.execute(text(f"TRUNCATE TABLE {tables} RESTART IDENTITY"))
            counts = {
                name: connection.scalar(text(
                    f"SELECT count(*) FROM public.{connection.dialect.identifier_preparer.quote(name)}"
                )) for name in names
            }
            if any(count != 0 for count in counts.values()):
                raise RuntimeError("No se pudo verificar que todas las tablas quedaron vacías")
            return counts
    finally:
        engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm-database", required=True, help="Nombre de la base cuyos datos se borrarán")
    arguments = parser.parse_args()
    try:
        counts = reset_database(get_settings(), arguments.confirm_database)
    except (ValueError, RuntimeError) as error:
        parser.exit(1, f"{error}\n")
    print(json.dumps({"reset": True, "table_counts": counts}, ensure_ascii=False))


if __name__ == "__main__":
    main()
