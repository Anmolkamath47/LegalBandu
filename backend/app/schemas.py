from pydantic import BaseModel, EmailStr, Field, ConfigDict, BeforeValidator
from typing import Optional, List, Dict, Any, Annotated, Union
from datetime import datetime
from uuid import UUID

# Robust string ID type that automatically stringifies UUID objects returned by PostgreSQL/SQLAlchemy
StrId = Annotated[str, BeforeValidator(lambda v: str(v) if v is not None else v)]


# ==========================================
# Profiles & Users
# ==========================================
class UserProfile(BaseModel):
    id: StrId
    email: str
    full_name: str

    model_config = ConfigDict(from_attributes=True)


class ProfileUpdate(BaseModel):
    full_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: Optional[str] = None


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserProfile


# ==========================================
# Deals & Participants
# ==========================================
class DealCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    category: str = Field(default="Services", max_length=100)
    description: str = Field(default="")
    currency: str = Field(default="INR", max_length=10)
    counterparty_name: Optional[str] = None
    counterparty_email: Optional[EmailStr] = None
    expected_start_date: Optional[str] = None
    expected_completion_date: Optional[str] = None


class DealUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    category: Optional[str] = None
    description: Optional[str] = None
    currency: Optional[str] = None
    status: Optional[str] = None


class ParticipantOut(BaseModel):
    id: StrId
    deal_id: StrId
    user_id: Optional[StrId] = None
    role: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    joined_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DealOut(BaseModel):
    id: StrId
    creator_id: StrId
    creator_name: Optional[str] = None
    title: str
    category: str
    description: str
    currency: str
    status: str
    current_version_id: Optional[StrId] = None
    current_version_number: Optional[int] = None
    participants: List[ParticipantOut] = []
    counterparty: Optional[ParticipantOut] = None
    next_action: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DashboardStats(BaseModel):
    total_deals: int = 0
    draft_deals: int = 0
    awaiting_action: int = 0
    mutually_confirmed: int = 0


# ==========================================
# Invitations
# ==========================================
class InvitationCreate(BaseModel):
    email: Optional[EmailStr] = None
    expires_in_days: int = Field(default=7, ge=1, le=30)


class InvitationOut(BaseModel):
    invitation_url: str
    invitation_email: Optional[str] = None
    expires_at: Optional[datetime] = None
    status: str = "pending"


class InvitationInfo(BaseModel):
    deal_id: StrId
    deal_title: str
    creator_name: str
    category: str
    description: str
    currency: str
    is_expired: bool
    is_already_accepted: bool
    invitation_email: Optional[str] = None


# ==========================================
# Conversations & Messages
# ==========================================
class ConversationCreate(BaseModel):
    source_type: str = Field(default="paste")  # 'paste' or 'file_upload'
    original_content: str = Field(..., min_length=1)


class MessageOut(BaseModel):
    id: StrId
    speaker_label: str
    message_text: str
    message_timestamp: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationOut(BaseModel):
    id: StrId
    deal_id: StrId
    uploaded_by: StrId
    uploaded_by_name: Optional[str] = None
    source_type: str
    original_content: str
    audio_url: Optional[str] = None
    audio_filename: Optional[str] = None
    audio_duration: Optional[int] = None
    image_url: Optional[str] = None
    messages: List[MessageOut] = []
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# AI Conversation Analysis
# ==========================================
class ExtractedField(BaseModel):
    field_name: str
    value: Optional[str] = None
    status: str = Field(
        ...,
        description="found_in_conversation, proposed_not_confirmed, unclear, missing, conflicting, reviewed_by_participants",
    )
    confidence: Optional[str] = "medium"  # high, medium, low
    supporting_quote: Optional[str] = None
    is_confirmed: bool = False


class AnalysisSchema(BaseModel):
    deal_title: Optional[str] = None
    parties_involved: Optional[List[str]] = None
    price: Optional[ExtractedField] = None
    currency: Optional[ExtractedField] = None
    work_scope: Optional[ExtractedField] = None
    payment_terms: Optional[ExtractedField] = None
    start_date: Optional[ExtractedField] = None
    completion_deadline: Optional[ExtractedField] = None
    delivery_acceptance_conditions: Optional[ExtractedField] = None
    responsibilities: Optional[ExtractedField] = None
    cancellation_refund_conditions: Optional[ExtractedField] = None
    warranty_revision_terms: Optional[ExtractedField] = None
    additional_agreed_conditions: Optional[ExtractedField] = None
    unresolved_terms: List[str] = []
    contradictory_statements: List[str] = []
    clarification_questions: List[str] = []


class AnalysisOut(BaseModel):
    id: StrId
    deal_id: StrId
    conversation_id: Optional[StrId] = None
    analysis: Dict[str, Any]
    created_by: StrId
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Clarifications
# ==========================================
class ClarificationCreate(BaseModel):
    field_name: str
    question: str
    answer: str


class ClarificationUpdate(BaseModel):
    answer: str


class ClarificationOut(BaseModel):
    id: StrId
    deal_id: StrId
    field_name: str
    question: str
    answer: str
    answered_by: StrId
    answered_by_name: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Agreement Versions & Approvals
# ==========================================
class AgreementSection(BaseModel):
    title: str
    content: str
    status: str = "reviewed"  # reviewed, unconfirmed, missing


class AgreementCreate(BaseModel):
    agreement_json: Dict[str, Any]
    agreement_text: str


class AgreementUpdate(BaseModel):
    agreement_json: Dict[str, Any]
    agreement_text: str
    change_summary: Optional[str] = "Updated terms"


class ApprovalRequest(BaseModel):
    status: str = Field(..., pattern="^(approved|changes_requested)$")
    comment: Optional[str] = None


class ApprovalOut(BaseModel):
    id: StrId
    participant_id: StrId
    participant_name: str
    role: str
    status: str  # approved, changes_requested, pending
    comment: Optional[str] = None
    confirmed_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CommentCreate(BaseModel):
    field_name: str = "general"
    comment_text: str = Field(..., min_length=1)


class CommentOut(BaseModel):
    id: StrId
    participant_id: StrId
    participant_name: str
    field_name: str
    comment_text: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AgreementVersionOut(BaseModel):
    id: StrId
    deal_id: StrId
    version_number: int
    agreement_json: Dict[str, Any]
    agreement_text: str
    created_by: StrId
    created_by_name: Optional[str] = None
    created_at: datetime
    superseded_at: Optional[datetime] = None
    approvals: List[ApprovalOut] = []
    comments: List[CommentOut] = []
    is_current: bool = False
    is_mutually_confirmed: bool = False

    model_config = ConfigDict(from_attributes=True)


class SignAgreementRequest(BaseModel):
    signature_image: str = Field(..., min_length=20)
    signer_name: Optional[str] = None


# ==========================================
# Amendments
# ==========================================
class AmendmentCreate(BaseModel):
    field_name: str
    original_value: str
    proposed_value: str
    reason: str


class AmendmentOut(BaseModel):
    id: StrId
    deal_id: StrId
    proposed_by: StrId
    proposed_by_name: Optional[str] = None
    field_name: str
    original_value: str
    proposed_value: str
    reason: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Activity Logs (Tamper-Evident SHA-256)
# ==========================================
class ActivityLogOut(BaseModel):
    id: StrId
    deal_id: StrId
    actor_id: Optional[StrId] = None
    actor_name: Optional[str] = None
    event_type: str
    event_data: Dict[str, Any]
    previous_hash: str
    event_hash: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditVerificationResult(BaseModel):
    valid: bool
    total_events: int
    verified_events: int
    broken_at_id: Optional[StrId] = None
    message: str


# ==========================================
# Notifications
# ==========================================
class NotificationOut(BaseModel):
    id: StrId
    user_id: StrId
    deal_id: Optional[StrId] = None
    deal_title: Optional[str] = None
    title: str
    message: str
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# Bond Documents & AI Detector
# ==========================================
class AIMarker(BaseModel):
    marker_type: str
    severity: str
    description: str
    excerpt: Optional[str] = None


class BondDocumentOut(BaseModel):
    id: StrId
    deal_id: StrId
    uploaded_by: StrId
    uploaded_by_name: Optional[str] = None
    filename: str
    file_type: str
    bond_type: str
    document_text: str
    is_ai_generated: bool
    ai_detection_score: float
    ai_verdict: str
    ai_confidence: str
    ai_markers: List[Dict[str, Any]] = []
    ai_alert_triggered: bool
    extracted_terms: Dict[str, Any] = {}
    auto_stored_in_agreement: Optional[bool] = False
    agreement_version_number: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BondDocumentCreate(BaseModel):
    bond_type: Optional[str] = "Legal Bond"
    content: Optional[str] = None


# ==========================================
# Government Authorization & Compliance
# ==========================================
class AuthorizationProviderOut(BaseModel):
    id: StrId
    provider_code: str
    name: str
    authority_type: str
    official_website: str
    documentation_url: str
    authorization_type: str
    eligible_legal_entity: str
    eligibility_criteria: str
    application_procedure: str
    required_corporate_docs: List[str] = []
    technical_certifications: List[str] = []
    agreements_fees_obligations: str
    api_access_details: str
    authorization_status: str
    approval_reference: Optional[str] = None
    supporting_evidence: Dict[str, Any] = {}
    issue_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    renewal_requirements: Optional[str] = None
    geographic_coverage: str
    document_category_coverage: List[str] = []
    restrictions: Optional[str] = None
    responsible_admin_email: str
    is_sandbox_only: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AuthorizationProviderUpdate(BaseModel):
    authorization_status: str
    approval_reference: Optional[str] = None
    supporting_evidence: Optional[Dict[str, Any]] = None
    issue_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    restrictions: Optional[str] = None
    is_sandbox_only: Optional[bool] = None


class StatutoryExclusionOut(BaseModel):
    id: StrId
    exclusion_code: str
    instrument_name: str
    statutory_source: str
    section_reference: str
    effective_date: str
    is_electronic_execution_permitted: bool
    required_physical_formalities: str
    statutory_exceptions: str
    legal_review_mandatory: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ComplianceRecordOut(BaseModel):
    id: StrId
    deal_id: StrId
    instrument_category: str
    instrument_type: str
    lifecycle_status: str
    validity_checks: Dict[str, Any] = {}
    legal_review_flags: List[str] = []
    is_statutory_exclusion: bool
    exclusion_details: Dict[str, Any] = {}
    stamp_duty_required: bool
    stamp_duty_state: Optional[str] = None
    stamp_duty_amount: Optional[float] = None
    stamp_certificate_no: Optional[str] = None
    stamp_grn: Optional[str] = None
    stamp_verified: bool
    stamp_verification_source: Optional[str] = None
    signature_method_required: str
    signature_evidence: Dict[str, Any] = {}
    registration_required: bool
    sro_details: Dict[str, Any] = {}
    official_submission_channel: Optional[str] = None
    official_acknowledgement_ref: Optional[str] = None
    official_issued_bond_number: Optional[str] = None
    official_status_evidence: Dict[str, Any] = {}
    issued_document_hash_sha256: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ComplianceAdvanceRequest(BaseModel):
    target_state: str
    evidence_payload: Optional[Dict[str, Any]] = None


class CustomsEBondOut(BaseModel):
    id: StrId
    deal_id: StrId
    iec_number: str
    entity_pan: str
    customs_station_code: str
    bond_category: str
    bond_amount: float
    bank_guarantee_amount: float
    workflow_step: int
    declarations_accepted: bool
    icegate_job_number: Optional[str] = None
    icegate_ack_number: Optional[str] = None
    customs_officer_approval_ref: Optional[str] = None
    official_bond_number: Optional[str] = None
    step_status_log: Dict[str, Any] = {}
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomsEBondStepRequest(BaseModel):
    step_num: int
    step_data: Dict[str, Any] = {}

