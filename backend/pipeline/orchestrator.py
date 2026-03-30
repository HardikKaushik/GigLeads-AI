"""Pipeline Orchestrator — runs module-specific pipelines (leads, gigs, jobs).

Each module has its own pipeline:
  Leads: Planner → Lead Finder → Proposal → Review → Communication
  Gigs:  Planner → Gig Finder  → Proposal → Review → Communication
  Jobs:  Planner → Job Finder  → Cover Letter → Review → Simulated Apply

A shared Planner step runs once, then each module pipeline runs in sequence.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..agents import (
    CommunicationAgent,
    CoverLetterAgent,
    GigFinderAgent,
    JobFinderAgent,
    LeadFinderAgent,
    PlannerAgent,
    ProposalAgent,
    ReviewerAgent,
)
from ..db.models import (
    Gig,
    GigStatus,
    Job,
    JobStatus,
    Lead,
    LeadStatus,
    Message,
    MessageChannel,
    MessageDirection,
    PipelineRun,
    PipelineStatus,
    Proposal,
    ProposalStatus,
    User,
)

logger = logging.getLogger(__name__)

MAX_PROPOSALS_PER_RUN = 20
REVIEW_THRESHOLD = 70


def _update(db: Session, run: PipelineRun, **kwargs):
    for k, v in kwargs.items():
        setattr(run, k, v)
    db.commit()
    db.refresh(run)


# ═══════════════════════════════════════════════════════════════════════
# Lead Pipeline
# ═══════════════════════════════════════════════════════════════════════


async def _run_lead_pipeline(
    user: User, db: Session, run: PipelineRun, strategy: dict
):
    """Find leads → generate proposals → review → send."""
    skills = user.skills or []
    portfolio = user.portfolio or ""
    industry = user.target_industry or "Technology"
    onboarding = user.onboarding_data or {}

    _update(db, run, status=PipelineStatus.finding_leads)
    lead_agent = LeadFinderAgent()

    weekly = strategy.get("weekly_targets", {})
    lead_count = min(weekly.get("leads_to_find", 5), 10)

    # Get location preference from onboarding data
    leads_location = onboarding.get("jobs", {}).get("location_preference", "")

    raw_leads = await lead_agent.find_and_score_leads(
        skills=skills, target_industry=industry, count=lead_count,
        portfolio=portfolio, location=leads_location,
    )
    logger.info("Lead pipeline: found %d leads", len(raw_leads))

    db_leads = []
    for rl in raw_leads:
        lead = Lead(
            user_id=user.id, name=rl.get("name", rl.get("company", "Unknown")),
            company=rl.get("company", ""), role=rl.get("role", ""),
            email=rl.get("email", ""), linkedin_url=rl.get("linkedin_url", ""),
            score=rl.get("score", 0), status=LeadStatus.new,
            source=rl.get("source", "pipeline"), notes=rl.get("reasoning", ""),
            location=rl.get("location", ""),
            company_website=rl.get("company_website", ""),
            company_logo=rl.get("company_logo", ""),
            funding_usd=rl.get("funding_usd"),
            industries=rl.get("industries"),
            founders=rl.get("founders"),
            service_opportunity=rl.get("service_opportunity", ""),
            job_url=rl.get("job_url", ""),
        )
        db.add(lead)
        db_leads.append(lead)
    db.commit()
    for obj in db_leads:
        db.refresh(obj)
    _update(db, run, leads_found=run.leads_found + len(db_leads))

    # Generate proposals for top leads
    _update(db, run, status=PipelineStatus.generating_proposals)
    proposal_agent = ProposalAgent()
    reviewer = ReviewerAgent()
    comm_agent = CommunicationAgent()
    sent = 0

    for lead in sorted(db_leads, key=lambda l: l.score or 0, reverse=True)[:MAX_PROPOSALS_PER_RUN]:
        if (lead.score or 0) < 50:
            continue
        try:
            raw = next((r for r in raw_leads if r.get("name") == lead.name), {})
            text = await proposal_agent.write_lead_proposal(
                lead_info={"name": lead.name, "company": lead.company, "role": lead.role},
                portfolio=portfolio, talking_points=raw.get("talking_points"),
                user_skills=skills,
            )
            review = await reviewer.review_proposal(
                proposal_text=text, client_info={"name": lead.name, "company": lead.company, "role": lead.role},
            )
            score = review.get("score", 0)
            content = review.get("improved_version", text) if score < 85 else text

            proposal = Proposal(
                lead_id=lead.id, content=content, review_score=score,
                review_feedback="; ".join(f"[{i['severity']}] {i['issue']}" for i in review.get("issues", [])),
                improved_content=review.get("improved_version"),
                status=ProposalStatus.approved if score >= REVIEW_THRESHOLD else ProposalStatus.reviewed,
            )
            db.add(proposal)
            db.commit()

            if score >= REVIEW_THRESHOLD:
                # Proposal is approved and ready — user sends manually
                sent += 1
        except Exception as exc:
            logger.warning("Lead proposal failed for %s: %s", lead.name, exc)

    _update(db, run, proposals_sent=run.proposals_sent + sent)


# ═══════════════════════════════════════════════════════════════════════
# Gig Pipeline
# ═══════════════════════════════════════════════════════════════════════


async def _run_gig_pipeline(
    user: User, db: Session, run: PipelineRun, strategy: dict
):
    """Find gigs → generate proposals → review → send."""
    skills = user.skills or []
    portfolio = user.portfolio or ""
    industry = user.target_industry or "Technology"

    _update(db, run, status=PipelineStatus.finding_gigs)
    gig_agent = GigFinderAgent()

    platforms = [
        p["platform"] for p in strategy.get("recommended_platforms", [])
        if p.get("priority") in ("high", "medium")
    ]
    raw_gigs = await gig_agent.find_and_rank_gigs(
        skills=skills, target_industry=industry, platforms=platforms or None, count=15,
    )
    logger.info("Gig pipeline: found %d gigs", len(raw_gigs))

    db_gigs = []
    for rg in raw_gigs:
        gig = Gig(
            user_id=user.id, title=rg.get("title", "Untitled"),
            platform=rg.get("platform", "upwork"), budget=rg.get("budget", 0),
            description=rg.get("description", ""), url=rg.get("url", ""),
            match_score=rg.get("match_score", 0), status=GigStatus.discovered,
        )
        db.add(gig)
        db_gigs.append(gig)
    db.commit()
    for obj in db_gigs:
        db.refresh(obj)
    _update(db, run, gigs_found=run.gigs_found + len(db_gigs))

    _update(db, run, status=PipelineStatus.generating_proposals)
    proposal_agent = ProposalAgent()
    reviewer = ReviewerAgent()
    sent = 0

    for gig in sorted(db_gigs, key=lambda g: g.match_score or 0, reverse=True)[:MAX_PROPOSALS_PER_RUN]:
        if (gig.match_score or 0) < 50:
            continue
        try:
            raw = next((r for r in raw_gigs if r.get("title") == gig.title), {})
            job_desc = gig.description or gig.title
            angle = raw.get("proposal_angle", "")
            if angle:
                job_desc += f"\n\nSuggested angle: {angle}"

            text = await proposal_agent.write_proposal(
                job_description=job_desc, portfolio=portfolio,
                client_info={"name": "", "company": "", "role": ""},
                user_skills=skills,
            )
            review = await reviewer.review_proposal(proposal_text=text, job_description=job_desc)
            score = review.get("score", 0)
            content = review.get("improved_version", text) if score < 85 else text

            proposal = Proposal(
                gig_id=gig.id, content=content, review_score=score,
                review_feedback="; ".join(f"[{i['severity']}] {i['issue']}" for i in review.get("issues", [])),
                improved_content=review.get("improved_version"),
                status=ProposalStatus.approved if score >= REVIEW_THRESHOLD else ProposalStatus.reviewed,
            )
            db.add(proposal)

            if score >= REVIEW_THRESHOLD:
                proposal.status = ProposalStatus.approved  # Ready — user sends manually
                gig.status = GigStatus.discovered  # Proposal ready — user applies manually
                sent += 1

            db.commit()
        except Exception as exc:
            logger.warning("Gig proposal failed for %s: %s", gig.title[:40], exc)

    _update(db, run, proposals_sent=run.proposals_sent + sent)


# ═══════════════════════════════════════════════════════════════════════
# Job Pipeline
# ═══════════════════════════════════════════════════════════════════════


async def _run_job_pipeline(
    user: User, db: Session, run: PipelineRun, strategy: dict
):
    """Find jobs → generate cover letters → review → simulated apply."""
    skills = user.skills or []
    portfolio = user.portfolio or ""
    onboarding = user.onboarding_data or {}
    jobs_data = onboarding.get("jobs", {})

    _update(db, run, status=PipelineStatus.finding_jobs)
    job_agent = JobFinderAgent()

    raw_jobs = await job_agent.find_and_rank_jobs(
        skills=skills,
        desired_role=jobs_data.get("desired_role", ""),
        experience_level=jobs_data.get("experience_level", ""),
        location_preference=jobs_data.get("location_preference", ""),
        salary_range=jobs_data.get("salary_range", ""),
        count=20,
    )
    logger.info("Job pipeline: found %d jobs", len(raw_jobs))

    db_jobs = []
    for rj in raw_jobs:
        job = Job(
            user_id=user.id, title=rj.get("title", "Untitled"),
            company=rj.get("company", ""), platform=rj.get("platform", "linkedin"),
            job_type=rj.get("job_type", "full-time"),
            salary_min=rj.get("salary_min"), salary_max=rj.get("salary_max"),
            location=rj.get("location", ""), remote=rj.get("remote", False),
            description=rj.get("description", ""), url=rj.get("url", ""),
            match_score=rj.get("match_score", 0), status=JobStatus.discovered,
        )
        db.add(job)
        db_jobs.append(job)
    db.commit()
    for obj in db_jobs:
        db.refresh(obj)
    _update(db, run, jobs_found=run.jobs_found + len(db_jobs))

    # Generate cover letters for top jobs
    _update(db, run, status=PipelineStatus.generating_cover_letters)
    cl_agent = CoverLetterAgent()
    reviewer = ReviewerAgent()
    applied = 0

    for job in sorted(db_jobs, key=lambda j: j.match_score or 0, reverse=True)[:MAX_PROPOSALS_PER_RUN]:
        if (job.match_score or 0) < 50:
            continue
        try:
            letter = await cl_agent.write_cover_letter(
                job_description=job.description or job.title,
                company=job.company or "", job_title=job.title,
                portfolio=portfolio, user_skills=skills,
                desired_role=jobs_data.get("desired_role", ""),
            )

            review = await reviewer.review_proposal(
                proposal_text=letter, job_description=job.description or job.title,
            )
            score = review.get("score", 0)
            final_letter = review.get("improved_version", letter) if score < 85 else letter

            job.cover_letter = final_letter

            if score >= REVIEW_THRESHOLD:
                job.status = JobStatus.bookmarked  # Ready to apply — user decides
                applied += 1
            else:
                job.status = JobStatus.discovered  # Needs improvement

            db.commit()
        except Exception as exc:
            logger.warning("Job cover letter failed for %s: %s", job.title[:40], exc)

    _update(db, run, proposals_sent=run.proposals_sent + applied)


# ═══════════════════════════════════════════════════════════════════════
# Main Entry Point
# ═══════════════════════════════════════════════════════════════════════


async def run_selected_pipelines(
    user_id: str, db: Session, run_id: str | None = None, modules: list[str] | None = None
) -> str:
    """Execute pipelines for the specified modules.

    Args:
        user_id: UUID string of the user
        db: SQLAlchemy session
        run_id: Optional existing pipeline run ID
        modules: List of modules to run — ["leads", "gigs", "jobs"]

    Returns:
        The pipeline_run id string.
    """
    user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
    if not user:
        raise ValueError(f"User {user_id} not found")

    modules = modules or user.selected_modules or ["leads", "gigs", "jobs"]

    if run_id:
        run = db.query(PipelineRun).filter(PipelineRun.id == uuid.UUID(run_id)).first()
        if not run:
            raise ValueError(f"Pipeline run {run_id} not found")
    else:
        pipeline_type = ",".join(sorted(modules)) if len(modules) < 3 else "all"
        run = PipelineRun(user_id=user.id, status=PipelineStatus.pending, pipeline_type=pipeline_type)
        db.add(run)
        db.commit()
        db.refresh(run)

    run_id = str(run.id)
    logger.info("Pipeline %s started for user %s — modules: %s", run_id, user_id, modules)

    try:
        # Step 1: Module-specific planning
        _update(db, run, status=PipelineStatus.planning)
        planner = PlannerAgent()
        strategy = await planner.create_strategy(
            skills=user.skills or [], target_industry=user.target_industry or "Technology",
            income_goal=user.income_goal or 5000.0, portfolio=user.portfolio or "",
            modules=modules,
        )
        _update(db, run, strategy=strategy)
        logger.info("Pipeline %s: strategy created", run_id)

        # Step 2: Run each selected module pipeline
        if "leads" in modules:
            await _run_lead_pipeline(user, db, run, strategy)

        if "gigs" in modules:
            await _run_gig_pipeline(user, db, run, strategy)

        if "jobs" in modules:
            await _run_job_pipeline(user, db, run, strategy)

        # Complete
        _update(db, run, status=PipelineStatus.completed, completed_at=datetime.now(timezone.utc))
        logger.info(
            "Pipeline %s completed: %d leads, %d gigs, %d jobs, %d proposals sent",
            run_id, run.leads_found, run.gigs_found, run.jobs_found, run.proposals_sent,
        )

    except Exception as exc:
        logger.exception("Pipeline %s failed: %s", run_id, exc)
        _update(db, run, status=PipelineStatus.failed, error_message=str(exc), completed_at=datetime.now(timezone.utc))
        raise

    return run_id
