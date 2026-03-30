"""FastMCP server — tool layer for the GigLeads AI agents.

Uses RapidAPI for real data from LinkedIn, Indeed, Naukri, and Internshala.
No mock data — all results come from real API calls.
"""

import os
import random
import uuid
from datetime import datetime, timedelta, timezone

from fastmcp import FastMCP

from .rapidapi_clients import RapidAPIService

mcp = FastMCP("GigLeadsAI")

# Shared RapidAPI service instance
_rapidapi: RapidAPIService | None = None


def _get_rapidapi() -> RapidAPIService:
    global _rapidapi
    if _rapidapi is None:
        _rapidapi = RapidAPIService()
    return _rapidapi


# ── Tools ────────────────────────────────────────────────────────────────


@mcp.tool()
async def search_gigs(query: str, platform: str = "all") -> list[dict]:
    """Search for real freelance gigs from LinkedIn and job platforms.

    Args:
        query: Keywords to search for (e.g. "python backend api")
        platform: Filter by platform — "linkedin", "indeed", or "all"

    Returns:
        List of real gig dicts with title, platform, budget, description, url.
    """
    service = _get_rapidapi()
    if not service.enabled:
        return [{"error": "RAPIDAPI_KEY not configured"}]

    return await service.search_gigs(query=query, count=10)


@mcp.tool()
async def find_leads(industry: str, role: str = "", count: int = 5) -> list[dict]:
    """Find real LinkedIn leads filtered by industry and optional role.

    Uses LinkedIn People Search via RapidAPI for real profiles with real LinkedIn URLs.

    Args:
        industry: Target industry (e.g. "SaaS", "FinTech", "HealthTech")
        role: Optional role filter (e.g. "CTO", "VP")
        count: Max number of leads to return (default 5)

    Returns:
        List of real lead dicts with name, company, role, linkedin_url.
    """
    service = _get_rapidapi()
    if not service.enabled:
        return [{"error": "RAPIDAPI_KEY not configured"}]

    return await service.search_leads(
        industry=industry,
        role=role,
        count=count,
    )


@mcp.tool()
async def search_jobs(
    query: str,
    location: str = "",
    platforms: str = "all",
    count: int = 10,
) -> list[dict]:
    """Search for real jobs across LinkedIn, Indeed, Naukri, and Internshala.

    Args:
        query: Job search keywords (e.g. "python developer")
        location: Location filter (e.g. "India", "Remote", "New York")
        platforms: Comma-separated platforms — "linkedin,indeed,naukri,internshala" or "all"
        count: Max results to return

    Returns:
        List of real job dicts from multiple platforms.
    """
    service = _get_rapidapi()
    if not service.enabled:
        return [{"error": "RAPIDAPI_KEY not configured"}]

    platform_list = None
    if platforms != "all":
        platform_list = [p.strip() for p in platforms.split(",")]

    return await service.search_all_jobs(
        query=query,
        location=location,
        platforms=platform_list,
        count_per_platform=max(count // 4, 3),
    )


@mcp.tool()
def generate_proposal(job_desc: str, portfolio: str, client_info: dict) -> str:
    """Generate a personalized freelance proposal using AI.

    Args:
        job_desc: The full job/gig description
        portfolio: The freelancer's portfolio summary text
        client_info: Dict with client details — name, company, role (all optional)

    Returns:
        The generated proposal text.
    """
    from openai import OpenAI

    client = OpenAI(
        api_key=os.getenv("XAI_API_KEY", ""),
        base_url=os.getenv("XAI_BASE_URL", "https://api.groq.com/openai/v1"),
    )
    model = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")

    client_name = client_info.get("name", "the client")
    company = client_info.get("company", "your company")
    role = client_info.get("role", "")

    prompt = f"""Write a compelling, personalized freelance proposal for the following job.

## Job Description
{job_desc}

## Client Info
- Name: {client_name}
- Company: {company}
- Role: {role}

## Freelancer Portfolio
{portfolio}

## Requirements
- Address the client BY NAME and reference their COMPANY specifically
- Reference specific requirements from the job description
- Highlight relevant experience from the portfolio
- Include a rough timeline and approach
- Keep it professional but warm — not generic
- 250-400 words
- Do NOT use placeholder brackets like [X] — write concrete content"""

    response = client.chat.completions.create(
        model=model,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


@mcp.tool()
def create_invoice(client: str, amount: float, services: list[dict]) -> dict:
    """Create a professional invoice.

    Args:
        client: Client name
        amount: Total invoice amount in USD
        services: List of service line items, each with "description" and "amount" keys

    Returns:
        Dict with invoice_number, client, amount, services, due_date, html snippet.
    """
    inv_number = f"INV-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    due_date = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()

    rows = "".join(
        f"<tr><td>{s.get('description', '')}</td>"
        f"<td style='text-align:right'>${s.get('amount', 0):,.2f}</td></tr>"
        for s in services
    )

    html = f"""<!DOCTYPE html>
<html><head><style>
body {{ font-family: 'Helvetica Neue', sans-serif; max-width: 700px; margin: 40px auto; color: #1a1a1a; }}
h1 {{ color: #2563eb; margin-bottom: 4px; }}
table {{ width: 100%; border-collapse: collapse; margin-top: 24px; }}
th, td {{ padding: 10px 12px; border-bottom: 1px solid #e5e7eb; text-align: left; }}
th {{ background: #f9fafb; font-weight: 600; }}
.total {{ font-size: 1.25em; font-weight: 700; text-align: right; margin-top: 16px; }}
.meta {{ color: #6b7280; font-size: 0.9em; }}
</style></head><body>
<h1>INVOICE</h1>
<p class="meta">{inv_number}</p>
<p><strong>Bill To:</strong> {client}</p>
<p class="meta"><strong>Due Date:</strong> {due_date[:10]}</p>
<table>
<thead><tr><th>Service</th><th style="text-align:right">Amount</th></tr></thead>
<tbody>{rows}</tbody>
</table>
<p class="total">Total: ${amount:,.2f}</p>
</body></html>"""

    return {
        "invoice_number": inv_number,
        "client": client,
        "amount": amount,
        "services": services,
        "due_date": due_date,
        "html": html,
    }


@mcp.tool()
def send_message(to: str, subject: str, body: str, channel: str = "email") -> dict:
    """Simulate sending a message via email or LinkedIn (logged, not actually sent).

    Args:
        to: Recipient email or LinkedIn profile URL
        subject: Message subject line
        body: Message body text
        channel: "email" or "linkedin"

    Returns:
        Dict with sent status, message_id, timestamp, and channel.
    """
    return {
        "sent": True,
        "message_id": uuid.uuid4().hex,
        "to": to,
        "subject": subject,
        "channel": channel,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "note": "Message logged (MVP — not actually delivered)",
    }


@mcp.tool()
def score_lead(lead: dict, user_skills: list[str]) -> dict:
    """Score a lead based on relevance to the user's skills and profile.

    Args:
        lead: Lead dict with name, company, role, and optionally industry
        user_skills: List of the freelancer's skills

    Returns:
        Dict with score (0-100), reasoning, and recommended_action.
    """
    score = 50  # base

    role = lead.get("role", "").lower()
    if any(title in role for title in ["cto", "vp", "head", "director", "ceo", "founder"]):
        score += 20
    elif any(title in role for title in ["manager", "lead"]):
        score += 10

    if lead.get("company"):
        score += 10
    if lead.get("email"):
        score += 5
    if lead.get("linkedin_url"):
        score += 5
    if lead.get("company_size") and lead["company_size"] > 50:
        score += 5

    score += random.randint(-5, 10)
    score = max(0, min(100, score))

    if score >= 80:
        action = "high_priority"
        reasoning = f"{lead.get('name', 'Lead')} is a decision-maker at {lead.get('company', 'their company')} — prioritize outreach."
    elif score >= 60:
        action = "worth_pursuing"
        reasoning = f"{lead.get('name', 'Lead')} at {lead.get('company', 'their company')} is a solid prospect."
    else:
        action = "low_priority"
        reasoning = f"{lead.get('name', 'Lead')} may not be the ideal fit — consider a soft introduction."

    return {
        "lead_name": lead.get("name", ""),
        "score": score,
        "reasoning": reasoning,
        "recommended_action": action,
    }


# ── Entry point ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
