"""Lead Finder Agent — discovers real LinkedIn leads via RapidAPI + AI scoring."""

import json
from .base import BaseAgent
from ..mcp_server.rapidapi_clients import RapidAPIService

SYSTEM_PROMPT = """You are an expert B2B lead researcher for freelancers.
Given a list of REAL leads fetched from LinkedIn, score and enrich each one based on the freelancer's profile.

You MUST respond with valid JSON only — a list of lead objects.

Each lead object schema:
{
  "name": "string (keep original name from data)",
  "company": "string (keep original company from data)",
  "role": "string (keep original role/headline from data)",
  "email": "string (keep if provided, empty string if not)",
  "linkedin_url": "string (keep the EXACT original LinkedIn URL — do NOT modify it)",
  "location": "string (keep original)",
  "score": number (0-100),
  "reasoning": "why this lead is a good/bad fit — 1-2 sentences",
  "recommended_approach": "email|linkedin|skip",
  "talking_points": ["specific point to mention in outreach", ...]
}

CRITICAL RULES:
- Keep ALL original data fields EXACTLY as provided (especially linkedin_url)
- Do NOT invent or modify LinkedIn URLs
- Do NOT change names or companies
- ONLY add: score, reasoning, recommended_approach, talking_points

Score criteria:
- 80-100: Decision-maker in target industry, clear need for freelancer's skills
- 60-79: Relevant role or industry, moderate fit
- 40-59: Tangential fit, worth a soft introduction
- 0-39: Poor fit, recommend skipping"""


class LeadFinderAgent(BaseAgent):
    name = "lead_finder"

    def __init__(self):
        super().__init__()
        self.rapidapi = RapidAPIService()

    async def find_and_score_leads(
        self,
        skills: list[str],
        target_industry: str,
        count: int = 5,
        portfolio: str = "",
    ) -> list[dict]:
        """Find real LinkedIn leads and score them with AI.

        1. Fetches real profiles from LinkedIn via RapidAPI
        2. AI scores each lead based on freelancer's skills/industry
        3. Returns scored leads with real LinkedIn URLs

        Args:
            skills: User's skills list
            target_industry: Target industry to focus on
            count: Number of leads to return
            portfolio: Optional portfolio summary for context

        Returns:
            List of scored lead dicts with real LinkedIn data.
        """
        # Step 1: Fetch real leads — use SHORT, focused queries
        # JSearch works best with concise queries like "Python developer SaaS"
        raw_leads = []
        if self.rapidapi.enabled:
            # Use primary skill + first industry (not all skills jammed together)
            primary_skill = skills[0] if skills else "developer"
            # Clean industry — take first one if comma-separated
            industry_clean = target_industry.split(",")[0].strip() if target_industry else ""

            raw_leads = await self.rapidapi.search_leads(
                keywords=f"{primary_skill} developer",
                industry=industry_clean,
                role="",
                count=count,
            )

            # If first query returned few results, try a broader query
            if len(raw_leads) < count and len(skills) > 1:
                more = await self.rapidapi.search_leads(
                    keywords=f"{skills[1]} engineer",
                    industry=industry_clean,
                    count=count - len(raw_leads),
                )
                # Deduplicate by company name
                seen = {l.get("company", "") for l in raw_leads}
                for lead in more:
                    if lead.get("company", "") not in seen:
                        raw_leads.append(lead)
                        seen.add(lead.get("company", ""))

        if not raw_leads:
            # Return empty — no fake data
            return []

        # Step 2: Score real leads with AI
        leads_text = "\n".join(
            f"- {l['name']}, \"{l.get('role', 'N/A')}\" at {l.get('company', 'N/A')}"
            f" | LinkedIn: {l.get('linkedin_url', 'N/A')}"
            f" | Location: {l.get('location', 'N/A')}"
            for l in raw_leads
        )

        user_prompt = f"""Score these REAL LinkedIn leads for a freelancer:

## Freelancer Skills
{', '.join(skills)}

## Target Industry
{target_industry}

## Portfolio
{portfolio or 'General development experience.'}

## Real LinkedIn Leads (DO NOT modify linkedin_url or any original data!)
{leads_text}

Return EXACTLY {len(raw_leads)} leads as a JSON array.
PRESERVE all original linkedin_url values exactly — do NOT change them."""

        try:
            scored = await self.call_claude_json(SYSTEM_PROMPT, user_prompt)
            if isinstance(scored, list):
                # Ensure LinkedIn URLs weren't modified by AI
                for i, lead in enumerate(scored):
                    if i < len(raw_leads):
                        original = raw_leads[i]
                        lead["linkedin_url"] = original.get("linkedin_url", lead.get("linkedin_url", ""))
                        lead["source"] = "linkedin_rapidapi"
                        if not lead.get("name") and original.get("name"):
                            lead["name"] = original["name"]
                        if not lead.get("company") and original.get("company"):
                            lead["company"] = original["company"]
                return scored
        except Exception as e:
            # If AI scoring fails, return raw leads with basic scoring
            for lead in raw_leads:
                lead["score"] = 50
                lead["reasoning"] = "AI scoring unavailable — manual review recommended"
                lead["recommended_approach"] = "linkedin"
                lead["talking_points"] = [f"Connected via LinkedIn for {target_industry} opportunities"]

        return raw_leads
