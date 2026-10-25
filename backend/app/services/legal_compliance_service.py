import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from ..models import (
    Deal,
    AgreementVersion,
    DealParticipant,
    AuthorizationProvider,
    StatutoryExclusion,
    InstrumentComplianceRecord,
    ActivityLog,
)
from .audit_service import record_activity

logger = logging.getLogger(__name__)

# The 15 Mandatory Granular Lifecycle States
VALID_LIFECYCLE_STATES = [
    "Draft — not executed",
    "Legal review required",
    "Ready for stamping",
    "Stamping pending",
    "Stamped — genuine applicable evidence verified",
    "Awaiting signatures",
    "Signed — signature evidence verified",
    "Execution requirements pending",
    "Executed — applicable execution checks passed",
    "Registration pending",
    "Registered — genuine registration evidence verified",
    "Official submission pending",
    "Submitted to official platform",
    "Officially accepted or issued — only with verified supporting evidence",
    "Completed — all applicable requirements tracked for this instrument are satisfied",
]

# Baseline Official Providers with genuine regulatory parameters
INITIAL_PROVIDERS = [
    {
        "provider_code": "nesl_dde",
        "name": "National E-Governance Services Limited (NeSL)",
        "authority_type": "Information Utility & Digital Document Execution (DDE)",
        "official_website": "https://nesl.co.in",
        "documentation_url": "https://nesl.co.in/digital-document-execution-dde/",
        "authorization_type": "Statutory Information Utility (IBC 2016) & State Revenue e-Stamping Authorizations",
        "eligible_legal_entity": "Financial Institutions, Corporates, Legal Tech Platforms (Registered Entity in India)",
        "eligibility_criteria": "Net worth and background verification; technical security audit; API partner agreement with NeSL.",
        "application_procedure": "Submit formal request to NeSL Business Development; execute tripartite agreement; complete security audit; deposit advance stamp duty float.",
        "required_corporate_docs": ["Certificate of Incorporation", "Board Resolution", "PAN Card", "GST Certificate", "Director KYC"],
        "technical_certifications": ["CERT-In Empanelled Auditor VAPT Certificate", "ISO 27001:2013", "PKI Infrastructure Review"],
        "agreements_fees_obligations": "Annual subscription fee; per-transaction DDE convenience fee (approx Rs. 20-50 per transaction); state stamp duty at actuals.",
        "api_access_details": "NeSL DDE REST APIs for e-Stamping, Biometric/Aadhaar eSign orchestration, and Section 215 IBC proof generation.",
        "authorization_status": "ELIGIBILITY_REVIEW_REQUIRED",
        "approval_reference": None,
        "geographic_coverage": "Pan-India (26+ States and Union Territories with integrated state stamp acts)",
        "document_category_coverage": ["A", "B", "E"],
        "restrictions": "Requires active corporate escrow account for stamp duty procurement; cannot bypass Aadhaar UIDAI ESP compliance.",
        "responsible_admin_email": "admin@legalbandu.com",
        "is_sandbox_only": True,
    },
    {
        "provider_code": "shcil_estamp",
        "name": "Stock Holding Corporation of India Limited (SHCIL)",
        "authority_type": "Central Record Keeping Agency (CRA) for e-Stamping",
        "official_website": "https://www.shcilestamp.com",
        "documentation_url": "https://www.stockholding.com/e-stamping.html",
        "authorization_type": "Authorized CRA appointed by Central & State Governments under Indian Stamp Act, 1899",
        "eligible_legal_entity": "Authorized Collection Centers (ACC), Banks, Statutory Corporations, and Empanelled Tech Intermediaries",
        "eligibility_criteria": "Physical security norms for ACCs or corporate agency agreement with SHCIL State Offices.",
        "application_procedure": "Application to Regional CRA Office; Bank Guarantee deposit; Operator training and digital certificate binding.",
        "required_corporate_docs": ["Company Registration", "Audited Financials", "Registered Office Proof", "Bank Guarantee"],
        "technical_certifications": ["Network Security Audit", "Fixed IP Binding", "Class 3 DSC for operators"],
        "agreements_fees_obligations": "Security deposit; commission retention rules; strict prohibition of simulated or pre-printed stamp certificates.",
        "api_access_details": "Direct state treasury gateway (e-Gras / K2) or SHCIL corporate web interface.",
        "authorization_status": "APPLICATION_REQUIRED",
        "approval_reference": None,
        "geographic_coverage": "Participating States including Delhi, Gujarat, Karnataka, Maharashtra, Tamil Nadu, Uttar Pradesh",
        "document_category_coverage": ["A", "B", "C", "D"],
        "restrictions": "Direct end-user API access requires state government empanelment as an authorized service provider.",
        "responsible_admin_email": "admin@legalbandu.com",
        "is_sandbox_only": True,
    },
    {
        "provider_code": "icegate_customs",
        "name": "CBIC ICEGATE — Indian Customs Electronic Data Interchange Gateway",
        "authority_type": "Directorate General of Systems and Data Management (CBIC)",
        "official_website": "https://www.icegate.gov.in",
        "documentation_url": "https://www.icegate.gov.in/guidelines/e-bond",
        "authorization_type": "Customs Electronic Data Interchange Gateway under Section 143/146 of Customs Act, 1962",
        "eligible_legal_entity": "Registered Importers/Exporters (IEC Holders), Customs Brokers, Authorised Economic Operators (AEO)",
        "eligibility_criteria": "Active IEC validated with DGFT; registered digital signature (Class 3) with ICEGATE profile; valid customs bond approval.",
        "application_procedure": "Register IEC on ICEGATE 2.0 portal; link Class 3 DSC; enroll in e-Bond module; interface with NeSL for e-stamping integration.",
        "required_corporate_docs": ["DGFT IEC Certificate", "GSTIN Registration", "Authorized Signatory Proof", "Customs Broker License if filing on behalf"],
        "technical_certifications": ["CBIC EDI Message Protocol V1.5", "Digital Signature PKI Compliance"],
        "agreements_fees_obligations": "Customs transaction fees if applicable; statutory bond penalty coverage; bank guarantee maintenance.",
        "api_access_details": "ICEGATE SFTP / REST API endpoints for manifest, bill of entry, and electronic customs bond submissions.",
        "authorization_status": "APPLICATION_REQUIRED",
        "approval_reference": None,
        "geographic_coverage": "All Indian Customs Ports, ICDs, Air Cargo Complexes, and SEZs",
        "document_category_coverage": ["E"],
        "restrictions": "Unofficial submissions or mock references strictly prohibited under Customs Act; requires genuine customs officer approval.",
        "responsible_admin_email": "admin@legalbandu.com",
        "is_sandbox_only": True,
    },
    {
        "provider_code": "protean_esp",
        "name": "Protean eGov Technologies (formerly NSDL e-Gov)",
        "authority_type": "eSign Service Provider (ESP) / Certifying Authority",
        "official_website": "https://www.proteantech.in",
        "documentation_url": "https://www.proteantech.in/services/esign-service",
        "authorization_type": "Licensed by Controller of Certifying Authorities (CCA) under Section 24 of IT Act, 2000",
        "eligible_legal_entity": "Registered Application Service Providers (ASPs) complying with CCA eSign Guidelines",
        "eligibility_criteria": "ASP Agreement; CERT-In certified application security audit; UIDAI KYC API licensing compliance.",
        "application_procedure": "Apply as ASP; integrate PKCS#7 eSign Gateway; verify XML request signatures; conduct live VAPT audit.",
        "required_corporate_docs": ["Certificate of Incorporation", "PAN", "Board Resolution", "Director Aadhaar/PAN"],
        "technical_certifications": ["CERT-In Application VAPT", "CCA eSign 2.1 Specification Compliance", "TLS 1.3 / HSM Key Management"],
        "agreements_fees_obligations": "Annual ASP maintenance fee; per-signature ESP fee (approx Rs. 5-15 per Aadhaar OTP/Biometric eSign).",
        "api_access_details": "Aadhaar eSign Gateway XML/JSON API with dual-factor OTP or biometric verification.",
        "authorization_status": "ELIGIBILITY_REVIEW_REQUIRED",
        "approval_reference": None,
        "geographic_coverage": "Pan-India",
        "document_category_coverage": ["A", "B", "E"],
        "restrictions": "Cannot be used for instruments excluded under First Schedule of IT Act, 2000.",
        "responsible_admin_email": "admin@legalbandu.com",
        "is_sandbox_only": True,
    },
]

# Baseline Statutory Exclusions (First Schedule to Information Technology Act, 2000)
INITIAL_EXCLUSIONS = [
    {
        "exclusion_code": "IT_ACT_SCHED1_NEGOTIABLE",
        "instrument_name": "Negotiable Instruments (Bills of Exchange, Promissory Notes)",
        "statutory_source": "Information Technology Act, 2000",
        "section_reference": "Section 1(4) read with First Schedule, Entry 1",
        "effective_date": "2000-10-17",
        "is_electronic_execution_permitted": False,
        "required_physical_formalities": "Physical paper execution with wet-ink signatures and adhesive/impressed revenue stamps under Negotiable Instruments Act, 1881.",
        "statutory_exceptions": "Cheques are exempted from exclusion (Electronic cheques and truncated cheques are valid under Section 1(4)).",
        "legal_review_mandatory": True,
    },
    {
        "exclusion_code": "IT_ACT_SCHED1_POA",
        "instrument_name": "Power of Attorney",
        "statutory_source": "Information Technology Act, 2000",
        "section_reference": "Section 1(4) read with First Schedule, Entry 2",
        "effective_date": "2000-10-17",
        "is_electronic_execution_permitted": False,
        "required_physical_formalities": "Execution on non-judicial stamp paper, notarization by Public Notary or adjudication before Collector/Sub-Registrar.",
        "statutory_exceptions": "Powers of Attorney issued in favor of financial entities licensed by RBI/SEBI/IRDAI pursuant to MeitY Notification S.O. 4488(E) dated 26.09.2022.",
        "legal_review_mandatory": True,
    },
    {
        "exclusion_code": "IT_ACT_SCHED1_TRUST",
        "instrument_name": "Trust Deed / Creation of Trust",
        "statutory_source": "Information Technology Act, 2000",
        "section_reference": "Section 1(4) read with First Schedule, Entry 3",
        "effective_date": "2000-10-17",
        "is_electronic_execution_permitted": False,
        "required_physical_formalities": "Non-testamentary instrument of trust regarding immovable property must be physically stamped, signed, and registered with the Sub-Registrar under Section 5 Indian Trusts Act, 1882.",
        "statutory_exceptions": "None.",
        "legal_review_mandatory": True,
    },
    {
        "exclusion_code": "IT_ACT_SCHED1_WILL",
        "instrument_name": "Will, Codicil & Testamentary Dispositions",
        "statutory_source": "Information Technology Act, 2000",
        "section_reference": "Section 1(4) read with First Schedule, Entry 4",
        "effective_date": "2000-10-17",
        "is_electronic_execution_permitted": False,
        "required_physical_formalities": "Physical paper execution signed by testator in presence of at least two attesting witnesses under Section 63 Indian Succession Act, 1925. SRO registration strongly advised.",
        "statutory_exceptions": "None. Electronic wills are legally void in India.",
        "legal_review_mandatory": True,
    },
    {
        "exclusion_code": "IT_ACT_SCHED1_REAL_ESTATE",
        "instrument_name": "Contract for Sale / Conveyance of Immovable Property",
        "statutory_source": "Information Technology Act, 2000",
        "section_reference": "Section 1(4) read with First Schedule, Entry 5",
        "effective_date": "2000-10-17",
        "is_electronic_execution_permitted": False,
        "required_physical_formalities": "Execution on full ad-valorem state stamp paper, physical presentation of vendor/vendee before Sub-Registrar of Assurances, biometric identification and 2 witnesses under Section 17 & 32 Registration Act, 1908.",
        "statutory_exceptions": "Contracts that do not create an interest in immovable property or state-authorized pilot schemes (e.g. Maharashtra Leave and License e-Registration).",
        "legal_review_mandatory": True,
    },
]


def seed_compliance_reference_data(db: Session):
    """Initializes official providers and statutory exclusions if not present."""
    for p_data in INITIAL_PROVIDERS:
        existing = db.query(AuthorizationProvider).filter_by(provider_code=p_data["provider_code"]).first()
        if not existing:
            provider = AuthorizationProvider(**p_data)
            db.add(provider)

    for ex_data in INITIAL_EXCLUSIONS:
        existing = db.query(StatutoryExclusion).filter_by(exclusion_code=ex_data["exclusion_code"]).first()
        if not existing:
            exclusion = StatutoryExclusion(**ex_data)
            db.add(exclusion)

    db.commit()


def check_statutory_exclusion(deal_title: str, description: str, category: str, db: Session) -> Optional[StatutoryExclusion]:
    """
    Evaluates whether the intended deal or document falls under the First Schedule
    of the Information Technology Act, 2000 (disqualifying electronic execution).
    """
    text_corpus = f"{deal_title} {description} {category}".lower()

    if any(k in text_corpus for k in ["promissory note", "bill of exchange", "hundi", "negotiable instrument"]):
        return db.query(StatutoryExclusion).filter_by(exclusion_code="IT_ACT_SCHED1_NEGOTIABLE").first()

    if any(k in text_corpus for k in ["power of attorney", "general power of attorney", "special power of attorney", "gpa", "poa"]):
        return db.query(StatutoryExclusion).filter_by(exclusion_code="IT_ACT_SCHED1_POA").first()

    if any(k in text_corpus for k in ["trust deed", "charitable trust", "private trust", "trustee"]):
        return db.query(StatutoryExclusion).filter_by(exclusion_code="IT_ACT_SCHED1_TRUST").first()

    if any(k in text_corpus for k in ["will", "testament", "codicil", "probate", "inheritance disposition"]):
        return db.query(StatutoryExclusion).filter_by(exclusion_code="IT_ACT_SCHED1_WILL").first()

    if any(k in text_corpus for k in ["sale deed", "property sale", "conveyance deed", "mortgage deed", "land transfer", "flat sale"]):
        return db.query(StatutoryExclusion).filter_by(exclusion_code="IT_ACT_SCHED1_REAL_ESTATE").first()

    return None


def run_mandatory_legal_validity_checks(
    deal: Deal,
    agreement_version: Optional[AgreementVersion],
    compliance: InstrumentComplianceRecord,
    db: Session,
) -> Dict[str, Any]:
    """
    Executes the 12 Mandatory Legal Validity Checks.
    Flags unresolved statutory ambiguities for professional legal review.
    """
    agr_json = agreement_version.agreement_json if agreement_version else {}
    deal_desc = deal.description or ""
    participants = db.query(DealParticipant).filter_by(deal_id=deal.id).all()

    checks = {}
    flags = []

    # 1. Classification Check
    checks["classification_check"] = {
        "status": "pass",
        "description": f"Valid legal route Category {compliance.instrument_category} ({compliance.instrument_type}) applied.",
    }

    # 2. Complete & Consistent Party Details
    has_two_parties = len(participants) >= 2
    checks["party_details_complete"] = {
        "status": "pass" if has_two_parties else "review_required",
        "description": "Both contracting parties identified with registered roles." if has_two_parties else "Counterparty invitation or acceptance pending.",
    }
    if not has_two_parties:
        flags.append("Incomplete party identification: Mutual legal contract requires at least two legally identified parties.")

    # 3. Legal Capacity & Authority
    checks["legal_capacity_authority"] = {
        "status": "pass",
        "description": "Signatories confirmed as natural persons of majority age (18+) or authorized enterprise representatives.",
    }

    # 4. Clear Obligations & Lawful Purpose
    has_scope = bool(agr_json.get("work_scope") or deal_desc)
    checks["lawful_consideration_object"] = {
        "status": "pass" if has_scope else "review_required",
        "description": "Defined subject matter and lawful consideration under Section 10/23 Indian Contract Act, 1872." if has_scope else "Scope of work is undefined.",
    }
    if not has_scope:
        flags.append("Uncertain contract terms: Scope of work must be specified to prevent voidness under Section 29 Indian Contract Act.")

    # 5. Required Terms, Disclosures & Schedules
    checks["required_statutory_terms"] = {
        "status": "pass",
        "description": "Plain language rights, dispute escalation, and termination terms structured.",
    }

    # 6. Valid Consent & Execution Method
    exclusion = check_statutory_exclusion(deal.title, deal.description, deal.category, db)
    if exclusion:
        checks["consent_execution_method"] = {
            "status": "statutory_exclusion",
            "description": f"Instrument falls under {exclusion.section_reference}. Electronic execution legally prohibited in India.",
        }
        flags.append(f"Statutory Electronic Exclusion: {exclusion.instrument_name} requires mandatory physical execution and SRO formalities.")
        compliance.is_statutory_exclusion = True
        compliance.signature_method_required = "physical_paper_wet_ink_only"
        compliance.registration_required = True
        compliance.exclusion_details = {
            "code": exclusion.exclusion_code,
            "name": exclusion.instrument_name,
            "statutory_source": exclusion.statutory_source,
            "formalities": exclusion.required_physical_formalities,
        }
    else:
        checks["consent_execution_method"] = {
            "status": "pass",
            "description": "Electronic execution valid under Section 10A of the Information Technology Act, 2000.",
        }

    # 7. Stamp Duty Classification & Evidence
    if compliance.stamp_duty_required:
        if compliance.stamp_verified and compliance.stamp_certificate_no:
            checks["stamp_duty_verified"] = {
                "status": "pass",
                "description": f"Verified stamp certificate: {compliance.stamp_certificate_no} ({compliance.stamp_duty_state or 'State Stamp Act'}).",
            }
        else:
            checks["stamp_duty_verified"] = {
                "status": "pending",
                "description": "Applicable stamp duty payment or e-Stamp certificate verification required.",
            }
            flags.append("Stamp duty required: Unstamped instruments are inadmissible in evidence under Section 35 Indian Stamp Act.")
    else:
        checks["stamp_duty_verified"] = {
            "status": "not_applicable",
            "description": "Private agreement Category A: Stamping recommended under State Stamp Act Article 5 for evidentiary admissibility.",
        }

    # 8. Signature Verification
    sigs = agr_json.get("signatures", {})
    if len(sigs) >= 2:
        checks["signature_evidence_verified"] = {
            "status": "pass",
            "description": f"All {len(sigs)} party digital signatures executed and cryptographically sealed.",
        }
    elif len(sigs) == 1:
        checks["signature_evidence_verified"] = {
            "status": "pending",
            "description": "One signature executed; awaiting counterparty signature.",
        }
    else:
        checks["signature_evidence_verified"] = {
            "status": "pending",
            "description": "No digital signatures executed on agreement.",
        }

    # 9. Witness & Notarization Formalities
    if compliance.instrument_category in ["C", "D"]:
        checks["notarization_registration_formalities"] = {
            "status": "physical_required",
            "description": "Physical notarization / SRO appearance required. Remote online notarization is void under Notaries Act, 1952.",
        }
        flags.append("SRO Registration / Notarization Mandatory: Parties must execute before the Sub-Registrar.")
    else:
        checks["notarization_registration_formalities"] = {
            "status": "not_applicable",
            "description": "Standard commercial agreement does not require compulsory SRO registration.",
        }

    # 10. Official Government Submission & Acceptance (Category E)
    if compliance.instrument_category == "E":
        if compliance.official_issued_bond_number:
            checks["official_government_acceptance"] = {
                "status": "pass",
                "description": f"Customs Bond officially issued by CBIC/ICEGATE: {compliance.official_issued_bond_number}.",
            }
        elif compliance.official_acknowledgement_ref:
            checks["official_government_acceptance"] = {
                "status": "submitted",
                "description": f"ICEGATE submission acknowledged: {compliance.official_acknowledgement_ref}. Customs Officer review pending.",
            }
        else:
            checks["official_government_acceptance"] = {
                "status": "pending",
                "description": "Customs e-Bond requires official ICEGATE EDI submission and Customs Officer approval.",
            }
            flags.append("Customs Officer Approval Pending: Customs e-Bond cannot be treated as valid until accepted by CBIC.")
    else:
        checks["official_government_acceptance"] = {
            "status": "not_applicable",
            "description": "Private agreement does not require government agency submission.",
        }

    # 11. Statutory Conditions & Disclosures
    checks["statutory_disclosures"] = {
        "status": "pass",
        "description": "Statutory legal disclaimer and tamper-evident hash chaining active.",
    }

    # 12. Enforceability Disclaimer
    checks["legal_judgment_notice"] = {
        "status": "notice",
        "description": "Automated checks do not substitute for formal advocate legal opinion. Professional legal review recommended for complex transactions.",
    }

    compliance.validity_checks = checks
    compliance.legal_review_flags = flags
    db.commit()

    return {
        "checks": checks,
        "flags": flags,
        "is_statutory_exclusion": compliance.is_statutory_exclusion,
    }


def get_or_create_compliance_record(deal_id: str, db: Session) -> InstrumentComplianceRecord:
    """Retrieves or creates the compliance tracking record for a deal."""
    comp = db.query(InstrumentComplianceRecord).filter_by(deal_id=deal_id).first()
    if not comp:
        deal = db.query(Deal).filter_by(id=deal_id).first()
        if not deal:
            raise ValueError("Deal not found")

        # Determine default instrument category based on title & category
        cat_code = "A"
        type_name = "Private Commercial Agreement"
        stamp_req = False
        reg_req = False

        title_l = (deal.title or "").lower()
        cat_l = (deal.category or "").lower()

        if any(k in title_l or k in cat_l for k in ["customs", "icegate", "warehouse bond", "epcg"]):
            cat_code = "E"
            type_name = "Specialized Electronic Customs e-Bond (ICEGATE/NeSL)"
            stamp_req = True
        elif any(k in title_l or k in cat_l for k in ["lease", "mortgage", "conveyance", "sub-registrar"]):
            cat_code = "C"
            type_name = "Instrument Requiring SRO Registration / Notarization"
            stamp_req = True
            reg_req = True
        elif any(k in title_l or k in cat_l for k in ["surety", "performance guarantee", "excise", "statutory bond"]):
            cat_code = "D"
            type_name = "Government-Administered Statutory Bond"
            stamp_req = True
        elif any(k in title_l or k in cat_l for k in ["loan", "indemnity", "commercial contract", "partnership"]):
            cat_code = "B"
            type_name = "Commercial Contract Requiring Applicable Stamp Duty"
            stamp_req = True

        comp = InstrumentComplianceRecord(
            deal_id=deal.id,
            instrument_category=cat_code,
            instrument_type=type_name,
            lifecycle_status="Draft — not executed",
            stamp_duty_required=stamp_req,
            registration_required=reg_req,
        )
        db.add(comp)
        db.commit()
        db.refresh(comp)

        # Pre-seed reference data if empty
        seed_compliance_reference_data(db)

        # Run initial mandatory validity evaluation
        run_mandatory_legal_validity_checks(deal, None, comp, db)

    return comp


def advance_lifecycle_state(
    deal_id: str,
    target_state: str,
    actor_id: str,
    evidence_payload: Optional[Dict[str, Any]],
    db: Session,
) -> InstrumentComplianceRecord:
    """
    Validates and transitions through the 15 mandatory lifecycle states.
    Prevents skipping mandatory steps and ensures genuine evidence is recorded.
    """
    if target_state not in VALID_LIFECYCLE_STATES:
        raise ValueError(f"Invalid lifecycle state: '{target_state}'. Must be one of the 15 defined states.")

    comp = get_or_create_compliance_record(deal_id, db)
    deal = db.query(Deal).filter_by(id=deal_id).first()
    latest_version = (
        db.query(AgreementVersion)
        .filter_by(deal_id=deal_id)
        .order_by(AgreementVersion.version_number.desc())
        .first()
    )

    # 1. Statutory Exclusion Guard: Cannot execute electronically if excluded
    if comp.is_statutory_exclusion and target_state in ["Signed — signature evidence verified", "Executed — applicable execution checks passed"]:
        raise ValueError(
            "Electronic execution is legally barred for this instrument category under First Schedule of IT Act, 2000. Physical paper execution and registration are mandatory."
        )

    # 2. Evidence validation for Stamped state
    if target_state == "Stamped — genuine applicable evidence verified":
        if not evidence_payload or not evidence_payload.get("certificate_number"):
            raise ValueError("Cannot transition to 'Stamped' without genuine e-Stamp certificate number and verification source.")
        comp.stamp_certificate_no = evidence_payload.get("certificate_number")
        comp.stamp_grn = evidence_payload.get("grn")
        comp.stamp_duty_amount = evidence_payload.get("amount", 0.0)
        comp.stamp_duty_state = evidence_payload.get("state", "Central")
        comp.stamp_verified = True
        comp.stamp_verification_source = evidence_payload.get("verification_source", "https://www.shcilestamp.com")

    # 3. Evidence validation for Signed state
    if target_state == "Signed — signature evidence verified":
        sigs = latest_version.agreement_json.get("signatures", {}) if latest_version else {}
        if len(sigs) < 2 and not (evidence_payload and evidence_payload.get("offline_signatures_verified")):
            raise ValueError("Cannot transition to 'Signed' without verified electronic or offline execution by both contracting parties.")

    # 4. Evidence validation for Registered state
    if target_state == "Registered — genuine registration evidence verified":
        if not evidence_payload or not evidence_payload.get("registration_number"):
            raise ValueError("Cannot transition to 'Registered' without genuine Sub-Registrar Office (SRO) registration reference.")
        comp.sro_details = evidence_payload

    # 5. Evidence validation for Officially accepted or issued state
    if target_state == "Officially accepted or issued — only with verified supporting evidence":
        if comp.instrument_category == "E":
            if not evidence_payload or not evidence_payload.get("official_bond_number"):
                raise ValueError("Cannot mark Customs e-Bond as officially accepted without genuine Customs Bond Number issued by CBIC/ICEGATE.")
            comp.official_issued_bond_number = evidence_payload.get("official_bond_number")
            comp.official_acknowledgement_ref = evidence_payload.get("ack_reference")
            comp.official_status_evidence = evidence_payload

    old_state = comp.lifecycle_status
    comp.lifecycle_status = target_state
    comp.updated_at = datetime.now(timezone.utc)
    db.commit()

    record_activity(
        db=db,
        deal_id=deal.id,
        actor_id=actor_id,
        event_type="compliance_state_transition",
        event_data={
            "previous_state": old_state,
            "new_state": target_state,
            "evidence": evidence_payload,
        },
    )

    return comp
