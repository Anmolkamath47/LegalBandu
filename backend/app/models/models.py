import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Text,
    Boolean,
    Integer,
    Float,
    ForeignKey,
    DateTime,
    JSON,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class GUID(TypeDecorator):
    """Platform-independent GUID type.
    Uses PostgreSQL's UUID type, otherwise uses CHAR(36).
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=False))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return str(value)


def utc_now():
    return datetime.now(timezone.utc)


def gen_uuid():
    return str(uuid.uuid4())


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(String(36), primary_key=True)  # Auth user id
    full_name = Column(String(255), nullable=False, default="")
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class Deal(Base):
    __tablename__ = "deals"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    creator_id = Column(String(36), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False, default="Services")
    description = Column(Text, nullable=False, default="")
    currency = Column(String(10), nullable=False, default="INR")
    status = Column(
        String(50), nullable=False, default="draft"
    )  # draft, awaiting_review, changes_requested, mutually_confirmed, superseded
    current_version_id = Column(String(36), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, index=True
    )

    participants = relationship(
        "DealParticipant", back_populates="deal", cascade="all, delete-orphan"
    )
    conversations = relationship(
        "Conversation", back_populates="deal", cascade="all, delete-orphan"
    )
    analyses = relationship(
        "DealAnalysis", back_populates="deal", cascade="all, delete-orphan"
    )
    clarifications = relationship(
        "ClarificationAnswer", back_populates="deal", cascade="all, delete-orphan"
    )
    versions = relationship(
        "AgreementVersion",
        back_populates="deal",
        cascade="all, delete-orphan",
        foreign_keys="AgreementVersion.deal_id",
    )
    activity_logs = relationship(
        "ActivityLog", back_populates="deal", cascade="all, delete-orphan"
    )
    amendments = relationship(
        "Amendment", back_populates="deal", cascade="all, delete-orphan"
    )
    bond_documents = relationship(
        "BondDocument", back_populates="deal", cascade="all, delete-orphan"
    )
    compliance_record = relationship(
        "InstrumentComplianceRecord", back_populates="deal", uselist=False, cascade="all, delete-orphan"
    )
    customs_bonds = relationship(
        "CustomsEBondRecord", back_populates="deal", cascade="all, delete-orphan"
    )
    lawyer_reviews = relationship(
        "LawyerReview", back_populates="deal", cascade="all, delete-orphan"
    )
    lawyer_suggestions = relationship(
        "LawyerSuggestion", back_populates="deal", cascade="all, delete-orphan"
    )
    assistance_records = relationship(
        "AgreementAssistanceRecord", back_populates="deal", cascade="all, delete-orphan"
    )


class DealParticipant(Base):
    __tablename__ = "deal_participants"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    deal_id = Column(
        String(36),
        ForeignKey("deals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(String(36), nullable=True, index=True)
    role = Column(
        String(20), nullable=False
    )  # 'creator' or 'counterparty'
    invitation_email = Column(String(255), nullable=True)
    invitation_token_hash = Column(String(64), nullable=True, index=True)
    invitation_expires_at = Column(DateTime(timezone=True), nullable=True)
    joined_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    deal = relationship("Deal", back_populates="participants")
    approvals = relationship(
        "AgreementApproval", back_populates="participant", cascade="all, delete-orphan"
    )


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    deal_id = Column(
        String(36),
        ForeignKey("deals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    uploaded_by = Column(String(36), nullable=False)
    source_type = Column(
        String(50), nullable=False, default="paste"
    )  # 'paste' or 'file_upload'
    original_content = Column(Text, nullable=False)
    audio_url = Column(String(500), nullable=True)
    audio_filename = Column(String(255), nullable=True)
    audio_duration = Column(Integer, nullable=True)
    image_url = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    deal = relationship("Deal", back_populates="conversations")
    messages = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan"
    )


class Message(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    conversation_id = Column(
        String(36),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    speaker_label = Column(String(100), nullable=False, default="Participant")
    message_text = Column(Text, nullable=False)
    message_timestamp = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    conversation = relationship("Conversation", back_populates="messages")


class DealAnalysis(Base):
    __tablename__ = "deal_analyses"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    deal_id = Column(
        String(36),
        ForeignKey("deals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    conversation_id = Column(
        String(36), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True
    )
    analysis_json = Column(JSON, nullable=False, default=dict)
    created_by = Column(String(36), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    deal = relationship("Deal", back_populates="analyses")


class ClarificationAnswer(Base):
    __tablename__ = "clarification_answers"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    deal_id = Column(
        String(36),
        ForeignKey("deals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    field_name = Column(String(100), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    answered_by = Column(String(36), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    deal = relationship("Deal", back_populates="clarifications")


class BondDocument(Base):
    __tablename__ = "bond_documents"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    deal_id = Column(
        String(36),
        ForeignKey("deals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    uploaded_by = Column(String(36), nullable=False)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False, default="pdf")
    bond_type = Column(String(100), nullable=False, default="Legal Bond")
    document_text = Column(Text, nullable=False, default="")

    # AI Detection fields
    is_ai_generated = Column(Boolean, nullable=False, default=False)
    ai_detection_score = Column(Float, nullable=False, default=0.0)
    ai_verdict = Column(String(100), nullable=False, default="Likely Human")
    ai_confidence = Column(String(50), nullable=False, default="medium")
    ai_markers = Column(JSON, nullable=False, default=list)
    ai_alert_triggered = Column(Boolean, nullable=False, default=False)

    # Extracted legal terms from the bond
    extracted_terms = Column(JSON, nullable=False, default=dict)

    created_at = Column(DateTime(timezone=True), default=utc_now)

    deal = relationship("Deal", back_populates="bond_documents")


class AgreementVersion(Base):
    __tablename__ = "agreement_versions"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    deal_id = Column(
        String(36),
        ForeignKey("deals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number = Column(Integer, nullable=False)
    agreement_json = Column(JSON, nullable=False, default=dict)
    agreement_text = Column(Text, nullable=False, default="")
    created_by = Column(String(36), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    superseded_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("deal_id", "version_number", name="uq_deal_version"),
    )

    deal = relationship(
        "Deal", back_populates="versions", foreign_keys=[deal_id]
    )
    approvals = relationship(
        "AgreementApproval", back_populates="version", cascade="all, delete-orphan"
    )
    comments = relationship(
        "AgreementComment", back_populates="version", cascade="all, delete-orphan"
    )


class AgreementApproval(Base):
    __tablename__ = "agreement_approvals"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    agreement_version_id = Column(
        String(36),
        ForeignKey("agreement_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    participant_id = Column(
        String(36),
        ForeignKey("deal_participants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(
        String(50), nullable=False
    )  # 'approved', 'changes_requested', 'pending'
    comment = Column(Text, nullable=True)
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    __table_args__ = (
        UniqueConstraint(
            "agreement_version_id", "participant_id", name="uq_version_participant"
        ),
    )

    version = relationship("AgreementVersion", back_populates="approvals")
    participant = relationship("DealParticipant", back_populates="approvals")


class AgreementComment(Base):
    __tablename__ = "agreement_comments"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    agreement_version_id = Column(
        String(36),
        ForeignKey("agreement_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    participant_id = Column(
        String(36),
        ForeignKey("deal_participants.id", ondelete="CASCADE"),
        nullable=False,
    )
    field_name = Column(String(100), nullable=False, default="general")
    comment_text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    version = relationship("AgreementVersion", back_populates="comments")


class Amendment(Base):
    __tablename__ = "amendments"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    deal_id = Column(
        String(36),
        ForeignKey("deals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    proposed_by = Column(String(36), nullable=False)
    field_name = Column(String(100), nullable=False)
    original_value = Column(Text, nullable=False, default="")
    proposed_value = Column(Text, nullable=False, default="")
    reason = Column(Text, nullable=False, default="")
    status = Column(
        String(50), nullable=False, default="proposed"
    )  # 'proposed', 'confirmed', 'rejected'
    created_at = Column(DateTime(timezone=True), default=utc_now)

    deal = relationship("Deal", back_populates="amendments")


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    deal_id = Column(
        String(36),
        ForeignKey("deals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_id = Column(String(36), nullable=True)
    event_type = Column(String(100), nullable=False)
    event_data = Column(JSON, nullable=False, default=dict)
    previous_hash = Column(String(64), nullable=False)
    event_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    deal = relationship("Deal", back_populates="activity_logs")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), nullable=False, index=True)
    deal_id = Column(
        String(36),
        ForeignKey("deals.id", ondelete="CASCADE"),
        nullable=True,
    )
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class AuthorizationProvider(Base):
    """
    Administrator-Only Register of Government Integrations & Approved Service Providers.
    Tracks authorization state, genuine onboarding evidence, certifications, and valid coverage.
    States: NOT_ASSESSED, ELIGIBILITY_REVIEW_REQUIRED, APPLICATION_REQUIRED, APPLICATION_SUBMITTED,
            APPROVED_PENDING_INTEGRATION, PRODUCTION_VERIFIED, EXPIRED, SUSPENDED, REJECTED.
    """
    __tablename__ = "authorization_providers"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    provider_code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    authority_type = Column(String(100), nullable=False)  # CRA, DDE, ESP, Customs Gateway, SRO
    official_website = Column(String(500), nullable=False)
    documentation_url = Column(String(500), nullable=False)
    authorization_type = Column(String(150), nullable=False)
    eligible_legal_entity = Column(String(255), nullable=False)
    eligibility_criteria = Column(Text, nullable=False)
    application_procedure = Column(Text, nullable=False)
    required_corporate_docs = Column(JSON, nullable=False, default=list)
    technical_certifications = Column(JSON, nullable=False, default=list)  # CERT-In, ISO27001, VAPT
    agreements_fees_obligations = Column(Text, nullable=False)
    api_access_details = Column(Text, nullable=False)

    # Authorization status: NEVER invented. PRODUCTION_VERIFIED requires live verification evidence
    authorization_status = Column(
        String(50), nullable=False, default="ELIGIBILITY_REVIEW_REQUIRED"
    )
    approval_reference = Column(String(255), nullable=True)
    supporting_evidence = Column(JSON, nullable=False, default=dict)
    issue_date = Column(DateTime(timezone=True), nullable=True)
    expiry_date = Column(DateTime(timezone=True), nullable=True)
    renewal_requirements = Column(Text, nullable=True)
    geographic_coverage = Column(String(255), nullable=False, default="Pan-India")
    document_category_coverage = Column(JSON, nullable=False, default=list)  # ["A", "B", "E"]
    restrictions = Column(Text, nullable=True)
    responsible_admin_email = Column(String(255), nullable=False, default="admin@legalbandu.com")
    is_sandbox_only = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class StatutoryExclusion(Base):
    """
    Maintained Register of Statutory Exclusions under the First Schedule of IT Act, 2000.
    Identifies instruments that CANNOT be executed electronically in India.
    """
    __tablename__ = "statutory_exclusions"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    exclusion_code = Column(String(50), unique=True, nullable=False, index=True)
    instrument_name = Column(String(255), nullable=False)
    statutory_source = Column(String(255), nullable=False)
    section_reference = Column(String(150), nullable=False)
    effective_date = Column(String(50), nullable=False, default="2000-10-17")
    is_electronic_execution_permitted = Column(Boolean, nullable=False, default=False)
    required_physical_formalities = Column(Text, nullable=False)
    statutory_exceptions = Column(Text, nullable=False, default="None")
    legal_review_mandatory = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime(timezone=True), default=utc_now)


class InstrumentComplianceRecord(Base):
    """
    Per-deal compliance record tracking the exact 15-state legal lifecycle,
    mandatory validity checklist, genuine verification evidence, and statutory exclusion state.
    """
    __tablename__ = "instrument_compliance_records"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    deal_id = Column(
        GUID(),
        ForeignKey("deals.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    instrument_category = Column(String(10), nullable=False, default="A")  # A, B, C, D, E
    instrument_type = Column(String(150), nullable=False, default="Private Commercial Agreement")

    # The 15 mandatory lifecycle states:
    # 1. Draft — not executed
    # 2. Legal review required
    # 3. Ready for stamping
    # 4. Stamping pending
    # 5. Stamped — genuine applicable evidence verified
    # 6. Awaiting signatures
    # 7. Signed — signature evidence verified
    # 8. Execution requirements pending
    # 9. Executed — applicable execution checks passed
    # 10. Registration pending
    # 11. Registered — genuine registration evidence verified
    # 12. Official submission pending
    # 13. Submitted to official platform
    # 14. Officially accepted or issued — only with verified supporting evidence
    # 15. Completed — all applicable requirements tracked for this instrument are satisfied
    lifecycle_status = Column(
        String(100), nullable=False, default="Draft — not executed"
    )

    validity_checks = Column(JSON, nullable=False, default=dict)
    legal_review_flags = Column(JSON, nullable=False, default=list)

    # Statutory Exclusion
    is_statutory_exclusion = Column(Boolean, nullable=False, default=False)
    exclusion_details = Column(JSON, nullable=False, default=dict)

    # Stamping
    stamp_duty_required = Column(Boolean, nullable=False, default=False)
    stamp_duty_state = Column(String(100), nullable=True)
    stamp_duty_amount = Column(Float, nullable=True)
    stamp_certificate_no = Column(String(100), nullable=True)
    stamp_grn = Column(String(100), nullable=True)
    stamp_verified = Column(Boolean, nullable=False, default=False)
    stamp_verification_source = Column(String(500), nullable=True)

    # Execution / Signatures
    signature_method_required = Column(String(100), nullable=False, default="electronic")
    signature_evidence = Column(JSON, nullable=False, default=dict)

    # Registration & Notarization
    registration_required = Column(Boolean, nullable=False, default=False)
    sro_details = Column(JSON, nullable=False, default=dict)

    # Government / Official Platform
    official_submission_channel = Column(String(100), nullable=True)
    official_acknowledgement_ref = Column(String(255), nullable=True)
    official_issued_bond_number = Column(String(255), nullable=True)
    official_status_evidence = Column(JSON, nullable=False, default=dict)

    issued_document_hash_sha256 = Column(String(64), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    deal = relationship("Deal", back_populates="compliance_record")


class CustomsEBondRecord(Base):
    """
    Category E: Specialized electronic customs e-Bond workflow (ICEGATE & NeSL integration).
    Tracks the authentic 11-step sequence under CBIC Circular No. 19/2022-Customs.
    """
    __tablename__ = "customs_e_bonds"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    deal_id = Column(
        GUID(),
        ForeignKey("deals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    iec_number = Column(String(20), nullable=False)
    entity_pan = Column(String(20), nullable=False)
    customs_station_code = Column(String(20), nullable=False, default="INNSA1")
    bond_category = Column(String(100), nullable=False, default="Warehousing Bond (Sec 59)")
    bond_amount = Column(Float, nullable=False, default=0.0)
    bank_guarantee_amount = Column(Float, nullable=False, default=0.0)
    workflow_step = Column(Integer, nullable=False, default=1)  # 1 to 11
    declarations_accepted = Column(Boolean, nullable=False, default=False)

    icegate_job_number = Column(String(100), nullable=True)
    icegate_ack_number = Column(String(100), nullable=True)
    customs_officer_approval_ref = Column(String(100), nullable=True)
    official_bond_number = Column(String(100), nullable=True)

    step_status_log = Column(JSON, nullable=False, default=dict)

    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    deal = relationship("Deal", back_populates="customs_bonds")


class LawyerReview(Base):
    __tablename__ = "lawyer_reviews"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    deal_id = Column(
        GUID(),
        ForeignKey("deals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lawyer_id = Column(String(36), nullable=True, index=True)
    invitation_email = Column(String(255), nullable=True)
    invitation_token_hash = Column(String(64), nullable=True, index=True)
    invitation_expires_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(
        String(50), nullable=False, default="invite_sent"
    )  # invite_sent, in_review, changes_recommended, approved, declined
    decline_reason = Column(Text, nullable=True)
    overall_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    deal = relationship("Deal", back_populates="lawyer_reviews")
    suggestions = relationship(
        "LawyerSuggestion", back_populates="review", cascade="all, delete-orphan"
    )


class LawyerSuggestion(Base):
    __tablename__ = "lawyer_suggestions"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    deal_id = Column(
        GUID(),
        ForeignKey("deals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    review_id = Column(
        String(36),
        ForeignKey("lawyer_reviews.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    lawyer_id = Column(String(36), nullable=False, index=True)
    clause_reference = Column(String(150), nullable=False)
    original_text = Column(Text, nullable=False, default="")
    suggested_text = Column(Text, nullable=False)
    explanation = Column(Text, nullable=False)
    status = Column(
        String(50), nullable=False, default="pending"
    )  # pending, accepted, rejected
    rejection_reason = Column(Text, nullable=True)
    discussion_notes = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    deal = relationship("Deal", back_populates="lawyer_suggestions")
    review = relationship("LawyerReview", back_populates="suggestions")


class AgreementAssistanceRecord(Base):
    __tablename__ = "agreement_assistance_records"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    deal_id = Column(
        GUID(),
        ForeignKey("deals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    topic_id = Column(String(100), nullable=False, index=True)
    status = Column(
        String(50), nullable=False, default="pending"
    )  # pending, in_discussion, discussed
    answers = Column(JSON, nullable=False, default=dict)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    deal = relationship("Deal", back_populates="assistance_records")
