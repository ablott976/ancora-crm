"""Restaurant Bookings plugin - Reservas de restaurante."""
from app.plugins.base import BasePlugin
from app.plugins.restaurant_bookings.routes import router as rest_router
from app.plugins.restaurant_bookings.tools import RESTAURANT_TOOLS, RESTAURANT_TOOL_HANDLERS


class RestaurantBookingsPlugin(BasePlugin):
    id = "restaurant_bookings"
    name = "Reservas Restaurante"
    version = "1.0.0"
    dependencies = []
    description = "Reservas de mesa para restaurantes con gestión de capacidad y turnos"
    icon = "utensils"

    def get_router(self):
        return rest_router

    def get_tools(self):
        return RESTAURANT_TOOLS

    def get_tool_handlers(self):
        return RESTAURANT_TOOL_HANDLERS

    def get_system_prompt_section(self, config: dict) -> str:
        return (
            "\n\n## RESERVAS DE RESTAURANTE\n"
            "Gestionas reservas de mesa. Puedes:\n"
            "- Consultar disponibilidad por fecha, hora y número de comensales\n"
            "- Crear reservas (nombre, teléfono, fecha, hora, comensales, notas/alergias)\n"
            "- Buscar reservas existentes por teléfono\n"
            "- Cancelar o modificar reservas\n"
            "Siempre confirma los datos antes de crear o modificar una reserva."
        )

    async def on_install(self, db, instance_id: int):
        await db.execute(SCHEMA_SQL)

    def get_frontend_routes(self):
        return [
            {"path": "restaurant-bookings", "label": "Reservas Mesa", "icon": "utensils"},
            {"path": "restaurant-zones", "label": "Zonas/Mesas", "icon": "layout"},
        ]


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS ancora_crm.plugin_restaurant_zones (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES ancora_crm.chatbot_instances(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    capacity INTEGER NOT NULL DEFAULT 20,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(instance_id, name)
);

CREATE TABLE IF NOT EXISTS ancora_crm.plugin_restaurant_tables (
    id SERIAL PRIMARY KEY,
    zone_id INTEGER NOT NULL REFERENCES ancora_crm.plugin_restaurant_zones(id) ON DELETE CASCADE,
    table_number VARCHAR(20) NOT NULL,
    seats INTEGER NOT NULL DEFAULT 4,
    is_active BOOLEAN DEFAULT true
);

CREATE TABLE IF NOT EXISTS ancora_crm.plugin_restaurant_reservations (
    id SERIAL PRIMARY KEY,
    instance_id INTEGER NOT NULL REFERENCES ancora_crm.chatbot_instances(id) ON DELETE CASCADE,
    contact_id INTEGER REFERENCES ancora_crm.chatbot_contacts(id) ON DELETE SET NULL,
    client_name VARCHAR(200) NOT NULL,
    client_phone VARCHAR(20),
    date DATE NOT NULL,
    time VARCHAR(5) NOT NULL,
    party_size INTEGER NOT NULL DEFAULT 2,
    zone_id INTEGER REFERENCES ancora_crm.plugin_restaurant_zones(id) ON DELETE SET NULL,
    table_id INTEGER REFERENCES ancora_crm.plugin_restaurant_tables(id) ON DELETE SET NULL,
    status VARCHAR(20) DEFAULT 'confirmada',
    notes TEXT,
    allergies TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_rest_reservations_date ON ancora_crm.plugin_restaurant_reservations(instance_id, date);
CREATE INDEX IF NOT EXISTS idx_rest_reservations_phone ON ancora_crm.plugin_restaurant_reservations(client_phone);
"""
