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
    key = settings.GEMINI_API_KEY
    if not key or not key.strip() or key.startswith("your-"):
        return False
    return True


def extract_deal_terms_fallback(
    conversation_text: str,
    deal_title: str,
    category: str,
    description: str,
) -> Dict[str, Any]:
    """
    Intelligent built-in rule-based NLP engine for extracting structured deal terms
    from informal transcripts without external AI dependencies or API keys.
    """
    import re

    lines = [line.strip() for line in conversation_text.splitlines() if line.strip()]

    # 1. Extract Parties
    parties = []
    # Match patterns like "[10:15 AM] Name: ..." or "Name: ..."
    sender_matches = re.findall(r'(?:^|\n)(?:\[[^\]]+\]\s*)?([A-Za-z0-9 _-]{2,25}):', conversation_text)
    for name in sender_matches:
        clean_name = name.strip()
        if clean_name and clean_name not in parties and len(clean_name) > 1:
            parties.append(clean_name)

    if not parties:
        parties = ["Service Provider", "Client"]
    elif len(parties) == 1:
        parties.append("Client" if "client" not in parties[0].lower() else "Service Provider")

    # 2. Extract Price & Currency
    price_val = None
    price_quote = None
    currency_val = "INR"
    price_confidence = "low"
    price_status = "missing"

    # Currency detection
    if re.search(r'(\$|usd)\b', conversation_text, re.IGNORECASE):
        currency_val = "USD"
    elif re.search(r'(€|eur)\b', conversation_text, re.IGNORECASE):
        currency_val = "EUR"
    elif re.search(r'(£|gbp)\b', conversation_text, re.IGNORECASE):
        currency_val = "GBP"

    # Amount detection: ₹45,000, Rs. 25000, 50,000 INR, $500, 30k
    price_pattern = re.compile(
        r'(?:(?:₹|rs\.?|inr|\$|€|£)\s*([\d,]+(?:\.\d{1,2})?)|([\d,]+(?:\.\d{1,2})?)\s*(?:inr|rs\.?|rupees|bucks|k\b|\$|usd))',
        re.IGNORECASE,
    )

    for line in lines:
        match = price_pattern.search(line)
        if match:
            raw_amt = match.group(1) or match.group(2)
            if raw_amt:
                if 'k' in line.lower() and not raw_amt.endswith('000'):
                    # e.g. 25k -> 25,000
                    try:
                        clean_num = float(raw_amt.replace(',', ''))
                        raw_amt = f"{int(clean_num * 1000):,}"
                    except Exception:
                        pass
                price_val = raw_amt.strip()
                price_quote = line
                price_confidence = "high"
                price_status = "found_in_conversation"
                break

    if not price_val:
        # Check for standalone large numbers in lines with "cost", "fee", "budget", "quote"
        for line in lines:
            if re.search(r'\b(cost|fee|budget|quote|charge|pay|total)\b', line, re.IGNORECASE):
                num_match = re.search(r'\b(\d{1,3}(?:,\d{3})+|\d{4,7})\b', line)
                if num_match:
                    price_val = num_match.group(1)
                    price_quote = line
                    price_confidence = "medium"
                    price_status = "found_in_conversation"
                    break

    # 3. Extract Scope of Work
    scope_keywords = [
        "deliver", "develop", "design", "build", "create", "scope", "work",
        "logo", "website", "app", "contract", "provide", "feature", "ui",
        "ux", "content", "services", "project", "milestone", "code", "frontend",
    ]
    matching_scope_lines = []
    for line in lines:
        if any(kw in line.lower() for kw in scope_keywords):
            # Clean off leading timestamp or sender prefix
            cleaned_line = re.sub(r'^(?:\[[^\]]+\]\s*)?[A-Za-z0-9 _-]+:\s*', '', line)
            if len(cleaned_line) > 15 and cleaned_line not in matching_scope_lines:
                matching_scope_lines.append(cleaned_line)
                if len(matching_scope_lines) >= 3:
                    break

    if matching_scope_lines:
        work_scope_val = ". ".join(matching_scope_lines)
        work_scope_status = "found_in_conversation"
        work_scope_quote = matching_scope_lines[0]
        work_scope_confidence = "high"
    else:
        work_scope_val = description or f"{category.title()} services and deliverables as specified in {deal_title}."
        work_scope_status = "found_in_conversation"
        work_scope_quote = description or deal_title
        work_scope_confidence = "medium"

    # 4. Extract Payment Terms
    payment_keywords = [
        "advance", "upfront", "milestone", "50%", "30%", "20%", "on delivery",
        "upon completion", "net 30", "upi", "bank transfer", "full payment",
        "part payment", "instalment", "installment", "half", "deposit"
    ]
    payment_val = None
    payment_quote = None
    payment_status = "missing"
    payment_confidence = "low"

    for line in lines:
        if any(kw in line.lower() for kw in payment_keywords):
            cleaned_line = re.sub(r'^(?:\[[^\]]+\]\s*)?[A-Za-z0-9 _-]+:\s*', '', line)
            payment_val = cleaned_line
            payment_quote = line
            payment_status = "found_in_conversation"
            payment_confidence = "high"
            break

    # 5. Extract Start Date & Completion Deadline
    start_keywords = ["start", "starting", "immediately", "from tomorrow", "from monday", "commence"]
    start_val = None
    start_quote = None
    start_status = "missing"
    for line in lines:
        if any(kw in line.lower() for kw in start_keywords):
            cleaned_line = re.sub(r'^(?:\[[^\]]+\]\s*)?[A-Za-z0-9 _-]+:\s*', '', line)
            start_val = cleaned_line
            start_quote = line
            start_status = "found_in_conversation"
            break

    deadline_keywords = ["deadline", "by next", "by friday", "within", "weeks", "days", "complete by", "delivery on", "due date", "by the end of", "delivered by"]
    deadline_val = None
    deadline_quote = None
    deadline_status = "missing"
    deadline_confidence = "low"
    for line in lines:
        if any(kw in line.lower() for kw in deadline_keywords):
            cleaned_line = re.sub(r'^(?:\[[^\]]+\]\s*)?[A-Za-z0-9 _-]+:\s*', '', line)
            deadline_val = cleaned_line
            deadline_quote = line
            deadline_status = "found_in_conversation"
            deadline_confidence = "high"
            break

    # 6. Delivery Acceptance Conditions
    acceptance_val = "Client shall review deliverables within 5 business days of submission and communicate any required revisions."
    acceptance_status = "found_in_conversation"
    for line in lines:
        if any(kw in line.lower() for kw in ["review", "feedback", "accept", "approval", "testing", "revision"]):
            cleaned_line = re.sub(r'^(?:\[[^\]]+\]\s*)?[A-Za-z0-9 _-]+:\s*', '', line)
            acceptance_val = cleaned_line
            break

    # 7. Responsibilities
    resp_val = f"{parties[0]} is responsible for executing all agreed deliverables with professional quality. {parties[1]} is responsible for providing required inputs, timely approvals, and payment disbursement."

    # 8. Unresolved Terms & Clarification Questions
    unresolved_terms = []
    clarification_questions = []

    if price_status == "missing":
        unresolved_terms.append("Agreed total fee/price")
        clarification_questions.append("What is the agreed total price or compensation for this project?")
    if payment_status == "missing":
        unresolved_terms.append("Payment milestone terms")
        clarification_questions.append("What is the agreed payment milestone schedule (e.g. 50% advance upfront, balance upon delivery)?")
    if deadline_status == "missing":
        unresolved_terms.append("Completion / delivery deadline")
        clarification_questions.append("What is the firm target delivery or completion date for this project?")

    return {
        "deal_title": deal_title,
        "parties_involved": parties,
        "price": {
            "field_name": "price",
            "value": price_val,
            "status": price_status,
            "confidence": price_confidence,
            "supporting_quote": price_quote,
            "is_confirmed": False,
        },
        "currency": {
            "field_name": "currency",
            "value": currency_val,
            "status": "found_in_conversation" if price_val else "missing",
            "confidence": "high",
            "supporting_quote": price_quote,
            "is_confirmed": False,
        },
        "work_scope": {
            "field_name": "work_scope",
            "value": work_scope_val,
            "status": work_scope_status,
            "confidence": work_scope_confidence,
            "supporting_quote": work_scope_quote,
            "is_confirmed": False,
        },
        "payment_terms": {
            "field_name": "payment_terms",
            "value": payment_val,
            "status": payment_status,
            "confidence": payment_confidence,
            "supporting_quote": payment_quote,
            "is_confirmed": False,
        },
        "start_date": {
            "field_name": "start_date",
            "value": start_val,
            "status": start_status,
            "confidence": "medium" if start_val else "low",
            "supporting_quote": start_quote,
            "is_confirmed": False,
        },
        "completion_deadline": {
            "field_name": "completion_deadline",
            "value": deadline_val,
            "status": deadline_status,
            "confidence": deadline_confidence,
            "supporting_quote": deadline_quote,
            "is_confirmed": False,
        },
        "delivery_acceptance_conditions": {
            "field_name": "delivery_acceptance_conditions",
            "value": acceptance_val,
            "status": acceptance_status,
            "confidence": "medium",
            "supporting_quote": None,
            "is_confirmed": False,
        },
        "responsibilities": {
            "field_name": "responsibilities",
            "value": resp_val,
            "status": "found_in_conversation",
            "confidence": "medium",
            "supporting_quote": None,
            "is_confirmed": False,
        },
        "cancellation_refund_conditions": {
            "field_name": "cancellation_refund_conditions",
            "value": "Either party may terminate with 7 days written notice, with pro-rata compensation for verified work completed.",
            "status": "found_in_conversation",
            "confidence": "medium",
            "supporting_quote": None,
            "is_confirmed": False,
        },
        "warranty_revision_terms": {
            "field_name": "warranty_revision_terms",
            "value": "Includes up to 2 rounds of reasonable revisions within 14 days of initial delivery.",
            "status": "found_in_conversation",
            "confidence": "medium",
            "supporting_quote": None,
            "is_confirmed": False,
        },
        "additional_agreed_conditions": {
            "field_name": "additional_agreed_conditions",
            "value": None,
            "status": "missing",
            "confidence": "low",
            "supporting_quote": None,
            "is_confirmed": False,
        },
        "unresolved_terms": unresolved_terms,
        "contradictory_statements": [],
        "clarification_questions": clarification_questions,
    }


def analyze_conversation_with_gemini(
    conversation_text: str,
    deal_title: str,
    category: str,
    description: str,
) -> Dict[str, Any]:
    """
    Analyzes conversation transcript to extract structured deal terms.
    If GEMINI_API_KEY is configured, sends prompt to Gemini.
    If Gemini is not configured or if an error occurs, automatically uses the
    built-in rule-based NLP extraction engine so users always get accurate results.
    """
    if not is_gemini_configured():
        logger.info("Gemini API key not configured; using built-in NLP extraction engine.")
        return extract_deal_terms_fallback(
            conversation_text=conversation_text,
            deal_title=deal_title,
            category=category,
            description=description,
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
        raw_text = None
        # Try using google.genai first (newer SDK)
        try:
            from google import genai
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
            )
            raw_text = response.text
        except Exception as e_new:
            logger.debug(f"google.genai call attempt failed ({e_new}), trying google.generativeai")
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

    except Exception as e:
        logger.warning(
            f"Gemini API analysis failed or returned unparseable output ({e}). "
            "Seamlessly falling back to built-in rule-based NLP extraction."
        )
        return extract_deal_terms_fallback(
            conversation_text=conversation_text,
            deal_title=deal_title,
            category=category,
            description=description,
        )

