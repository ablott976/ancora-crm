from unittest.mock import AsyncMock

import pytest

from app.plugins.broadcasts import BroadcastsPlugin, SCHEMA_SQL, services
from app.plugins.broadcasts import routes as broadcast_routes


@pytest.mark.asyncio
async def test_broadcasts_plugin_registration_and_install():
    plugin = BroadcastsPlugin()
    db = AsyncMock()

    await plugin.on_install(db, 1)

    assert plugin.id == "broadcasts"
    db.execute.assert_awaited_once_with(SCHEMA_SQL)


@pytest.mark.asyncio
async def test_delete_campaign_returns_false_when_db_deletes_nothing():
    db = AsyncMock()
    db.execute.return_value = "DELETE 0"

    assert await services.delete_campaign(db, 1, 10) is False


@pytest.mark.asyncio
async def test_broadcast_routes_require_admin_auth(client):
    response = await client.get("/api/chatbot/api/plugins/broadcasts/campaigns/1")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_campaign_route_works_with_auth(client, admin_headers, monkeypatch):
    monkeypatch.setattr(
        broadcast_routes.services,
        "create_campaign",
        AsyncMock(return_value={"id": 3, "name": "Promo"}),
    )

    response = await client.post(
        "/api/chatbot/api/plugins/broadcasts/campaigns",
        headers=admin_headers,
        json={"instance_id": 1, "name": "Promo", "message_template": "Hola", "target_tags": ["vip"]},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Promo"


@pytest.mark.asyncio
async def test_delete_campaign_route_rejects_non_draft_campaigns(client, admin_headers, monkeypatch):
    monkeypatch.setattr(broadcast_routes.services, "delete_campaign", AsyncMock(return_value=False))

    response = await client.delete(
        "/api/chatbot/api/plugins/broadcasts/campaigns/1/22",
        headers=admin_headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Only draft campaigns can be deleted"
