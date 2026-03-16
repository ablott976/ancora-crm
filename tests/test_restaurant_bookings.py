from datetime import date
from unittest.mock import AsyncMock

import pytest

from app.plugins.restaurant_bookings import RestaurantBookingsPlugin, SCHEMA_SQL, services
from app.plugins.restaurant_bookings import routes as restaurant_routes


@pytest.mark.asyncio
async def test_restaurant_plugin_registration_and_install():
    plugin = RestaurantBookingsPlugin()
    db = AsyncMock()

    await plugin.on_install(db, 1)

    assert plugin.id == "restaurant_bookings"
    assert len(plugin.get_tools()) == 4
    db.execute.assert_awaited_once_with(SCHEMA_SQL)


@pytest.mark.asyncio
async def test_check_availability_computes_remaining_capacity():
    db = AsyncMock()
    db.fetchval.side_effect = [8, 20]

    result = await services.check_availability(db, 1, date(2025, 1, 10), "21:00", 4)

    assert result["available_seats"] == 12
    assert result["can_book"] is True


@pytest.mark.asyncio
async def test_create_reservation_rejects_zone_over_capacity():
    db = AsyncMock()
    db.fetchrow.side_effect = [{"id": 3, "instance_id": 1, "capacity": 4, "is_active": True}]
    db.fetchval.return_value = 3

    with pytest.raises(ValueError, match="capacidad suficiente en la zona"):
        await services.create_reservation(
            db,
            1,
            client_name="Ana",
            client_phone="600111222",
            target_date=date(2025, 1, 10),
            time="21:00",
            party_size=2,
            zone_id=3,
        )


@pytest.mark.asyncio
async def test_confirm_reservation_rejects_invalid_transition():
    db = AsyncMock()
    db.fetchrow.return_value = {"id": 4, "instance_id": 1, "status": "cancelada"}

    with pytest.raises(ValueError, match="cancelada a confirmada"):
        await services.confirm_reservation(db, 1, 4)


@pytest.mark.asyncio
async def test_restaurant_routes_require_chatbot_auth(client):
    response = await client.post("/api/chatbot/dashboard/1/restaurant/zones", json={"name": "Terraza", "capacity": 20})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_zone_route_returns_created_zone(client, chatbot_headers, monkeypatch):
    monkeypatch.setattr(
        restaurant_routes.svc,
        "create_zone",
        AsyncMock(return_value={"id": 5, "name": "Terraza", "capacity": 30}),
    )

    response = await client.post(
        "/api/chatbot/dashboard/1/restaurant/zones",
        headers=chatbot_headers,
        json={"name": "Terraza", "capacity": 30},
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Terraza"


@pytest.mark.asyncio
async def test_create_reservation_route_translates_conflicts_to_409(client, chatbot_headers, monkeypatch):
    monkeypatch.setattr(
        restaurant_routes.svc,
        "create_reservation",
        AsyncMock(side_effect=ValueError("La mesa ya está reservada en esa franja")),
    )

    response = await client.post(
        "/api/chatbot/dashboard/1/restaurant/reservations",
        headers=chatbot_headers,
        json={
            "client_name": "Ana",
            "client_phone": "600111222",
            "date": "2025-01-10",
            "time": "21:00",
            "party_size": 4,
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "La mesa ya está reservada en esa franja"


@pytest.mark.asyncio
async def test_create_zone_route_validates_required_fields(client, chatbot_headers):
    response = await client.post(
        "/api/chatbot/dashboard/1/restaurant/zones",
        headers=chatbot_headers,
        json={"capacity": 20},
    )

    assert response.status_code == 422
