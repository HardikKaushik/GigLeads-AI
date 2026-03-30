"""Lead Finder Agent — discovers B2B leads (potential clients) via RapidAPI + Crunchbase + AI scoring."""

import json
from .base import BaseAgent
from ..mcp_server.rapidapi_clients import RapidAPIService

SYSTEM_PROMPT = """You are an expert B2B lead researcher for freelancers.
You help freelancers find CLIENTS — companies/people who NEED services built (software, websites, apps, etc).

Given a list of REAL companies found from job platforms and enriched with Crunchbase data,
score each as a potential CLIENT based on the freelancer's skills.

You MUST respond with valid JSON only — a list of lead objects.

Each lead object schema:
{
  "name": "string (keep original company name)",
  "company": "string (keep original)",
  "role": "string (keep original signal)",
  "email": "string (keep if provided)",
  "linkedin_url": "string (keep EXACT original URL)",
  "location": "string (keep original)",
  "score": number (0-100),
  "reasoning": "why this company is a good/bad potential CLIENT — 1-2 sentences",
  "recommended_approach": "linkedin|email|website|skip",
  "talking_points": ["specific value you can offer this company", ...],
  "service_opportunity": "what specific service/project you could pitch to them"
}

CRITICAL RULES:
- Keep ALL original data fields EXACTLY as provided
- Do NOT invent or modify URLs
- ONLY add: score, reasoning, recommended_approach, talking_points, service_opportunity

Score criteria (as POTENTIAL CLIENT, not employer):
- 85-100: Recently funded, actively buying freelance services, perfect skill match
- 70-84: Growing company in target industry, likely needs your skills
- 50-69: Relevant industry but unclear need, worth exploring
- Below 50: Poor fit as a client"""


class LeadFinderAgent(BaseAgent):
    name = "lead_finder"

    def __init__(self):
        super().__init__()
        self.rapidapi = RapidAPIService()

    async def find_and_score_leads(
        self,
        skills: list[str],
        target_industry: str,
        count: int = 10,
        portfolio: str = "",
        location: str = "",
    ) -> list[dict]:
        """Find B2B leads (potential clients) and score them with AI.

        Flow:
          1. Search LinkedIn + JSearch for companies posting freelance/contract work
          2. Enrich with Crunchbase (funding, founders, industry)
          3. AI scores each company as a potential CLIENT
          4. Returns scored leads sorted by opportunity

        Args:
            skills: User's skills list
            target_industry: Target industry to focus on
            count: Number of leads to return
            portfolio: Optional portfolio summary for context
            location: Location preference

        Returns:
            List of scored B2B lead dicts.
        """
        # Step 1: Fetch real B2B leads
        raw_leads = []
        if self.rapidapi.enabled:
            primary_skill = skills[0] if skills else "developer"
            industry_clean = target_industry.split(",")[0].strip() if target_industry else ""

            raw_leads = await self.rapidapi.search_leads(
                keywords=primary_skill,
                industry=industry_clean,
                location=location,
                count=count,
            )

            # If first query returned few results, try broader
            if len(raw_leads) < count and len(skills) > 1:
                more = await self.rapidapi.search_leads(
                    keywords=skills[1],
                    industry=industry_clean,
                    location=location,
                    count=count - len(raw_leads),
                )
                seen = {l.get("company", "").lower() for l in raw_leads}
                for lead in more:
                    if lead.get("company", "").lower() not in seen:
                        raw_leads.append(lead)
                        seen.add(lead.get("company", "").lower())

        if not raw_leads:
            return []

        # Step 2: Score with AI
        leads_text = "\n".join(
            f"- {l.get('company', 'Unknown')} | Signal: {l.get('role', 'N/A')}"
            f" | Location: {l.get('location', 'N/A')}"
            f" | LinkedIn: {l.get('linkedin_url', 'N/A')}"
            f" | Funding: {'$' + str(l['funding_usd']) if l.get('funding_usd') else 'Unknown'}"
            f" | Industries: {', '.join(l.get('industries', [])) if l.get('industries') else 'N/A'}"
            f" | Employees: {l.get('num_employees', 'N/A')}"
            f" | Founders: {', '.join(f.get('name', '') for f in l.get('founders', [])) if l.get('founders') else 'N/A'}"
            f" | Contract: {'Yes' if l.get('is_contract') else 'No'}"
            for l in raw_leads
        )

        user_prompt = f"""Score these companies as POTENTIAL CLIENTS for a freelancer:

## Freelancer Skills
{', '.join(skills)}

## Target Industry
{target_industry or 'All industries'}

## Portfolio
{portfolio or 'Experienced developer available for contract work.'}

## Companies Found (DO NOT modify any URLs or original data!)
{leads_text}

Key signals for high scores:
- Company has recent funding → they have BUDGET
- Company is posting freelance/contract jobs → they NEED outside help
- Company is in the freelancer's target industry → RELEVANT
- Company has founders listed → direct decision-makers to contact

Return EXACTLY {len(raw_leads)} leads as a JSON array.
PRESERVE all original data exactly."""

        try:
            scored = await self.call_claude_json(SYSTEM_PROMPT, user_prompt)
            if isinstance(scored, list):
                # Preserve original data that AI might have modified
                for i, lead in enumerate(scored):
                    if i < len(raw_leads):
                        original = raw_leads[i]
                        lead["linkedin_url"] = original.get("linkedin_url", lead.get("linkedin_url", ""))
                        lead["company_website"] = original.get("company_website", "")
                        lead["company_logo"] = original.get("company_logo", "")
                        lead["source"] = original.get("source", "rapidapi")
                        lead["job_url"] = original.get("job_url", "")
                        lead["funding_usd"] = original.get("funding_usd")
                        lead["founders"] = original.get("founders", [])
                        lead["industries"] = original.get("industries", [])
                        lead["crunchbase_enriched"] = original.get("crunchbase_enriched", False)
                        if not lead.get("name"):
                            lead["name"] = original.get("name", original.get("company", ""))
                        if not lead.get("company"):
                            lead["company"] = original.get("company", "")
                return scored
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("Lead AI scoring failed: %s", e)
            # Fallback: basic scoring based on signals
            for lead in raw_leads:
                score = 40  # base
                if lead.get("funding_usd"):
                    score += 25  # funded = has budget
                if lead.get("is_contract"):
                    score += 20  # posting freelance work
                if lead.get("founders"):
                    score += 10  # we know who to contact
                if lead.get("crunchbase_enriched"):
                    score += 5
                lead["score"] = min(score, 95)
                lead["reasoning"] = "AI scoring unavailable — scored by funding and signals"
                lead["recommended_approach"] = "linkedin" if lead.get("linkedin_url") else "website"
                lead["talking_points"] = [f"Can help with {skills[0]} development" if skills else "Available for contract work"]
                lead["service_opportunity"] = f"{skills[0]} development services" if skills else "Software development"

        return raw_leads
