/**
 * API client — all backend calls go through here.
 * Automatically attaches JWT Bearer token from localStorage.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("freelance_token");
}

async function request<T>(path: string, opts: RequestInit = {}, tokenOverride?: string): Promise<T> {
  const token = tokenOverride || getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(opts.headers as Record<string, string> || {}),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, { ...opts, headers });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `API error ${res.status}`);
  }
  return res.json();
}

// ── Types ──────────────────────────────────────────────────────

export interface User {
  id: string;
  name: string;
  email: string;
  skills: string[];
  portfolio: string | null;
  income_goal: number | null;
  target_industry: string | null;
  selected_modules: string[];
  onboarding_completed: boolean;
  onboarding_data: Record<string, unknown> | null;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface PipelineRun {
  id: string;
  user_id: string;
  status: string;
  pipeline_type: string | null;
  strategy: Record<string, unknown> | null;
  leads_found: number;
  gigs_found: number;
  jobs_found: number;
  proposals_sent: number;
  error_message: string | null;
  started_at: string;
  completed_at: string | null;
}

export interface Lead {
  id: string;
  user_id: string;
  name: string;
  company: string | null;
  role: string | null;
  email: string | null;
  linkedin_url: string | null;
  score: number | null;
  status: string;
  source: string | null;
  notes: string | null;
  created_at: string;
}

export interface Gig {
  id: string;
  user_id: string;
  title: string;
  platform: string;
  budget: number | null;
  description: string | null;
  url: string | null;
  match_score: number | null;
  status: string;
  deadline: string | null;
  created_at: string;
}

export interface Job {
  id: string;
  user_id: string;
  title: string;
  company: string | null;
  platform: string;
  job_type: string | null;
  salary_min: number | null;
  salary_max: number | null;
  location: string | null;
  remote: boolean;
  description: string | null;
  url: string | null;
  match_score: number | null;
  status: string;
  cover_letter: string | null;
  created_at: string;
}

export interface Proposal {
  id: string;
  gig_id: string | null;
  lead_id: string | null;
  content: string;
  review_score: number | null;
  review_feedback: string | null;
  improved_content: string | null;
  status: string;
  sent_at: string | null;
  response: string | null;
  created_at: string;
}

export interface Invoice {
  id: string;
  user_id: string;
  invoice_number: string;
  client_name: string;
  client_email: string | null;
  amount: number;
  services: { description: string; amount: number }[];
  status: string;
  due_date: string;
  paid_at: string | null;
  html_content: string | null;
  created_at: string;
}

export interface Analytics {
  total_leads: number;
  total_gigs: number;
  total_jobs: number;
  total_proposals: number;
  proposals_sent: number;
  proposals_accepted: number;
  response_rate: number;
  total_revenue: number;
  invoices_paid: number;
  invoices_pending: number;
  pipeline_runs: number;
  best_platforms: { platform: string; gig_count: number }[];
}

// ── API calls ──────────────────────────────────────────────────

export const api = {
  // Auth
  signup: (data: { name: string; email: string; password: string }) =>
    request<AuthResponse>("/api/auth/signup", { method: "POST", body: JSON.stringify(data) }),

  login: (data: { email: string; password: string }) =>
    request<AuthResponse>("/api/auth/login", { method: "POST", body: JSON.stringify(data) }),

  getMe: (token?: string) =>
    request<User>("/api/auth/me", {}, token),

  // Profile
  updateProfile: (data: Partial<Pick<User, "name" | "skills" | "portfolio" | "income_goal" | "target_industry">>) =>
    request<User>("/api/users/profile", { method: "PUT", body: JSON.stringify(data) }),

  updateModules: (selectedModules: string[]) =>
    request<User>("/api/users/modules", {
      method: "PUT",
      body: JSON.stringify({ selected_modules: selectedModules }),
    }),

  completeOnboarding: (onboardingData: Record<string, unknown>) =>
    request<User>("/api/users/onboarding", {
      method: "PUT",
      body: JSON.stringify({ onboarding_data: onboardingData }),
    }),

  // Pipeline
  startPipeline: (modules?: string[]) =>
    request<PipelineRun>("/api/pipeline/start", {
      method: "POST",
      body: JSON.stringify({ modules: modules || null }),
    }),

  getPipelineStatus: (runId: string) =>
    request<PipelineRun>(`/api/pipeline/${runId}/status`),

  getPipelineHistory: (limit = 10) =>
    request<PipelineRun[]>(`/api/pipeline/history?limit=${limit}`),

  // Leads
  getLeads: (params?: { status?: string; min_score?: number }) => {
    const qs = new URLSearchParams();
    if (params?.status) qs.set("status", params.status);
    if (params?.min_score) qs.set("min_score", String(params.min_score));
    return request<Lead[]>(`/api/leads?${qs}`);
  },

  updateLeadStatus: (leadId: string, status: string) =>
    request<Lead>(`/api/leads/${leadId}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),

  // Gigs
  getGigs: (params?: { platform?: string; status?: string }) => {
    const qs = new URLSearchParams();
    if (params?.platform) qs.set("platform", params.platform);
    if (params?.status) qs.set("status", params.status);
    return request<Gig[]>(`/api/gigs?${qs}`);
  },

  // Jobs
  getJobs: (params?: { platform?: string; job_type?: string; status?: string }) => {
    const qs = new URLSearchParams();
    if (params?.platform) qs.set("platform", params.platform);
    if (params?.job_type) qs.set("job_type", params.job_type);
    if (params?.status) qs.set("status", params.status);
    return request<Job[]>(`/api/jobs?${qs}`);
  },

  updateJobStatus: (jobId: string, status: string) =>
    request<Job>(`/api/jobs/${jobId}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),

  // Proposals
  getProposals: (status?: string) => {
    const qs = new URLSearchParams();
    if (status) qs.set("status", status);
    return request<Proposal[]>(`/api/proposals?${qs}`);
  },

  generateProposal: (data: { gig_id?: string; lead_id?: string }) =>
    request<Proposal>("/api/proposals/generate", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  sendProposal: (proposalId: string) =>
    request<Proposal>(`/api/proposals/${proposalId}/send`, { method: "POST" }),

  // Invoices
  getInvoices: (status?: string) => {
    const qs = new URLSearchParams();
    if (status) qs.set("status", status);
    return request<Invoice[]>(`/api/invoices?${qs}`);
  },

  createInvoice: (data: {
    client_name: string;
    client_email?: string;
    services: { description: string; amount: number }[];
    notes?: string;
  }) =>
    request<Invoice>("/api/invoices", { method: "POST", body: JSON.stringify(data) }),

  updateInvoiceStatus: (invoiceId: string, status: string) =>
    request<Invoice>(`/api/invoices/${invoiceId}/status?status=${status}`, {
      method: "PATCH",
    }),

  // Analytics
  getAnalytics: () =>
    request<Analytics>(`/api/analytics`),
};
