"""Gemini function calling tools for the bookings plugin."""
from datetime import date, datetime
from typing import Any, Dict
from google.genai import types
import json


def _fd(name, description, parameters):
    """Shorthand for creating a FunctionDeclaration dict."""
    return types.FunctionDeclaration(
        name=name,
        description=description,
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties=parameters["properties"],
            required=parameters.get("required", []),
        ),
    )


BOOKING_TOOLS = [
    _fd(
        "DISPONIBILIDAD",
        "Consulta los horarios disponibles para un profesional en una fecha determinada. "
        "Usa esta herramienta cuando el cliente pregunte por disponibilidad.",
        {
            "properties": {
                "professional_id": types.Schema(type=types.Type.INTEGER, description="ID del profesional"),
                "fecha": types.Schema(type=types.Type.STRING, description="Fecha en formato YYYY-MM-DD"),
                "service_id": types.Schema(type=types.Type.INTEGER, description="ID del servicio (opcional)"),
            },
            "required": ["professional_id", "fecha"],
        },
    ),
    _fd(
        "AGENDAR",
        "Crea una nueva cita/reserva. Necesitas: profesional, servicio, nombre del cliente, telefono, fecha y hora.",
        {
            "properties": {
                "professional_id": types.Schema(type=types.Type.INTEGER, description="ID del profesional"),
                "service_id": types.Schema(type=types.Type.INTEGER, description="ID del servicio"),
                "client_name": types.Schema(type=types.Type.STRING, description="Nombre del cliente"),
                "client_phone": types.Schema(type=types.Type.STRING, description="Telefono del cliente"),
                "fecha": types.Schema(type=types.Type.STRING, description="Fecha en formato YYYY-MM-DD"),
                "hora": types.Schema(type=types.Type.STRING, description="Hora en formato HH:MM"),
                "notas": types.Schema(type=types.Type.STRING, description="Notas adicionales (opcional)"),
            },
            "required": ["professional_id", "service_id", "client_name", "client_phone", "fecha", "hora"],
        },
    ),
    _fd(
        "BUSCAR_CITAS",
        "Busca citas por telefono del cliente.",
        {
            "properties": {
                "telefono": types.Schema(type=types.Type.STRING, description="Telefono del cliente para buscar"),
            },
            "required": ["telefono"],
        },
    ),
    _fd(
        "CANCELAR_CITA",
        "Cancela una cita existente por su ID.",
        {
            "properties": {
                "appointment_id": types.Schema(type=types.Type.INTEGER, description="ID de la cita a cancelar"),
            },
            "required": ["appointment_id"],
        },
    ),
    _fd(
        "REPROGRAMAR_CITA",
        "Cambia la fecha y/o hora de una cita existente.",
        {
            "properties": {
                "appointment_id": types.Schema(type=types.Type.INTEGER, description="ID de la cita"),
                "nueva_fecha": types.Schema(type=types.Type.STRING, description="Nueva fecha YYYY-MM-DD"),
                "nueva_hora": types.Schema(type=types.Type.STRING, description="Nueva hora HH:MM"),
            },
            "required": ["appointment_id", "nueva_fecha", "nueva_hora"],
        },
    ),
    _fd(
        "PROFESIONALES_POR_SERVICIO",
        "Lista los profesionales disponibles para un tipo de servicio.",
        {
            "properties": {
                "service_id": types.Schema(type=types.Type.INTEGER, description="ID del servicio"),
            },
            "required": ["service_id"],
        },
    ),
]


async def _handle_disponibilidad(args: dict, ctx: dict) -> str:
    from app.plugins.bookings.services import get_availability
    db = ctx["db"]
    instance_id = ctx["instance_id"]
    prof_id = args["professional_id"]
    fecha = date.fromisoformat(args["fecha"])
    service_id = args.get("service_id")
    result = await get_availability(db, instance_id, prof_id, fecha, service_id)
    return json.dumps(result, default=str, ensure_ascii=False)


async def _handle_agendar(args: dict, ctx: dict) -> str:
    from app.plugins.bookings.services import create_appointment
    db = ctx["db"]
    instance_id = ctx["instance_id"]
    try:
        result = await create_appointment(
            db, instance_id,
            professional_id=args["professional_id"],
            service_id=args["service_id"],
            client_name=args["client_name"],
            client_phone=args["client_phone"],
            appt_date=date.fromisoformat(args["fecha"]),
            start_time=args["hora"],
            contact_id=ctx.get("contact_id"),
            notes=args.get("notas"),
        )
        return json.dumps({"success": True, "appointment": result}, default=str, ensure_ascii=False)
    except ValueError as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


async def _handle_buscar(args: dict, ctx: dict) -> str:
    from app.plugins.bookings.services import search_appointments
    db = ctx["db"]
    instance_id = ctx["instance_id"]
    results = await search_appointments(db, instance_id, phone=args["telefono"])
    # Filter to upcoming only
    today = date.today()
    upcoming = [r for r in results if r.get("date") and r["date"] >= today and r.get("status") != "cancelada"]
    return json.dumps({"appointments": upcoming[:10]}, default=str, ensure_ascii=False)


async def _handle_cancelar(args: dict, ctx: dict) -> str:
    from app.plugins.bookings.services import cancel_appointment
    db = ctx["db"]
    instance_id = ctx["instance_id"]
    result = await cancel_appointment(db, instance_id, args["appointment_id"])
    if result:
        return json.dumps({"success": True, "cancelled": result}, default=str, ensure_ascii=False)
    return json.dumps({"success": False, "error": "Cita no encontrada o ya cancelada"}, ensure_ascii=False)


async def _handle_reprogramar(args: dict, ctx: dict) -> str:
    from app.plugins.bookings.services import reschedule_appointment
    db = ctx["db"]
    instance_id = ctx["instance_id"]
    try:
        result = await reschedule_appointment(
            db, instance_id, args["appointment_id"],
            date.fromisoformat(args["nueva_fecha"]),
            args["nueva_hora"],
        )
        if result:
            return json.dumps({"success": True, "rescheduled": result}, default=str, ensure_ascii=False)
        return json.dumps({"success": False, "error": "Cita no encontrada"}, ensure_ascii=False)
    except ValueError as e:
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


async def _handle_profesionales(args: dict, ctx: dict) -> str:
    from app.plugins.bookings.services import get_professionals_for_service
    db = ctx["db"]
    instance_id = ctx["instance_id"]
    results = await get_professionals_for_service(db, instance_id, args["service_id"])
    return json.dumps({"professionals": results}, default=str, ensure_ascii=False)


BOOKING_TOOL_HANDLERS = {
    "DISPONIBILIDAD": _handle_disponibilidad,
    "AGENDAR": _handle_agendar,
    "BUSCAR_CITAS": _handle_buscar,
    "CANCELAR_CITA": _handle_cancelar,
    "REPROGRAMAR_CITA": _handle_reprogramar,
    "PROFESIONALES_POR_SERVICIO": _handle_profesionales,
}
