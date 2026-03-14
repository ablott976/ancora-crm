from google import genai
from google.genai import types
from datetime import datetime, timedelta
import calendar
import pytz
import logging
from typing import List, Dict, Any, Optional
from app.config import settings

logger = logging.getLogger(__name__)


class ChatbotEngine:
    def __init__(self, instance_id: int, db, config: Dict[str, Any]):
        self.instance_id = instance_id
        self.db = db
        self.config = config
        self.api_key = self.config.get('google_api_key') or settings.google_api_key

    @staticmethod
    async def create(instance_id: int, db):
        query = "SELECT * FROM ancora_crm.chatbot_instances WHERE id = $1"
        config = await db.fetchrow(query, instance_id)
        if not config:
            raise ValueError(f"Chatbot instance {instance_id} not found")
        return ChatbotEngine(instance_id, db, dict(config))

    async def _get_enabled_plugins(self):
        """Load enabled plugins for this instance."""
        from app.plugins import PluginRegistry
        return await PluginRegistry.get_enabled_plugins(self.db, self.instance_id)

    def _build_temporal_context(self) -> str:
        """Builds rich temporal context for the system prompt."""
        tz = pytz.timezone('Europe/Madrid')
        now = datetime.now(tz)
        
        dias = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo"]
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                 "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        
        # Next weekday dates
        today_weekday = now.weekday()  # 0=Monday
        next_days = {}
        for i in range(7):
            days_ahead = (i - today_weekday) % 7
            if days_ahead == 0:
                days_ahead = 7
            next_date = now + timedelta(days=days_ahead)
            next_days[f"proximo_{dias[i].lower()}"] = next_date.strftime('%d/%m/%Y')
        
        # Calendar text
        cal = calendar.TextCalendar(calendar.MONDAY)
        current_month_cal = cal.formatmonth(now.year, now.month)
        next_month = now.month + 1 if now.month < 12 else 1
        next_month_year = now.year if now.month < 12 else now.year + 1
        next_month_cal = cal.formatmonth(next_month_year, next_month)
        
        fecha_limite = now + timedelta(days=60)
        manana = now + timedelta(days=1)
        pasado = now + timedelta(days=2)
        
        lines = [
            "<contexto_temporal>",
            f"  <dia_semana>{dias[now.weekday()]}</dia_semana>",
            f"  <fecha_hoy>{now.strftime('%d/%m/%Y')}</fecha_hoy>",
            f"  <hora_actual>{now.strftime('%H:%M')}</hora_actual>",
            f"  <dia_del_mes>{now.day}</dia_del_mes>",
            f"  <mes_actual>{meses[now.month - 1]} {now.year}</mes_actual>",
            f"  <mes_siguiente>{meses[next_month - 1]} {next_month_year}</mes_siguiente>",
            f"  <fecha_manana>{manana.strftime('%d/%m/%Y')} ({dias[manana.weekday()]})</fecha_manana>",
            f"  <fecha_pasado_manana>{pasado.strftime('%d/%m/%Y')} ({dias[pasado.weekday()]})</fecha_pasado_manana>",
            f"  <fecha_limite_reservas>{fecha_limite.strftime('%d/%m/%Y')}</fecha_limite_reservas>",
        ]
        
        for key, val in next_days.items():
            lines.append(f"  <{key}>{val}</{key}>")
        
        lines.append(f"  <calendario>\n{current_month_cal}\n{next_month_cal}  </calendario>")
        lines.append("</contexto_temporal>")
        
        return "\n".join(lines)

    async def _build_rich_prompt(self, prompt_config: dict) -> str:
        """Builds a dynamic system prompt from the prompt_config table."""
        pc = prompt_config
        
        # Load schedule and holidays
        schedule_rows = await self.db.fetch(
            "SELECT dia_semana, hora_apertura, hora_cierre, abierto FROM ancora_crm.chatbot_schedule WHERE instance_id = $1 ORDER BY dia_semana",
            self.instance_id
        )
        holiday_rows = await self.db.fetch(
            "SELECT fecha, nombre FROM ancora_crm.chatbot_holidays WHERE instance_id = $1 AND fecha >= current_date ORDER BY fecha",
            self.instance_id
        )
        business_info = await self.db.fetchrow(
            "SELECT * FROM ancora_crm.chatbot_business_info WHERE instance_id = $1",
            self.instance_id
        )
        
        dias = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo"]
        
        # Schedule text
        schedule_text = "\n".join(
            f"    {dias[row['dia_semana']]}: {'De ' + row['hora_apertura'] + ' a ' + row['hora_cierre'] if row['abierto'] else 'Cerrado'}"
            for row in schedule_rows
        ) if schedule_rows else "    No configurado"
        
        # Holidays text
        holidays_text = "\n".join(
            f"    - {row['fecha'].strftime('%d/%m/%Y')}: {row['nombre']}"
            for row in holiday_rows
        ) if holiday_rows else "    No hay festivos proximos."
        
        # Build the XML-structured prompt
        sections = []
        
        # Identity
        identity_name = pc.get('identity_name') or (business_info and business_info.get('business_name')) or 'Asistente'
        identity_company = pc.get('identity_company') or (business_info and business_info.get('business_name')) or ''
        
        sections.append(f"""<identidad>
  <nombre>{identity_name}</nombre>
  <empresa>{identity_company}</empresa>
  <tagline>{pc.get('identity_tagline', '')}</tagline>
  <tono>{pc.get('identity_tone', 'profesional pero cercano')}</tono>
</identidad>""")

        # Business context
        biz_context = pc.get('business_context', '')
        if not biz_context and business_info:
            # Build from business_info fields
            parts = []
            if business_info.get('description'):
                parts.append(business_info['description'])
            if business_info.get('services_offered'):
                parts.append(f"Servicios: {business_info['services_offered']}")
            if business_info.get('additional_info'):
                parts.append(business_info['additional_info'])
            biz_context = "\n".join(parts)
        
        if biz_context:
            sections.append(f"""<contexto_negocio>
{biz_context}
</contexto_negocio>""")

        # Contact info from business_info
        if business_info:
            contact_parts = []
            if business_info.get('address'):
                contact_parts.append(f"  <direccion>{business_info['address']}{', ' + business_info.get('city', '') if business_info.get('city') else ''}</direccion>")
            if business_info.get('phone'):
                contact_parts.append(f"  <telefono>{business_info['phone']}</telefono>")
            if business_info.get('email'):
                contact_parts.append(f"  <email>{business_info['email']}</email>")
            if business_info.get('website'):
                contact_parts.append(f"  <web>{business_info['website']}</web>")
            if contact_parts:
                sections.append("<datos_contacto>\n" + "\n".join(contact_parts) + "\n</datos_contacto>")

        # Schedule
        sections.append(f"""<horario>
{schedule_text}
</horario>""")

        # Holidays
        sections.append(f"""<festivos>
{holidays_text}
</festivos>""")

        # Temporal context
        sections.append(self._build_temporal_context())

        # Behaviors
        behaviors = []
        if pc.get('first_contact_behavior'):
            behaviors.append(f"  <primer_contacto>{pc['first_contact_behavior']}</primer_contacto>")
        if pc.get('pricing_response'):
            behaviors.append(f"  <precios>{pc['pricing_response']}</precios>")
        if pc.get('off_topic_response'):
            behaviors.append(f"  <fuera_de_tema>{pc['off_topic_response']}</fuera_de_tema>")
        
        # Custom responses
        custom_responses = pc.get('custom_responses', [])
        if custom_responses and isinstance(custom_responses, list):
            for cr in custom_responses:
                trigger = cr.get('trigger', '')
                response = cr.get('response', '')
                if trigger and response:
                    behaviors.append(f"  <respuesta_personalizada trigger=\"{trigger}\">{response}</respuesta_personalizada>")
        
        if behaviors:
            sections.append("<comportamientos>\n" + "\n".join(behaviors) + "\n</comportamientos>")

        # Restrictions
        restrictions = []
        max_chars = pc.get('restrictions_max_chars', 1000)
        no_markdown = pc.get('restrictions_no_markdown', True)
        max_emojis = pc.get('restrictions_max_emojis', 2)
        
        restrictions.append(f"  <max_caracteres>{max_chars}</max_caracteres>")
        if no_markdown:
            restrictions.append("  <formato>NO uses markdown, encabezados ni formato especial. Solo texto plano con saltos de linea.</formato>")
        restrictions.append(f"  <max_emojis>{max_emojis}</max_emojis>")
        restrictions.append("  <idioma>Responde SIEMPRE en el idioma del usuario.</idioma>")
        
        sections.append("<restricciones>\n" + "\n".join(restrictions) + "\n</restricciones>")

        # Final assembly
        prompt = f"""Eres {identity_name}, asistente virtual de {identity_company}.

{"".join(s + chr(10) + chr(10) for s in sections)}

INSTRUCCIONES PRINCIPALES:
- Responde de forma {pc.get('identity_tone', 'profesional pero cercana')}.
- Usa la informacion del contexto temporal para resolver referencias a fechas (ej: "el jueves", "manana", "la semana que viene").
- Si te preguntan algo que no sabes o esta fuera de tu ambito, redirige amablemente.
- No inventes informacion. Si no tienes datos, dilo.
- Mantén las respuestas concisas (maximo {max_chars} caracteres aprox).
- Maximo {max_emojis} emojis por respuesta."""

        # Inject plugin prompt sections
        plugins = await self._get_enabled_plugins()
        for plugin in plugins:
            section = plugin.get_system_prompt_section(self.config)
            if section:
                prompt += section

        return prompt

    async def get_system_prompt(self) -> str:
        """Builds the dynamic system prompt. Uses rich prompt config if available, falls back to legacy."""
        # Check for rich prompt config
        prompt_config = await self.db.fetchrow(
            "SELECT * FROM ancora_crm.chatbot_prompt_config WHERE instance_id = $1",
            self.instance_id
        )
        
        if prompt_config:
            return await self._build_rich_prompt(dict(prompt_config))
        
        # Legacy fallback - original system
        base_prompt_row = await self.db.fetchrow(
            "SELECT content FROM ancora_crm.chatbot_prompts WHERE instance_id = $1 AND filename = 'system.txt'",
            self.instance_id
        )
        business_info = await self.db.fetchrow(
            "SELECT * FROM ancora_crm.chatbot_business_info WHERE instance_id = $1",
            self.instance_id
        )
        schedule_rows = await self.db.fetch(
            "SELECT dia_semana, hora_apertura, hora_cierre, abierto FROM ancora_crm.chatbot_schedule WHERE instance_id = $1 ORDER BY dia_semana",
            self.instance_id
        )
        holiday_rows = await self.db.fetch(
            "SELECT fecha, nombre FROM ancora_crm.chatbot_holidays WHERE instance_id = $1 AND fecha >= current_date ORDER BY fecha",
            self.instance_id
        )

        prompt = base_prompt_row['content'] if base_prompt_row else "You are a helpful assistant."

        if business_info:
            bi = dict(business_info)
            for key, val in bi.items():
                prompt = prompt.replace("{" + key + "}", str(val or ""))

        # Format schedule
        dias = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo"]
        schedule_text = "\n".join(
            f"- {dias[row['dia_semana']]}: {'De ' + row['hora_apertura'] + ' a ' + row['hora_cierre'] if row['abierto'] else 'Cerrado'}"
            for row in schedule_rows
        )
        prompt = prompt.replace("{schedule_formatted}", schedule_text)

        # Format holidays
        holidays_text = "\n".join(
            f"- {row['fecha'].strftime('%d/%m/%Y')}: {row['nombre']}"
            for row in holiday_rows
        ) if holiday_rows else "No hay festivos proximos."
        prompt = prompt.replace("{holidays_formatted}", holidays_text)

        # Temporal context (enhanced even in legacy mode)
        tz = pytz.timezone('Europe/Madrid')
        now = datetime.now(tz)
        prompt = prompt.replace("{dia_semana}", dias[now.weekday()])
        prompt = prompt.replace("{fecha_hoy}", now.strftime('%d/%m/%Y'))
        prompt = prompt.replace("{hora_actual}", now.strftime('%H:%M'))
        
        # Append temporal context block
        prompt += "\n\n" + self._build_temporal_context()

        # Inject plugin prompt sections
        plugins = await self._get_enabled_plugins()
        for plugin in plugins:
            section = plugin.get_system_prompt_section(self.config)
            if section:
                prompt += section

        return prompt

    async def get_conversation_history(self, contact_id: int) -> list[types.Content]:
        """Loads conversation history with context window management."""
        # First check for a summary
        summary_row = await self.db.fetchrow(
            """SELECT message FROM ancora_crm.chatbot_conversations 
            WHERE contact_id = $1 AND role = 'system_summary' 
            ORDER BY created_at DESC LIMIT 1""",
            contact_id
        )
        
        # Load last 20 non-summary messages
        query = """
        SELECT role, message
        FROM ancora_crm.chatbot_conversations
        WHERE contact_id = $1 AND role != 'system_summary'
        ORDER BY created_at DESC
        LIMIT 20
        """
        rows = await self.db.fetch(query, contact_id)
        history = []
        
        # Prepend summary as context if exists
        if summary_row:
            history.append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=f"[Resumen de conversacion anterior: {summary_row['message']}]")],
                )
            )
            history.append(
                types.Content(
                    role="model",
                    parts=[types.Part.from_text(text="Entendido, tengo el contexto de nuestra conversacion anterior.")],
                )
            )
        
        for row in reversed(rows):
            history.append(
                types.Content(
                    role=row['role'],
                    parts=[types.Part.from_text(text=row['message'])],
                )
            )
        return history

    async def _maybe_summarize_old_messages(self, contact_id: int):
        """If conversation exceeds 40 messages, summarize the oldest ones."""
        count = await self.db.fetchval(
            "SELECT COUNT(*) FROM ancora_crm.chatbot_conversations WHERE contact_id = $1 AND role != 'system_summary'",
            contact_id
        )
        
        if count < 40:
            return
        
        # Get messages older than the last 20
        old_messages = await self.db.fetch(
            """SELECT role, message, created_at FROM ancora_crm.chatbot_conversations 
            WHERE contact_id = $1 AND role != 'system_summary'
            ORDER BY created_at ASC
            LIMIT $2""",
            contact_id, count - 20
        )
        
        if not old_messages:
            return
        
        # Build conversation text to summarize
        conv_text = "\n".join(
            f"{'Usuario' if r['role'] == 'user' else 'Asistente'}: {r['message']}"
            for r in old_messages
        )
        
        # Use Gemini to summarize
        try:
            client = genai.Client(api_key=self.api_key)
            summary_prompt = f"""Resume la siguiente conversacion en un parrafo conciso. 
Incluye: temas tratados, datos importantes del usuario (nombre, preferencias), 
decisiones tomadas, y cualquier compromiso pendiente.

Conversacion:
{conv_text[:4000]}"""
            
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=summary_prompt,
                config=types.GenerateContentConfig(temperature=0.3),
            )
            
            summary_text = response.text if response.text else ""
            if summary_text:
                # Delete old summary if exists
                await self.db.execute(
                    "DELETE FROM ancora_crm.chatbot_conversations WHERE contact_id = $1 AND role = 'system_summary'",
                    contact_id
                )
                # Insert new summary
                await self.db.execute(
                    "INSERT INTO ancora_crm.chatbot_conversations (instance_id, contact_id, role, message) VALUES ($1, $2, 'system_summary', $3)",
                    self.instance_id, contact_id, summary_text
                )
                # Delete old messages (keep last 20)
                await self.db.execute(
                    """DELETE FROM ancora_crm.chatbot_conversations 
                    WHERE contact_id = $1 AND role != 'system_summary' 
                    AND id NOT IN (
                        SELECT id FROM ancora_crm.chatbot_conversations 
                        WHERE contact_id = $1 AND role != 'system_summary' 
                        ORDER BY created_at DESC LIMIT 20
                    )""",
                    contact_id
                )
                logger.info(f"Summarized {len(old_messages)} old messages for contact {contact_id}")
        except Exception as e:
            logger.error(f"Error summarizing messages: {e}")

    async def generate_response(self, contact_id: int, user_message: str) -> str:
        """Generates a response using Gemini with optional function calling for plugins."""
        if not self.api_key:
            return "El servicio de IA no esta configurado."

        # Trigger summarization if needed (non-blocking conceptually, but we await it)
        await self._maybe_summarize_old_messages(contact_id)

        system_prompt = await self.get_system_prompt()
        history = await self.get_conversation_history(contact_id)

        # Collect tools from enabled plugins
        plugins = await self._get_enabled_plugins()
        all_tools = []
        all_handlers = {}
        for plugin in plugins:
            all_tools.extend(plugin.get_tools())
            all_handlers.update(plugin.get_tool_handlers())

        client = genai.Client(api_key=self.api_key)

        current_user_content = types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_message)],
        )
        contents = history + [current_user_content]

        # Build config with tools if available
        tool_config = None
        if all_tools:
            tool_config = [types.Tool(function_declarations=all_tools)]

        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=self.config.get('gemini_temperature', 0.7),
            tools=tool_config,
        )

        # Context for tool handlers
        tool_context = {
            "db": self.db,
            "instance_id": self.instance_id,
            "contact_id": contact_id,
        }

        try:
            response = client.models.generate_content(
                model=self.config.get('gemini_model', 'gemini-2.0-flash'),
                contents=contents,
                config=config,
            )

            # Tool call loop - process up to 5 rounds of tool calls
            max_rounds = 5
            for _ in range(max_rounds):
                candidate = response.candidates[0] if response.candidates else None
                if not candidate:
                    return "No he podido generar una respuesta. Intenta de nuevo."

                # Check if there are function calls
                function_calls = [
                    part for part in candidate.content.parts
                    if part.function_call
                ]

                if not function_calls:
                    break  # No more tool calls, extract text

                # Process each function call
                tool_results = []
                for fc_part in function_calls:
                    fc = fc_part.function_call
                    handler = all_handlers.get(fc.name)

                    if handler:
                        try:
                            result_str = await handler(dict(fc.args), tool_context)
                        except Exception as e:
                            logger.error(f"Tool handler error for {fc.name}: {e}")
                            result_str = f'{{"error": "Error al ejecutar {fc.name}: {str(e)}"}}'
                    else:
                        result_str = f'{{"error": "Herramienta {fc.name} no encontrada"}}'

                    tool_results.append(
                        types.Part.from_function_response(
                            name=fc.name,
                            response={"result": result_str},
                        )
                    )

                # Add assistant message + tool results to contents
                contents.append(candidate.content)
                contents.append(
                    types.Content(
                        role="user",
                        parts=tool_results,
                    )
                )

                # Call Gemini again with the tool results
                response = client.models.generate_content(
                    model=self.config.get('gemini_model', 'gemini-2.0-flash'),
                    contents=contents,
                    config=config,
                )

            # Extract final text response
            candidate = response.candidates[0] if response.candidates else None
            if not candidate:
                return "No he podido generar una respuesta."

            text_parts = []
            for part in candidate.content.parts:
                if part.text:
                    text_parts.append(part.text)

            return "".join(text_parts) if text_parts else "No he podido generar una respuesta."

        except Exception as e:
            logger.error(f"Error generating Gemini response: {e}", exc_info=True)
            return "Lo siento, he tenido un problema al procesar tu solicitud. Por favor, intenta de nuevo."

    async def save_message(self, contact_id: int, role: str, message: str):
        """Saves a message to the conversation history."""
        await self.db.execute(
            "INSERT INTO ancora_crm.chatbot_conversations (instance_id, contact_id, role, message) VALUES ($1, $2, $3, $4)",
            self.instance_id, contact_id, role, message
        )
