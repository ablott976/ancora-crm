"""Bookings plugin - Reservas/Citas."""
from app.plugins.base import BasePlugin
from app.plugins.bookings.routes import router as bookings_router
from app.plugins.bookings.tools import BOOKING_TOOLS, BOOKING_TOOL_HANDLERS


class BookingsPlugin(BasePlugin):
    id = "bookings"
    name = "Reservas/Citas"
    version = "1.0.0"
    dependencies = []
    description = "Motor de reservas con disponibilidad, profesionales y servicios"
    icon = "calendar-check"

    def get_router(self):
        return bookings_router

    def get_tools(self):
        return BOOKING_TOOLS

    def get_tool_handlers(self):
        return BOOKING_TOOL_HANDLERS

    def get_system_prompt_section(self, config: dict) -> str:
        return (
            "\n\n## RESERVAS\n"
            "Tienes acceso a un sistema de reservas. Puedes:\n"
            "- Consultar disponibilidad de profesionales/recursos\n"
            "- Agendar citas (necesitas: nombre del cliente, telefono, servicio, profesional, fecha y hora)\n"
            "- Buscar citas existentes por telefono\n"
            "- Cancelar o reprogramar citas\n"
            "- Informar sobre los profesionales disponibles para cada servicio\n"
            "Usa las herramientas disponibles para gestionar las reservas. "
            "Siempre confirma los datos con el cliente antes de crear o modificar una cita."
        )

    async def on_install(self, db, instance_id: int):
        """Create bookings tables if they don't exist."""
        await db.execute(SCHEMA_SQL)

    def get_frontend_routes(self):
        return [
            {"path": "bookings", "label": "Reservas", "icon": "calendar-check"},
            {"path": "professionals", "label": "Profesionales", "icon": "users"},
            {"path": "services", "label": "Servicios", "icon": "briefcase"},
        ]


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS ancora_crm.plugin_bookings_services (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES ancora_crm.chatbot_instances(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    duration_minutes INTEGER NOT NULL DEFAULT 60,
    description TEXT,
    price DECIMAL(10,2),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(instance_id, name)
);

CREATE TABLE IF NOT EXISTS ancora_crm.plugin_bookings_professionals (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES ancora_crm.chatbot_instances(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    phone VARCHAR(20),
    email VARCHAR(200),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ancora_crm.plugin_bookings_professional_services (
    id SERIAL PRIMARY KEY,
    professional_id INTEGER NOT NULL REFERENCES ancora_crm.plugin_bookings_professionals(id) ON DELETE CASCADE,
    service_id INTEGER NOT NULL REFERENCES ancora_crm.plugin_bookings_services(id) ON DELETE CASCADE,
    UNIQUE(professional_id, service_id)
);

CREATE TABLE IF NOT EXISTS ancora_crm.plugin_bookings_appointments (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES ancora_crm.chatbot_instances(id) ON DELETE CASCADE,
    contact_id INTEGER REFERENCES ancora_crm.chatbot_contacts(id) ON DELETE SET NULL,
    professional_id INTEGER REFERENCES ancora_crm.plugin_bookings_professionals(id) ON DELETE SET NULL,
    service_id INTEGER REFERENCES ancora_crm.plugin_bookings_services(id) ON DELETE SET NULL,
    client_name VARCHAR(200),
    client_phone VARCHAR(20),
    date DATE NOT NULL,
    start_time VARCHAR(5) NOT NULL,
    end_time VARCHAR(5) NOT NULL,
    status VARCHAR(20) DEFAULT 'confirmada',
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_bookings_instance_date ON ancora_crm.plugin_bookings_appointments(instance_id, date);
CREATE INDEX IF NOT EXISTS idx_bookings_phone ON ancora_crm.plugin_bookings_appointments(client_phone);

CREATE TABLE IF NOT EXISTS ancora_crm.plugin_bookings_availability_overrides (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES ancora_crm.chatbot_instances(id) ON DELETE CASCADE,
    professional_id INTEGER REFERENCES ancora_crm.plugin_bookings_professionals(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    available BOOLEAN DEFAULT false,
    start_time VARCHAR(5),
    end_time VARCHAR(5),
    reason VARCHAR(200),
    UNIQUE(instance_id, professional_id, date)
);
"""
