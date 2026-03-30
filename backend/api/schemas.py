"""Pydantic request/response schemas for the API."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# ── Auth ────────────────────────────────────────────────────────────────


class SignupRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserProfileOut"


# ── Users ────────────────────────────────────────────────────────────────


class UserProfileCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: str = Field(..., min_length=3, max_length=255)
    skills: list[str] = Field(default_factory=list)
    portfolio: str | None = None
    income_goal: float | None = None
    target_industry: str | None = None


class UserProfileUpdate(BaseModel):
    name: str | None = None
    skills: list[str] | None = None
    portfolio: str | None = None
    income_goal: float | None = None
    target_industry: str | None = None


class UserProfileOut(BaseModel):
    id: UUID
    name: str
    email: str
    skills: list[str]
    portfolio: str | None
    income_goal: float | None
    target_industry: str | None
    selected_modules: list[str]
    onboarding_completed: bool
    onboarding_data: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ModuleSelectionRequest(BaseModel):
    selected_modules: list[str] = Field(..., min_length=1)


class OnboardingRequest(BaseModel):
    onboarding_data: dict[str, Any]


# ── Pipeline ─────────────────────────────────────────────────────────────


class PipelineStartRequest(BaseModel):
    modules: list[str] | None = None  # ["leads", "gigs", "jobs"]; defaults to user's selected_modules


class PipelineStatusOut(BaseModel):
    id: UUID
    user_id: UUID
    status: str
    pipeline_type: str | None = None
    strategy: dict | None = None
    leads_found: int
    gigs_found: int
    jobs_found: int = 0
    proposals_sent: int
    error_message: str | None = None
    started_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


# ── Leads ────────────────────────────────────────────────────────────────


class LeadOut(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    company: str | None
    role: str | None
    email: str | None
    linkedin_url: str | None
    score: int | None
    status: str
    source: str | None
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class LeadStatusUpdate(BaseModel):
    status: str


# ── Gigs ─────────────────────────────────────────────────────────────────


class GigOut(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    platform: str
    budget: float | None
    description: str | None
    url: str | None
    match_score: int | None
    status: str
    deadline: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Jobs ─────────────────────────────────────────────────────────────────


class JobOut(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    company: str | None
    platform: str
    job_type: str | None
    salary_min: float | None
    salary_max: float | None
    location: str | None
    remote: bool
    description: str | None
    url: str | None
    match_score: int | None
    status: str
    cover_letter: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class JobStatusUpdate(BaseModel):
    status: str


# ── Proposals ────────────────────────────────────────────────────────────


class ProposalOut(BaseModel):
    id: UUID
    gig_id: UUID | None
    lead_id: UUID | None
    content: str
    review_score: int | None
    review_feedback: str | None
    improved_content: str | None
    status: str
    sent_at: datetime | None
    response: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ProposalGenerateRequest(BaseModel):
    gig_id: UUID | None = None
    lead_id: UUID | None = None


# ── Invoices ─────────────────────────────────────────────────────────────


class InvoiceCreateRequest(BaseModel):
    client_name: str
    client_email: str | None = None
    services: list[dict] = Field(..., min_length=1)
    notes: str | None = None


class InvoiceOut(BaseModel):
    id: UUID
    user_id: UUID
    invoice_number: str
    client_name: str
    client_email: str | None
    amount: float
    services: list[dict]
    status: str
    due_date: datetime
    paid_at: datetime | None
    html_content: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Analytics ────────────────────────────────────────────────────────────


class AnalyticsOut(BaseModel):
    total_leads: int
    total_gigs: int
    total_jobs: int = 0
    total_proposals: int
    proposals_sent: int
    proposals_accepted: int
    response_rate: float
    total_revenue: float
    invoices_paid: int
    invoices_pending: int
    pipeline_runs: int
    best_platforms: list[dict]
