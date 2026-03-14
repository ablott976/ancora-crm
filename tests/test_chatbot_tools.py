import json
from unittest.mock import AsyncMock

import pytest
from google.genai import types

from app.plugins.advanced_crm.tools import CRM_TOOL_HANDLERS, CRM_TOOLS
from app.plugins.bookings.tools import BOOKING_TOOL_HANDLERS, BOOKING_TOOLS
from app.plugins.closures.tools import CLOSURE_TOOL_HANDLERS, CLOSURE_TOOLS
from app.plugins.consent_forms.tools import CONSENT_TOOL_HANDLERS, CONSENT_TOOLS
from app.plugins.daily_menus.tools import DAILY_MENU_TOOL_HANDLERS, DAILY_MENU_TOOLS
from app.plugins.owner_agent.tools import OWNER_TOOL_HANDLERS, OWNER_TOOLS
from app.plugins.restaurant_bookings.tools import RESTAURANT_TOOL_HANDLERS, RESTAURANT_TOOLS
from app.plugins.shift_view.tools import SHIFT_TOOL_HANDLERS, SHIFT_TOOLS


ALL_TOOLSETS = [
    (BOOKING_TOOLS, BOOKING_TOOL_HANDLERS),
    (CLOSURE_TOOLS, CLOSURE_TOOL_HANDLERS),
    (DAILY_MENU_TOOLS, DAILY_MENU_TOOL_HANDLERS),
    (CRM_TOOLS, CRM_TOOL_HANDLERS),
    (OWNER_TOOLS, OWNER_TOOL_HANDLERS),
    (CONSENT_TOOLS, CONSENT_TOOL_HANDLERS),
    (RESTAURANT_TOOLS, RESTAURANT_TOOL_HANDLERS),
    (SHIFT_TOOLS, SHIFT_TOOL_HANDLERS),
]


def test_all_plugin_tools_are_valid_function_declarations():
    for tools, handlers in ALL_TOOLSETS:
        for declaration in tools:
            assert isinstance(declaration, types.FunctionDeclaration)
            assert declaration.name in handlers
            assert declaration.parameters is not None


@pytest.mark.asyncio
async def test_booking_agendar_handler_returns_success_json(monkeypatch):
    monkeypatch.setattr(
        "app.plugins.bookings.services.create_appointment",
        AsyncMock(return_value={"id": 1}),
    )

    payload = await BOOKING_TOOL_HANDLERS["AGENDAR"](
        {
            "professional_id": 1,
            "service_id": 2,
            "client_name": "Ana",
            "client_phone": "600",
            "fecha": "2025-01-10",
            "hora": "10:00",
        },
        {"db": object(), "instance_id": 1, "contact_id": 7},
    )

    body = json.loads(payload)
    assert body["success"] is True
    assert body["appointment"]["id"] == 1


@pytest.mark.asyncio
async def test_booking_agendar_handler_returns_graceful_error(monkeypatch):
    monkeypatch.setattr(
        "app.plugins.bookings.services.create_appointment",
        AsyncMock(side_effect=ValueError("ocupado")),
    )

    payload = await BOOKING_TOOL_HANDLERS["AGENDAR"](
        {
            "professional_id": 1,
            "service_id": 2,
            "client_name": "Ana",
            "client_phone": "600",
            "fecha": "2025-01-10",
            "hora": "10:00",
        },
        {"db": object(), "instance_id": 1},
    )

    assert json.loads(payload) == {"success": False, "error": "ocupado"}


@pytest.mark.asyncio
async def test_closures_handler_returns_json(monkeypatch):
    monkeypatch.setattr(
        "app.plugins.closures.services.check_closures",
        AsyncMock(return_value={"closed": True}),
    )

    payload = await CLOSURE_TOOL_HANDLERS["check_closures"](
        {"date": "2025-01-10"},
        {"db": object(), "instance_id": 1},
    )

    assert json.loads(payload)["closed"] is True


@pytest.mark.asyncio
async def test_daily_menu_handler_handles_missing_menu(monkeypatch):
    monkeypatch.setattr(
        "app.plugins.daily_menus.services.get_menu_for_date",
        AsyncMock(return_value=None),
    )

    payload = await DAILY_MENU_TOOL_HANDLERS["get_menu_for_date"](
        {"date": "2025-01-10"},
        {"db": object(), "instance_id": 1},
    )

    assert json.loads(payload) == {"available": False, "date": "2025-01-10"}


@pytest.mark.asyncio
async def test_crm_lookup_handler_handles_missing_customer(monkeypatch):
    monkeypatch.setattr("app.plugins.advanced_crm.services.lookup_customer", AsyncMock(return_value=None))

    payload = await CRM_TOOL_HANDLERS["lookup_customer"](
        {"phone": "600"},
        {"db": object(), "instance_id": 1},
    )

    assert json.loads(payload) == {"found": False}


@pytest.mark.asyncio
async def test_owner_summary_handler_returns_summary(monkeypatch):
    monkeypatch.setattr(
        "app.plugins.owner_agent.services.get_daily_summary",
        AsyncMock(return_value={"messages": 5}),
    )

    payload = await OWNER_TOOL_HANDLERS["get_business_summary"]({}, {"db": object(), "instance_id": 1})

    assert json.loads(payload)["messages"] == 5


@pytest.mark.asyncio
async def test_consent_handler_counts_pending_consents(monkeypatch):
    monkeypatch.setattr(
        "app.plugins.consent_forms.services.pending_for_phone",
        AsyncMock(return_value=[{"id": 1}, {"id": 2}]),
    )

    payload = await CONSENT_TOOL_HANDLERS["check_pending_consents"](
        {"phone": "600"},
        {"db": object(), "instance_id": 1},
    )

    assert json.loads(payload)["pending_count"] == 2


@pytest.mark.asyncio
async def test_restaurant_cancel_handler_returns_boolean_result(monkeypatch):
    monkeypatch.setattr(
        "app.plugins.restaurant_bookings.services.cancel_reservation",
        AsyncMock(return_value=False),
    )

    payload = await RESTAURANT_TOOL_HANDLERS["cancel_restaurant_reservation"](
        {"reservation_id": 8},
        {"db": object(), "instance_id": 1},
    )

    assert json.loads(payload) == {"cancelled": False}


@pytest.mark.asyncio
async def test_shift_agenda_handler_returns_valid_json(monkeypatch):
    monkeypatch.setattr(
        "app.plugins.shift_view.services.get_day_agenda",
        AsyncMock(return_value={"appointments": []}),
    )

    payload = await SHIFT_TOOL_HANDLERS["get_professional_agenda"](
        {"professional_id": 2, "date": "2025-01-10"},
        {"db": object(), "instance_id": 1},
    )

    assert json.loads(payload) == {"appointments": []}
