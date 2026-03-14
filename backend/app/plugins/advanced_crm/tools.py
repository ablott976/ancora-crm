"""Gemini function calling tools for Advanced CRM."""
import json
from google.genai import types


def _fd(name, desc, params):
    return types.FunctionDeclaration(name=name, description=desc,
        parameters=types.Schema(type=types.Type.OBJECT, properties=params["properties"], required=params.get("required", [])))


CRM_TOOLS = [
    _fd("lookup_customer", "Busca el perfil de un cliente por teléfono o código de cliente. Devuelve historial de visitas, gasto total, tags y estado VIP.",
        {"properties": {
            "phone": types.Schema(type=types.Type.STRING, description="Teléfono del cliente"),
            "customer_code": types.Schema(type=types.Type.STRING, description="Código de cliente (ej: CL-1234)"),
        }, "required": []}),
    _fd("get_customer_history", "Obtiene el historial de interacciones de un cliente por teléfono.",
        {"properties": {
            "phone": types.Schema(type=types.Type.STRING, description="Teléfono del cliente"),
        }, "required": ["phone"]}),
]


async def _handle_lookup(args, ctx):
    from app.plugins.advanced_crm.services import lookup_customer
    result = await lookup_customer(ctx["db"], ctx["instance_id"], phone=args.get("phone"), customer_code=args.get("customer_code"))
    if not result:
        return json.dumps({"found": False}, ensure_ascii=False)
    return json.dumps({"found": True, "profile": result}, default=str, ensure_ascii=False)


async def _handle_history(args, ctx):
    from app.plugins.advanced_crm.services import lookup_customer, get_customer_history
    profile = await lookup_customer(ctx["db"], ctx["instance_id"], phone=args["phone"])
    if not profile:
        return json.dumps({"found": False}, ensure_ascii=False)
    history = await get_customer_history(ctx["db"], profile["id"])
    return json.dumps({"profile": profile, "history": history}, default=str, ensure_ascii=False)


CRM_TOOL_HANDLERS = {"lookup_customer": _handle_lookup, "get_customer_history": _handle_history}
