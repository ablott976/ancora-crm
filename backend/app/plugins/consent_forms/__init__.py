"""Consent Forms plugin - Formularios de consentimiento GDPR."""
from app.plugins.base import BasePlugin
from app.plugins.consent_forms.routes import router as consent_router
from app.plugins.consent_forms.tools import CONSENT_TOOLS, CONSENT_TOOL_HANDLERS


class ConsentFormsPlugin(BasePlugin):
    id = "consent_forms"
    name = "Consentimientos"
    version = "1.0.0"
    dependencies = ["bookings"]
    description = "Formularios de consentimiento informado vinculados a citas (GDPR/Sanidad)"
    icon = "file-check"

    def get_router(self):
        return consent_router

    def get_tools(self):
        return CONSENT_TOOLS

    def get_tool_handlers(self):
        return CONSENT_TOOL_HANDLERS

    def get_system_prompt_section(self, config: dict) -> str:
        return (
            "\n\n## CONSENTIMIENTOS\n"
            "Puedes consultar si un cliente tiene consentimientos pendientes de firmar "
            "y enviarle el enlace para completarlos."
        )

    async def on_install(self, db, instance_id: int):
        await db.execute(SCHEMA_SQL)

    def get_frontend_routes(self):
        return [
            {"path": "consent-templates", "label": "Plantillas Consentimiento", "icon": "file-text"},
            {"path": "consent-records", "label": "Consentimientos", "icon": "file-check"},
        ]


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS ancora_crm.plugin_consent_templates (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES ancora_crm.chatbot_instances(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    content_html TEXT NOT NULL,
    service_id INTEGER REFERENCES ancora_crm.plugin_bookings_services(id) ON DELETE SET NULL,
    requires_id_number BOOLEAN DEFAULT false,
    requires_signature BOOLEAN DEFAULT true,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(instance_id, name)
);

CREATE TABLE IF NOT EXISTS ancora_crm.plugin_consent_records (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES ancora_crm.chatbot_instances(id) ON DELETE CASCADE,
    template_id INTEGER NOT NULL REFERENCES ancora_crm.plugin_consent_templates(id) ON DELETE RESTRICT,
    appointment_id INTEGER REFERENCES ancora_crm.plugin_bookings_appointments(id) ON DELETE SET NULL,
    client_name VARCHAR(200) NOT NULL,
    client_phone VARCHAR(20),
    client_id_number VARCHAR(50),
    signature_data TEXT,
    signed_at TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'pending',
    ip_address VARCHAR(45),
    retention_until DATE,
    anonymized_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_consent_records_instance ON ancora_crm.plugin_consent_records(instance_id, status);
CREATE INDEX IF NOT EXISTS idx_consent_records_phone ON ancora_crm.plugin_consent_records(client_phone);
"""
