from unittest.mock import AsyncMock

import pytest

from app.plugins.instagram_dm import InstagramDMPlugin, SCHEMA_SQL, services
from app.plugins.instagram_dm import routes as ig_routes


@pytest.mark.asyncio
async def test_instagram_plugin_registration_and_install():
    plugin = InstagramDMPlugin()
    db = AsyncMock()

    await plugin.on_install(db, 1)
    db.execute.assert_awaited_once_with(SCHEMA_SQL)


@pytest.mark.asyncio
async def test_get_config_service_returns_none_for_unconfigured_instance():
    db = AsyncMock()
    db.fetchrow.return_value = None

    assert await services.get_config(db, 1) is None


@pytest.mark.asyncio
async def test_instagram_routes_require_admin_auth(client):
    response = await client.get("/api/chatbot/api/plugins/instagram-dm/config/1")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_config_route_hides_access_token(client, admin_headers, monkeypatch):
    monkeypatch.setattr(
        ig_routes.services,
        "get_config",
        AsyncMock(return_value={"instance_id": 1, "ig_access_token": "secret", "ig_username": "ancora"}),
    )

    response = await client.get("/api/chatbot/api/plugins/instagram-dm/config/1", headers=admin_headers)

    assert response.status_code == 200
    body = response.json()
    assert "ig_access_token" not in body
    assert body["configured"] is True
    assert body["token_set"] is True


@pytest.mark.asyncio
async def test_resolve_route_returns_404_for_missing_conversation(client, admin_headers, monkeypatch):
    monkeypatch.setattr(ig_routes.services, "resolve_conversation", AsyncMock(return_value=False))

    response = await client.post(
        "/api/chatbot/api/plugins/instagram-dm/conversations/9/resolve",
        headers=admin_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Conversation not found"
