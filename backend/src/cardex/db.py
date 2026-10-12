from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from cardex.config import get_settings
from cardex.models import Base

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        settings = get_settings()
        connect_args = (
            {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
        )
        _engine = create_engine(settings.database_url, connect_args=connect_args)
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _session_factory


def init_db() -> None:
    Base.metadata.create_all(get_engine())


def reset_engine() -> None:
    """Drop cached engine/session factory. Used by tests to rebind to a fresh DB."""
    global _engine, _session_factory
    _engine = None
    _session_factory = None


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency: yields a session, closes it after the request."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
