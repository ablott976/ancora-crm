from unittest.mock import AsyncMock

import pytest

from app.plugins.consent_forms import ConsentFormsPlugin, SCHEMA_SQL, services
from app.plugins.consent_forms import routes as consent_routes


@pytest.mark.asyncio
async def test_consent_plugin_registration_and_install():
    plugin = ConsentFormsPlugin()
    db = AsyncMock()

    await plugin.on_install(db, 1)
    assert plugin.dependencies == ["bookings"]
    db.execute.assert_awaited_once_with(SCHEMA_SQL)


@pytest.mark.asyncio
async def test_sign_consent_returns_none_when_record_missing():
    db = AsyncMock()
    db.fetchrow.return_value = None

    assert await services.sign_consent(db, 3) is None


@pytest.mark.asyncio
async def test_consent_routes_require_admin_auth(client):
    response = await client.get("/api/chatbot/api/plugins/consents/templates/1")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_template_route_returns_service_result(client, admin_headers, monkeypatch):
    monkeypatch.setattr(
        consent_routes.services,
        "create_template",
        AsyncMock(return_value={"id": 2, "name": "RGPD"}),
    )

    response = await client.post(
        "/api/chatbot/api/plugins/consents/templates",
        headers=admin_headers,
        json={"instance_id": 1, "name": "RGPD", "content_html": "<p>ok</p>"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "RGPD"


@pytest.mark.asyncio
async def test_sign_route_returns_404_for_unknown_record(client, admin_headers, monkeypatch):
    monkeypatch.setattr(consent_routes.services, "sign_consent", AsyncMock(return_value=None))

    response = await client.post(
        "/api/chatbot/api/plugins/consents/records/77/sign",
        headers=admin_headers,
        json={"signature_data": "sig"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Record not found"
