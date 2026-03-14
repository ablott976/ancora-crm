from unittest.mock import AsyncMock

import pytest

from app.plugins.voice_agent import VoiceAgentPlugin, SCHEMA_SQL, services
from app.plugins.voice_agent import routes as voice_routes


@pytest.mark.asyncio
async def test_voice_plugin_registration_and_install():
    plugin = VoiceAgentPlugin()
    db = AsyncMock()

    await plugin.on_install(db, 1)
    db.execute.assert_awaited_once_with(SCHEMA_SQL)


@pytest.mark.asyncio
async def test_get_config_hides_credentials():
    db = AsyncMock()
    db.fetchrow.return_value = {"provider": "twilio", "api_key": "key", "api_secret": "secret"}

    result = await services.get_config(db, 1)

    assert "api_key" not in result
    assert "api_secret" not in result
    assert result["credentials_set"] is True


@pytest.mark.asyncio
async def test_voice_routes_require_admin_auth(client):
    response = await client.get("/api/chatbot/api/plugins/voice/config/1")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_set_config_route_uses_service(client, admin_headers, monkeypatch):
    monkeypatch.setattr(
        voice_routes.services,
        "upsert_config",
        AsyncMock(return_value={"instance_id": 1, "provider": "twilio"}),
    )

    response = await client.post(
        "/api/chatbot/api/plugins/voice/config",
        headers=admin_headers,
        json={"instance_id": 1, "provider": "twilio", "max_call_duration_seconds": 300},
    )

    assert response.status_code == 200
    assert response.json()["provider"] == "twilio"


@pytest.mark.asyncio
async def test_list_calls_route_returns_service_data(client, admin_headers, monkeypatch):
    monkeypatch.setattr(voice_routes.services, "list_calls", AsyncMock(return_value=[{"id": 1, "status": "completed"}]))

    response = await client.get("/api/chatbot/api/plugins/voice/calls/1", headers=admin_headers)

    assert response.status_code == 200
    assert response.json()[0]["status"] == "completed"
