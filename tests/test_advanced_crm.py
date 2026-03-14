from unittest.mock import AsyncMock

import pytest

from app.plugins.advanced_crm import AdvancedCRMPlugin, SCHEMA_SQL, services
from app.plugins.advanced_crm import routes as crm_routes


@pytest.mark.asyncio
async def test_advanced_crm_plugin_registration_and_install():
    plugin = AdvancedCRMPlugin()
    db = AsyncMock()

    await plugin.on_install(db, 1)

    assert set(plugin.get_tool_handlers()) == {"lookup_customer", "get_customer_history"}
    db.execute.assert_awaited_once_with(SCHEMA_SQL)


@pytest.mark.asyncio
async def test_lookup_customer_returns_none_without_search_params():
    assert await services.lookup_customer(AsyncMock(), 1) is None


@pytest.mark.asyncio
async def test_crm_routes_require_admin_auth(client):
    response = await client.get("/api/chatbot/api/plugins/crm/profiles/1")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_profile_route_returns_404_when_missing(client, admin_headers, monkeypatch):
    monkeypatch.setattr(crm_routes.services, "list_profiles", AsyncMock(return_value=[]))

    response = await client.get("/api/chatbot/api/plugins/crm/profiles/1/10", headers=admin_headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "Profile not found"


@pytest.mark.asyncio
async def test_update_profile_route_returns_updated_profile(client, admin_headers, monkeypatch):
    monkeypatch.setattr(
        crm_routes.services,
        "update_profile",
        AsyncMock(return_value={"id": 10, "vip_status": True}),
    )

    response = await client.put(
        "/api/chatbot/api/plugins/crm/profiles/1/10",
        headers=admin_headers,
        json={"vip_status": True},
    )

    assert response.status_code == 200
    assert response.json()["vip_status"] is True
