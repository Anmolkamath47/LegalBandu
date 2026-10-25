import io
import os
import json
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session

from ..auth import get_current_user, verify_deal_participant, AuthenticatedUser
from ..config import settings
from ..database import get_db
from ..models import Deal, BondDocument, Profile, AgreementVersion, DealAnalysis, DealParticipant, AgreementApproval, ActivityLog
from ..schemas import BondDocumentOut, BondDocumentCreate
from ..services.ai_detector_service import detect_ai_in_document, extract_bond_terms
from ..services.audit_service import record_activity
from ..services.notification_service import create_notification

logger = logging.getLogger("legalbandu.bonds")

router = APIRouter(prefix="", tags=["Bonds & AI Detector"])


def _apply_bond_to_deal_agreement(deal: Deal, bond: BondDocument, current_user: AuthenticatedUser, db: Session):
    """
    Auto-stores verified authentic legal bond terms into the deal agreement version.
    """
    terms = bond.extracted_terms or {}
    bond_title = terms.get("bond_type", bond.bond_type or "Bond Agreement")
    obligor = terms.get("obligor", "Principal / Executant")
    obligee = terms.get("obligee", "Beneficiary / Obligee")
    amount = terms.get("bond_amount", "To be specified")
    core_obl = terms.get("core_obligation", "Performance and fulfillment of agreed covenants.")
    penalty = terms.get("default_penalty_terms", f"Forfeiture of {amount} upon default.")
    stamp_ref = terms.get("stamp_reference", "Digital Record")

    agreement_json = {
        "work_scope": f"{bond_title} execution. Obligor ({obligor}) guarantees faithful performance of covenants to Obligee ({obligee}). Core obligation: {core_obl}",
        "financial_terms": f"Bond Guarantee Sum: {amount}. Stamp / Registration Ref: {stamp_ref}. Default Penalty: {penalty}",
        "timeline": "Effective immediately upon bilateral execution and valid until all underlying obligations are discharged.",
        "responsibilities": f"1. {obligor} (Obligor) shall strictly fulfill all duties and indemnify {obligee}.\n2. {obligee} (Obligee) shall release the bond upon verified completion.",
        "delivery_acceptance": "Verification of non-default and formal written discharge by the Obligee.",
        "cancellation_refunds": "Subject to mutual written consent and statutory bond cancellation procedures.",
        "unresolved_terms": [],
    }

    plain_text = (
        f"AGREEMENT & BOND COVENANT: {deal.title}\n\n"
        f"TYPE: {bond_title}\n"
        f"OBLIGOR (EXECUTANT): {obligor}\n"
        f"OBLIGEE (BENEFICIARY): {obligee}\n\n"
        f"1. SCOPE OF GUARANTEE & COVENANT\n{agreement_json['work_scope']}\n\n"
        f"2. FINANCIAL TERMS & PENALTY BOND SUM\n{agreement_json['financial_terms']}\n\n"
        f"3. DURATION & TIMELINE\n{agreement_json['timeline']}\n\n"
        f"4. MUTUAL RESPONSIBILITIES\n{agreement_json['responsibilities']}\n\n"
        f"AI DETECTION STATUS AT IMPORT: {bond.ai_verdict} (Score: {int(bond.ai_detection_score*100)}%)\n"
    )

    latest_v = (
        db.query(AgreementVersion)
        .filter(AgreementVersion.deal_id == deal.id)
        .order_by(AgreementVersion.version_number.desc())
        .first()
    )
    next_ver_num = (latest_v.version_number + 1) if latest_v else 1

    new_version = AgreementVersion(
        deal_id=str(deal.id),
        version_number=next_ver_num,
        agreement_json=agreement_json,
        agreement_text=plain_text,
        created_by=str(current_user.id),
    )
    db.add(new_version)
    db.commit()
    db.refresh(new_version)

    deal.current_version_id = str(new_version.id)
    deal.status = "awaiting_review"
    db.commit()

    participants = db.query(DealParticipant).filter(DealParticipant.deal_id == str(deal.id)).all()
    for p in participants:
        approval = AgreementApproval(
            agreement_version_id=str(new_version.id),
            participant_id=p.id,
            status="pending",
        )
        db.add(approval)
    db.commit()

    record_activity(
        db=db,
        deal_id=str(deal.id),
        actor_id=str(current_user.id),
        event_type="agreement_version_created_from_bond",
        event_data={
            "bond_id": str(bond.id),
            "version_id": str(new_version.id),
            "version_number": next_ver_num,
        },
    )
    return new_version, next_ver_num


def extract_text_from_file_bytes(file_bytes: bytes, filename: str) -> str:
    """Extracts plain text from PDF, TXT, or common document formats."""
    ext = os.path.splitext(filename)[1].lower()

    if ext == ".pdf":
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            text_parts = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            extracted = "\n".join(text_parts).strip()
            if extracted:
                return extracted
        except Exception as e:
            logger.warning(f"pypdf extraction error ({e}), trying fallback string scan.")

        # Fallback raw string scan for stream text in PDF
        ascii_matches = []
        for line in file_bytes.split(b"\n"):
            try:
                decoded = line.decode("ascii", errors="ignore").strip()
                if len(decoded) > 8 and any(c.isalpha() for c in decoded):
                    ascii_matches.append(decoded)
            except Exception:
                pass
        if ascii_matches:
            return "\n".join(ascii_matches[:100])
        return "Scanned PDF Bond Document (Digital copy preserved)"

    # Text / Markdown / Chat files
    try:
        return file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return file_bytes.decode("latin-1")
        except Exception:
            return "Unable to decode text stream from uploaded file."


@router.post("/deals/{deal_id}/bonds", response_model=BondDocumentOut)
async def upload_bond_document(
    deal_id: str,
    bond_type: str = Form("Legal Bond"),
    content: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Uploads an existing legal bond, indemnity bond, stamp agreement, or promissory note.
    Runs deep AI synthetic content detection to alert if the document was generated by AI.
    Extracts key legal terms (obligor, obligee, penalty sum, stamp duty reference).
    """
    verify_deal_participant(deal_id, current_user, db)
    deal = db.query(Deal).filter(Deal.id == deal_id).first()

    raw_text = ""
    filename = "Pasted_Bond_Text.txt"
    file_type = "txt"

    if file:
        filename = file.filename or "Uploaded_Bond.pdf"
        file_bytes = await file.read()
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if len(file_bytes) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Bond file exceeds limit of {settings.MAX_UPLOAD_SIZE_MB}MB.",
            )
        file_type = os.path.splitext(filename)[1].replace(".", "").lower() or "pdf"
        raw_text = extract_text_from_file_bytes(file_bytes, filename)
    elif content and content.strip():
        raw_text = content.strip()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please upload a bond document file (.pdf, .txt) or paste bond text.",
        )

    # 1. Run AI Detection Engine
    detection_res = detect_ai_in_document(raw_text, filename)

    # 2. Extract Bond Terms
    extracted_terms = extract_bond_terms(raw_text)
    if bond_type and bond_type != "Legal Bond":
        extracted_terms["bond_type"] = bond_type

    # 3. Create Bond Document Record
    bond = BondDocument(
        deal_id=str(deal.id),
        uploaded_by=str(current_user.id),
        filename=filename,
        file_type=file_type,
        bond_type=extracted_terms.get("bond_type", bond_type),
        document_text=raw_text,
        is_ai_generated=detection_res["is_ai_generated"],
        ai_detection_score=detection_res["ai_detection_score"],
        ai_verdict=detection_res["ai_verdict"],
        ai_confidence=detection_res["ai_confidence"],
        ai_markers=detection_res["ai_markers"],
        ai_alert_triggered=detection_res["ai_alert_triggered"],
        extracted_terms=extracted_terms,
    )
    db.add(bond)
    db.commit()
    db.refresh(bond)

    # 4. Audit Log
    record_activity(
        db=db,
        deal_id=str(deal.id),
        actor_id=str(current_user.id),
        event_type="bond_uploaded_and_scanned",
        event_data={
            "bond_id": str(bond.id),
            "filename": filename,
            "bond_type": bond.bond_type,
            "is_ai_generated": bond.is_ai_generated,
            "ai_score": bond.ai_detection_score,
            "ai_verdict": bond.ai_verdict,
            "alert_triggered": bond.ai_alert_triggered,
        },
    )

    # 5. If AI detected, trigger immediate notification; if authentic, auto-store in legal agreement
    auto_stored = False
    new_version_num = None
    if bond.is_ai_generated:
        create_notification(
            db=db,
            user_id=str(current_user.id),
            deal_id=str(deal.id),
            title="⚠️ AI-Generated Bond Content Detected!",
            message=f"Uploaded bond '{filename}' contains synthetic AI text markers ({int(bond.ai_detection_score*100)}% AI probability). Please verify enforceability.",
        )
    else:
        # Automatic requirement: "if it is not ai generated then store it in legal aggrement"
        try:
            new_v, next_ver_num = _apply_bond_to_deal_agreement(deal, bond, current_user, db)
            auto_stored = True
            new_version_num = next_ver_num
        except Exception as e:
            logger.warning(f"Auto-store bond into agreement notice: {e}")

    prof = db.query(Profile).filter(Profile.id == current_user.id).first()
    uploader_name = prof.full_name if prof else current_user.email

    return BondDocumentOut(
        id=bond.id,
        deal_id=bond.deal_id,
        uploaded_by=bond.uploaded_by,
        uploaded_by_name=uploader_name,
        filename=bond.filename,
        file_type=bond.file_type,
        bond_type=bond.bond_type,
        document_text=bond.document_text,
        is_ai_generated=bond.is_ai_generated,
        ai_detection_score=bond.ai_detection_score,
        ai_verdict=bond.ai_verdict,
        ai_confidence=bond.ai_confidence,
        ai_markers=bond.ai_markers,
        ai_alert_triggered=bond.ai_alert_triggered,
        extracted_terms=bond.extracted_terms,
        auto_stored_in_agreement=auto_stored,
        agreement_version_number=new_version_num,
        created_at=bond.created_at,
    )


@router.get("/deals/{deal_id}/bonds", response_model=List[BondDocumentOut])
def get_deal_bonds(
    deal_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves all uploaded bonds and AI scan reports for a deal room."""
    verify_deal_participant(deal_id, current_user, db)
    bonds = (
        db.query(BondDocument)
        .filter(BondDocument.deal_id == deal_id)
        .order_by(BondDocument.created_at.desc())
        .all()
    )

    # Query logs to see which bonds were converted/stored into agreement versions
    agreement_logs = (
        db.query(ActivityLog)
        .filter(
            ActivityLog.deal_id == deal_id,
            ActivityLog.event_type == "agreement_version_created_from_bond",
        )
        .all()
    )
    bond_to_version = {}
    for l in agreement_logs:
        edata = l.event_data or {}
        b_id = str(edata.get("bond_id", ""))
        v_num = edata.get("version_number")
        if b_id:
            bond_to_version[b_id] = v_num

    results = []
    for b in bonds:
        prof = db.query(Profile).filter(Profile.id == b.uploaded_by).first()
        b_id_str = str(b.id)
        is_stored = (b_id_str in bond_to_version) or (not b.is_ai_generated)
        v_num = bond_to_version.get(b_id_str)
        results.append(
            BondDocumentOut(
                id=b.id,
                deal_id=b.deal_id,
                uploaded_by=b.uploaded_by,
                uploaded_by_name=prof.full_name if prof else "Participant",
                filename=b.filename,
                file_type=b.file_type,
                bond_type=b.bond_type,
                document_text=b.document_text,
                is_ai_generated=b.is_ai_generated,
                ai_detection_score=b.ai_detection_score,
                ai_verdict=b.ai_verdict,
                ai_confidence=b.ai_confidence,
                ai_markers=b.ai_markers,
                ai_alert_triggered=b.ai_alert_triggered,
                extracted_terms=b.extracted_terms,
                auto_stored_in_agreement=is_stored,
                agreement_version_number=v_num,
                created_at=b.created_at,
            )
        )
    return results


@router.delete("/deals/{deal_id}/bonds/{bond_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bond_document(
    deal_id: str,
    bond_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deletes an uploaded bond document."""
    verify_deal_participant(deal_id, current_user, db)
    bond = db.query(BondDocument).filter(BondDocument.id == bond_id, BondDocument.deal_id == deal_id).first()
    if not bond:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bond document not found.")

    db.delete(bond)
    db.commit()
    return None


@router.post("/deals/{deal_id}/bonds/{bond_id}/apply-to-agreement")
def apply_bond_terms_to_agreement(
    deal_id: str,
    bond_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Applies extracted bond terms (obligor, obligee, penalty sum, obligations)
    directly into the deal room's bilateral plain agreement.
    """
    verify_deal_participant(deal_id, current_user, db)
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    bond = db.query(BondDocument).filter(BondDocument.id == bond_id, BondDocument.deal_id == deal_id).first()
    if not bond:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bond document not found.")

    new_version, next_ver_num = _apply_bond_to_deal_agreement(deal, bond, current_user, db)

    return {
        "status": "success",
        "message": f"Bond terms successfully applied to Agreement Version {next_ver_num}.0",
        "version_id": str(new_version.id),
        "version_number": next_ver_num,
    }
