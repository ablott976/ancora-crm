"""Advanced CRM plugin - Perfiles de cliente avanzados."""
from app.plugins.base import BasePlugin
from app.plugins.advanced_crm.routes import router as crm_router
from app.plugins.advanced_crm.tools import CRM_TOOLS, CRM_TOOL_HANDLERS


class AdvancedCRMPlugin(BasePlugin):
    id = "advanced_crm"
    name = "CRM Avanzado"
    version = "1.0.0"
    dependencies = []
    description = "Perfiles de cliente, historial de visitas, segmentación y tags"
    icon = "user-check"

    def get_router(self):
        return crm_router

    def get_tools(self):
        return CRM_TOOLS

    def get_tool_handlers(self):
        return CRM_TOOL_HANDLERS

    def get_system_prompt_section(self, config: dict) -> str:
        return (
            "\n\n## CRM AVANZADO\n"
            "Puedes consultar el perfil de un cliente por teléfono o código de cliente. "
            "Esto incluye: historial de visitas, gasto total, tags, estado VIP y notas. "
            "Usa estas herramientas para personalizar la atención al cliente."
        )

    async def on_install(self, db, instance_id: int):
        await db.execute(SCHEMA_SQL)

    def get_frontend_routes(self):
        return [
            {"path": "crm-profiles", "label": "Clientes CRM", "icon": "user-check"},
        ]


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS ancora_crm.plugin_crm_customer_profiles (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES ancora_crm.chatbot_instances(id) ON DELETE CASCADE,
    contact_id INTEGER REFERENCES ancora_crm.chatbot_contacts(id) ON DELETE SET NULL,
    customer_code VARCHAR(20),
    phone VARCHAR(20),
    name VARCHAR(200),
    tags TEXT[] DEFAULT '{}',
    notes TEXT,
    total_visits INTEGER DEFAULT 0,
    total_spent NUMERIC(10,2) DEFAULT 0,
    last_visit_at TIMESTAMPTZ,
    vip_status BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(instance_id, customer_code),
    UNIQUE(instance_id, phone)
);

CREATE TABLE IF NOT EXISTS ancora_crm.plugin_crm_interactions (
    id SERIAL PRIMARY KEY,
    profile_id INTEGER NOT NULL REFERENCES ancora_crm.plugin_crm_customer_profiles(id) ON DELETE CASCADE,
    interaction_type VARCHAR(50) NOT NULL,
    description TEXT,
    amount NUMERIC(10,2),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_crm_profiles_instance ON ancora_crm.plugin_crm_customer_profiles(instance_id);
CREATE INDEX IF NOT EXISTS idx_crm_profiles_phone ON ancora_crm.plugin_crm_customer_profiles(phone);
CREATE INDEX IF NOT EXISTS idx_crm_interactions_profile ON ancora_crm.plugin_crm_interactions(profile_id, created_at DESC);
"""
