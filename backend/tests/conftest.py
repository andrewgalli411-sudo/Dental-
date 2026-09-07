from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Base


@pytest.fixture
def engine():
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture
def db_session(session_factory) -> Session:
    s = session_factory()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture
def client(session_factory, tmp_path):
    from fastapi.testclient import TestClient

    from app.db import get_session
    from app.main import app
    from app.storage import LocalObjectStore, get_object_store

    def _override_session():
        s = session_factory()
        try:
            yield s
        finally:
            s.close()

    store = LocalObjectStore(tmp_path / "obj")
    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[get_object_store] = lambda: store
    yield TestClient(app)
    app.dependency_overrides.clear()
