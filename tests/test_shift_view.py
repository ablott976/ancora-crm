from datetime import date
from unittest.mock import AsyncMock

import pytest

from app.plugins.shift_view import ShiftViewPlugin, SCHEMA_SQL, services
from app.plugins.shift_view import routes as shift_routes


@pytest.mark.asyncio
async def test_shift_view_plugin_registration_and_install():
    plugin = ShiftViewPlugin()
    db = AsyncMock()

    await plugin.on_install(db, 1)
    assert plugin.get_tool_handlers()["get_professional_agenda"]
    db.execute.assert_awaited_once_with(SCHEMA_SQL)


@pytest.mark.asyncio
async def test_get_day_agenda_returns_day_off_payload():
    db = AsyncMock()
    db.fetch.return_value = []
    db.fetchrow.return_value = {"is_off": True, "reason": "Vacaciones"}

    result = await services.get_day_agenda(db, 1, 3, date(2025, 1, 10))

    assert result["is_off"] is True
    assert result["appointments"] == []


@pytest.mark.asyncio
async def test_shift_routes_require_admin_auth(client):
    response = await client.get("/api/chatbot/api/plugins/shifts/1")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_shift_route_calls_service(client, admin_headers, monkeypatch):
    monkeypatch.setattr(
        shift_routes.services,
        "set_shift",
        AsyncMock(return_value={"id": 1, "day_of_week": 1}),
    )

    response = await client.post(
        "/api/chatbot/api/plugins/shifts/",
        headers=admin_headers,
        json={
            "instance_id": 1,
            "professional_id": 2,
            "day_of_week": 1,
            "start_time": "09:00",
            "end_time": "17:00",
        },
    )

    assert response.status_code == 200
    assert response.json()["day_of_week"] == 1


@pytest.mark.asyncio
async def test_get_agenda_route_parses_date_string(client, admin_headers, monkeypatch):
    agenda_mock = AsyncMock(return_value={"date": "2025-01-10", "appointments": []})
    monkeypatch.setattr(shift_routes.services, "get_day_agenda", agenda_mock)

    response = await client.get(
        "/api/chatbot/api/plugins/shifts/agenda/1/2?date_str=2025-01-10",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["date"] == "2025-01-10"
    agenda_mock.assert_awaited_once()
