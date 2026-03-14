"""Plugin registry for Ancora CRM."""
from __future__ import annotations
from typing import Dict, List, Optional
from app.plugins.base import BasePlugin


class PluginRegistry:
    """Central registry of all available plugins."""

    _plugins: Dict[str, BasePlugin] = {}

    @classmethod
    def register(cls, plugin: BasePlugin):
        cls._plugins[plugin.id] = plugin

    @classmethod
    def get(cls, plugin_id: str) -> Optional[BasePlugin]:
        return cls._plugins.get(plugin_id)

    @classmethod
    def all_plugins(cls) -> List[BasePlugin]:
        return list(cls._plugins.values())

    @classmethod
    def get_plugin_info(cls) -> List[dict]:
        return [
            {
                "id": p.id,
                "name": p.name,
                "version": p.version,
                "description": p.description,
                "icon": p.icon,
                "dependencies": p.dependencies,
            }
            for p in cls._plugins.values()
        ]

    @classmethod
    async def get_enabled_plugins(cls, db, instance_id: int) -> List[BasePlugin]:
        rows = await db.fetch(
            "SELECT plugin_id FROM ancora_crm.instance_plugins "
            "WHERE instance_id = $1 AND enabled = true",
            instance_id,
        )
        enabled_ids = {r["plugin_id"] for r in rows}
        return [p for pid, p in cls._plugins.items() if pid in enabled_ids]


def register_all_plugins():
    """Import and register all available plugins."""
    # Level 0 - Core (always present)
    from app.plugins.bookings import BookingsPlugin
    from app.plugins.reminders import RemindersPlugin

    # Level 1 - No dependencies
    from app.plugins.closures import ClosuresPlugin
    from app.plugins.daily_menus import DailyMenusPlugin
    from app.plugins.broadcasts import BroadcastsPlugin
    from app.plugins.instagram_dm import InstagramDMPlugin
    from app.plugins.advanced_crm import AdvancedCRMPlugin
    from app.plugins.audio_transcription import AudioTranscriptionPlugin
    from app.plugins.restaurant_bookings import RestaurantBookingsPlugin
    from app.plugins.owner_agent import OwnerAgentPlugin

    # Level 2 - With dependencies
    from app.plugins.consent_forms import ConsentFormsPlugin
    from app.plugins.shift_view import ShiftViewPlugin
    from app.plugins.voice_agent import VoiceAgentPlugin

    PluginRegistry.register(BookingsPlugin())
    PluginRegistry.register(RemindersPlugin())
    PluginRegistry.register(ClosuresPlugin())
    PluginRegistry.register(DailyMenusPlugin())
    PluginRegistry.register(BroadcastsPlugin())
    PluginRegistry.register(InstagramDMPlugin())
    PluginRegistry.register(AdvancedCRMPlugin())
    PluginRegistry.register(AudioTranscriptionPlugin())
    PluginRegistry.register(RestaurantBookingsPlugin())
    PluginRegistry.register(OwnerAgentPlugin())
    PluginRegistry.register(ConsentFormsPlugin())
    PluginRegistry.register(ShiftViewPlugin())
    PluginRegistry.register(VoiceAgentPlugin())
