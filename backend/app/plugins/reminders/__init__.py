"""Reminders plugin - Recordatorios automáticos."""
from app.plugins.base import BasePlugin
from app.plugins.reminders.routes import router as reminders_router


class RemindersPlugin(BasePlugin):
    id = "reminders"
    name = "Recordatorios"
    version = "1.0.0"
    dependencies = ["bookings"]
    description = "Recordatorios automáticos pre/post cita por WhatsApp"
    icon = "bell"

    def get_router(self):
        return reminders_router

    def get_system_prompt_section(self, config: dict) -> str:
        return ""  # Reminders are automatic, no chatbot tools needed

    async def on_install(self, db, instance_id: int):
        await db.execute(SCHEMA_SQL)

    def get_frontend_routes(self):
        return [
            {"path": "reminders", "label": "Recordatorios", "icon": "bell"},
        ]


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS ancora_crm.plugin_reminders_templates (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES ancora_crm.chatbot_instances(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    type VARCHAR(20) NOT NULL DEFAULT 'pre',
    hours_before INTEGER NOT NULL DEFAULT 24,
    template_text TEXT NOT NULL,
    is_active BOOLEAN DEFAULT true,
    send_to VARCHAR(20) DEFAULT 'client',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(instance_id, name)
);

CREATE TABLE IF NOT EXISTS ancora_crm.plugin_reminders_log (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES ancora_crm.chatbot_instances(id) ON DELETE CASCADE,
    appointment_id INTEGER,
    template_id INTEGER REFERENCES ancora_crm.plugin_reminders_templates(id) ON DELETE SET NULL,
    recipient_phone VARCHAR(20),
    message_text TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    sent_at TIMESTAMPTZ,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_reminders_log_instance ON ancora_crm.plugin_reminders_log(instance_id, created_at);
"""
