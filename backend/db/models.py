import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Enum as SAEnum,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .database import Base


def utcnow():
    return datetime.now(timezone.utc)


def new_uuid():
    return uuid.uuid4()


# ── Enums ────────────────────────────────────────────────────────────────

import enum


class LeadStatus(str, enum.Enum):
    new = "new"
    contacted = "contacted"
    replied = "replied"
    qualified = "qualified"
    lost = "lost"
    converted = "converted"


class JobStatus(str, enum.Enum):
    discovered = "discovered"
    bookmarked = "bookmarked"
    applied = "applied"
    interviewing = "interviewing"
    offered = "offered"
    accepted = "accepted"
    rejected = "rejected"
    skipped = "skipped"


class GigStatus(str, enum.Enum):
    discovered = "discovered"
    applied = "applied"
    interviewing = "interviewing"
    won = "won"
    lost = "lost"
    skipped = "skipped"


class ProposalStatus(str, enum.Enum):
    draft = "draft"
    reviewed = "reviewed"
    approved = "approved"
    sent = "sent"
    accepted = "accepted"
    rejected = "rejected"


class MessageDirection(str, enum.Enum):
    outbound = "outbound"
    inbound = "inbound"


class MessageChannel(str, enum.Enum):
    email = "email"
    linkedin = "linkedin"
    upwork = "upwork"


class InvoiceStatus(str, enum.Enum):
    draft = "draft"
    sent = "sent"
    paid = "paid"
    overdue = "overdue"
    cancelled = "cancelled"


class PipelineStatus(str, enum.Enum):
    pending = "pending"
    planning = "planning"
    finding_leads = "finding_leads"
    finding_gigs = "finding_gigs"
    finding_jobs = "finding_jobs"
    generating_proposals = "generating_proposals"
    generating_cover_letters = "generating_cover_letters"
    reviewing = "reviewing"
    sending = "sending"
    completed = "completed"
    failed = "failed"


# ── Models ───────────────────────────────────────────────────────────────


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=True)
    skills = Column(JSON, nullable=False, default=list)  # ["Python", "FastAPI", ...]
    portfolio = Column(Text, nullable=True)  # free-text portfolio summary
    income_goal = Column(Float, nullable=True)  # monthly USD
    target_industry = Column(String(255), nullable=True)
    selected_modules = Column(JSON, nullable=False, default=lambda: ["leads", "gigs", "jobs"])
    onboarding_completed = Column(Boolean, default=False)
    onboarding_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    leads = relationship("Lead", back_populates="user", cascade="all, delete-orphan")
    gigs = relationship("Gig", back_populates="user", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="user", cascade="all, delete-orphan")
    invoices = relationship(
        "Invoice", back_populates="user", cascade="all, delete-orphan"
    )
    pipeline_runs = relationship(
        "PipelineRun", back_populates="user", cascade="all, delete-orphan"
    )


class Lead(Base):
    __tablename__ = "leads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String(255), nullable=False)
    company = Column(String(255), nullable=True)
    role = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    linkedin_url = Column(String(512), nullable=True)
    score = Column(Integer, nullable=True)  # 0-100 lead quality score
    status = Column(
        SAEnum(LeadStatus, name="lead_status"),
        default=LeadStatus.new,
        nullable=False,
    )
    source = Column(String(100), nullable=True)  # "jsearch", "linkedin", "crunchbase"
    notes = Column(Text, nullable=True)
    location = Column(String(255), nullable=True)
    company_website = Column(String(512), nullable=True)
    company_logo = Column(String(512), nullable=True)
    funding_usd = Column(Float, nullable=True)  # Crunchbase funding amount
    industries = Column(JSON, nullable=True)  # ["SaaS", "FinTech"]
    founders = Column(JSON, nullable=True)  # [{"name":"...", "title":"...", "linkedin":"..."}]
    service_opportunity = Column(Text, nullable=True)  # What you could pitch
    job_url = Column(String(512), nullable=True)  # Original job posting URL
    created_at = Column(DateTime(timezone=True), default=utcnow)

    user = relationship("User", back_populates="leads")
    proposals = relationship(
        "Proposal", back_populates="lead", cascade="all, delete-orphan"
    )
    messages = relationship(
        "Message", back_populates="lead", cascade="all, delete-orphan"
    )


class Gig(Base):
    __tablename__ = "gigs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title = Column(String(500), nullable=False)
    platform = Column(String(100), nullable=False)  # "upwork", "linkedin", "freelancer"
    budget = Column(Float, nullable=True)
    description = Column(Text, nullable=True)
    url = Column(String(512), nullable=True)
    match_score = Column(Integer, nullable=True)  # 0-100
    status = Column(
        SAEnum(GigStatus, name="gig_status"),
        default=GigStatus.discovered,
        nullable=False,
    )
    deadline = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    user = relationship("User", back_populates="gigs")
    proposals = relationship(
        "Proposal", back_populates="gig", cascade="all, delete-orphan"
    )


class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title = Column(String(500), nullable=False)
    company = Column(String(255), nullable=True)
    platform = Column(String(100), nullable=False)  # "linkedin", "indeed", "glassdoor"
    job_type = Column(String(50), nullable=True)  # "full-time", "part-time", "contract"
    salary_min = Column(Float, nullable=True)
    salary_max = Column(Float, nullable=True)
    location = Column(String(255), nullable=True)
    remote = Column(Boolean, default=False)
    description = Column(Text, nullable=True)
    url = Column(String(512), nullable=True)
    match_score = Column(Integer, nullable=True)  # 0-100
    status = Column(
        SAEnum(JobStatus, name="job_status"),
        default=JobStatus.discovered,
        nullable=False,
    )
    cover_letter = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    user = relationship("User", back_populates="jobs")


class Proposal(Base):
    __tablename__ = "proposals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    gig_id = Column(
        UUID(as_uuid=True), ForeignKey("gigs.id", ondelete="CASCADE"), nullable=True
    )
    lead_id = Column(
        UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), nullable=True
    )
    content = Column(Text, nullable=False)
    review_score = Column(Integer, nullable=True)  # 0-100 from reviewer agent
    review_feedback = Column(Text, nullable=True)
    improved_content = Column(Text, nullable=True)  # reviewer's improved version
    status = Column(
        SAEnum(ProposalStatus, name="proposal_status"),
        default=ProposalStatus.draft,
        nullable=False,
    )
    sent_at = Column(DateTime(timezone=True), nullable=True)
    response = Column(Text, nullable=True)  # client response text
    created_at = Column(DateTime(timezone=True), default=utcnow)

    gig = relationship("Gig", back_populates="proposals")
    lead = relationship("Lead", back_populates="proposals")


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    lead_id = Column(
        UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False
    )
    direction = Column(
        SAEnum(MessageDirection, name="message_direction"), nullable=False
    )
    content = Column(Text, nullable=False)
    channel = Column(SAEnum(MessageChannel, name="message_channel"), nullable=False)
    subject = Column(String(500), nullable=True)
    sent_at = Column(DateTime(timezone=True), default=utcnow)

    lead = relationship("Lead", back_populates="messages")


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    invoice_number = Column(String(50), unique=True, nullable=False)
    client_name = Column(String(255), nullable=False)
    client_email = Column(String(255), nullable=True)
    amount = Column(Float, nullable=False)
    services = Column(JSON, nullable=False, default=list)  # [{"desc": ..., "amount": ...}]
    status = Column(
        SAEnum(InvoiceStatus, name="invoice_status"),
        default=InvoiceStatus.draft,
        nullable=False,
    )
    due_date = Column(DateTime(timezone=True), nullable=False)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    html_content = Column(Text, nullable=True)  # rendered invoice HTML
    created_at = Column(DateTime(timezone=True), default=utcnow)

    user = relationship("User", back_populates="invoices")


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    status = Column(
        SAEnum(PipelineStatus, name="pipeline_status"),
        default=PipelineStatus.pending,
        nullable=False,
    )
    pipeline_type = Column(String(50), nullable=True)  # "leads", "gigs", "jobs", "all"
    strategy = Column(JSON, nullable=True)  # planner agent output
    leads_found = Column(Integer, default=0)
    gigs_found = Column(Integer, default=0)
    jobs_found = Column(Integer, default=0)
    proposals_sent = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), default=utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="pipeline_runs")
