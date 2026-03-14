from unittest.mock import AsyncMock

import pytest

from app.plugins.audio_transcription import AudioTranscriptionPlugin, SCHEMA_SQL, services
from app.plugins.audio_transcription import routes as audio_routes


@pytest.mark.asyncio
async def test_audio_plugin_registration_and_install():
    plugin = AudioTranscriptionPlugin()
    db = AsyncMock()

    await plugin.on_install(db, 1)
    db.execute.assert_awaited_once_with(SCHEMA_SQL)


@pytest.mark.asyncio
async def test_get_stats_returns_zero_dict_when_db_has_no_row():
    db = AsyncMock()
    db.fetchrow.return_value = None

    result = await services.get_stats(db, 1)

    assert result == {"total": 0, "total_duration": 0, "total_tokens": 0}


@pytest.mark.asyncio
async def test_audio_routes_require_admin_auth(client):
    response = await client.get("/api/chatbot/api/plugins/audio/transcriptions/1")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_transcriptions_route_passes_optional_phone_filter(client, admin_headers, monkeypatch):
    list_mock = AsyncMock(return_value=[{"id": 1, "contact_phone": "600"}])
    monkeypatch.setattr(audio_routes.services, "list_transcriptions", list_mock)

    response = await client.get(
        "/api/chatbot/api/plugins/audio/transcriptions/1?phone=600",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()[0]["id"] == 1
    list_mock.assert_awaited_once()
