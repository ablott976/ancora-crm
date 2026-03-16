"""Gemini function calling tools for the broadcasts plugin."""
import json

from google.genai import types


def _fd(name, desc, params):
    return types.FunctionDeclaration(
        name=name,
        description=desc,
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties=params.get("properties", {}),
            required=params.get("required", []),
        ),
    )


BROADCAST_TOOLS = [
    _fd(
        "check_broadcast_status",
        "Consulta si hay campañas activas, enviandose o programadas para esta instancia.",
        {"properties": {}},
    ),
    _fd(
        "get_opt_in_count",
        "Devuelve cuántos destinatarios tienen consentimiento de marketing activo.",
        {"properties": {}},
    ),
]


async def _handle_check_status(args, ctx):
    rows = await ctx["db"].fetch(
        """SELECT id, name, status, scheduled_at, total_recipients, total_sent, total_failed
           FROM ancora_crm.plugin_broadcasts_campaigns
           WHERE instance_id = $1
             AND status IN ('scheduled', 'sending')
           ORDER BY created_at DESC
           LIMIT 10""",
        ctx["instance_id"],
    )
    campaigns = [dict(row) for row in rows]
    return json.dumps(
        {
            "has_active_campaigns": any(c["status"] in {"scheduled", "sending"} for c in campaigns),
            "campaigns": campaigns,
        },
        default=str,
        ensure_ascii=False,
    )


async def _handle_opt_in_count(args, ctx):
    count = await ctx["db"].fetchval(
        """SELECT COUNT(*)
           FROM ancora_crm.plugin_broadcasts_recipients
           WHERE instance_id = $1
             AND opt_in_marketing = true
             AND opted_out_at IS NULL""",
        ctx["instance_id"],
    )
    return json.dumps({"opt_in_count": count}, ensure_ascii=False)


BROADCAST_TOOL_HANDLERS = {
    "check_broadcast_status": _handle_check_status,
    "get_opt_in_count": _handle_opt_in_count,
}
