"""Gemini function calling tools for restaurant bookings."""
import json
from datetime import date
from google.genai import types


def _fd(name, desc, params):
    return types.FunctionDeclaration(name=name, description=desc,
        parameters=types.Schema(type=types.Type.OBJECT, properties=params["properties"], required=params.get("required", [])))


RESTAURANT_TOOLS = [
    _fd("check_restaurant_availability", "Consulta disponibilidad de mesa para una fecha, hora y número de comensales.",
        {"properties": {
            "date": types.Schema(type=types.Type.STRING, description="Fecha YYYY-MM-DD"),
            "time": types.Schema(type=types.Type.STRING, description="Hora HH:MM"),
            "party_size": types.Schema(type=types.Type.INTEGER, description="Número de comensales"),
        }, "required": ["date", "time", "party_size"]}),
    _fd("create_restaurant_reservation", "Crea una reserva de mesa.",
        {"properties": {
            "client_name": types.Schema(type=types.Type.STRING, description="Nombre del cliente"),
            "client_phone": types.Schema(type=types.Type.STRING, description="Teléfono"),
            "date": types.Schema(type=types.Type.STRING, description="Fecha YYYY-MM-DD"),
            "time": types.Schema(type=types.Type.STRING, description="Hora HH:MM"),
            "party_size": types.Schema(type=types.Type.INTEGER, description="Comensales"),
            "notes": types.Schema(type=types.Type.STRING, description="Notas adicionales"),
            "allergies": types.Schema(type=types.Type.STRING, description="Alergias alimentarias"),
        }, "required": ["client_name", "client_phone", "date", "time", "party_size"]}),
    _fd("find_restaurant_reservation", "Busca reservas por teléfono del cliente.",
        {"properties": {"phone": types.Schema(type=types.Type.STRING, description="Teléfono del cliente")}, "required": ["phone"]}),
    _fd("cancel_restaurant_reservation", "Cancela una reserva por su ID.",
        {"properties": {"reservation_id": types.Schema(type=types.Type.INTEGER, description="ID de la reserva")}, "required": ["reservation_id"]}),
]


async def _handle_availability(args, ctx):
    from app.plugins.restaurant_bookings.services import check_availability
    result = await check_availability(ctx["db"], ctx["instance_id"], date.fromisoformat(args["date"]), args["time"], args["party_size"])
    return json.dumps(result, default=str, ensure_ascii=False)

async def _handle_create(args, ctx):
    from app.plugins.restaurant_bookings.services import create_reservation
    result = await create_reservation(ctx["db"], ctx["instance_id"], args["client_name"], args["client_phone"], date.fromisoformat(args["date"]), args["time"], args["party_size"], args.get("notes"), args.get("allergies"))
    return json.dumps(result, default=str, ensure_ascii=False)

async def _handle_find(args, ctx):
    from app.plugins.restaurant_bookings.services import find_by_phone
    results = await find_by_phone(ctx["db"], ctx["instance_id"], args["phone"])
    return json.dumps({"reservations": results}, default=str, ensure_ascii=False)

async def _handle_cancel(args, ctx):
    from app.plugins.restaurant_bookings.services import cancel_reservation
    ok = await cancel_reservation(ctx["db"], ctx["instance_id"], args["reservation_id"])
    return json.dumps({"cancelled": ok}, ensure_ascii=False)


RESTAURANT_TOOL_HANDLERS = {
    "check_restaurant_availability": _handle_availability,
    "create_restaurant_reservation": _handle_create,
    "find_restaurant_reservation": _handle_find,
    "cancel_restaurant_reservation": _handle_cancel,
}
