import asyncio
import json
import base64
import logging
from google import genai
from google.genai import types as genai_types
from app.database import get_db
from app.redis_client import get_redis
from app.services.chatbot_engine import ChatbotEngine
from app.services.chatbot_whatsapp import send_message, get_media_url, download_media

logger = logging.getLogger(__name__)

BATCH_WAIT_SECONDS = 10

def get_message_text(message_payload: dict) -> str:
    """Extracts the text from a WhatsApp message payload."""
    if message_payload.get("type") == "text":
        return message_payload.get("text", {}).get("body", "")
    if message_payload.get("type") == "interactive":
        interactive = message_payload.get("interactive", {})
        if interactive.get("type") == "button_reply":
            return interactive.get("button_reply", {}).get("title", "")
        if interactive.get("type") == "list_reply":
            return interactive.get("list_reply", {}).get("title", "")
    return ""

def get_message_type(message_payload: dict) -> str:
    """Returns the message type (text, audio, image, etc.)."""
    return message_payload.get("type", "text")

def get_media_id(message_payload: dict) -> str:
    """Extracts media ID from audio/image messages."""
    msg_type = get_message_type(message_payload)
    media_obj = message_payload.get(msg_type, {})
    return media_obj.get("id", "")

def get_image_caption(message_payload: dict) -> str:
    """Extracts caption from image messages."""
    return message_payload.get("image", {}).get("caption", "")


async def transcribe_audio(audio_data: bytes, mime_type: str, api_key: str) -> str:
    """Transcribes audio using Gemini Flash."""
    try:
        client = genai.Client(api_key=api_key)
        
        # Upload as inline data
        audio_part = genai_types.Part.from_bytes(
            data=audio_data,
            mime_type=mime_type if mime_type else "audio/ogg",
        )
        
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                genai_types.Content(
                    role="user",
                    parts=[
                        audio_part,
                        genai_types.Part.from_text(
                            text="Transcribe este audio de forma exacta. Solo devuelve la transcripcion textual, sin explicaciones ni formato adicional. Si no se entiende algo, indica [inaudible]."
                        ),
                    ],
                )
            ],
            config=genai_types.GenerateContentConfig(temperature=0.1),
        )
        
        return response.text.strip() if response.text else "[Audio no reconocido]"
    except Exception as e:
        logger.error(f"Audio transcription error: {e}")
        return "[Error al transcribir audio]"


async def analyze_image(image_data: bytes, mime_type: str, api_key: str, business_name: str) -> str:
    """Analyzes an image using Gemini Flash."""
    try:
        client = genai.Client(api_key=api_key)
        
        image_part = genai_types.Part.from_bytes(
            data=image_data,
            mime_type=mime_type if mime_type else "image/jpeg",
        )
        
        prompt = f"""Analiza esta imagen como asistente de {business_name}. Proporciona de forma concisa:

1. QUE ES: Descripcion breve de la imagen
2. TEXTO COMPLETO: Si hay texto visible, transcribelo exacto
3. INFORMACION UTIL: Datos relevantes para el negocio
4. TIPO Y PROPOSITO: Que tipo de imagen es y por que la envia el usuario
5. RESPUESTA SUGERIDA: Como deberia responder el asistente

Se conciso y directo."""
        
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                genai_types.Content(
                    role="user",
                    parts=[
                        image_part,
                        genai_types.Part.from_text(text=prompt),
                    ],
                )
            ],
            config=genai_types.GenerateContentConfig(temperature=0.3),
        )
        
        return response.text.strip() if response.text else "[Imagen no analizada]"
    except Exception as e:
        logger.error(f"Image analysis error: {e}")
        return "[Error al analizar imagen]"


async def process_media_message(
    message_payload: dict,
    access_token: str,
    api_key: str,
    business_name: str,
    base_url: str = "https://graph.facebook.com/v19.0"
) -> str:
    """Processes audio/image messages and returns text representation."""
    msg_type = get_message_type(message_payload)
    media_id = get_media_id(message_payload)
    
    if not media_id:
        return get_message_text(message_payload) or ""
    
    # Get media download URL
    media_url = await get_media_url(media_id, access_token, base_url)
    if not media_url:
        logger.error(f"Could not get media URL for {media_id}")
        if msg_type == "audio":
            return "[El usuario envio un audio que no se pudo procesar]"
        return "[El usuario envio una imagen que no se pudo procesar]"
    
    # Download media
    result = await download_media(media_url, access_token)
    if not result:
        logger.error(f"Could not download media from {media_url}")
        if msg_type == "audio":
            return "[El usuario envio un audio que no se pudo descargar]"
        return "[El usuario envio una imagen que no se pudo descargar]"
    
    media_data, mime_type = result
    
    if msg_type == "audio":
        transcription = await transcribe_audio(media_data, mime_type, api_key)
        return f"[Audio transcrito: {transcription}]"
    
    elif msg_type == "image":
        caption = get_image_caption(message_payload)
        analysis = await analyze_image(media_data, mime_type, api_key, business_name)
        caption_text = f" Mensaje del usuario con la imagen: {caption}" if caption else ""
        return f"[El usuario envio una imagen.{caption_text} Analisis: {analysis}]"
    
    # For other types, try to get text
    return get_message_text(message_payload) or f"[El usuario envio un mensaje de tipo {msg_type}]"


async def add_to_batch(instance_id: int, message_payload: dict):
    """Adds a message to the Redis batch for an instance."""
    redis_client = get_redis()
    batch_key = f"chatbot_batch:{instance_id}"
    
    await redis_client.rpush(batch_key, json.dumps(message_payload))
    
    if await redis_client.llen(batch_key) == 1:
        asyncio.create_task(process_batch_after_delay(instance_id))

async def process_batch_after_delay(instance_id: int):
    """Waits for a bit, then processes the whole batch for a given instance."""
    await asyncio.sleep(BATCH_WAIT_SECONDS)
    
    redis_client = get_redis()
    batch_key = f"chatbot_batch:{instance_id}"
    
    messages_str = await redis_client.lrange(batch_key, 0, -1)
    await redis_client.delete(batch_key)

    if not messages_str:
        return

    messages = [json.loads(msg) for msg in messages_str]
    
    # Group messages by sender
    messages_by_sender = {}
    for msg in messages:
        sender_contact = next((c for c in msg.get('contacts', [])), None)
        if not sender_contact:
            continue
        sender_phone = sender_contact.get('wa_id')
        if not sender_phone:
            continue
            
        if sender_phone not in messages_by_sender:
            messages_by_sender[sender_phone] = {
                'raw_messages': [],
                'profile_name': sender_contact.get('profile', {}).get('name'),
            }
        
        # Store the raw message for processing
        raw_msg = msg.get('messages', [{}])[0]
        messages_by_sender[sender_phone]['raw_messages'].append(raw_msg)

    async for db in get_db():
        try:
            engine = await ChatbotEngine.create(instance_id, db)
            
            # Get config for media processing
            access_token = engine.config.get('whatsapp_access_token', '')
            api_key = engine.api_key
            base_url = engine.config.get('whatsapp_graph_url', 'https://graph.facebook.com/v19.0')
            
            # Get business name for image analysis context
            biz_info = await db.fetchrow(
                "SELECT business_name FROM ancora_crm.chatbot_business_info WHERE instance_id = $1",
                instance_id
            )
            business_name = biz_info['business_name'] if biz_info else 'la empresa'
            
            for sender_phone, sender_data in messages_by_sender.items():
                raw_messages = sender_data['raw_messages']
                profile_name = sender_data['profile_name']
                
                if not raw_messages:
                    continue

                # Process each message (text, audio, image)
                processed_texts = []
                for raw_msg in raw_messages:
                    msg_type = get_message_type(raw_msg)
                    
                    if msg_type in ('audio', 'image'):
                        text = await process_media_message(
                            raw_msg, access_token, api_key, business_name, base_url
                        )
                    else:
                        text = get_message_text(raw_msg)
                    
                    if text:
                        processed_texts.append(text)
                
                if not processed_texts:
                    continue
                
                full_message = " ".join(processed_texts)
                
                # Get or create contact
                contact = await db.fetchrow(
                    "SELECT * FROM ancora_crm.chatbot_contacts WHERE phone = $1 AND instance_id = $2",
                    sender_phone, instance_id
                )
                if not contact:
                    contact = await db.fetchrow(
                        "INSERT INTO ancora_crm.chatbot_contacts (instance_id, phone, name) VALUES ($1, $2, $3) RETURNING *",
                        instance_id, sender_phone, profile_name or "New Contact"
                    )
                
                contact_id = contact['id']

                # Update contact name if available
                if profile_name and contact['name'] != profile_name:
                    await db.execute(
                        "UPDATE ancora_crm.chatbot_contacts SET name = $1, last_seen = NOW() WHERE id = $2",
                        profile_name, contact_id
                    )
                else:
                    await db.execute(
                        "UPDATE ancora_crm.chatbot_contacts SET last_seen = NOW() WHERE id = $1",
                        contact_id
                    )
                
                await engine.save_message(contact_id, 'user', full_message)
                
                response_text = await engine.generate_response(contact_id, full_message)
                
                await engine.save_message(contact_id, 'model', response_text)
                
                # Send response via WhatsApp
                await send_message(
                    to=sender_phone,
                    body=response_text,
                    access_token=access_token,
                    phone_number_id=engine.config['phone_number_id'],
                    base_url=base_url
                )
        except Exception as e:
            logger.error(f"Error processing batch for instance {instance_id}: {e}", exc_info=True)
