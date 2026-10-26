"""
Agreement Assistance Service
Provides guided legal assistance, missing term analysis, counterparty conversation questions,
and template placeholder updating based on the General Agreement Template (Indian Law).

Conforms strictly to:
- Indian Contract Act, 1872 (Sections 10, 11, 23, 25, 29, 74)
- Indian Stamp Act, 1899 & Karnataka Stamp Act, 1957 (Article 5)
- Arbitration and Conciliation Act, 1996
"""

import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

# =========================================================================
# Verbatim General Agreement Template (from statutory schedule)
# =========================================================================
GENERAL_AGREEMENT_TEMPLATE = """AGREEMENT
(General Agreement Template - for completion by the parties)

Important: This is an unsigned draft template with placeholders in [SQUARE BRACKETS]. It is not a government-issued or government-approved form. It becomes a binding, enforceable document only if it is completed accurately, properly stamped under the applicable State stamp law, executed by the parties, and (where the law requires) registered. Have it reviewed by a licensed advocate before signing. Delete this box before execution.

Reference No.: [REFERENCE NUMBER]
Date of Execution: [DD/MM/YYYY]
Place of Execution: [CITY, STATE]

THIS AGREEMENT is made at [PLACE] on [DATE] BETWEEN:

(1) [FULL LEGAL NAME OF PARTY A], [individual / company incorporated under the Companies Act, 2013 / LLP / partnership firm], son/daughter/spouse of [NAME] (for individuals), aged [AGE], residing / having its registered office at [FULL ADDRESS], PAN [PAN], Contact: [PHONE / EMAIL] (hereinafter the "First Party", which expression shall include legal heirs, successors and permitted assigns);

AND

(2) [FULL LEGAL NAME OF PARTY B], [individual / company / LLP / partnership firm], son/daughter/spouse of [NAME] (for individuals), aged [AGE], residing / having its registered office at [FULL ADDRESS], PAN [PAN], Contact: [PHONE / EMAIL] (hereinafter the "Second Party", which expression shall include legal heirs, successors and permitted assigns).

The First Party and the Second Party are together the "Parties" and individually a "Party".

RECITALS
A. [BACKGROUND OF THE FIRST PARTY AND ITS RELEVANT BUSINESS / CAPACITY].
B. [BACKGROUND OF THE SECOND PARTY].
C. The Parties wish to record the terms on which they will [PURPOSE OF THE AGREEMENT].

NOW, THEREFORE, the Parties agree as follows:

1. Definitions and Interpretation
"Effective Date" means [DATE]. "Term" has the meaning in Clause 4. "Scope" means the matters described in Clause 2. Headings are for convenience only. References to clauses are to clauses of this Agreement.

2. Scope and Purpose
The Parties agree to [DESCRIBE THE ARRANGEMENT, GOODS, SERVICES OR OBLIGATIONS IN CLEAR DETAIL].

3. Rights and Obligations
3.1 The First Party shall: [OBLIGATIONS OF FIRST PARTY].
3.2 The Second Party shall: [OBLIGATIONS OF SECOND PARTY].
3.3 Each Party shall act in good faith and cooperate to give effect to this Agreement.

4. Term
This Agreement commences on [START DATE] and, unless terminated earlier under Clause 7, continues until [END DATE / EVENT]. [Renewal: describe, or state "None"].

5. Consideration and Payment
5.1 Total consideration / fee: Rs. [AMOUNT] (Rupees [AMOUNT IN WORDS] only).
5.2 Payment schedule: [INSTALMENTS / DATES / MILESTONES].
5.3 Mode of payment: [BANK TRANSFER / CHEQUE / OTHER], to [ACCOUNT DETAILS OR PAYEE].
5.4 Taxes: [STATE WHO BEARS GST, TDS AND OTHER TAXES].
5.5 Late payment: [INTEREST / CONSEQUENCE, OR "None"].

6. Representations and Warranties
Each Party represents that (a) it has full legal capacity and authority to enter into this Agreement; (b) the information it has provided is true and complete; and (c) entering into this Agreement does not breach any law or other agreement binding on it.

7. Termination
7.1 Either Party may terminate by giving [NUMBER] days' written notice.
7.2 Either Party may terminate immediately by written notice if the other commits a material breach and fails to cure it within [NUMBER] days of written notice.
7.3 Termination does not affect rights accrued before termination or clauses intended to survive (including Clauses 8, 9, 11 and 12).

8. Breach and Remedies
A Party in breach shall compensate the other for loss that naturally arises from the breach, subject to Section 74 of the Indian Contract Act, 1872. [Optional: agreed liquidated damages of Rs. [AMOUNT], being a genuine pre-estimate of loss].

9. Confidentiality
Each Party shall keep confidential all non-public information received from the other and use it only for this Agreement, except where disclosure is required by law or a court. This obligation continues for [NUMBER] years after the Term. [Delete if not required].

10. Force Majeure
Neither Party is liable for delay or failure caused by events beyond its reasonable control, including natural disasters, war, epidemic, or government orders, provided it gives prompt written notice and uses reasonable efforts to resume performance. If the event continues beyond [NUMBER] days, either Party may terminate on written notice.

11. Governing Law and Dispute Resolution
11.1 This Agreement is governed by the laws of India and, as applicable, the State of [STATE].
11.2 The Parties shall first try to resolve any dispute by good-faith negotiation for [NUMBER] days.
11.3 Failing that, the dispute shall be referred to [arbitration by a sole arbitrator appointed by mutual consent under the Arbitration and Conciliation Act, 1996, seat [CITY], language English / the courts at [CITY]].
11.4 Courts at [CITY] shall have [exclusive / non-exclusive] jurisdiction, subject to Clause 11.3.

12. Notices
Notices shall be in writing and delivered by hand, registered post or email to the addresses stated above (or as later notified). Notice is deemed received [on delivery / [NUMBER] days after posting / on sending, if email sent before 6 pm on a working day].

13. General
13.1 Entire agreement: this Agreement is the whole agreement and supersede prior understandings on the same subject.
13.2 Amendment: only by a written document signed by both Parties.
13.3 Assignment: neither Party may assign without the other's written consent.
13.4 Severability: if any provision is held invalid, the rest remains in force.
13.5 Waiver: failure to enforce a right is not a waiver of it.
13.6 Counterparts: this Agreement may be signed in counterparts, each being an original.
13.7 Stamp duty: stamp duty and registration charges (if any) shall be borne by [PARTY / EQUALLY].

IN WITNESS WHEREOF the Parties have signed this Agreement on the date first written above.

FIRST PARTY
Signature: ____________________
Name: [NAME]
Designation (if entity): [TITLE]
Date: [DATE]

SECOND PARTY
Signature: ____________________
Name: [NAME]
Designation (if entity): [TITLE]
Date: [DATE]

WITNESSES
1. Signature: ______________________
Name: [NAME]
Address: [ADDRESS]
ID proof / No.: [ID]

2. Signature: ______________________
Name: [NAME]
Address: [ADDRESS]
ID proof / No.: [ID]"""


# =========================================================================
# Structured Assistance Topics & Statutory Explanations
# =========================================================================
ASSISTANCE_TOPIC_DEFINITIONS = [
    {
        "topic_id": "execution_meta",
        "title": "Reference, Date & Execution Location",
        "clause_ref": "Header & Place of Execution",
        "placeholders": ["[REFERENCE NUMBER]", "[DD/MM/YYYY]", "[CITY, STATE]", "[PLACE]", "[DATE]"],
        "questions": [
            "What is the official internal reference number for this deal?",
            "On what calendar date will both parties formally sign/execute this document?",
            "In which City and State is the agreement physically or electronically executed?",
        ],
        "importance": (
            "Under the Indian Stamp Act, 1899 and State Stamp Acts (e.g. Karnataka Stamp Act 1957), "
            "the date and place of execution determine which State's stamp duty schedule applies, "
            "the calculation of stamp penalties, and the 30-day statutory time limit for stamping. "
            "An incorrectly dated or unlocated instrument risks inadmissibility in court under Section 35."
        ),
        "fields": [
            {"key": "reference_number", "label": "Reference Number (e.g. LB-2026-001)", "placeholder": "LB-2026-001"},
            {"key": "execution_date", "label": "Date of Execution (DD/MM/YYYY)", "placeholder": "26/10/2026"},
            {"key": "execution_place", "label": "Place of Execution (City, State)", "placeholder": "Bengaluru, Karnataka"},
        ],
    },
    {
        "topic_id": "first_party_identity",
        "title": "First Party (Party A) Legal Capacity & Details",
        "clause_ref": "Preamble — Clause (1)",
        "placeholders": [
            "[FULL LEGAL NAME OF PARTY A]",
            "[individual / company incorporated under the Companies Act, 2013 / LLP / partnership firm]",
            "[NAME]",
            "[AGE]",
            "[FULL ADDRESS]",
            "[PAN]",
            "[PHONE / EMAIL]",
        ],
        "questions": [
            "What is the exact registered legal name of Party A (as appearing on Certificate of Incorporation / PAN)?",
            "What is the entity type (Individual, Private Limited Company, LLP, Partnership)?",
            "What is the official registered office address and Permanent Account Number (PAN)?",
            "Who is the authorized signatory or parent/spouse name for individuals?",
        ],
        "importance": (
            "Sections 10 and 11 of the Indian Contract Act, 1872 require competent contracting parties. "
            "Using trade names instead of registered corporate identities invalidates privity of contract. "
            "PAN and verified address are essential for tax deductions, service of legal notices, and filing civil suits."
        ),
        "fields": [
            {"key": "party_a_legal_name", "label": "Party A Full Legal Name", "placeholder": "Acme Solutions Pvt Ltd / Rajesh Kumar"},
            {"key": "party_a_entity_type", "label": "Entity Type (e.g. Company under Companies Act 2013 / Individual)", "placeholder": "company incorporated under the Companies Act, 2013"},
            {"key": "party_a_rep_name", "label": "Parent/Spouse Name or Authorized Director", "placeholder": "Rajesh Kumar (Director)"},
            {"key": "party_a_address", "label": "Full Registered Address", "placeholder": "No. 12, MG Road, Bengaluru, Karnataka 560001"},
            {"key": "party_a_pan", "label": "PAN Number", "placeholder": "AAACA1234F"},
            {"key": "party_a_contact", "label": "Phone / Email", "placeholder": "+91 9876543210 / contact@acme.in"},
        ],
    },
    {
        "topic_id": "second_party_identity",
        "title": "Second Party (Party B) Legal Capacity & Details",
        "clause_ref": "Preamble — Clause (2)",
        "placeholders": [
            "[FULL LEGAL NAME OF PARTY B]",
            "[individual / company / LLP / partnership firm]",
            "[NAME]",
            "[AGE]",
            "[FULL ADDRESS]",
            "[PAN]",
            "[PHONE / EMAIL]",
        ],
        "questions": [
            "What is the exact registered legal name of Party B?",
            "What is Party B's constitution and registered office / residential address?",
            "What is Party B's verified PAN and contact email/phone?",
        ],
        "importance": (
            "Clear counterparty identification ensures enforceability under Section 2(h) of the Indian Contract Act. "
            "Without full registered names and addresses, executing recovery decrees or serving statutory arbitration notices is severely delayed."
        ),
        "fields": [
            {"key": "party_b_legal_name", "label": "Party B Full Legal Name", "placeholder": "Zenith Enterprises / Sunil Sharma"},
            {"key": "party_b_entity_type", "label": "Entity Type", "placeholder": "proprietorship firm / individual"},
            {"key": "party_b_rep_name", "label": "Authorized Representative / Parent Name", "placeholder": "Sunil Sharma"},
            {"key": "party_b_address", "label": "Full Registered Address", "placeholder": "Suite 4, Indiranagar, Bengaluru, Karnataka 560038"},
            {"key": "party_b_pan", "label": "PAN Number", "placeholder": "BBBPB5678K"},
            {"key": "party_b_contact", "label": "Phone / Email", "placeholder": "+91 9123456789 / sunil@zenith.com"},
        ],
    },
    {
        "topic_id": "recitals_purpose",
        "title": "Recitals & Mutual Business Purpose",
        "clause_ref": "Recitals A, B, C",
        "placeholders": [
            "[BACKGROUND OF THE FIRST PARTY AND ITS RELEVANT BUSINESS / CAPACITY]",
            "[BACKGROUND OF THE SECOND PARTY]",
            "[PURPOSE OF THE AGREEMENT]",
        ],
        "questions": [
            "What is Party A's relevant commercial domain, expertise, or capacity?",
            "What is Party B's operational need or business objective?",
            "What is the exact mutual purpose that brings both parties together?",
        ],
        "importance": (
            "Section 23 of the Indian Contract Act requires that the consideration and object of an agreement "
            "must be lawful. Recitals provide the factual background that Indian courts and arbitrators "
            "examine to ascertain the true intention of the contracting parties."
        ),
        "fields": [
            {"key": "party_a_background", "label": "Background of First Party", "placeholder": "Engaged in providing enterprise software development and cloud consulting"},
            {"key": "party_b_background", "label": "Background of Second Party", "placeholder": "Engaged in retail distribution and logistics seeking automated software solutions"},
            {"key": "agreement_purpose", "label": "Purpose of the Agreement", "placeholder": "develop, deliver, and maintain an enterprise inventory management web application"},
        ],
    },
    {
        "topic_id": "scope_and_specifications",
        "title": "Detailed Scope & Arrangement",
        "clause_ref": "Clause 2: Scope and Purpose",
        "placeholders": ["[DESCRIBE THE ARRANGEMENT, GOODS, SERVICES OR OBLIGATIONS IN CLEAR DETAIL]"],
        "questions": [
            "What specific deliverables, services, materials, or obligations are agreed in clear detail?",
            "What are the precise technical milestones, quality criteria, and review stages?",
            "What items are explicitly excluded from this arrangement?",
        ],
        "importance": (
            "Under Section 29 of the Indian Contract Act, 1872, agreements whose meaning is not certain "
            "or capable of being made certain are void for uncertainty. Ambiguity in deliverables "
            "is the number one cause of commercial litigation in India."
        ),
        "fields": [
            {
                "key": "scope_description",
                "label": "Detailed Scope Description",
                "placeholder": "Design, develop, test, and deploy the cloud backend, responsive frontend, and API integrations as specified in technical annexure.",
            }
        ],
    },
    {
        "topic_id": "rights_and_obligations",
        "title": "Mutual Rights & Bilateral Obligations",
        "clause_ref": "Clause 3: Rights and Obligations (3.1 & 3.2)",
        "placeholders": ["[OBLIGATIONS OF FIRST PARTY]", "[OBLIGATIONS OF SECOND PARTY]"],
        "questions": [
            "What specific duties, inputs, deliverables, and service levels must the First Party perform?",
            "What specific duties, resources, data access, and approvals must the Second Party provide?",
        ],
        "importance": (
            "Sections 51 to 54 of the Indian Contract Act govern reciprocal promises. Clear obligations "
            "ensure that if the counterparty fails to provide required access, inputs, or approvals, "
            "the performing party is legally protected against allegations of delay or breach."
        ),
        "fields": [
            {
                "key": "obligations_first_party",
                "label": "Obligations of First Party",
                "placeholder": "Provide trained personnel, submit bi-weekly milestone reports, maintain data confidentiality, and deliver source code.",
            },
            {
                "key": "obligations_second_party",
                "label": "Obligations of Second Party",
                "placeholder": "Provide server credentials, review milestone deliverables within 5 working days, and disburse payments upon acceptance.",
            },
        ],
    },
    {
        "topic_id": "term_and_renewal",
        "title": "Contract Duration, Milestones & Renewal",
        "clause_ref": "Clause 4: Term",
        "placeholders": ["[START DATE]", "[END DATE / EVENT]", "[Renewal: describe, or state \"None\"]"],
        "questions": [
            "What is the official start date of the agreement?",
            "When will performance conclude, or what event marks completion?",
            "Will the agreement renew automatically, or only by written mutual agreement (or 'None')?",
        ],
        "importance": (
            "Clear term boundaries define when obligations commence, when warranties start, "
            "and when limitation periods under the Limitation Act, 1963 begin to run for recovery claims."
        ),
        "fields": [
            {"key": "term_start_date", "label": "Commencement / Start Date", "placeholder": "01/11/2026"},
            {"key": "term_end_date", "label": "End Date or Completion Event", "placeholder": "31/10/2027 or final system sign-off"},
            {"key": "renewal_terms", "label": "Renewal Terms (or 'None')", "placeholder": "Renewable annually upon mutual written agreement 30 days prior to expiry"},
        ],
    },
    {
        "topic_id": "consideration_and_payment",
        "title": "Consideration, Milestones & Bank Details",
        "clause_ref": "Clause 5: Consideration and Payment (5.1, 5.2, 5.3)",
        "placeholders": [
            "[AMOUNT]",
            "[AMOUNT IN WORDS]",
            "[INSTALMENTS / DATES / MILESTONES]",
            "[BANK TRANSFER / CHEQUE / OTHER]",
            "[ACCOUNT DETAILS OR PAYEE]",
        ],
        "questions": [
            "What is the total fee / consideration in numerical figures (INR)?",
            "What is the amount written in words to avoid typographical discrepancies?",
            "What are the milestone instalments or payment schedule dates?",
            "What is the approved mode of payment (NEFT, RTGS, UPI, Cheque) and payee bank details?",
        ],
        "importance": (
            "Section 2(d) & Section 25 of the Indian Contract Act mandate lawful consideration for contract validity. "
            "Writing the amount in both numbers and words prevents numerical tampering. "
            "Documented bank channels ensure compliance with Section 269ST of the Income Tax Act."
        ),
        "fields": [
            {"key": "consideration_amount", "label": "Total Amount (Rs.)", "placeholder": "2,50,000"},
            {"key": "amount_in_words", "label": "Amount in Words", "placeholder": "Two Lakhs Fifty Thousand Rupees"},
            {"key": "payment_schedule", "label": "Payment Schedule / Milestones", "placeholder": "30% advance on signing, 40% on alpha deployment, 30% upon final acceptance"},
            {"key": "payment_mode", "label": "Mode of Payment", "placeholder": "Direct Bank Transfer (NEFT / RTGS / IMPS)"},
            {"key": "account_details", "label": "Beneficiary Account Details / Payee", "placeholder": "HDFC Bank, Indiranagar Branch, A/C No: 50200012345678, IFSC: HDFC0001234"},
        ],
    },
    {
        "topic_id": "taxes_and_late_payment",
        "title": "Taxes (GST, TDS) & Late Payment Remedies",
        "clause_ref": "Clause 5.4 & 5.5",
        "placeholders": [
            "[STATE WHO BEARS GST, TDS AND OTHER TAXES]",
            "[INTEREST / CONSEQUENCE, OR \"None\"]",
        ],
        "questions": [
            "Who bears GST (is consideration inclusive or exclusive), and will statutory TDS be deducted?",
            "What interest rate per annum or commercial consequence applies if payment is delayed beyond due date?",
        ],
        "importance": (
            "Under the Central Goods and Services Tax Act, 2017, failure to specify whether fees are inclusive "
            "or exclusive of 18% GST leads to disputes. Reasonable interest for late payment (e.g. 12% to 18% p.a.) "
            "is recognized by commercial courts under Section 34 of CPC."
        ),
        "fields": [
            {"key": "tax_allocation", "label": "Tax Allocation (GST, TDS)", "placeholder": "Second Party bears applicable GST (18%) in addition to the fee; TDS deducted as per Income Tax Act"},
            {"key": "late_payment_interest", "label": "Late Payment Interest / Consequence", "placeholder": "Interest at 12% per annum from the due date until full realization"},
        ],
    },
    {
        "topic_id": "termination_and_cure",
        "title": "Notice Periods for Termination & Cure",
        "clause_ref": "Clause 7: Termination (7.1 & 7.2)",
        "placeholders": ["[NUMBER] days' written notice", "[NUMBER] days of written notice"],
        "questions": [
            "How many calendar days written notice must either party give to terminate for convenience?",
            "How many days notice must be provided to cure a material breach before immediate termination?",
        ],
        "importance": (
            "Under the Specific Relief Act, 1963 (Section 14 & 20A), Indian courts evaluate whether reasonable notice "
            "and cure opportunity were granted before contract determination. Clear notice protects against wrongful termination claims."
        ),
        "fields": [
            {"key": "notice_days_convenience", "label": "Notice Days for Convenience (e.g. 30)", "placeholder": "30"},
            {"key": "notice_days_cure", "label": "Cure Period for Breach (e.g. 14)", "placeholder": "14"},
        ],
    },
    {
        "topic_id": "breach_liquidated_damages",
        "title": "Breach Compensation & Liquidated Damages",
        "clause_ref": "Clause 8: Breach and Remedies",
        "placeholders": ["[Optional: agreed liquidated damages of Rs. [AMOUNT], being a genuine pre-estimate of loss]"],
        "questions": [
            "Have the parties agreed on a specific liquidated damages sum for breach, or rely on actual proven loss under Section 74 ICA?",
        ],
        "importance": (
            "Section 74 of the Indian Contract Act, 1872 governs liquidated damages. In Kailash Nath Associates v. DDA (2015), "
            "the Supreme Court established that liquidated damages are enforceable only if they represent a genuine pre-estimate "
            "of loss where actual damage is difficult to prove."
        ),
        "fields": [
            {"key": "liquidated_damages_sum", "label": "Liquidated Damages (or 'As per Section 74 Indian Contract Act')", "placeholder": "Rs. 50,000, being a genuine pre-estimate of direct losses"},
        ],
    },
    {
        "topic_id": "dispute_resolution_and_stamp",
        "title": "Dispute Seat, State Law & Stamp Duty Allocation",
        "clause_ref": "Clause 11 & Clause 13.7",
        "placeholders": [
            "[STATE]",
            "[NUMBER] days",
            "[arbitration by a sole arbitrator appointed by mutual consent under the Arbitration and Conciliation Act, 1996, seat [CITY], language English / the courts at [CITY]]",
            "[CITY]",
            "[exclusive / non-exclusive]",
            "[PARTY / EQUALLY]",
        ],
        "questions": [
            "Which Indian State's laws govern this agreement?",
            "How many days of good faith negotiation must precede legal action?",
            "Will disputes be resolved by sole arbitrator under Arbitration & Conciliation Act 1996 or through civil courts?",
            "Which city is the seat of arbitration / jurisdiction?",
            "Who bears the state stamp duty and registration charges (First Party, Second Party, or Equally)?",
        ],
        "importance": (
            "Fixing the 'seat' of arbitration under the Arbitration and Conciliation Act, 1996 vests exclusive supervisory "
            "jurisdiction in that seat's High Court. Under the Stamp Act, unstamped documents cannot be received in evidence. "
            "Clear allocation prevents disputes over who must purchase the stamp paper."
        ),
        "fields": [
            {"key": "governing_state", "label": "Governing State Law", "placeholder": "Karnataka"},
            {"key": "negotiation_days", "label": "Negotiation Days before Dispute", "placeholder": "15"},
            {"key": "dispute_resolution_body", "label": "Dispute Mechanism & Seat", "placeholder": "arbitration by a sole arbitrator appointed by mutual consent under the Arbitration and Conciliation Act, 1996, seat Bengaluru, language English"},
            {"key": "jurisdiction_city", "label": "Jurisdiction City", "placeholder": "Bengaluru"},
            {"key": "jurisdiction_type", "label": "Jurisdiction Type", "placeholder": "exclusive"},
            {"key": "stamp_duty_borne", "label": "Stamp Duty Borne By", "placeholder": "EQUALLY by both Parties"},
        ],
    },
]


def extract_template_placeholders(text: str) -> List[str]:
    """Finds all distinct [SQUARE BRACKET] placeholders in the text."""
    if not text:
        return []
    matches = re.findall(r"\[[A-Za-z0-9\s\/\,\.\-\:\'\"]+\]", text)
    # Deduplicate preserving order
    seen = set()
    result = []
    for m in matches:
        if m not in seen:
            seen.add(m)
            result.append(m)
    return result


def get_agreement_assistance_data(
    deal: Any,
    current_agreement_text: str,
    assistance_records: List[Any],
) -> Dict[str, Any]:
    """
    Computes guided assistance data, topic completion status, missing placeholders,
    and statutory questions.
    """
    # Build dictionary of saved records by topic_id
    records_by_topic = {r.topic_id: r for r in assistance_records}

    text_to_scan = current_agreement_text or GENERAL_AGREEMENT_TEMPLATE
    existing_placeholders = extract_template_placeholders(text_to_scan)

    topics_out = []
    discussed_count = 0

    for defn in ASSISTANCE_TOPIC_DEFINITIONS:
        rec = records_by_topic.get(defn["topic_id"])
        status = rec.status if rec else "pending"
        answers = rec.answers if rec and rec.answers else {}
        notes = rec.notes if rec else ""

        # Check if any placeholders for this topic still remain in text
        topic_placeholders = defn["placeholders"]
        placeholders_remaining = any(p in text_to_scan for p in topic_placeholders)

        # A topic is complete if marked discussed and has at least one answer
        is_complete = status == "discussed" and len(answers) > 0

        if is_complete:
            discussed_count += 1

        topics_out.append(
            {
                "topic_id": defn["topic_id"],
                "title": defn["title"],
                "clause_ref": defn["clause_ref"],
                "placeholders": defn["placeholders"],
                "questions": defn["questions"],
                "importance": defn["importance"],
                "fields": defn["fields"],
                "status": status,
                "answers": answers,
                "notes": notes,
                "is_complete": is_complete,
                "has_unfilled_placeholders": placeholders_remaining,
            }
        )

    total_topics = len(ASSISTANCE_TOPIC_DEFINITIONS)
    completion_pct = round((discussed_count / total_topics) * 100, 1)

    return {
        "deal_id": str(deal.id),
        "total_topics": total_topics,
        "discussed_topics": discussed_count,
        "pending_topics": total_topics - discussed_count,
        "completion_percentage": completion_pct,
        "missing_placeholders": existing_placeholders,
        "topics": topics_out,
    }


def apply_answers_to_agreement_draft(
    agreement_text: str,
    all_topic_answers: Dict[str, Dict[str, Any]],
) -> str:
    """
    Replaces bracketed placeholders in the agreement draft with confirmed user answers.
    Never alters clause titles, numbers, or standard legal phrasing.
    Only replaces confirmed fields, never inventing missing terms.
    """
    if not agreement_text:
        agreement_text = GENERAL_AGREEMENT_TEMPLATE

    updated_text = agreement_text

    # Flatten all field answers from topics
    flat_answers: Dict[str, str] = {}
    for topic_id, answers in all_topic_answers.items():
        if isinstance(answers, dict):
            for k, v in answers.items():
                if v and str(v).strip():
                    flat_answers[k] = str(v).strip()

    # Deterministic mapping from confirmed fields to bracket placeholders
    replacements = []

    # Execution Meta
    if "reference_number" in flat_answers:
        replacements.append(("[REFERENCE NUMBER]", flat_answers["reference_number"]))
    if "execution_date" in flat_answers:
        replacements.append(("[DD/MM/YYYY]", flat_answers["execution_date"]))
        replacements.append(("[DATE]", flat_answers["execution_date"]))
    if "execution_place" in flat_answers:
        replacements.append(("[CITY, STATE]", flat_answers["execution_place"]))
        replacements.append(("[PLACE]", flat_answers["execution_place"]))

    # First Party
    if "party_a_legal_name" in flat_answers:
        replacements.append(("[FULL LEGAL NAME OF PARTY A]", flat_answers["party_a_legal_name"]))
        updated_text = re.sub(r'\(1\)\s*[^,]+,', f'(1) {flat_answers["party_a_legal_name"]},', updated_text, count=1)
    if "party_a_entity_type" in flat_answers:
        replacements.append(("[individual / company incorporated under the Companies Act, 2013 / LLP / partnership firm]", flat_answers["party_a_entity_type"]))
    if "party_a_address" in flat_answers:
        # replace first address occurrence
        updated_text = updated_text.replace("residing / having its registered office at [FULL ADDRESS]", f"residing / having its registered office at {flat_answers['party_a_address']}", 1)
    if "party_a_pan" in flat_answers:
        updated_text = updated_text.replace("PAN [PAN]", f"PAN {flat_answers['party_a_pan']}", 1)
    if "party_a_contact" in flat_answers:
        updated_text = updated_text.replace("Contact: [PHONE / EMAIL]", f"Contact: {flat_answers['party_a_contact']}", 1)

    # Second Party
    if "party_b_legal_name" in flat_answers:
        replacements.append(("[FULL LEGAL NAME OF PARTY B]", flat_answers["party_b_legal_name"]))
        updated_text = re.sub(r'\(2\)\s*[^,]+,', f'(2) {flat_answers["party_b_legal_name"]},', updated_text, count=1)
    if "party_b_entity_type" in flat_answers:
        replacements.append(("[individual / company / LLP / partnership firm]", flat_answers["party_b_entity_type"]))
    if "party_b_address" in flat_answers:
        updated_text = updated_text.replace("residing / having its registered office at [FULL ADDRESS]", f"residing / having its registered office at {flat_answers['party_b_address']}", 1)
    if "party_b_pan" in flat_answers:
        updated_text = updated_text.replace("PAN [PAN]", f"PAN {flat_answers['party_b_pan']}", 1)
    if "party_b_contact" in flat_answers:
        updated_text = updated_text.replace("Contact: [PHONE / EMAIL]", f"Contact: {flat_answers['party_b_contact']}", 1)

    # Recitals
    if "party_a_background" in flat_answers:
        replacements.append(("[BACKGROUND OF THE FIRST PARTY AND ITS RELEVANT BUSINESS / CAPACITY]", flat_answers["party_a_background"]))
    if "party_b_background" in flat_answers:
        replacements.append(("[BACKGROUND OF THE SECOND PARTY]", flat_answers["party_b_background"]))
    if "agreement_purpose" in flat_answers:
        replacements.append(("[PURPOSE OF THE AGREEMENT]", flat_answers["agreement_purpose"]))

    # Scope
    if "scope_description" in flat_answers:
        replacements.append(("[DESCRIBE THE ARRANGEMENT, GOODS, SERVICES OR OBLIGATIONS IN CLEAR DETAIL]", flat_answers["scope_description"]))

    # Obligations
    if "obligations_first_party" in flat_answers:
        replacements.append(("[OBLIGATIONS OF FIRST PARTY]", flat_answers["obligations_first_party"]))
    if "obligations_second_party" in flat_answers:
        replacements.append(("[OBLIGATIONS OF SECOND PARTY]", flat_answers["obligations_second_party"]))

    # Term
    if "term_start_date" in flat_answers:
        replacements.append(("[START DATE]", flat_answers["term_start_date"]))
    if "term_end_date" in flat_answers:
        replacements.append(("[END DATE / EVENT]", flat_answers["term_end_date"]))
    if "renewal_terms" in flat_answers:
        replacements.append(('[Renewal: describe, or state "None"]', flat_answers["renewal_terms"]))

    # Consideration & Payment
    if "consideration_amount" in flat_answers:
        replacements.append(("[AMOUNT]", flat_answers["consideration_amount"]))
    if "amount_in_words" in flat_answers:
        replacements.append(("[AMOUNT IN WORDS]", flat_answers["amount_in_words"]))
    if "payment_schedule" in flat_answers:
        replacements.append(("[INSTALMENTS / DATES / MILESTONES]", flat_answers["payment_schedule"]))
    if "payment_mode" in flat_answers:
        replacements.append(("[BANK TRANSFER / CHEQUE / OTHER]", flat_answers["payment_mode"]))
    if "account_details" in flat_answers:
        replacements.append(("[ACCOUNT DETAILS OR PAYEE]", flat_answers["account_details"]))

    # Taxes & Late Payment
    if "tax_allocation" in flat_answers:
        replacements.append(("[STATE WHO BEARS GST, TDS AND OTHER TAXES]", flat_answers["tax_allocation"]))
    if "late_payment_interest" in flat_answers:
        replacements.append(('[INTEREST / CONSEQUENCE, OR "None"]', flat_answers["late_payment_interest"]))

    # Termination
    if "notice_days_convenience" in flat_answers:
        updated_text = updated_text.replace("[NUMBER] days' written notice", f"{flat_answers['notice_days_convenience']} days' written notice", 1)
    if "notice_days_cure" in flat_answers:
        updated_text = updated_text.replace("[NUMBER] days of written notice", f"{flat_answers['notice_days_cure']} days of written notice", 1)

    # Liquidated Damages
    if "liquidated_damages_sum" in flat_answers:
        replacements.append(("[Optional: agreed liquidated damages of Rs. [AMOUNT], being a genuine pre-estimate of loss]", f"Agreed liquidated damages of {flat_answers['liquidated_damages_sum']}"))

    # Dispute Resolution & Stamp Duty
    if "governing_state" in flat_answers:
        replacements.append(("[STATE]", flat_answers["governing_state"]))
    if "negotiation_days" in flat_answers:
        updated_text = updated_text.replace("negotiation for [NUMBER] days", f"negotiation for {flat_answers['negotiation_days']} days", 1)
    if "dispute_resolution_body" in flat_answers:
        replacements.append(("[arbitration by a sole arbitrator appointed by mutual consent under the Arbitration and Conciliation Act, 1996, seat [CITY], language English / the courts at [CITY]]", flat_answers["dispute_resolution_body"]))
    if "jurisdiction_city" in flat_answers:
        replacements.append(("[CITY]", flat_answers["jurisdiction_city"]))
    if "jurisdiction_type" in flat_answers:
        replacements.append(("[exclusive / non-exclusive]", flat_answers["jurisdiction_type"]))
    if "stamp_duty_borne" in flat_answers:
        replacements.append(("[PARTY / EQUALLY]", flat_answers["stamp_duty_borne"]))

    # Execute all direct replacements
    for target, rep in replacements:
        if target in updated_text:
            updated_text = updated_text.replace(target, rep)

    return updated_text


def initialize_general_template_from_deal(deal: Any, creator_name: str, counterparty_name: str) -> str:
    """
    Creates an initial draft of the General Agreement Template pre-populated with
    initial deal attributes (dates, title, parties, currency, scope) without inventing unconfirmed terms.
    """
    today_str = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    ref_no = f"LB-{str(deal.id)[:8].upper()}"
    place = "Bengaluru, Karnataka"

    text = GENERAL_AGREEMENT_TEMPLATE
    text = text.replace("[REFERENCE NUMBER]", ref_no)
    text = text.replace("[DD/MM/YYYY]", today_str)
    text = text.replace("[CITY, STATE]", place)
    text = text.replace("[PLACE]", place)
    text = text.replace("[DATE]", today_str)

    if creator_name:
        text = text.replace("[FULL LEGAL NAME OF PARTY A]", creator_name)
    if counterparty_name:
        text = text.replace("[FULL LEGAL NAME OF PARTY B]", counterparty_name)

    if deal.description:
        text = text.replace("[PURPOSE OF THE AGREEMENT]", deal.title or "commercial engagement")
        text = text.replace(
            "[DESCRIBE THE ARRANGEMENT, GOODS, SERVICES OR OBLIGATIONS IN CLEAR DETAIL]",
            deal.description.strip(),
        )

    return text
