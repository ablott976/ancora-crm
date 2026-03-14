import httpx
import re
from typing import Optional, Tuple

async def send_message(to: str, body: str, access_token: str, phone_number_id: str, base_url: str = "https://graph.facebook.com/v19.0"):
    """
    Sends a WhatsApp message using the Cloud API.
    """
    url = f"{base_url}/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": clean_markdown(body)},
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"Error sending WhatsApp message: {e.response.text}")
            return None

async def get_media_url(media_id: str, access_token: str, base_url: str = "https://graph.facebook.com/v19.0") -> Optional[str]:
    """
    Retrieves the download URL for a media object.
    """
    url = f"{base_url}/{media_id}"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data.get("url")
        except httpx.HTTPStatusError as e:
            print(f"Error getting media URL: {e.response.text}")
            return None

async def download_media(media_url: str, access_token: str) -> Optional[Tuple[bytes, str]]:
    """
    Downloads media from a given URL.
    Returns a tuple of (media_data, mime_type) or None on failure.
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(media_url, headers=headers)
            response.raise_for_status()
            mime_type = response.headers.get("Content-Type", "application/octet-stream")
            return response.content, mime_type
        except httpx.HTTPStatusError as e:
            print(f"Error downloading media: {e.response.text}")
            return None

def clean_markdown(text: str) -> str:
    """
    Removes unsupported WhatsApp markdown.
    - Removes headings (#)
    - Removes horizontal rules (---, ***)
    - Replaces unordered lists (*, -) with indented hyphens
    - Replaces ordered lists (1.) with indented numbers
    """
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*([-*_]){3,}\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*[\*\-]\s+', '  - ', text, flags=re.MULTILINE)
    
    def replace_ordered_list(match):
        # This is a simple version. A more robust one would track the number.
        return f"  {match.group(1)}. "
    text = re.sub(r'^\s*(\d+)\.\s+', replace_ordered_list, text, flags=re.MULTILINE)
    
    return text
