import os
import tempfile

_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.close(_db_fd)
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, delete

from coldfront_interface_api.auth import get_user
from coldfront_interface_api.main import app
from coldfront_interface_api.models import (
    APIUser,
    PrFis,
    StorageOwnerStatus,
    StorageOwnerStatusChange,
    StorageOwnerStatusNotes,
    engine,
)


@pytest.fixture(autouse=True)
def clean_db():
    with Session(engine) as session:
        session.exec(delete(StorageOwnerStatusNotes))
        session.exec(delete(StorageOwnerStatusChange))
        session.exec(delete(StorageOwnerStatus))
        session.exec(delete(APIUser))
        session.exec(delete(PrFis))
        session.commit()


@pytest.fixture
def db_session():
    with Session(engine) as session:
        yield session


@pytest.fixture
def client():
    app.dependency_overrides[get_user] = lambda: {"username": "test-service-account"}
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
