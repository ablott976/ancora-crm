import pytest
from unittest.mock import AsyncMock

from app.plugins import PluginRegistry, register_all_plugins


EXPECTED_PLUGINS = {
    "bookings": {"name": "Reservas/Citas", "dependencies": []},
    "reminders": {"name": "Recordatorios", "dependencies": ["bookings"]},
    "closures": {"name": "Cierres", "dependencies": []},
    "daily_menus": {"name": "Menus Diarios", "dependencies": []},
    "broadcasts": {"name": "Campañas WhatsApp", "dependencies": []},
    "instagram_dm": {"name": "Instagram DM", "dependencies": []},
    "advanced_crm": {"name": "CRM Avanzado", "dependencies": []},
    "audio_transcription": {"name": "Transcripción de Audio", "dependencies": []},
    "restaurant_bookings": {"name": "Reservas Restaurante", "dependencies": []},
    "owner_agent": {"name": "Agente del Propietario", "dependencies": []},
    "consent_forms": {"name": "Consentimientos", "dependencies": ["bookings"]},
    "shift_view": {"name": "Vista de Turnos", "dependencies": ["bookings"]},
    "voice_agent": {"name": "Agente de Voz", "dependencies": ["bookings"]},
}


def test_register_all_plugins_exposes_all_expected_plugins():
    PluginRegistry._plugins.clear()
    register_all_plugins()

    assert set(PluginRegistry._plugins) == set(EXPECTED_PLUGINS)
    info = {plugin["id"]: plugin for plugin in PluginRegistry.get_plugin_info()}

    for plugin_id, expected in EXPECTED_PLUGINS.items():
        plugin = PluginRegistry.get(plugin_id)
        assert plugin is not None
        assert plugin.id == plugin_id
        assert plugin.name == expected["name"]
        assert plugin.version == "1.0.0"
        assert plugin.dependencies == expected["dependencies"]
        assert info[plugin_id]["name"] == expected["name"]
        assert info[plugin_id]["dependencies"] == expected["dependencies"]
        assert plugin.get_router() is not None
        assert isinstance(plugin.get_tools(), list)
        assert isinstance(plugin.get_tool_handlers(), dict)


@pytest.mark.asyncio
async def test_registry_returns_enabled_plugins_from_database():
    PluginRegistry._plugins.clear()
    register_all_plugins()
    db = AsyncMock()
    db.fetch.return_value = [{"plugin_id": "bookings"}, {"plugin_id": "closures"}]

    enabled = await PluginRegistry.get_enabled_plugins(db, 1)

    assert {plugin.id for plugin in enabled} == {"bookings", "closures"}
    db.fetch.assert_awaited_once()
