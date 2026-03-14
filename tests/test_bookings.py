from datetime import date
from unittest.mock import AsyncMock

import pytest

from app.plugins.bookings import BookingsPlugin, SCHEMA_SQL, services
from app.plugins.bookings import routes as booking_routes


@pytest.mark.asyncio
async def test_bookings_plugin_registration_and_install():
    plugin = BookingsPlugin()
    db = AsyncMock()

    await plugin.on_install(db, 1)

    assert plugin.id == "bookings"
    assert plugin.get_router() is not None
    assert len(plugin.get_tools()) == 6
    db.execute.assert_awaited_once_with(SCHEMA_SQL)


@pytest.mark.asyncio
async def test_create_appointment_rejects_conflicting_slot(monkeypatch):
    db = AsyncMock()
    db.fetchrow.return_value = {"duration_minutes": 60}
    monkeypatch.setattr(
        services,
        "get_booked_slots",
        AsyncMock(return_value=[{"start_time": "10:00", "end_time": "11:00"}]),
    )

    with pytest.raises(ValueError, match="Conflicto"):
        await services.create_appointment(
            db,
            1,
            professional_id=2,
            service_id=3,
            client_name="Ana",
            client_phone="600111222",
            appt_date=date(2025, 1, 10),
            start_time="10:30",
        )


@pytest.mark.asyncio
async def test_bookings_routes_require_chatbot_auth(client):
    response = await client.get("/api/chatbot/dashboard/1/bookings/professionals")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_appointment_route_uses_service(client, chatbot_headers, monkeypatch):
    create_mock = AsyncMock(return_value={"id": 9, "client_name": "Ana"})
    monkeypatch.setattr(booking_routes.svc, "create_appointment", create_mock)

    response = await client.post(
        "/api/chatbot/dashboard/1/bookings/appointments",
        headers=chatbot_headers,
        json={
            "professional_id": 2,
            "service_id": 3,
            "client_name": "Ana",
            "client_phone": "600111222",
            "date": "2025-01-10",
            "start_time": "10:00",
        },
    )

    assert response.status_code == 201
    assert response.json()["id"] == 9
    create_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_reschedule_route_translates_conflicts_to_409(client, chatbot_headers, monkeypatch):
    monkeypatch.setattr(
        booking_routes.svc,
        "reschedule_appointment",
        AsyncMock(side_effect=ValueError("slot ocupado")),
    )

    response = await client.post(
        "/api/chatbot/dashboard/1/bookings/appointments/5/reschedule",
        headers=chatbot_headers,
        json={"new_date": "2025-01-11", "new_start_time": "11:00"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "slot ocupado"


@pytest.mark.asyncio
async def test_create_appointment_route_validates_time_format(client, chatbot_headers):
    response = await client.post(
        "/api/chatbot/dashboard/1/bookings/appointments",
        headers=chatbot_headers,
        json={
            "professional_id": 2,
            "service_id": 3,
            "client_name": "Ana",
            "client_phone": "600111222",
            "date": "2025-01-10",
            "start_time": "1000",
        },
    )

    assert response.status_code == 422
