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
    assert len(plugin.get_tools()) == 4
    db.execute.assert_awaited_once_with(SCHEMA_SQL)


@pytest.mark.asyncio
async def test_check_availability_computes_remaining_capacity():
    db = AsyncMock()
    db.fetch.side_effect = [
        [{"total": 8}],
        [{"total": 20}],
    ]

    result = await services.check_availability(db, 1, date(2025, 1, 10), "21:00", 4)

    assert result["available_seats"] == 12
    assert result["can_book"] is True


@pytest.mark.asyncio
async def test_restaurant_routes_require_admin_auth(client):
    response = await client.get("/api/chatbot/api/plugins/restaurant/zones/1")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_zone_route_returns_created_zone(client, admin_headers, monkeypatch):
    monkeypatch.setattr(
        restaurant_routes.services,
        "create_zone",
        AsyncMock(return_value={"id": 5, "name": "Terraza", "capacity": 30}),
    )

    response = await client.post(
        "/api/chatbot/api/plugins/restaurant/zones",
        headers=admin_headers,
        json={"instance_id": 1, "name": "Terraza", "capacity": 30},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Terraza"


@pytest.mark.asyncio
async def test_create_zone_route_validates_required_fields(client, admin_headers):
    response = await client.post(
        "/api/chatbot/api/plugins/restaurant/zones",
        headers=admin_headers,
        json={"instance_id": 1, "capacity": 20},
    )

    assert response.status_code == 422
