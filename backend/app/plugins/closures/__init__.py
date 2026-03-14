"""Closures plugin - Cierres del negocio."""
from app.plugins.base import BasePlugin
from app.plugins.closures.routes import router as closures_router
from app.plugins.closures.tools import CLOSURE_TOOLS, CLOSURE_TOOL_HANDLERS


class ClosuresPlugin(BasePlugin):
    id = "closures"
    name = "Cierres"
    version = "1.0.0"
    dependencies = []
    description = "Gestion de cierres temporales, vacaciones, festivos y mantenimiento"
    icon = "calendar-x"

    def get_router(self):
        return closures_router

    def get_tools(self):
        return CLOSURE_TOOLS

    def get_tool_handlers(self):
        return CLOSURE_TOOL_HANDLERS

    def get_system_prompt_section(self, config: dict) -> str:
        return (
            "\n\n## CIERRES\n"
            "Tienes acceso al calendario de cierres del negocio. Puedes:\n"
            "- Informar si el negocio estara cerrado en una fecha concreta\n"
            "- Consultar proximos cierres, vacaciones, festivos o mantenimientos\n"
            "- Explicar el motivo del cierre cuando exista\n"
            "Usa las herramientas disponibles para responder preguntas sobre cierres antes de confirmar disponibilidad."
        )

    async def on_install(self, db, instance_id: int):
        """Create closures tables if they don't exist."""
        await db.execute(SCHEMA_SQL)

    def get_frontend_routes(self):
        return [
            {"path": "closures", "label": "Cierres", "icon": "calendar-x"},
        ]


SCHEMA_SQL = """
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_type t
        JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE t.typname = 'plugin_closure_type'
          AND n.nspname = 'ancora_crm'
    ) THEN
        CREATE TYPE ancora_crm.plugin_closure_type AS ENUM ('holiday', 'vacation', 'maintenance', 'other');
    END IF;
END
$$;

CREATE TABLE IF NOT EXISTS ancora_crm.plugin_closures (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES ancora_crm.chatbot_instances(id) ON DELETE CASCADE,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    reason VARCHAR(255),
    closure_type ancora_crm.plugin_closure_type NOT NULL DEFAULT 'other',
    affects_all BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CHECK (end_date >= start_date)
);
CREATE INDEX IF NOT EXISTS idx_plugin_closures_instance_dates
    ON ancora_crm.plugin_closures(instance_id, start_date, end_date);
"""
