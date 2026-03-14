from contextlib import asynccontextmanager
from pathlib import Path
import sys
import types as pytypes
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from google import genai as _genai  # noqa: F401
except Exception:
    google_module = sys.modules.setdefault("google", pytypes.ModuleType("google"))
    genai_module = pytypes.ModuleType("google.genai")
    types_module = pytypes.ModuleType("google.genai.types")

    class _Type:
        OBJECT = "object"
        STRING = "string"
        INTEGER = "integer"

    class _Schema:
        def __init__(self, type=None, properties=None, required=None, description=None):
            self.type = type
            self.properties = properties or {}
            self.required = required or []
            self.description = description

    class _FunctionDeclaration:
        def __init__(self, name, description, parameters):
            self.name = name
            self.description = description
            self.parameters = parameters

    class _Tool:
        def __init__(self, function_declarations=None):
            self.function_declarations = function_declarations or []

    class _GenerateContentConfig:
        def __init__(self, system_instruction=None, temperature=None, tools=None):
            self.system_instruction = system_instruction
            self.temperature = temperature
            self.tools = tools

    class _Part:
        def __init__(self, text=None, function_call=None, response=None, name=None):
            self.text = text
            self.function_call = function_call
            self.response = response
            self.name = name

        @classmethod
        def from_text(cls, text):
            return cls(text=text)

        @classmethod
        def from_function_response(cls, name, response):
            return cls(name=name, response=response)

    class _Content:
        def __init__(self, role, parts):
            self.role = role
            self.parts = parts

    types_module.Type = _Type
    types_module.Schema = _Schema
    types_module.FunctionDeclaration = _FunctionDeclaration
    types_module.Tool = _Tool
    types_module.GenerateContentConfig = _GenerateContentConfig
    types_module.Part = _Part
    types_module.Content = _Content
    genai_module.types = types_module
    genai_module.Client = object
    google_module.genai = genai_module
    sys.modules["google.genai"] = genai_module
    sys.modules["google.genai.types"] = types_module

from app.database import get_db
from app.main import app
from app.plugins import PluginRegistry, register_all_plugins
from app.routes.auth import create_access_token
from app.services.chatbot_auth import create_access_token as create_chatbot_access_token


ALL_PLUGIN_IDS = {
    "bookings",
    "reminders",
    "closures",
    "daily_menus",
    "broadcasts",
    "instagram_dm",
    "advanced_crm",
    "audio_transcription",
    "restaurant_bookings",
    "owner_agent",
    "consent_forms",
    "shift_view",
    "voice_agent",
}


class MockDB:
    def __init__(self):
        self.enabled_plugins = set(ALL_PLUGIN_IDS)
        self.chatbot_user = {"id": 7, "username": "tester", "instance_id": 1, "role": "admin"}
        self.instance_lookup = {"id": 1, "is_active": True}
        self.instance_config = {"id": 1, "google_api_key": "", "gemini_temperature": 0.4}
        self.prompt_config = None
        self.system_prompt_row = {"content": "Hola {business_name}\n{schedule_formatted}\n{holidays_formatted}\n{fecha_hoy}"}
        self.business_info = {"business_name": "Ancora Demo"}
        self.schedule_rows = []
        self.holiday_rows = []
        self.fetchval_values = []
        self.fetchrow_overrides = []
        self.fetch_overrides = []
        self.execute_result = "DELETE 1"

        self.fetchrow = AsyncMock(side_effect=self._fetchrow)
        self.fetch = AsyncMock(side_effect=self._fetch)
        self.fetchval = AsyncMock(side_effect=self._fetchval)
        self.execute = AsyncMock(side_effect=self._execute)

    async def _fetchrow(self, query, *args):
        if self.fetchrow_overrides:
            value = self.fetchrow_overrides.pop(0)
            return value(query, *args) if callable(value) else value

        if "FROM ancora_crm.instance_plugins" in query:
            plugin_id = args[1]
            return {"plugin_id": plugin_id} if plugin_id in self.enabled_plugins else None
        if "FROM ancora_crm.chatbot_dashboard_users" in query:
            return self.chatbot_user
        if "FROM ancora_crm.chatbot_instances WHERE phone_number_id = $1" in query:
            return self.instance_lookup
        if "FROM ancora_crm.chatbot_instances WHERE id = $1" in query:
            return self.instance_config
        if "FROM ancora_crm.chatbot_prompt_config" in query:
            return self.prompt_config
        if "FROM ancora_crm.chatbot_prompts" in query:
            return self.system_prompt_row
        if "FROM ancora_crm.chatbot_business_info" in query:
            return self.business_info
        return None

    async def _fetch(self, query, *args):
        if self.fetch_overrides:
            value = self.fetch_overrides.pop(0)
            return value(query, *args) if callable(value) else value

        if "SELECT plugin_id FROM ancora_crm.instance_plugins" in query:
            return [{"plugin_id": plugin_id} for plugin_id in sorted(self.enabled_plugins)]
        if "FROM ancora_crm.chatbot_schedule" in query:
            return self.schedule_rows
        if "FROM ancora_crm.chatbot_holidays" in query:
            return self.holiday_rows
        return []

    async def _fetchval(self, query, *args):
        if self.fetchval_values:
            value = self.fetchval_values.pop(0)
            return value(query, *args) if callable(value) else value
        return 0

    async def _execute(self, query, *args):
        return self.execute_result

    def transaction(self):
        @asynccontextmanager
        async def _transaction():
            yield self

        return _transaction()


def _ensure_plugins_mounted():
    PluginRegistry._plugins.clear()
    register_all_plugins()
    existing_paths = {route.path for route in app.routes}
    for plugin in PluginRegistry.all_plugins():
        router = plugin.get_router()
        if not router or not router.routes:
            continue
        expected_paths = {f"/api/chatbot{route.path}" for route in router.routes if hasattr(route, "path")}
        if expected_paths.isdisjoint(existing_paths):
            app.include_router(router, prefix="/api/chatbot", tags=[f"plugin_{plugin.id}"])
            existing_paths.update(expected_paths)


@pytest.fixture(scope="session")
def test_app():
    _ensure_plugins_mounted()
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
def chatbot_headers():
    token = create_chatbot_access_token({"sub": "tester", "instance_id": 1})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_token():
    return create_access_token({"sub": "admin"})
