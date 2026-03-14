"""Owner Agent plugin - Canal privado para el dueño del negocio."""
from app.plugins.base import BasePlugin
from app.plugins.owner_agent.routes import router as owner_router
from app.plugins.owner_agent.tools import OWNER_TOOLS, OWNER_TOOL_HANDLERS


class OwnerAgentPlugin(BasePlugin):
    id = "owner_agent"
    name = "Agente del Propietario"
    version = "1.0.0"
    dependencies = []
    description = "Canal privado WhatsApp para que el dueño consulte datos de su negocio"
    icon = "shield"

    def get_router(self):
        return owner_router

    def get_tools(self):
        return OWNER_TOOLS

    def get_tool_handlers(self):
        return OWNER_TOOL_HANDLERS

    def get_system_prompt_section(self, config: dict) -> str:
        return ""

    async def on_install(self, db, instance_id: int):
        await db.execute(SCHEMA_SQL)

    def get_frontend_routes(self):
        return [
            {"path": "owner-config", "label": "Config Propietario", "icon": "shield"},
        ]


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS ancora_crm.plugin_owner_config (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES ancora_crm.chatbot_instances(id) ON DELETE CASCADE,
    owner_phone VARCHAR(20) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    daily_summary_enabled BOOLEAN DEFAULT true,
    daily_summary_time VARCHAR(5) DEFAULT '21:00',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(instance_id)
);

CREATE TABLE IF NOT EXISTS ancora_crm.plugin_owner_queries (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES ancora_crm.chatbot_instances(id) ON DELETE CASCADE,
    query_text TEXT,
    response_text TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
"""
