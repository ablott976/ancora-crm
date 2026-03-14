from unittest.mock import AsyncMock

import pytest

from app.plugins.reminders import RemindersPlugin, SCHEMA_SQL, services
from app.plugins.reminders import routes as reminder_routes


@pytest.mark.asyncio
async def test_reminders_plugin_registration_and_install():
    plugin = RemindersPlugin()
    db = AsyncMock()

    await plugin.on_install(db, 1)

    assert plugin.dependencies == ["bookings"]
    db.execute.assert_awaited_once_with(SCHEMA_SQL)


def test_render_template_replaces_known_placeholders():
    rendered = services.render_template(
        "Hola {nombre_cliente} el {fecha} a las {hora} con {profesional}",
        {
            "client_name": "Ana",
            "date": "2025-01-10",
            "start_time": "10:00",
            "professional_name": "Luis",
        },
    )

    assert rendered == "Hola Ana el 2025-01-10 a las 10:00 con Luis"


@pytest.mark.asyncio
async def test_reminders_routes_require_chatbot_auth(client):
    response = await client.get("/api/chatbot/dashboard/1/reminders/templates")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_template_route_returns_created_template(client, chatbot_headers, monkeypatch):
    monkeypatch.setattr(
        reminder_routes.svc,
        "create_template",
        AsyncMock(return_value={"id": 4, "name": "24h"}),
    )

    response = await client.post(
        "/api/chatbot/dashboard/1/reminders/templates",
        headers=chatbot_headers,
        json={
            "name": "24h",
            "type": "pre",
            "hours_before": 24,
            "template_text": "Hola",
            "send_to": "client",
        },
    )

    assert response.status_code == 201
    assert response.json()["name"] == "24h"


@pytest.mark.asyncio
async def test_update_template_route_returns_404_for_missing_record(client, chatbot_headers, monkeypatch):
    monkeypatch.setattr(reminder_routes.svc, "update_template", AsyncMock(return_value=None))

    response = await client.put(
        "/api/chatbot/dashboard/1/reminders/templates/55",
        headers=chatbot_headers,
        json={"template_text": "Nuevo"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Plantilla no encontrada"


@pytest.mark.asyncio
async def test_trigger_check_route_returns_created_count(client, chatbot_headers, monkeypatch):
    monkeypatch.setattr(reminder_routes.svc, "check_and_send_reminders", AsyncMock(return_value=3))

    response = await client.post("/api/chatbot/dashboard/1/reminders/check", headers=chatbot_headers)

    assert response.status_code == 200
    assert response.json() == {"checked": True, "reminders_created": 3}
