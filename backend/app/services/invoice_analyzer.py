import base64
import json
import logging
from anthropic import AsyncAnthropic
from app.config import settings

# Initialize Anthropic client if key is present
client = AsyncAnthropic(api_key=settings.anthropic_api_key) if settings.anthropic_api_key else None
logger = logging.getLogger(__name__)

async def analyze_invoice_pdf(pdf_path: str):
    if not client:
        return {"success": False, "error": "Anthropic API key not configured"}
    
    try:
        with open(pdf_path, "rb") as f:
            pdf_data = base64.b64encode(f.read()).decode("utf-8")
            
        prompt = """
        Analyze the following invoice PDF and extract these fields:
        - invoice_number (string)
        - invoice_date (YYYY-MM-DD)
        - due_date (YYYY-MM-DD, or null if not found)
        - amount (float, subtotal before tax)
        - tax_amount (float)
        - total_amount (float)
        - concept (string, short description of the main service/product)
        
        Return ONLY a JSON object with exactly these keys. Do not include any markdown formatting, just the raw JSON.
        """
        
        response = await client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": pdf_data
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        )
        
        text = response.content[0].text.strip()
        # Ensure it's valid JSON by removing potential markdown blocks
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        extracted_data = json.loads(text)
        return {
            "success": True,
            "data": extracted_data,
            "confidence": 0.95 # Mock confidence score
        }
    except Exception as e:
        logger.error(f"Error analyzing invoice: {e}")
        return {"success": False, "error": str(e)}
