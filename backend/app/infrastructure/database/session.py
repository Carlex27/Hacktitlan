"""SQLAlchemy engine and session lifecycle."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import MetaData, create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.app.config import Settings


NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def create_database_engine(settings: Settings, *, echo: bool = False) -> Engine:
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        echo=echo,
    )
    if engine.dialect.name == "postgresql":
        timeout = settings.database_statement_timeout_ms

        @event.listens_for(engine, "connect")
        def set_statement_timeout(dbapi_connection, _connection_record) -> None:
            autocommit = dbapi_connection.autocommit
            try:
                dbapi_connection.autocommit = True
                with dbapi_connection.cursor() as cursor:
                    cursor.execute(f"SET statement_timeout = {int(timeout)}")
            finally:
                dbapi_connection.autocommit = autocommit
    return engine


def create_session_factory(settings: Settings, *, echo: bool = False) -> sessionmaker[Session]:
    return sessionmaker(
        bind=create_database_engine(settings, echo=echo),
        class_=Session,
        expire_on_commit=False,
        autoflush=False,
    )


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
