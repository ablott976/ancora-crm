from pathlib import Path
import sys

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from app.database import get_db
from app.main import app
from app.routes.auth import create_access_token


class MockDB:
    def __init__(self):
        self.fetchrow_handler = None
        self.fetch_handler = None
        self.fetchval_handler = None
        self.execute_handler = None

    async def fetchrow(self, query, *args):
        if self.fetchrow_handler is None:
            return None
        return await self.fetchrow_handler(query, *args)

    async def fetch(self, query, *args):
        if self.fetch_handler is None:
            return []
        return await self.fetch_handler(query, *args)

    async def fetchval(self, query, *args):
        if self.fetchval_handler is None:
            return 0
        return await self.fetchval_handler(query, *args)

    async def execute(self, query, *args):
        if self.execute_handler is None:
            return "OK"
        return await self.execute_handler(query, *args)


@pytest.fixture(scope="session")
def test_app():
    return app


@pytest.fixture
def mock_db():
    return MockDB()


@pytest_asyncio.fixture
async def client(test_app, mock_db):
    async def _override_get_db():
        yield mock_db

    test_app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client
    test_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_headers(client):
    response = await client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "Ancora2026!"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_token():
    return create_access_token({"sub": "admin"})
