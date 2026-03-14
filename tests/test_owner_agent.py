from unittest.mock import AsyncMock

import pytest

from app.plugins.owner_agent import OwnerAgentPlugin, SCHEMA_SQL, services
from app.plugins.owner_agent import routes as owner_routes


@pytest.mark.asyncio
async def test_owner_plugin_registration_and_install():
    plugin = OwnerAgentPlugin()
    db = AsyncMock()

    await plugin.on_install(db, 1)
    assert plugin.get_tool_handlers()["get_business_summary"]
    db.execute.assert_awaited_once_with(SCHEMA_SQL)


@pytest.mark.asyncio
async def test_get_daily_summary_handles_missing_bookings_table():
    db = AsyncMock()
    db.fetchval.side_effect = [5, 12, RuntimeError("bookings missing")]

    result = await services.get_daily_summary(db, 1)

    assert result["conversations"] == 5
    assert result["messages"] == 12
    assert result["new_bookings"] == 0


@pytest.mark.asyncio
async def test_owner_routes_require_admin_auth(client):
    response = await client.get("/api/chatbot/api/plugins/owner/config/1")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_config_route_returns_unconfigured_marker(client, admin_headers, monkeypatch):
    monkeypatch.setattr(owner_routes.services, "get_config", AsyncMock(return_value=None))

    response = await client.get("/api/chatbot/api/plugins/owner/config/1", headers=admin_headers)

    assert response.status_code == 200
    assert response.json() == {"configured": False}


@pytest.mark.asyncio
async def test_set_config_route_persists_owner_settings(client, admin_headers, monkeypatch):
    monkeypatch.setattr(
        owner_routes.services,
        "set_config",
        AsyncMock(return_value={"instance_id": 1, "owner_phone": "600111222"}),
    )

    response = await client.post(
        "/api/chatbot/api/plugins/owner/config",
        headers=admin_headers,
        json={"instance_id": 1, "owner_phone": "600111222", "daily_summary_enabled": True},
    )

    assert response.status_code == 200
    assert response.json()["owner_phone"] == "600111222"
