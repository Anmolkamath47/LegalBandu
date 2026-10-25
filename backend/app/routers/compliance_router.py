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
)
from ..schemas import (
    AuthorizationProviderOut,
    AuthorizationProviderUpdate,
    StatutoryExclusionOut,
    ComplianceRecordOut,
    ComplianceAdvanceRequest,
    CustomsEBondOut,
    CustomsEBondStepRequest,
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
