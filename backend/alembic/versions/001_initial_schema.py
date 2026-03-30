"""Initial schema — all core tables.

Revision ID: 001
Revises: None
Create Date: 2026-03-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Enum types ---
    lead_status = sa.Enum(
        "new", "contacted", "replied", "qualified", "lost", "converted",
        name="lead_status",
    )
    gig_status = sa.Enum(
        "discovered", "applied", "interviewing", "won", "lost", "skipped",
        name="gig_status",
    )
    proposal_status = sa.Enum(
        "draft", "reviewed", "approved", "sent", "accepted", "rejected",
        name="proposal_status",
    )
    message_direction = sa.Enum("outbound", "inbound", name="message_direction")
    message_channel = sa.Enum("email", "linkedin", "upwork", name="message_channel")
    invoice_status = sa.Enum(
        "draft", "sent", "paid", "overdue", "cancelled", name="invoice_status"
    )
    pipeline_status = sa.Enum(
        "pending", "planning", "finding_leads", "finding_gigs",
        "generating_proposals", "reviewing", "sending", "completed", "failed",
        name="pipeline_status",
    )

    for e in [
        lead_status, gig_status, proposal_status,
        message_direction, message_channel, invoice_status, pipeline_status,
    ]:
        e.create(op.get_bind(), checkfirst=True)

    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("skills", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("portfolio", sa.Text, nullable=True),
        sa.Column("income_goal", sa.Float, nullable=True),
        sa.Column("target_industry", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Use existing enums (already created above) — create_type=False prevents duplicate creation
    ls = sa.Enum("new", "contacted", "replied", "qualified", "lost", "converted", name="lead_status", create_type=False)
    gs = sa.Enum("discovered", "applied", "interviewing", "won", "lost", "skipped", name="gig_status", create_type=False)
    ps = sa.Enum("draft", "reviewed", "approved", "sent", "accepted", "rejected", name="proposal_status", create_type=False)
    md = sa.Enum("outbound", "inbound", name="message_direction", create_type=False)
    mc = sa.Enum("email", "linkedin", "upwork", name="message_channel", create_type=False)
    ins = sa.Enum("draft", "sent", "paid", "overdue", "cancelled", name="invoice_status", create_type=False)
    pls = sa.Enum("pending", "planning", "finding_leads", "finding_gigs", "generating_proposals", "reviewing", "sending", "completed", "failed", name="pipeline_status", create_type=False)

    # --- leads ---
    op.create_table(
        "leads",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("company", sa.String(255), nullable=True),
        sa.Column("role", sa.String(255), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("linkedin_url", sa.String(512), nullable=True),
        sa.Column("score", sa.Integer, nullable=True),
        sa.Column("status", ls, nullable=False, server_default="new"),
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- gigs ---
    op.create_table(
        "gigs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("platform", sa.String(100), nullable=False),
        sa.Column("budget", sa.Float, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("url", sa.String(512), nullable=True),
        sa.Column("match_score", sa.Integer, nullable=True),
        sa.Column("status", gs, nullable=False, server_default="discovered"),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- proposals ---
    op.create_table(
        "proposals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("gig_id", UUID(as_uuid=True), sa.ForeignKey("gigs.id", ondelete="CASCADE"), nullable=True),
        sa.Column("lead_id", UUID(as_uuid=True), sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("review_score", sa.Integer, nullable=True),
        sa.Column("review_feedback", sa.Text, nullable=True),
        sa.Column("improved_content", sa.Text, nullable=True),
        sa.Column("status", ps, nullable=False, server_default="draft"),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("response", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- messages ---
    op.create_table(
        "messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("lead_id", UUID(as_uuid=True), sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("direction", md, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("channel", mc, nullable=False),
        sa.Column("subject", sa.String(500), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- invoices ---
    op.create_table(
        "invoices",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("invoice_number", sa.String(50), unique=True, nullable=False),
        sa.Column("client_name", sa.String(255), nullable=False),
        sa.Column("client_email", sa.String(255), nullable=True),
        sa.Column("amount", sa.Float, nullable=False),
        sa.Column("services", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("status", ins, nullable=False, server_default="draft"),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("html_content", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- pipeline_runs ---
    op.create_table(
        "pipeline_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", pls, nullable=False, server_default="pending"),
        sa.Column("strategy", sa.JSON, nullable=True),
        sa.Column("leads_found", sa.Integer, server_default="0"),
        sa.Column("gigs_found", sa.Integer, server_default="0"),
        sa.Column("proposals_sent", sa.Integer, server_default="0"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # --- Indexes ---
    op.create_index("ix_leads_user_id", "leads", ["user_id"])
    op.create_index("ix_leads_status", "leads", ["status"])
    op.create_index("ix_gigs_user_id", "gigs", ["user_id"])
    op.create_index("ix_gigs_status", "gigs", ["status"])
    op.create_index("ix_proposals_gig_id", "proposals", ["gig_id"])
    op.create_index("ix_proposals_lead_id", "proposals", ["lead_id"])
    op.create_index("ix_messages_lead_id", "messages", ["lead_id"])
    op.create_index("ix_invoices_user_id", "invoices", ["user_id"])
    op.create_index("ix_pipeline_runs_user_id", "pipeline_runs", ["user_id"])


def downgrade() -> None:
    op.drop_table("pipeline_runs")
    op.drop_table("invoices")
    op.drop_table("messages")
    op.drop_table("proposals")
    op.drop_table("gigs")
    op.drop_table("leads")
    op.drop_table("users")

    for name in [
        "pipeline_status", "invoice_status", "message_channel",
        "message_direction", "proposal_status", "gig_status", "lead_status",
    ]:
        sa.Enum(name=name).drop(op.get_bind(), checkfirst=True)
