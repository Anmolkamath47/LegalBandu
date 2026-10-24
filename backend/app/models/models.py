import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Text,
    Boolean,
    Integer,
    ForeignKey,
    DateTime,
    JSON,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


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
