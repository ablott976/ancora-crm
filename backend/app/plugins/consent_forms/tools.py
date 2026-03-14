"""Gemini tools for consent forms."""
import json
from google.genai import types


def _fd(name, desc, params):
    return types.FunctionDeclaration(name=name, description=desc,
        parameters=types.Schema(type=types.Type.OBJECT, properties=params["properties"], required=params.get("required", [])))


CONSENT_TOOLS = [
    _fd("check_pending_consents", "Verifica si un cliente tiene consentimientos pendientes de firmar.",
        {"properties": {"phone": types.Schema(type=types.Type.STRING, description="Teléfono del cliente")}, "required": ["phone"]}),
]


async def _handle_check(args, ctx):
    from app.plugins.consent_forms.services import pending_for_phone
    pending = await pending_for_phone(ctx["db"], ctx["instance_id"], args["phone"])
    return json.dumps({"pending_count": len(pending), "consents": pending}, default=str, ensure_ascii=False)


CONSENT_TOOL_HANDLERS = {"check_pending_consents": _handle_check}
