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
    response = await client.get("/api/chatbot/dashboard/1/broadcasts/campaigns")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_campaign_route_works_with_auth(client, chatbot_headers, monkeypatch):
    monkeypatch.setattr(
        broadcast_routes.services,
        "create_campaign",
        AsyncMock(return_value={"id": 3, "name": "Promo"}),
    )

    response = await client.post(
        "/api/chatbot/dashboard/1/broadcasts/campaigns",
        headers=chatbot_headers,
        json={"name": "Promo", "message_template": "Hola", "target_tags": ["vip"]},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Promo"


@pytest.mark.asyncio
async def test_delete_campaign_route_rejects_non_draft_campaigns(client, chatbot_headers, monkeypatch):
    monkeypatch.setattr(broadcast_routes.services, "delete_campaign", AsyncMock(return_value=False))

    response = await client.delete(
        "/api/chatbot/dashboard/1/broadcasts/campaigns/22",
        headers=chatbot_headers,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Only draft campaigns can be deleted"


@pytest.mark.asyncio
async def test_send_campaign_updates_totals_and_logs(monkeypatch):
    db = AsyncMock()
    db.fetchrow.side_effect = [
        {"id": 4, "instance_id": 1, "status": "draft", "message_template": "Hola", "target_tags": []},
        {"whatsapp_access_token": "token", "phone_number_id": "123"},
    ]
    db.fetch.return_value = [
        {"phone": "34611111111", "name": "Ana"},
        {"phone": "34622222222", "name": "Luis"},
    ]

    monkeypatch.setattr(services, "send_message", AsyncMock(side_effect=[{"messages": [{"id": "wamid.1"}]}, None]))

    result = await services.send_campaign(db, 1, 4)

    assert result["total_recipients"] == 2
    assert result["total_sent"] == 1
    assert result["total_failed"] == 1
    assert db.execute.await_count == 4
