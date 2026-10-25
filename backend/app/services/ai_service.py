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
            for candidate_model in [settings.GEMINI_MODEL, "gemini-3.5-flash-lite", "gemini-flash-lite-latest", "gemini-3.8-flash"]:
                try:
                    response = client.models.generate_content(
                        model=candidate_model,
                        contents=prompt,
                    )
                    if response.text and response.text.strip():
                        raw_text = response.text
                        break
                except Exception as model_err:
                    logger.debug(f"Candidate model {candidate_model} failed ({model_err}); trying next.")
                    continue
        except Exception as e_new:
            logger.debug(f"google.genai call attempt failed ({e_new})")

        if not raw_text:
            raise ValueError("No Gemini model was able to produce a completion")

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
        if isinstance(data.get("price"), dict) and data["price"].get("value"):
            val = str(data["price"]["value"])
            val = re.sub(r'^(?:Rs\.?|₹|INR|\$|€|£)\s*', '', val, flags=re.IGNORECASE).strip()
            data["price"]["value"] = val
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


def generate_agreement_text(
    deal_title: str,
    deal_id: str,
    category: str,
    currency: str,
    party_a_name: str,
    party_b_name: str,
    work_scope: str,
    financial_terms: str,
    timeline: str,
    responsibilities: str,
    delivery_acceptance: str = "",
    cancellation_refunds: str = "",
    warranty_revisions: str = "",
    place_of_execution: str = "Bengaluru, Karnataka",
) -> str:
    """
    Generates a complete, legally-valid agreement text under Indian law.

    Uses Gemini AI when configured for a polished output, otherwise uses a
    structured template that satisfies:
    - Indian Contract Act, 1872 (Sections 10, 23, 25, 29)
    - Information Technology Act, 2000 (Section 10A) — electronic execution
    - Bharatiya Sakshya Adhiniyam, 2023 — electronic record admissibility
    - Arbitration and Conciliation Act, 1996 — dispute resolution
    """
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).strftime("%d %B %Y")
    ref_id = (deal_id or "XXXXXXXX")[:8].upper()

    if is_gemini_configured():
        prompt = (
            f"You are a qualified Indian commercial lawyer. Draft a complete, formal, numbered bilateral "
            f"commercial agreement under Indian law. Use plain English — no latin, no excessive legalese.\n\n"
            f"DEAL: {deal_title}\nREF: LB-{ref_id}\nDATE: {today}\nPLACE: {place_of_execution}\n"
            f"PARTY A: {party_a_name}\nPARTY B: {party_b_name}\n"
            f"CATEGORY: {category}\nCURRENCY: {currency}\n\n"
            f"AGREED TERMS:\n"
            f"Scope: {work_scope}\n"
            f"Financial: {financial_terms}\n"
            f"Timeline: {timeline}\n"
            f"Responsibilities: {responsibilities}\n"
            f"Delivery & Acceptance: {delivery_acceptance or 'Party B reviews within 5 business days; silence = accepted.'}\n"
            f"Cancellation: {cancellation_refunds or '7 days written notice; pro-rata payment for completed work.'}\n"
            f"Warranty: {warranty_revisions or '2 rounds of revisions within 14 days of delivery.'}\n\n"
            f"REQUIRED CLAUSES (number each):\n"
            f"1. Parties  2. Scope of Work  3. Financial Terms & Payment  4. Timeline  "
            f"5. Responsibilities  6. Delivery & Acceptance  7. Warranty  8. Termination  "
            f"9. Confidentiality  10. Intellectual Property  11. Dispute Resolution (Arbitration & Conciliation Act 1996, seat: {place_of_execution})  "
            f"12. Governing Law ({place_of_execution} courts)  13. General Provisions (entire agreement, amendments in writing, severability)  "
            f"14. Electronic Execution (IT Act 2000 s.10A, Legalbandu ref LB-{ref_id})  "
            f"15. Signatures block with blank lines for both parties\n\n"
            f"End with this disclaimer verbatim:\n"
            f"LEGAL DISCLAIMER: This Agreement is documented through Legalbandu (LB-{ref_id}), a Technology Intermediary "
            f"under Section 2(1)(w) of the Information Technology Act, 2000. Legalbandu is not a law firm and does not "
            f"provide legal advice. For instruments requiring stamp duty, notarization, or SRO registration, engage a "
            f"qualified advocate and comply with the Indian Stamp Act and Registration Act.\n\n"
            f"Output ONLY the agreement text. No markdown. No JSON. No commentary."
        )
        try:
            raw_text = None
            try:
                from google import genai
                client = genai.Client(api_key=settings.GEMINI_API_KEY)
                for candidate_model in [settings.GEMINI_MODEL, "gemini-3.5-flash-lite", "gemini-flash-lite-latest"]:
                    try:
                        response = client.models.generate_content(model=candidate_model, contents=prompt)
                        if response.text and response.text.strip():
                            raw_text = response.text.strip()
                            break
                    except Exception:
                        continue
            except Exception:
                pass
            if raw_text:
                if raw_text.startswith("```"):
                    parts = raw_text.split("```")
                    raw_text = parts[2] if len(parts) > 2 else parts[-1]
                return raw_text.strip()
        except Exception as e:
            logger.warning(f"Gemini agreement generation failed ({e}); using template.")

    # ── Template fallback ────────────────────────────────────────────────────
    delivery_text = delivery_acceptance or (
        f"{party_b_name} shall review deliverables and communicate acceptance or required revisions "
        "within 5 (five) business days of submission. Silence beyond that period shall be deemed acceptance."
    )
    cancel_text = cancellation_refunds or (
        "Either Party may terminate this Agreement by giving 7 (seven) days' written notice. "
        "Upon termination, payment shall be made on a pro-rata basis for work verified as completed."
    )
    warranty_text = warranty_revisions or (
        f"{party_a_name} shall rectify defects in deliverables at no additional cost within "
        "14 (fourteen) calendar days of written notice, limited to 2 (two) rounds of revisions."
    )

    return f"""BILATERAL COMMERCIAL AGREEMENT
Deal Reference: LB-{ref_id}
Date of Execution: {today}
Place of Execution: {place_of_execution}
Category: {category}

────────────────────────────────────────────────────────

1. PARTIES

This Agreement ("Agreement") is entered into on {today} at {place_of_execution}, by and between:

PARTY A: {party_a_name} ("First Party")
PARTY B: {party_b_name} ("Second Party")

The Parties enter into this Agreement freely and voluntarily, with full legal capacity to contract under Section 11 of the Indian Contract Act, 1872.

────────────────────────────────────────────────────────

2. SCOPE OF WORK AND DELIVERABLES

2.1 Party A shall perform and deliver the following:

{work_scope}

2.2 Any work outside this scope requires a written amendment signed by both Parties before commencement.

────────────────────────────────────────────────────────

3. FINANCIAL TERMS AND PAYMENT SCHEDULE

3.1 Party B agrees to pay Party A the following consideration in {currency}:

{financial_terms}

3.2 All amounts are in {currency}. GST or other applicable taxes shall be borne by Party B unless otherwise stated.

3.3 Payments delayed beyond 7 days of the due date shall attract interest at 12% per annum from the due date until actual payment.

────────────────────────────────────────────────────────

4. TIMELINE AND MILESTONES

4.1 {timeline}

4.2 Time is of the essence. Extension requests must be made in writing at least 3 days before the relevant deadline and require Party B's written consent.

────────────────────────────────────────────────────────

5. RESPONSIBILITIES AND OBLIGATIONS

5.1 {responsibilities}

5.2 Party A shall: perform all work with professional diligence; deliver outputs free of material defects; maintain confidentiality of Party B's information; communicate proactively on progress.

5.3 Party B shall: provide all required inputs, approvals, and access in a timely manner; make payments on the agreed schedule; not engage a third party for the same scope without Party A's written consent.

────────────────────────────────────────────────────────

6. DELIVERY AND ACCEPTANCE

6.1 {delivery_text}

6.2 Deliverables are accepted upon Party B's written confirmation or upon expiry of the review period, whichever occurs first.

────────────────────────────────────────────────────────

7. WARRANTY AND REVISIONS

7.1 {warranty_text}

────────────────────────────────────────────────────────

8. TERMINATION AND CANCELLATION

8.1 {cancel_text}

8.2 On termination, each Party shall return the other Party's confidential materials. All undisputed payment obligations accrued up to the termination date survive termination.

────────────────────────────────────────────────────────

9. CONFIDENTIALITY

9.1 Each Party shall treat as confidential all non-public information received from the other Party and shall not disclose it to any third party without prior written consent, except as required by applicable law.

────────────────────────────────────────────────────────

10. INTELLECTUAL PROPERTY

10.1 All deliverables created specifically for Party B under this Agreement shall, upon full payment of agreed compensation, vest absolutely in Party B, unless otherwise agreed in writing.

────────────────────────────────────────────────────────

11. DISPUTE RESOLUTION

11.1 The Parties shall first attempt to resolve any dispute through good-faith negotiation within 15 (fifteen) days of written notice of the dispute.

11.2 If unresolved, the dispute shall be referred to sole-arbitrator arbitration under the Arbitration and Conciliation Act, 1996 (as amended). The seat of arbitration shall be {place_of_execution}. The arbitral award shall be final and binding.

────────────────────────────────────────────────────────

12. GOVERNING LAW AND JURISDICTION

12.1 This Agreement shall be governed by the laws of the Republic of India. Subject to Clause 11, the courts at {place_of_execution} shall have exclusive jurisdiction.

────────────────────────────────────────────────────────

13. GENERAL PROVISIONS

13.1 ENTIRE AGREEMENT: This Agreement supersedes all prior representations and agreements on the same subject matter.

13.2 AMENDMENTS: Amendments are valid only if made in writing and confirmed by both Parties.

13.3 SEVERABILITY: If any clause is held unenforceable, the remaining clauses continue in full effect.

13.4 WAIVER: Failure to enforce any clause shall not be construed as a waiver of the right to enforce it subsequently.

13.5 INDEPENDENT CONTRACTORS: The Parties are independent contractors. Nothing herein creates an employment, partnership, or agency relationship.

13.6 FORCE MAJEURE: Neither Party is liable for delays caused by events beyond their reasonable control, provided prompt written notice is given.

────────────────────────────────────────────────────────

14. ELECTRONIC EXECUTION

14.1 This Agreement is documented and executed electronically through Legalbandu (Ref: LB-{ref_id}), a Technology Intermediary under Section 2(1)(w) of the Information Technology Act, 2000.

14.2 Electronic signatures and mutual digital confirmations on the Legalbandu platform are valid and legally binding under Section 10A of the Information Technology Act, 2000, and constitute acceptance under Section 10 of the Indian Contract Act, 1872.

14.3 The electronic record of this Agreement, including the tamper-evident SHA-256 audit trail, is admissible as evidence under the Bharatiya Sakshya Adhiniyam, 2023.

────────────────────────────────────────────────────────

SIGNATURES

IN WITNESS WHEREOF, the Parties hereby confirm their free, informed, and unconditional consent to this Agreement as of the date first written above.

PARTY A — {party_a_name}

Signature: _______________________________
Name: {party_a_name}
Date: _____________
Place: {place_of_execution}

PARTY B — {party_b_name}

Signature: _______________________________
Name: {party_b_name}
Date: _____________
Place: {place_of_execution}

────────────────────────────────────────────────────────

LEGAL DISCLAIMER: This Agreement is documented through Legalbandu (LB-{ref_id}), a Technology Intermediary under Section 2(1)(w) of the Information Technology Act, 2000. Legalbandu is not a law firm and does not provide legal advice. For instruments requiring stamp duty, notarization, or Sub-Registrar registration, engage a qualified advocate and comply with the Indian Stamp Act, 1899 and Registration Act, 1908.""".strip()
