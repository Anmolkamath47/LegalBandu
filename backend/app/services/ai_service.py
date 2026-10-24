import json
import logging
from typing import Dict, Any, Optional
from ..config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are Legalbandu's AI Conversation Analysis Engine.
Your task is to analyze real informal business conversations (such as WhatsApp chats, email threads, or verbal agreement transcripts) and extract factual agreement terms.

STRICT ACCURACY RULES:
1. DO NOT invent, hallucinate, or fabricate prices, dates, deadlines, or responsibilities that are not stated.
2. If a term was not discussed or is missing, explicitly set its value to null and status to 'missing'.
3. If participants expressed conflicting statements (e.g., one said ₹25,000, another said ₹28,000), set status to 'conflicting' and list the conflict in contradictory_statements.
4. If a term is vague or ambiguous (e.g., "pay whenever you can" or "soon"), set status to 'unclear' and suggest a clarification question.
5. If a term is clearly stated and agreed, set status to 'found_in_conversation'.
6. Quote exact supporting text where available in 'supporting_quote'.

Return ONLY valid JSON matching this exact structure:
{
  "deal_title": "string or null",
  "parties_involved": ["Party 1", "Party 2"],
  "price": {
    "field_name": "price",
    "value": "string or null",
    "status": "found_in_conversation | proposed_not_confirmed | unclear | missing | conflicting",
    "confidence": "high | medium | low",
    "supporting_quote": "string or null",
    "is_confirmed": false
  },
  "currency": {
    "field_name": "currency",
    "value": "INR",
    "status": "found_in_conversation | missing",
    "confidence": "high | medium",
    "supporting_quote": "string or null",
    "is_confirmed": false
  },
  "work_scope": {
    "field_name": "work_scope",
    "value": "string or null",
    "status": "found_in_conversation | proposed_not_confirmed | unclear | missing | conflicting",
    "confidence": "high | medium | low",
    "supporting_quote": "string or null",
    "is_confirmed": false
  },
  "payment_terms": {
    "field_name": "payment_terms",
    "value": "string or null",
    "status": "found_in_conversation | unclear | missing | conflicting",
    "confidence": "high | medium | low",
    "supporting_quote": "string or null",
    "is_confirmed": false
  },
  "start_date": {
    "field_name": "start_date",
    "value": "string or null",
    "status": "found_in_conversation | unclear | missing",
    "confidence": "high | medium | low",
    "supporting_quote": "string or null",
    "is_confirmed": false
  },
  "completion_deadline": {
    "field_name": "completion_deadline",
    "value": "string or null",
    "status": "found_in_conversation | unclear | missing | conflicting",
    "confidence": "high | medium | low",
    "supporting_quote": "string or null",
    "is_confirmed": false
  },
  "delivery_acceptance_conditions": {
    "field_name": "delivery_acceptance_conditions",
    "value": "string or null",
    "status": "found_in_conversation | unclear | missing",
    "confidence": "high | medium | low",
    "supporting_quote": "string or null",
    "is_confirmed": false
  },
  "responsibilities": {
    "field_name": "responsibilities",
    "value": "string or null",
    "status": "found_in_conversation | unclear | missing",
    "confidence": "high | medium | low",
    "supporting_quote": "string or null",
    "is_confirmed": false
  },
  "cancellation_refund_conditions": {
    "field_name": "cancellation_refund_conditions",
    "value": "string or null",
    "status": "found_in_conversation | unclear | missing",
    "confidence": "high | medium | low",
    "supporting_quote": "string or null",
    "is_confirmed": false
  },
  "warranty_revision_terms": {
    "field_name": "warranty_revision_terms",
    "value": "string or null",
    "status": "found_in_conversation | unclear | missing",
    "confidence": "high | medium | low",
    "supporting_quote": "string or null",
    "is_confirmed": false
  },
  "additional_agreed_conditions": {
    "field_name": "additional_agreed_conditions",
    "value": "string or null",
    "status": "found_in_conversation | missing",
    "confidence": "high | medium | low",
    "supporting_quote": "string or null",
    "is_confirmed": false
  },
  "unresolved_terms": ["List of terms that need explicit participant agreement"],
  "contradictory_statements": ["Specific contradictions identified across messages"],
  "clarification_questions": ["Clear questions to ask the participants to resolve ambiguities"]
}
"""


class AIConfigurationError(Exception):
    """Raised when Gemini API is not configured."""
    pass


class AIServiceError(Exception):
    """Raised when Gemini API call fails."""
    pass


def is_gemini_configured() -> bool:
    return bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip())


def analyze_conversation_with_gemini(
    conversation_text: str,
    deal_title: str,
    category: str,
    description: str,
) -> Dict[str, Any]:
    """
    Sends conversation content to Google Gemini API and extracts structured deal terms.
    If GEMINI_API_KEY is not configured or an error occurs, raises AIConfigurationError / AIServiceError.
    """
    if not is_gemini_configured():
        raise AIConfigurationError(
            "Google Gemini API key is not configured on the backend. "
            "Please configure GEMINI_API_KEY in the backend environment variables, "
            "or proceed with manual entry of deal terms."
        )

    prompt = f"""
{SYSTEM_PROMPT}

DEAL CONTEXT:
Deal Title: {deal_title}
Category: {category}
Description: {description}

IMPORTED CONVERSATION TRANSCRIPT:
\"\"\"
{conversation_text}
\"\"\"

Analyze the transcript thoroughly. Return strictly valid JSON with no markdown backticks.
"""

    try:
        # Try using google.genai first (newer SDK)
        try:
            from google import genai
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
            )
            raw_text = response.text
        except Exception:
            # Fallback to google.generativeai
            import google.generativeai as genai_legacy
            genai_legacy.configure(api_key=settings.GEMINI_API_KEY)
            model = genai_legacy.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            raw_text = response.text

        # Clean JSON from markdown fences if any
        cleaned = raw_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        data = json.loads(cleaned)
        return data

    except json.JSONDecodeError as jde:
        logger.error(f"Failed to parse Gemini JSON output: {jde}")
        raise AIServiceError(
            f"AI returned an unparseable response format. Error: {str(jde)}"
        )
    except Exception as e:
        logger.error(f"Gemini API execution error: {e}")
        raise AIServiceError(
            f"Google Gemini analysis request failed: {str(e)}"
        )
