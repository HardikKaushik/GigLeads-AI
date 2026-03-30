"""FastAPI route definitions — all API endpoints with JWT auth."""

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..agents import InvoiceAgent, ProposalAgent, ReviewerAgent
from ..db.database import get_db
from ..db.models import (
    Gig,
    GigStatus,
    Invoice,
    InvoiceStatus,
    Job,
    JobStatus,
    Lead,
    LeadStatus,
    Message,
    PipelineRun,
    PipelineStatus,
    Proposal,
    ProposalStatus,
    User,
)
from ..pipeline.orchestrator import run_selected_pipelines
from .auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from .schemas import (
    AnalyticsOut,
    AuthResponse,
    GigOut,
    InvoiceCreateRequest,
    InvoiceOut,
    JobOut,
    JobStatusUpdate,
    LeadOut,
    LeadStatusUpdate,
    LoginRequest,
    ModuleSelectionRequest,
    OnboardingRequest,
    PipelineStartRequest,
    PipelineStatusOut,
    ProposalGenerateRequest,
    ProposalOut,
    SignupRequest,
    UserProfileOut,
    UserProfileUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

MAX_PROPOSALS_PER_DAY = 50


# ═══════════════════════════════════════════════════════════════════════
# Auth
# ═══════════════════════════════════════════════════════════════════════


@router.post("/auth/signup", response_model=AuthResponse, status_code=201)
def signup(body: SignupRequest, db: Session = Depends(get_db)):
    """Create a new user account."""
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(409, "Email already registered")

    user = User(
        name=body.name,
        email=body.email,
        password_hash=hash_password(body.password),
        selected_modules=["leads", "gigs", "jobs"],
        onboarding_completed=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(str(user.id))
    return AuthResponse(access_token=token, user=UserProfileOut.model_validate(user))


@router.post("/auth/login", response_model=AuthResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """Log in with email + password."""
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not user.password_hash:
        raise HTTPException(401, "Invalid email or password")
    if not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")

    token = create_access_token(str(user.id))
    return AuthResponse(access_token=token, user=UserProfileOut.model_validate(user))


@router.get("/auth/me", response_model=UserProfileOut)
def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user."""
    return current_user


# ═══════════════════════════════════════════════════════════════════════
# Users / Profile / Onboarding
# ═══════════════════════════════════════════════════════════════════════


@router.put("/users/profile", response_model=UserProfileOut)
def update_profile(
    body: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update the authenticated user's profile."""
    if body.name is not None:
        current_user.name = body.name
    if body.skills is not None:
        current_user.skills = body.skills
    if body.portfolio is not None:
        current_user.portfolio = body.portfolio
    if body.income_goal is not None:
        current_user.income_goal = body.income_goal
    if body.target_industry is not None:
        current_user.target_industry = body.target_industry
    current_user.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.put("/users/modules", response_model=UserProfileOut)
def update_modules(
    body: ModuleSelectionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update which modules the user has selected (leads, gigs, jobs)."""
    valid = {"leads", "gigs", "jobs"}
    invalid = set(body.selected_modules) - valid
    if invalid:
        raise HTTPException(400, f"Invalid modules: {invalid}")
    current_user.selected_modules = body.selected_modules
    current_user.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.put("/users/onboarding", response_model=UserProfileOut)
def complete_onboarding(
    body: OnboardingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save onboarding data and mark onboarding as complete."""
    data = body.onboarding_data

    # Apply common fields to user model
    common = data.get("common", {})
    if common.get("name"):
        current_user.name = common["name"]
    if common.get("skills"):
        current_user.skills = common["skills"]
    if common.get("portfolio"):
        current_user.portfolio = common["portfolio"]

    # Apply leads-specific
    leads_data = data.get("leads", {})
    if leads_data.get("target_industry"):
        current_user.target_industry = leads_data["target_industry"]

    # Apply gigs-specific
    gigs_data = data.get("gigs", {})
    if gigs_data.get("hourly_rate"):
        current_user.income_goal = gigs_data["hourly_rate"] * 160  # monthly estimate

    current_user.onboarding_data = data
    current_user.onboarding_completed = True
    current_user.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(current_user)
    return current_user


# ═══════════════════════════════════════════════════════════════════════
# Pipeline
# ═══════════════════════════════════════════════════════════════════════


@router.post("/pipeline/start", response_model=PipelineStatusOut, status_code=202)
def start_pipeline(
    body: PipelineStartRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Trigger the pipeline for selected modules."""
    modules = body.modules or current_user.selected_modules or ["leads", "gigs", "jobs"]

    # Check for already-running pipeline
    active = (
        db.query(PipelineRun)
        .filter(
            PipelineRun.user_id == current_user.id,
            PipelineRun.status.notin_(
                [PipelineStatus.completed, PipelineStatus.failed]
            ),
        )
        .first()
    )
    if active:
        raise HTTPException(409, "A pipeline is already running")

    pipeline_type = ",".join(sorted(modules)) if len(modules) < 3 else "all"
    run = PipelineRun(
        user_id=current_user.id,
        status=PipelineStatus.pending,
        pipeline_type=pipeline_type,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    run_id_str = str(run.id)
    user_id_str = str(current_user.id)

    from ..db.database import SessionLocal

    def bg():
        session = SessionLocal()
        try:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(
                run_selected_pipelines(user_id_str, session, run_id=run_id_str, modules=modules)
            )
            loop.close()
        except Exception as exc:
            import traceback
            logger.exception("Background pipeline failed: %s", traceback.format_exc())
            try:
                bg_run = session.query(PipelineRun).get(run.id)
                if bg_run:
                    bg_run.status = PipelineStatus.failed
                    bg_run.error_message = f"{type(exc).__name__}: {str(exc)[:500]}"
                    session.commit()
            except Exception:
                pass
        finally:
            session.close()

    background_tasks.add_task(bg)
    return run


@router.get("/pipeline/{run_id}/status", response_model=PipelineStatusOut)
def pipeline_status(
    run_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Check pipeline run progress."""
    run = db.query(PipelineRun).filter(
        PipelineRun.id == run_id, PipelineRun.user_id == current_user.id
    ).first()
    if not run:
        raise HTTPException(404, "Pipeline run not found")
    return run


@router.get("/pipeline/history", response_model=list[PipelineStatusOut])
def pipeline_history(
    limit: int = Query(10, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List recent pipeline runs."""
    return (
        db.query(PipelineRun)
        .filter(PipelineRun.user_id == current_user.id)
        .order_by(PipelineRun.started_at.desc())
        .limit(limit)
        .all()
    )


# ═══════════════════════════════════════════════════════════════════════
# Leads
# ═══════════════════════════════════════════════════════════════════════


@router.get("/leads", response_model=list[LeadOut])
def list_leads(
    status: str | None = Query(None),
    min_score: int = Query(0, ge=0, le=100),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Lead).filter(Lead.user_id == current_user.id)
    if status:
        q = q.filter(Lead.status == status)
    if min_score > 0:
        q = q.filter(Lead.score >= min_score)
    return (
        q.order_by(Lead.score.desc().nullslast(), Lead.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.patch("/leads/{lead_id}/status", response_model=LeadOut)
def update_lead_status(
    lead_id: uuid.UUID,
    body: LeadStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lead = db.query(Lead).filter(Lead.id == lead_id, Lead.user_id == current_user.id).first()
    if not lead:
        raise HTTPException(404, "Lead not found")
    try:
        lead.status = LeadStatus(body.status)
    except ValueError:
        raise HTTPException(400, f"Invalid status: {body.status}")
    db.commit()
    db.refresh(lead)
    return lead


# ═══════════════════════════════════════════════════════════════════════
# Gigs
# ═══════════════════════════════════════════════════════════════════════


@router.get("/gigs", response_model=list[GigOut])
def list_gigs(
    platform: str | None = Query(None),
    min_score: int = Query(0, ge=0, le=100),
    status: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Gig).filter(Gig.user_id == current_user.id)
    if platform:
        q = q.filter(Gig.platform == platform)
    if status:
        q = q.filter(Gig.status == status)
    if min_score > 0:
        q = q.filter(Gig.match_score >= min_score)
    return (
        q.order_by(Gig.match_score.desc().nullslast(), Gig.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


# ═══════════════════════════════════════════════════════════════════════
# Jobs
# ═══════════════════════════════════════════════════════════════════════


@router.get("/jobs", response_model=list[JobOut])
def list_jobs(
    platform: str | None = Query(None),
    job_type: str | None = Query(None),
    status: str | None = Query(None),
    min_score: int = Query(0, ge=0, le=100),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Job).filter(Job.user_id == current_user.id)
    if platform:
        q = q.filter(Job.platform == platform)
    if job_type:
        q = q.filter(Job.job_type == job_type)
    if status:
        q = q.filter(Job.status == status)
    if min_score > 0:
        q = q.filter(Job.match_score >= min_score)
    return (
        q.order_by(Job.match_score.desc().nullslast(), Job.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.patch("/jobs/{job_id}/status", response_model=JobOut)
def update_job_status(
    job_id: uuid.UUID,
    body: JobStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == current_user.id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    try:
        job.status = JobStatus(body.status)
    except ValueError:
        raise HTTPException(400, f"Invalid status: {body.status}")
    db.commit()
    db.refresh(job)
    return job


# ═══════════════════════════════════════════════════════════════════════
# Proposals
# ═══════════════════════════════════════════════════════════════════════


@router.get("/proposals", response_model=list[ProposalOut])
def list_proposals(
    status: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    gig_ids = [g.id for g in db.query(Gig.id).filter(Gig.user_id == current_user.id).all()]
    lead_ids = [l.id for l in db.query(Lead.id).filter(Lead.user_id == current_user.id).all()]
    q = db.query(Proposal).filter(
        (Proposal.gig_id.in_(gig_ids)) | (Proposal.lead_id.in_(lead_ids))
    )
    if status:
        q = q.filter(Proposal.status == status)
    return q.order_by(Proposal.created_at.desc()).offset(offset).limit(limit).all()


@router.post("/proposals/generate", response_model=ProposalOut, status_code=201)
async def generate_proposal(
    body: ProposalGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate a new proposal for a gig or lead."""
    # Rate limit
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    gig_ids = [g.id for g in db.query(Gig.id).filter(Gig.user_id == current_user.id).all()]
    lead_ids = [l.id for l in db.query(Lead.id).filter(Lead.user_id == current_user.id).all()]
    today_count = (
        db.query(Proposal)
        .filter(
            (Proposal.gig_id.in_(gig_ids)) | (Proposal.lead_id.in_(lead_ids)),
            Proposal.created_at >= today_start,
        )
        .count()
    )
    if today_count >= MAX_PROPOSALS_PER_DAY:
        raise HTTPException(429, f"Daily proposal limit reached ({MAX_PROPOSALS_PER_DAY}/day)")

    agent = ProposalAgent()
    reviewer = ReviewerAgent()

    job_desc = ""
    client_info: dict = {}

    if body.gig_id:
        gig = db.query(Gig).filter(Gig.id == body.gig_id, Gig.user_id == current_user.id).first()
        if not gig:
            raise HTTPException(404, "Gig not found")
        job_desc = gig.description or gig.title

    if body.lead_id:
        lead = db.query(Lead).filter(Lead.id == body.lead_id, Lead.user_id == current_user.id).first()
        if not lead:
            raise HTTPException(404, "Lead not found")
        client_info = {"name": lead.name, "company": lead.company or "", "role": lead.role or ""}

    if body.lead_id and client_info:
        text = await agent.write_lead_proposal(
            lead_info=client_info,
            portfolio=current_user.portfolio or "",
            user_skills=current_user.skills or [],
        )
    else:
        text = await agent.write_proposal(
            job_description=job_desc,
            portfolio=current_user.portfolio or "",
            client_info=client_info,
            user_skills=current_user.skills or [],
        )

    review = await reviewer.review_proposal(
        proposal_text=text, job_description=job_desc, client_info=client_info or None,
    )

    score = review.get("score", 0)
    p_status = ProposalStatus.approved if score >= 70 else ProposalStatus.reviewed

    proposal = Proposal(
        gig_id=body.gig_id,
        lead_id=body.lead_id,
        content=review.get("improved_version", text) if score < 85 else text,
        review_score=score,
        review_feedback="; ".join(
            f"[{i['severity']}] {i['issue']}" for i in review.get("issues", [])
        ),
        improved_content=review.get("improved_version"),
        status=p_status,
    )
    db.add(proposal)
    db.commit()
    db.refresh(proposal)
    return proposal


@router.post("/proposals/{proposal_id}/send", response_model=ProposalOut)
def send_proposal(
    proposal_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a proposal as sent."""
    # Verify ownership
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(404, "Proposal not found")

    if proposal.status == ProposalStatus.sent:
        raise HTTPException(400, "Proposal already sent")
    if proposal.review_score is not None and proposal.review_score < 70:
        raise HTTPException(400, "Proposal did not pass quality review (score < 70)")

    proposal.status = ProposalStatus.sent
    proposal.sent_at = datetime.now(timezone.utc)

    if proposal.lead_id:
        lead = db.query(Lead).get(proposal.lead_id)
        if lead:
            lead.status = LeadStatus.contacted
    if proposal.gig_id:
        gig = db.query(Gig).get(proposal.gig_id)
        if gig:
            gig.status = GigStatus.applied

    db.commit()
    db.refresh(proposal)
    return proposal


# ═══════════════════════════════════════════════════════════════════════
# Invoices
# ═══════════════════════════════════════════════════════════════════════


@router.get("/invoices", response_model=list[InvoiceOut])
def list_invoices(
    status: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Invoice).filter(Invoice.user_id == current_user.id)
    if status:
        q = q.filter(Invoice.status == status)
    return q.order_by(Invoice.created_at.desc()).all()


@router.post("/invoices", response_model=InvoiceOut, status_code=201)
async def create_invoice(
    body: InvoiceCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    agent = InvoiceAgent()
    result = await agent.generate_invoice(
        client_name=body.client_name,
        client_email=body.client_email or "",
        services=body.services,
        freelancer_name=current_user.name,
        notes=body.notes or "",
    )

    invoice = Invoice(
        user_id=current_user.id,
        invoice_number=result["invoice_number"],
        client_name=body.client_name,
        client_email=body.client_email,
        amount=result["amount"],
        services=body.services,
        status=InvoiceStatus.draft,
        due_date=datetime.fromisoformat(result["due_date"]),
        html_content=result["html_content"],
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


@router.patch("/invoices/{invoice_id}/status", response_model=InvoiceOut)
def update_invoice_status(
    invoice_id: uuid.UUID,
    status: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id, Invoice.user_id == current_user.id
    ).first()
    if not invoice:
        raise HTTPException(404, "Invoice not found")
    try:
        invoice.status = InvoiceStatus(status)
    except ValueError:
        raise HTTPException(400, f"Invalid status: {status}")
    if status == "paid":
        invoice.paid_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(invoice)
    return invoice


# ═══════════════════════════════════════════════════════════════════════
# Analytics
# ═══════════════════════════════════════════════════════════════════════


@router.get("/analytics", response_model=AnalyticsOut)
def get_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    uid = current_user.id
    total_leads = db.query(Lead).filter(Lead.user_id == uid).count()
    total_gigs = db.query(Gig).filter(Gig.user_id == uid).count()
    total_jobs = db.query(Job).filter(Job.user_id == uid).count()

    gig_ids = [g.id for g in db.query(Gig.id).filter(Gig.user_id == uid).all()]
    lead_ids = [l.id for l in db.query(Lead.id).filter(Lead.user_id == uid).all()]

    proposals_q = db.query(Proposal).filter(
        (Proposal.gig_id.in_(gig_ids)) | (Proposal.lead_id.in_(lead_ids))
    )
    total_proposals = proposals_q.count()
    proposals_sent = proposals_q.filter(
        Proposal.status.in_([ProposalStatus.sent, ProposalStatus.accepted])
    ).count()
    proposals_accepted = proposals_q.filter(Proposal.status == ProposalStatus.accepted).count()
    response_rate = (proposals_accepted / proposals_sent * 100) if proposals_sent > 0 else 0.0

    invoices_q = db.query(Invoice).filter(Invoice.user_id == uid)
    invoices_paid = invoices_q.filter(Invoice.status == InvoiceStatus.paid).count()
    invoices_pending = invoices_q.filter(
        Invoice.status.in_([InvoiceStatus.draft, InvoiceStatus.sent, InvoiceStatus.overdue])
    ).count()
    total_revenue = (
        db.query(func.coalesce(func.sum(Invoice.amount), 0))
        .filter(Invoice.user_id == uid, Invoice.status == InvoiceStatus.paid)
        .scalar()
    ) or 0.0

    pipeline_runs = db.query(PipelineRun).filter(PipelineRun.user_id == uid).count()

    platform_stats = (
        db.query(Gig.platform, func.count(Gig.id).label("count"))
        .filter(Gig.user_id == uid)
        .group_by(Gig.platform)
        .order_by(func.count(Gig.id).desc())
        .all()
    )
    best_platforms = [{"platform": p, "gig_count": c} for p, c in platform_stats]

    return AnalyticsOut(
        total_leads=total_leads,
        total_gigs=total_gigs,
        total_jobs=total_jobs,
        total_proposals=total_proposals,
        proposals_sent=proposals_sent,
        proposals_accepted=proposals_accepted,
        response_rate=round(response_rate, 1),
        total_revenue=total_revenue,
        invoices_paid=invoices_paid,
        invoices_pending=invoices_pending,
        pipeline_runs=pipeline_runs,
        best_platforms=best_platforms,
    )
