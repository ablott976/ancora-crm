from datetime import date
from unittest.mock import AsyncMock

import pytest

from app.plugins.daily_menus import DailyMenusPlugin, SCHEMA_SQL, services
from app.plugins.daily_menus import routes as daily_routes


@pytest.mark.asyncio
async def test_daily_menus_plugin_registration_and_install():
    plugin = DailyMenusPlugin()
    db = AsyncMock()

    await plugin.on_install(db, 1)

    assert plugin.get_tools()
    db.execute.assert_awaited_once_with(SCHEMA_SQL)


@pytest.mark.asyncio
async def test_get_menu_for_date_returns_none_when_missing():
    db = AsyncMock()
    db.fetchrow.return_value = None

    result = await services.get_menu_for_date(db, 1, date(2025, 1, 10))

    assert result is None


@pytest.mark.asyncio
async def test_daily_menu_routes_require_chatbot_auth(client):
    response = await client.get("/api/chatbot/dashboard/1/daily-menus/menus")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_menu_route_returns_created_menu(client, chatbot_headers, monkeypatch):
    monkeypatch.setattr(
        daily_routes.svc,
        "create_menu",
        AsyncMock(return_value={"id": 11, "name": "Menu Ejecutivo", "items": []}),
    )

    response = await client.post(
        "/api/chatbot/dashboard/1/daily-menus/menus",
        headers=chatbot_headers,
        json={"date": "2025-01-10", "name": "Menu Ejecutivo", "price": 12.5, "is_active": True},
    )

    assert response.status_code == 201
    assert response.json()["id"] == 11


@pytest.mark.asyncio
async def test_get_menu_route_returns_404_when_missing(client, chatbot_headers, monkeypatch):
    monkeypatch.setattr(daily_routes.svc, "get_menu", AsyncMock(return_value=None))

    response = await client.get("/api/chatbot/dashboard/1/daily-menus/menus/999", headers=chatbot_headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "Menu no encontrado"


@pytest.mark.asyncio
async def test_create_menu_item_route_validates_required_fields(client, chatbot_headers):
    response = await client.post(
        "/api/chatbot/dashboard/1/daily-menus/menus/1/items",
        headers=chatbot_headers,
        json={"description": "sin nombre"},
    )

    assert response.status_code == 422
