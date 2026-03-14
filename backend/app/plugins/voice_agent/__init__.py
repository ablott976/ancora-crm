"""Voice Agent plugin - Agente de voz para llamadas."""
from app.plugins.base import BasePlugin
from app.plugins.voice_agent.routes import router as voice_router


class VoiceAgentPlugin(BasePlugin):
    id = "voice_agent"
    name = "Agente de Voz"
    version = "1.0.0"
    dependencies = ["bookings"]
    description = "Agente telefónico con IA para gestión de citas por llamada"
    icon = "phone"

    def get_router(self):
        return voice_router

    async def on_install(self, db, instance_id: int):
        await db.execute(SCHEMA_SQL)

    def get_frontend_routes(self):
        return [
            {"path": "voice-config", "label": "Agente de Voz", "icon": "phone"},
            {"path": "voice-calls", "label": "Llamadas", "icon": "phone-call"},
        ]


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS ancora_crm.plugin_voice_config (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES ancora_crm.chatbot_instances(id) ON DELETE CASCADE,
    provider VARCHAR(50) DEFAULT 'twilio',
    phone_number VARCHAR(20),
    voice_model VARCHAR(50) DEFAULT 'es-ES-Standard-A',
    greeting_text TEXT DEFAULT 'Hola, gracias por llamar. ¿En qué puedo ayudarte?',
    max_call_duration_seconds INTEGER DEFAULT 300,
    is_active BOOLEAN DEFAULT false,
    api_key TEXT,
    api_secret TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(instance_id)
);

CREATE TABLE IF NOT EXISTS ancora_crm.plugin_voice_calls (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES ancora_crm.chatbot_instances(id) ON DELETE CASCADE,
    caller_phone VARCHAR(20),
    call_sid VARCHAR(100),
    direction VARCHAR(10) DEFAULT 'inbound',
    status VARCHAR(20) DEFAULT 'ringing',
    duration_seconds INTEGER,
    transcript TEXT,
    summary TEXT,
    actions_taken TEXT[],
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_voice_calls_instance ON ancora_crm.plugin_voice_calls(instance_id, started_at DESC);
"""
