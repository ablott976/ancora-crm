"""
Broadcast engine — send any message to contacts.
Replaces the old "Publicador Automático" + "Envío Masivo" n8n workflows.

Supports:
  - menu_del_dia: daily menu with image
  - promo: "2x1 en cócteles esta noche"
  - evento: "DJ Pachanga el 26"
  - info: general announcements
  - custom: free-form message

Audience filtering:
  - todos: all active contacts
  - vip: contacts tagged 'vip'
  - con_reserva: contacts with upcoming reservations
  - custom: contacts matching specific tags
"""
import asyncio
import logging
from datetime import date, datetime
from typing import Optional

import asyncpg

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
_s = settings.db_schema

_pool: Optional[asyncpg.Pool] = None


def set_pool(pool: asyncpg.Pool) -> None:
    global _pool
    _pool = pool


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------
async def create_broadcast(
    tipo: str,
    titulo: str,
    mensaje: str,
    imagen_url: Optional[str] = None,
    programado_para: Optional[str] = None,
    audiencia: str = "todos",
    audiencia_tags: Optional[list[str]] = None,
    creado_por: Optional[str] = None,
) -> dict:
    """Create a new broadcast (draft or scheduled)."""
    # Parse string to datetime for asyncpg
    programado_dt = None
    if programado_para:
        programado_dt = datetime.fromisoformat(programado_para) if isinstance(programado_para, str) else programado_para
    estado = "programado" if programado_para else "borrador"

    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            f"""INSERT INTO {_s}.broadcasts
                (tipo, titulo, mensaje, imagen_url, programado_para, estado, audiencia, audiencia_tags, creado_por)
                VALUES ($1, $2, $3, $4, $5::timestamptz, $6, $7, $8, $9)
                RETURNING *""",
            tipo, titulo, mensaje, imagen_url, programado_dt, estado,
            audiencia, audiencia_tags or [], creado_por,
        )
    return dict(row)


async def list_broadcasts(
    estado: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """List broadcasts with optional status filter."""
    conditions = []
    params = []
    idx = 1

    if estado:
        conditions.append(f"estado = ${idx}")
        params.append(estado)
        idx += 1

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    async with _pool.acquire() as conn:
        total = await conn.fetchval(
            f"SELECT COUNT(*) FROM {_s}.broadcasts {where}", *params)

        rows = await conn.fetch(
            f"""SELECT * FROM {_s}.broadcasts {where}
                ORDER BY created_at DESC LIMIT ${idx} OFFSET ${idx + 1}""",
            *params, limit, offset)

    return {"total": total, "broadcasts": [dict(r) for r in rows]}


async def get_broadcast(broadcast_id: int) -> Optional[dict]:
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            f"SELECT * FROM {_s}.broadcasts WHERE id = $1", broadcast_id)
    return dict(row) if row else None


async def update_broadcast(broadcast_id: int, **kwargs) -> dict:
    """Update a draft broadcast."""
    allowed = {"titulo", "mensaje", "imagen_url", "tipo", "programado_para",
               "audiencia", "audiencia_tags"}
    updates = []
    params = []
    idx = 1
    for key, val in kwargs.items():
        if key in allowed:
            if key == "programado_para" and isinstance(val, str):
                val = datetime.fromisoformat(val)
            updates.append(f"{key} = ${idx}")
            params.append(val)
            idx += 1

    if not updates:
        return await get_broadcast(broadcast_id)

    params.append(broadcast_id)
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            f"""UPDATE {_s}.broadcasts SET {', '.join(updates)}
                WHERE id = ${idx} AND estado IN ('borrador', 'programado')
                RETURNING *""",
            *params)
    return dict(row) if row else {}


async def delete_broadcast(broadcast_id: int) -> bool:
    async with _pool.acquire() as conn:
        result = await conn.execute(
            f"DELETE FROM {_s}.broadcasts WHERE id = $1 AND estado = 'borrador'",
            broadcast_id)
    return result != "DELETE 0"


# ---------------------------------------------------------------------------
# Audience resolution
# ---------------------------------------------------------------------------
async def _resolve_audience(broadcast: dict) -> list[dict]:
    """Get list of contacts matching broadcast audience."""
    audiencia = broadcast["audiencia"]

    async with _pool.acquire() as conn:
        if audiencia == "todos":
            rows = await conn.fetch(
                f"SELECT * FROM {_s}.contactos WHERE activo = TRUE AND autorizado = TRUE")

        elif audiencia == "vip":
            rows = await conn.fetch(
                f"SELECT * FROM {_s}.contactos WHERE activo = TRUE AND autorizado = TRUE AND 'vip' = ANY(tags)")

        elif audiencia == "con_reserva":
            # Contacts with upcoming reservations
            rows = await conn.fetch(
                f"""SELECT DISTINCT c.* FROM {_s}.contactos c
                    INNER JOIN {_s}.reservas r ON c.telefono = r.telefono
                    WHERE c.activo = TRUE
                      AND c.autorizado = TRUE
                      AND r.fecha >= CURRENT_DATE
                      AND r.estado NOT IN ('Cancelada')""")

        elif audiencia == "custom":
            tags = broadcast.get("audiencia_tags") or []
            if tags:
                rows = await conn.fetch(
                    f"SELECT * FROM {_s}.contactos WHERE activo = TRUE AND autorizado = TRUE AND tags && $1",
                    tags)
            else:
                rows = []
        else:
            rows = []

    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Send broadcast
# ---------------------------------------------------------------------------
async def send_broadcast(broadcast_id: int) -> dict:
    """Execute a broadcast — send to all matching contacts."""
    from services.whatsapp import send_text_message, send_template

    broadcast = await get_broadcast(broadcast_id)
    if not broadcast:
        return {"exito": False, "mensaje": "Broadcast no encontrado"}

    if broadcast["estado"] not in ("borrador", "programado"):
        return {"exito": False, "mensaje": f"Estado inválido: {broadcast['estado']}"}

    # Mark as sending
    async with _pool.acquire() as conn:
        await conn.execute(
            f"UPDATE {_s}.broadcasts SET estado = 'enviando' WHERE id = $1",
            broadcast_id)

    contacts = await _resolve_audience(broadcast)
    if not contacts:
        async with _pool.acquire() as conn:
            await conn.execute(
                f"""UPDATE {_s}.broadcasts
                    SET estado = 'enviado', total_enviados = 0, enviado_at = NOW()
                    WHERE id = $1""",
                broadcast_id)
        return {"exito": True, "enviados": 0, "mensaje": "Sin contactos en audiencia"}

    enviados = 0
    fallidos = 0

    for contact in contacts:
        telefono = contact["telefono"]
        if not telefono.startswith("34"):
            telefono = f"34{telefono}"

        try:
            texto = broadcast["mensaje"]

            # Try template first (works outside 24h window), fallback to text
            try:
                await send_template(telefono, "comunicado_restaurante", body_params=[texto])
            except Exception:
                # Template might not be approved yet or text message within 24h window
                await send_text_message(telefono, texto)

            # Log success
            async with _pool.acquire() as conn:
                await conn.execute(
                    f"""INSERT INTO {_s}.broadcast_log
                        (broadcast_id, contacto_id, telefono, estado, enviado_at)
                        VALUES ($1, $2, $3, 'enviado', NOW())
                        ON CONFLICT (broadcast_id, contacto_id) DO UPDATE
                        SET estado = 'enviado', enviado_at = NOW()""",
                    broadcast_id, contact["id"], telefono)

                await conn.execute(
                    f"UPDATE {_s}.contactos SET ultimo_broadcast = NOW() WHERE id = $1",
                    contact["id"])

            enviados += 1

            # Rate limit: ~20 msgs/sec to stay within WA limits
            await asyncio.sleep(0.05)

        except Exception as e:
            logger.error(f"Broadcast {broadcast_id} failed for {telefono}: {e}")
            async with _pool.acquire() as conn:
                await conn.execute(
                    f"""INSERT INTO {_s}.broadcast_log
                        (broadcast_id, contacto_id, telefono, estado, error)
                        VALUES ($1, $2, $3, 'fallido', $4)
                        ON CONFLICT (broadcast_id, contacto_id) DO UPDATE
                        SET estado = 'fallido', error = $4""",
                    broadcast_id, contact["id"], telefono, str(e))
            fallidos += 1

    # Finalize
    async with _pool.acquire() as conn:
        await conn.execute(
            f"""UPDATE {_s}.broadcasts
                SET estado = 'enviado', total_enviados = $1, total_fallidos = $2,
                    enviado_at = NOW()
                WHERE id = $3""",
            enviados, fallidos, broadcast_id)

    logger.info(f"Broadcast {broadcast_id} complete: {enviados} sent, {fallidos} failed")
    return {"exito": True, "enviados": enviados, "fallidos": fallidos}


# ---------------------------------------------------------------------------
# Scheduled broadcast check (called by scheduler)
# ---------------------------------------------------------------------------
async def check_scheduled_broadcasts():
    """Find and send any broadcasts scheduled for now or past due."""
    async with _pool.acquire() as conn:
        rows = await conn.fetch(
            f"""SELECT id FROM {_s}.broadcasts
                WHERE estado = 'programado'
                  AND programado_para <= NOW()""")

    for row in rows:
        logger.info(f"Sending scheduled broadcast {row['id']}")
        await send_broadcast(row["id"])
