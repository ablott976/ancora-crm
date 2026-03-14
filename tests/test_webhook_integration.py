from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.chatbot_engine import ChatbotEngine


@pytest.mark.asyncio
async def test_whatsapp_webhook_batches_message_for_active_instance(client, mock_db, monkeypatch):
    batch_mock = AsyncMock()
    monkeypatch.setattr("app.routes.chatbot_webhook.add_to_batch", batch_mock)
    mock_db.instance_lookup = {"id": 42, "is_active": True}

    payload = {
        "messaging_product": "whatsapp",
        "metadata": {"phone_number_id": "12345"},
        "contacts": [{"wa_id": "34600111222"}],
        "messages": [{"id": "wamid.1", "text": {"body": "hola"}}],
        "field": "messages",
    }

    response = await client.post("/api/chatbot/webhook/whatsapp", json=payload)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    batch_mock.assert_awaited_once_with(42, payload)


@pytest.mark.asyncio
async def test_whatsapp_webhook_rejects_invalid_json_payload(client):
    response = await client.post(
        "/api/chatbot/webhook/whatsapp",
        content="{",
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid JSON payload"


@pytest.mark.asyncio
async def test_chatbot_engine_injects_plugin_prompt_sections(mock_db):
    mock_db.enabled_plugins = {"bookings", "closures"}
    mock_db.business_info = {"business_name": "Ancora"}
    mock_db.schedule_rows = [{"dia_semana": 0, "hora_apertura": "09:00", "hora_cierre": "18:00", "abierto": True}]
    mock_db.holiday_rows = []

    prompt = await ChatbotEngine(1, mock_db, {"google_api_key": ""}).get_system_prompt()

    assert "## RESERVAS" in prompt
    assert "## CIERRES" in prompt


@pytest.mark.asyncio
async def test_generate_response_collects_tools_from_enabled_plugins(mock_db, monkeypatch):
    mock_db.enabled_plugins = {"bookings", "closures"}
    engine = ChatbotEngine(1, mock_db, {"google_api_key": "fake-key"})
    monkeypatch.setattr(engine, "_maybe_summarize_old_messages", AsyncMock())
    monkeypatch.setattr(engine, "get_system_prompt", AsyncMock(return_value="system"))
    monkeypatch.setattr(engine, "get_conversation_history", AsyncMock(return_value=[]))

    captured = {}

    class FakeModels:
        def generate_content(self, model, contents, config):
            captured["tool_names"] = [fd.name for tool in (config.tools or []) for fd in tool.function_declarations]
            return SimpleNamespace(
                candidates=[
                    SimpleNamespace(
                        content=SimpleNamespace(parts=[SimpleNamespace(text="ok", function_call=None)])
                    )
                ]
            )

    class FakeClient:
        def __init__(self, api_key):
            self.models = FakeModels()

    monkeypatch.setattr("app.services.chatbot_engine.genai.Client", FakeClient)

    response = await engine.generate_response(99, "hola")

    assert response == "ok"
    assert "DISPONIBILIDAD" in captured["tool_names"]
    assert "check_closures" in captured["tool_names"]
