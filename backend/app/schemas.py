from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# ==========================================
# Profiles & Users
# ==========================================
class UserProfile(BaseModel):
    id: str
    email: str
    full_name: str

    class Config:
        from_attributes = True


class ProfileUpdate(BaseModel):
    full_name: str


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
    id: str
    deal_id: str
    user_id: Optional[str] = None
    role: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    joined_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DealOut(BaseModel):
    id: str
    creator_id: str
    creator_name: Optional[str] = None
    title: str
    category: str
    description: str
    currency: str
    status: str
    current_version_id: Optional[str] = None
    current_version_number: Optional[int] = None
    participants: List[ParticipantOut] = []
    counterparty: Optional[ParticipantOut] = None
    next_action: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


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
    deal_id: str
    deal_title: str
    creator_name: str
    category: str
    description: str
    currency: str
    is_expired: bool
    is_already_accepted: bool


# ==========================================
# Conversations & Messages
# ==========================================
class ConversationCreate(BaseModel):
    source_type: str = Field(default="paste")  # 'paste' or 'file_upload'
    original_content: str = Field(..., min_length=1)


class MessageOut(BaseModel):
    id: str
    speaker_label: str
    message_text: str
    message_timestamp: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationOut(BaseModel):
    id: str
    deal_id: str
    uploaded_by: str
    uploaded_by_name: Optional[str] = None
    source_type: str
    original_content: str
    messages: List[MessageOut] = []
    created_at: datetime

    class Config:
        from_attributes = True


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
    id: str
    deal_id: str
    conversation_id: Optional[str] = None
    analysis: Dict[str, Any]
    created_by: str
    created_at: datetime

    class Config:
        from_attributes = True


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
    id: str
    deal_id: str
    field_name: str
    question: str
    answer: str
    answered_by: str
    answered_by_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


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
    id: str
    participant_id: str
    participant_name: str
    role: str
    status: str  # approved, changes_requested, pending
    comment: Optional[str] = None
    confirmed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CommentCreate(BaseModel):
    field_name: str = "general"
    comment_text: str = Field(..., min_length=1)


class CommentOut(BaseModel):
    id: str
    participant_id: str
    participant_name: str
    field_name: str
    comment_text: str
    created_at: datetime

    class Config:
        from_attributes = True


class AgreementVersionOut(BaseModel):
    id: str
    deal_id: str
    version_number: int
    agreement_json: Dict[str, Any]
    agreement_text: str
    created_by: str
    created_by_name: Optional[str] = None
    created_at: datetime
    superseded_at: Optional[datetime] = None
    approvals: List[ApprovalOut] = []
    comments: List[CommentOut] = []
    is_current: bool = False
    is_mutually_confirmed: bool = False

    class Config:
        from_attributes = True


# ==========================================
# Amendments
# ==========================================
class AmendmentCreate(BaseModel):
    field_name: str
    original_value: str
    proposed_value: str
    reason: str


class AmendmentOut(BaseModel):
    id: str
    deal_id: str
    proposed_by: str
    proposed_by_name: Optional[str] = None
    field_name: str
    original_value: str
    proposed_value: str
    reason: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


# ==========================================
# Activity Logs (Tamper-Evident SHA-256)
# ==========================================
class ActivityLogOut(BaseModel):
    id: str
    deal_id: str
    actor_id: Optional[str] = None
    actor_name: Optional[str] = None
    event_type: str
    event_data: Dict[str, Any]
    previous_hash: str
    event_hash: str
    created_at: datetime

    class Config:
        from_attributes = True


class AuditVerificationResult(BaseModel):
    valid: bool
    total_events: int
    verified_events: int
    broken_at_id: Optional[str] = None
    message: str


# ==========================================
# Notifications
# ==========================================
class NotificationOut(BaseModel):
    id: str
    user_id: str
    deal_id: Optional[str] = None
    deal_title: Optional[str] = None
    title: str
    message: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True
