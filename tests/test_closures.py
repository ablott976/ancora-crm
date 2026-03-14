from datetime import date
from unittest.mock import AsyncMock

import pytest

from app.plugins.closures import ClosuresPlugin, SCHEMA_SQL, services
from app.plugins.closures import routes as closure_routes


@pytest.mark.asyncio
async def test_closures_plugin_registration_and_install():
    plugin = ClosuresPlugin()
    db = AsyncMock()

    await plugin.on_install(db, 1)

    assert plugin.get_tool_handlers()["check_closures"]
    db.execute.assert_awaited_once_with(SCHEMA_SQL)


@pytest.mark.asyncio
async def test_create_closure_rejects_inverted_dates():
    with pytest.raises(ValueError, match="fecha de fin"):
        await services.create_closure(
            AsyncMock(),
            1,
            start_date=date(2025, 1, 10),
            end_date=date(2025, 1, 9),
            reason="vacaciones",
        )


@pytest.mark.asyncio
async def test_closures_routes_require_chatbot_auth(client):
    response = await client.get("/api/chatbot/dashboard/1/closures")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_closure_route_maps_validation_errors(client, chatbot_headers, monkeypatch):
    monkeypatch.setattr(
        closure_routes.svc,
        "create_closure",
        AsyncMock(side_effect=ValueError("invalid range")),
    )

    response = await client.post(
        "/api/chatbot/dashboard/1/closures",
        headers=chatbot_headers,
        json={
            "start_date": "2025-01-10",
            "end_date": "2025-01-09",
            "reason": "test",
            "closure_type": "holiday",
            "affects_all_services": True,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "invalid range"


@pytest.mark.asyncio
async def test_get_closure_route_returns_404_when_missing(client, chatbot_headers, monkeypatch):
    monkeypatch.setattr(closure_routes.svc, "get_closure", AsyncMock(return_value=None))

    response = await client.get("/api/chatbot/dashboard/1/closures/99", headers=chatbot_headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "Cierre no encontrado"
