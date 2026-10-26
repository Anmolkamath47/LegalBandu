import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import get_current_user, verify_deal_participant, AuthenticatedUser
from ..database import get_db
from ..models import (
    Deal,
    AgreementVersion,
    AuthorizationProvider,
    StatutoryExclusion,
    InstrumentComplianceRecord,
    CustomsEBondRecord,
    Profile,
    DealParticipant,
    AgreementApproval,
)
from ..schemas import (
    AuthorizationProviderOut,
    AuthorizationProviderUpdate,
    StatutoryExclusionOut,
    ComplianceRecordOut,
    ComplianceAdvanceRequest,
    CustomsEBondOut,
    CustomsEBondStepRequest,
    VerifyStampCertificateRequest,
    ApplyTemplateRequest,
)
from ..services.legal_compliance_service import (
    seed_compliance_reference_data,
    get_or_create_compliance_record,
    run_mandatory_legal_validity_checks,
    advance_lifecycle_state,
    VALID_LIFECYCLE_STATES,
)
from ..services.customs_bond_service import (
    get_or_create_customs_bond,
    process_customs_bond_step,
    CUSTOMS_BOND_WORKFLOW_STEPS,
)
from ..services.legal_readiness_service import (
    get_esign_providers_evaluation,
    calculate_state_stamp_duty,
    verify_stamp_certificate_data,
    get_lawyer_approved_templates,
    generate_section_65b_certificate,
    evaluate_bond_readiness_checklist,
)
from ..services.audit_service import record_activity


logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["Legal Compliance & Government Authorization"])


# =========================================================================
# 1. Administrator Authorization Register & Statutory Exclusions
# =========================================================================
@router.get("/compliance/authorization-providers", response_model=List[AuthorizationProviderOut])
def get_authorization_providers(db: Session = Depends(get_db)):
    """
    Returns the maintained Register of Government & Statutory Integrations.
    Transparently reveals actual authorization state: NOT_ASSESSED, ELIGIBILITY_REVIEW_REQUIRED,
    APPLICATION_REQUIRED, APPLICATION_SUBMITTED, APPROVED_PENDING_INTEGRATION, PRODUCTION_VERIFIED,
    EXPIRED, SUSPENDED, REJECTED.
    """
    seed_compliance_reference_data(db)
    return db.query(AuthorizationProvider).order_by(AuthorizationProvider.name.asc()).all()


@router.patch("/compliance/authorization-providers/{provider_code}", response_model=AuthorizationProviderOut)
def update_authorization_provider(
    provider_code: str,
    data: AuthorizationProviderUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Administrator-only endpoint to record genuine onboarding evidence, license references,
    and update integration status. Only PRODUCTION_VERIFIED after genuine proof.
    """
    prov = db.query(AuthorizationProvider).filter_by(provider_code=provider_code).first()
    if not prov:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found.")

    valid_statuses = [
        "NOT_ASSESSED",
        "ELIGIBILITY_REVIEW_REQUIRED",
        "APPLICATION_REQUIRED",
        "APPLICATION_SUBMITTED",
        "APPROVED_PENDING_INTEGRATION",
        "PRODUCTION_VERIFIED",
        "EXPIRED",
        "SUSPENDED",
        "REJECTED",
    ]
    if data.authorization_status not in valid_statuses:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid status: {data.authorization_status}")

    # Production Acceptance Rule: Sandbox is not government authorization
    if data.authorization_status == "PRODUCTION_VERIFIED":
        if not data.approval_reference or not data.supporting_evidence:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot mark provider PRODUCTION_VERIFIED without an official approval reference and supporting verifiable evidence.",
            )

    prov.authorization_status = data.authorization_status
    if data.approval_reference is not None:
        prov.approval_reference = data.approval_reference
    if data.supporting_evidence is not None:
        prov.supporting_evidence = data.supporting_evidence
    if data.issue_date is not None:
        prov.issue_date = data.issue_date
    if data.expiry_date is not None:
        prov.expiry_date = data.expiry_date
    if data.restrictions is not None:
        prov.restrictions = data.restrictions
    if data.is_sandbox_only is not None:
        prov.is_sandbox_only = data.is_sandbox_only

    prov.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(prov)
    return prov


@router.get("/compliance/statutory-exclusions", response_model=List[StatutoryExclusionOut])
def get_statutory_exclusions(db: Session = Depends(get_db)):
    """
    Returns the maintained Register of Statutory Exclusions under the First Schedule
    of the Information Technology Act, 2000 (instruments barred from electronic execution).
    """
    seed_compliance_reference_data(db)
    return db.query(StatutoryExclusion).order_by(StatutoryExclusion.created_at.asc()).all()


# =========================================================================
# 2. Per-Deal Compliance Record & 12 Validity Checks
# =========================================================================
@router.get("/deals/{deal_id}/compliance", response_model=ComplianceRecordOut)
def get_deal_compliance(
    deal_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns the comprehensive legal compliance record for a deal, including
    instrument category (A/B/C/D/E), current lifecycle state (from the 15 states),
    validity check results, and verified stamp/signature evidence.
    """
    verify_deal_participant(deal_id, current_user, db)
    comp = get_or_create_compliance_record(deal_id, db)

    deal = db.query(Deal).filter_by(id=deal_id).first()
    latest_version = (
        db.query(AgreementVersion)
        .filter_by(deal_id=deal_id)
        .order_by(AgreementVersion.version_number.desc())
        .first()
    )

    # Automatically re-run checks if empty
    if not comp.validity_checks:
        run_mandatory_legal_validity_checks(deal, latest_version, comp, db)

    return comp


@router.post("/deals/{deal_id}/compliance/evaluate", response_model=ComplianceRecordOut)
def evaluate_deal_compliance(
    deal_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Re-evaluates the 12 mandatory legal validity checks against the latest deal data."""
    verify_deal_participant(deal_id, current_user, db)
    deal = db.query(Deal).filter_by(id=deal_id).first()
    comp = get_or_create_compliance_record(deal_id, db)
    latest_version = (
        db.query(AgreementVersion)
        .filter_by(deal_id=deal_id)
        .order_by(AgreementVersion.version_number.desc())
        .first()
    )

    run_mandatory_legal_validity_checks(deal, latest_version, comp, db)
    db.refresh(comp)
    return comp


@router.post("/deals/{deal_id}/compliance/advance-state", response_model=ComplianceRecordOut)
def advance_deal_compliance_state(
    deal_id: str,
    data: ComplianceAdvanceRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Transitions the instrument through the 15 granular lifecycle states.
    Validates genuine evidence and prevents skipping mandatory statutory steps.
    """
    verify_deal_participant(deal_id, current_user, db)
    try:
        updated_comp = advance_lifecycle_state(
            deal_id=deal_id,
            target_state=data.target_state,
            actor_id=current_user.id,
            evidence_payload=data.evidence_payload,
            db=db,
        )
        return updated_comp
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# =========================================================================
# 3. Category E: Specialized Customs e-Bond Workflow (ICEGATE & NeSL)
# =========================================================================
@router.get("/deals/{deal_id}/customs-bond")
def get_customs_bond_status(
    deal_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns the customs e-Bond particulars, current 11-step progress, and official status."""
    verify_deal_participant(deal_id, current_user, db)
    bond = get_or_create_customs_bond(deal_id, db)
    return {
        "current_step": bond.workflow_step,
        "bond": {
            "iec_number": bond.iec_number,
            "entity_pan": bond.entity_pan,
            "customs_station_code": bond.customs_station_code,
            "bond_category": bond.bond_category,
            "bond_amount": bond.bond_amount,
            "bank_guarantee_amount": bond.bank_guarantee_amount,
            "icegate_ack_number": bond.icegate_ack_number,
            "customs_officer_approval_ref": bond.customs_officer_approval_ref,
            "official_bond_number": bond.official_bond_number,
            "declarations_accepted": bond.declarations_accepted,
            "step_status_log": bond.step_status_log,
        },
        "steps_catalog": CUSTOMS_BOND_WORKFLOW_STEPS,
    }


@router.post("/deals/{deal_id}/customs-bond/step")
def submit_customs_bond_step(
    deal_id: str,
    data: CustomsEBondStepRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Executes a step in the 11-step ICEGATE customs e-Bond sequence."""
    verify_deal_participant(deal_id, current_user, db)
    try:
        res = process_customs_bond_step(
            deal_id=deal_id,
            step_num=data.step_num,
            step_data=data.step_data,
            actor_id=current_user.id,
            db=db,
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# =========================================================================
# 4. CCA-Approved e-Signature Providers & Compliant eSign Workflows
# =========================================================================
@router.get("/compliance/esign-providers")
def get_esign_providers():
    """
    Evaluates Indian electronic-signature service providers (eMudhra, Protean eGov, Digio, Leegality).
    Provides formal signing workflow, authentication options, signature evidence details,
    and direct link to official CCA directory.
    """
    return get_esign_providers_evaluation()


# =========================================================================
# 5. State-Aware Stamp Duty & e-Stamping Workflow (Karnataka Focus)
# =========================================================================
@router.get("/compliance/stamp-duty/calculate")
def get_stamp_duty_calculation(
    state: str = "Karnataka",
    instrument_type: str = "commercial_service",
    consideration_amount: float = 0.0,
    is_bond: bool = False,
    is_indemnity: bool = False,
):
    """
    State-aware stamp-duty calculation under current Karnataka Stamp Act (2023/2024 amendments)
    and key state stamp acts. Calculates applicable duty based on category, consideration, and terms.
    """
    return calculate_state_stamp_duty(
        state=state,
        instrument_type=instrument_type,
        consideration_amount=consideration_amount,
        is_bond=is_bond,
        is_indemnity=is_indemnity,
    )


@router.post("/compliance/stamp-duty/verify")
def verify_stamp_duty_certificate(
    data: VerifyStampCertificateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Verifies an authorized e-stamping certificate (SHCIL / NeSL DDE) against state duty schedules.
    """
    return verify_stamp_certificate_data(
        certificate_number=data.certificate_number,
        grn=data.grn,
        amount_paid=data.amount_paid,
        state=data.state,
        party_a=data.party_a or "",
        party_b=data.party_b or "",
    )


# =========================================================================
# 6. Indian Contract Law Review & Approved Lawyer Templates (Section 10 ICA)
# =========================================================================
@router.get("/compliance/templates")
def get_templates():
    """
    Returns library of pre-approved lawyer agreement and bond templates vetted under
    Section 10 of the Indian Contract Act, 1872 (Free consent, competent parties, lawful consideration).
    """
    return get_lawyer_approved_templates()


@router.post("/deals/{deal_id}/apply-template")
def apply_lawyer_template(
    deal_id: str,
    data: ApplyTemplateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Applies a lawyer-approved contract/bond template to the deal's active agreement version.
    Interpolates contracting parties, scope, financial terms, and governing law.
    """
    verify_deal_participant(deal_id, current_user, db)
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found.")

    templates = get_lawyer_approved_templates()
    selected_tpl = next((t for t in templates if t["template_id"] == data.template_id), None)
    if not selected_tpl:
        raise HTTPException(status_code=400, detail="Invalid template ID specified.")

    participants = db.query(DealParticipant).filter(DealParticipant.deal_id == deal.id).all()
    party_a_name = "First Party"
    party_b_name = "Second Party"
    for p in participants:
        prof = db.query(Profile).filter(Profile.id == p.user_id).first() if p.user_id else None
        p_name = (prof.full_name if prof else None) or p.invitation_email
        if p.role == "creator" and p_name:
            party_a_name = p_name
        elif p.role == "counterparty" and p_name:
            party_b_name = p_name

    today = datetime.now(timezone.utc).strftime("%d %B %Y")
    work_scope = deal.description or "Scope of deliverables as agreed between the Parties."
    financial_terms = f"Agreed consideration in {deal.currency} as per mutual specifications."
    timeline = "As mutually agreed in writing by the Parties."
    responsibilities = "Both Parties shall discharge their obligations in good faith and with professional diligence."

    # If current version exists, use its terms
    latest_v = (
        db.query(AgreementVersion)
        .filter(AgreementVersion.deal_id == deal.id)
        .order_by(AgreementVersion.version_number.desc())
        .first()
    )
    if latest_v and latest_v.agreement_json:
        aj = latest_v.agreement_json
        work_scope = aj.get("work_scope") or work_scope
        financial_terms = aj.get("financial_terms") or financial_terms
        timeline = aj.get("timeline") or timeline
        responsibilities = aj.get("responsibilities") or responsibilities

    formatted_text = selected_tpl["default_text"].format(
        date=today,
        party_a_name=party_a_name,
        party_b_name=party_b_name,
        work_scope=work_scope,
        financial_terms=financial_terms,
        timeline=timeline,
        responsibilities=responsibilities,
        currency=deal.currency or "INR",
    )

    new_v_num = (latest_v.version_number + 1) if latest_v else 1
    new_version = AgreementVersion(
        deal_id=deal.id,
        version_number=new_v_num,
        agreement_json={
            "work_scope": work_scope,
            "financial_terms": financial_terms,
            "timeline": timeline,
            "responsibilities": responsibilities,
            "applied_template_id": selected_tpl["template_id"],
            "applied_template_title": selected_tpl["title"],
            "legal_basis": selected_tpl["legal_basis"],
        },
        agreement_text=formatted_text,
        created_by=current_user.id,
    )
    db.add(new_version)
    db.commit()
    db.refresh(new_version)

    deal.current_version_id = new_version.id
    deal.status = "draft"
    db.commit()

    # Reset approvals
    for p in participants:
        db.add(AgreementApproval(
            agreement_version_id=new_version.id,
            participant_id=p.id,
            status="pending",
        ))
    db.commit()

    record_activity(
        db=db,
        deal_id=deal.id,
        actor_id=current_user.id,
        event_type="template_applied",
        event_data={
            "template_id": selected_tpl["template_id"],
            "template_title": selected_tpl["title"],
            "version_number": new_v_num,
        },
    )

    return {
        "message": f"Applied lawyer-approved template '{selected_tpl['title']}' as Version {new_v_num}.",
        "version_id": new_version.id,
        "version_number": new_v_num,
        "template": selected_tpl,
    }


# =========================================================================
# 7. 9-Point Legal-Document / Bond Readiness Checklist & Audit Certificate
# =========================================================================
@router.get("/deals/{deal_id}/readiness-checklist")
def get_deal_readiness_checklist(
    deal_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Evaluates the 9-point Bond and Legal-Document Readiness Checklist:
    Parties, Legal capacity, Clear terms, Consideration and purpose, Free consent,
    Applicable stamp duty, Signatures, Witnesses & registration, Final copy.
    """
    verify_deal_participant(deal_id, current_user, db)
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found.")

    version = (
        db.query(AgreementVersion)
        .filter(AgreementVersion.id == deal.current_version_id)
        .first()
    )
    compliance = (
        db.query(InstrumentComplianceRecord)
        .filter(InstrumentComplianceRecord.deal_id == deal.id)
        .first()
    )

    return evaluate_bond_readiness_checklist(deal, version, compliance, db)


@router.get("/deals/{deal_id}/audit-certificate")
def get_deal_audit_certificate(
    deal_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generates cryptographic SHA-256 hash and Section 65B Indian Evidence Act /
    Section 63 BSA 2023 Electronic Record Integrity Certificate for the finalized agreement.
    """
    verify_deal_participant(deal_id, current_user, db)
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found.")

    version = (
        db.query(AgreementVersion)
        .filter(AgreementVersion.id == deal.current_version_id)
        .first()
    )
    if not version:
        latest = (
            db.query(AgreementVersion)
            .filter(AgreementVersion.deal_id == deal.id)
            .order_by(AgreementVersion.version_number.desc())
            .first()
        )
        version = latest

    if not version:
        raise HTTPException(status_code=400, detail="No agreement version recorded yet to generate audit certificate.")

    return generate_section_65b_certificate(deal, version, db)

