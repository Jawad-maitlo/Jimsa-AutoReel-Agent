import os
import sys
import tempfile
from pathlib import Path
import pytest

TEST_ROOT = Path(tempfile.mkdtemp(prefix="jimsa_tests_"))
os.environ["STORAGE_DIR"] = str(TEST_ROOT / "storage")
os.environ["DATABASE_URL"] = f"sqlite:///{(TEST_ROOT / 'test.db').as_posix()}"
os.environ["WHISPER_MODEL"] = "tiny"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from app.database import Base, engine
from app.main import app


@pytest.fixture(scope="session")
def client():
    Base.metadata.drop_all(engine)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def project(client):
    response = client.post("/api/projects", json={"name": "Integration project"})
    assert response.status_code == 201
    return response.json()
