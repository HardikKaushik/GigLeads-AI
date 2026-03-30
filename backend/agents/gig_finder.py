"""Gig Finder Agent — finds real freelance gigs from LinkedIn + JSearch via RapidAPI."""

from .base import BaseAgent
from ..mcp_server.rapidapi_clients import RapidAPIService

SYSTEM_PROMPT = """You are an expert freelance job matcher. Given REAL job postings fetched from job platforms,
you score and rank them based on the freelancer's profile.

You MUST respond with valid JSON only — a list of gig objects.

Each gig object schema:
{
  "title": "string (keep EXACT original title)",
  "platform": "string (keep original platform)",
  "budget": number or null,
  "description": "string (keep original description)",
  "url": "string (keep EXACT original URL — do NOT modify)",
  "company": "string (keep original company)",
  "match_score": number (0-100),
  "skills_matched": ["skills from user that match"],
  "skills_missing": ["required skills user lacks"],
  "match_reasoning": "1-2 sentences on why this is a good/bad fit",
  "proposal_angle": "specific angle to use when proposing — 1 sentence",
  "estimated_hours": number or null,
  "deadline_days": number or null
}

CRITICAL RULES:
- Keep ALL original data (title, url, platform, company, description) EXACTLY as provided
- Do NOT invent or modify URLs
- ONLY add: match_score, skills_matched, skills_missing, match_reasoning, proposal_angle

Scoring:
- 85-100: Perfect skill match, high win probability
- 70-84: Strong match with minor skill gaps
- 50-69: Moderate match, would need to stretch
- Below 50: Poor fit"""


class GigFinderAgent(BaseAgent):
    name = "gig_finder"

    def __init__(self):
        super().__init__()
        self.rapidapi = RapidAPIService()

    async def find_and_rank_gigs(
        self,
        skills: list[str],
        target_industry: str = "",
        platforms: list[str] | None = None,
        count: int = 8,
    ) -> list[dict]:
        """Find real freelance gigs from LinkedIn + JSearch and rank by skill match.

        1. Fetches real contract/freelance jobs via RapidAPI
        2. AI scores each gig against freelancer's skills
        3. Returns scored gigs sorted by match_score

        Args:
            skills: User's skill list
            target_industry: Optional industry preference
            platforms: Platform filter (not used for real API — searches all)
            count: Max gigs to return

        Returns:
            List of ranked gig dicts with real URLs.
        """
        # Step 1: Fetch real gigs — SHORT focused queries
        # JSearch works best with concise queries, not skill dumps
        raw_gigs = []
        if self.rapidapi.enabled:
            import asyncio

            primary_skill = skills[0] if skills else "developer"
            industry_clean = target_industry.split(",")[0].strip() if target_industry else ""

            # Run 2 focused queries in parallel for better coverage
            queries = [f"{primary_skill} freelance"]
            if len(skills) > 1:
                queries.append(f"{skills[1]} contract remote")
            if industry_clean:
                queries[0] += f" {industry_clean}"

            tasks = [self.rapidapi.search_gigs(query=q, count=count) for q in queries]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            seen_urls: set[str] = set()
            for result in results:
                if isinstance(result, list):
                    for gig in result:
                        url = gig.get("url", "")
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            raw_gigs.append(gig)
                        elif not url:
                            raw_gigs.append(gig)

        if not raw_gigs:
            return []

        # Step 2: Score with AI
        gigs_text = "\n".join(
            f"- \"{g['title']}\" at {g.get('company', 'N/A')} ({g.get('platform', 'N/A')})"
            f" | URL: {g.get('url', 'N/A')}"
            f" | Location: {g.get('location', 'N/A')}"
            f" | Description: {(g.get('description', '') or '')[:200]}"
            for g in raw_gigs
        )

        user_prompt = f"""Score and rank these REAL freelance gigs for this freelancer:

## Freelancer Skills
{', '.join(skills)}

## Target Industry
{target_industry or 'No preference — best matches across industries'}

## Real Gigs (DO NOT modify URLs, titles, or any original data!)
{gigs_text}

Return EXACTLY {len(raw_gigs)} gigs as a JSON array, sorted by match_score descending.
PRESERVE all original URLs exactly."""

        try:
            scored = await self.call_claude_json(SYSTEM_PROMPT, user_prompt)
            if isinstance(scored, list):
                # Ensure URLs weren't modified
                for i, gig in enumerate(scored):
                    if i < len(raw_gigs):
                        original = raw_gigs[i]
                        gig["url"] = original.get("url", gig.get("url", ""))
                        gig["source"] = original.get("source", "rapidapi")
                        if not gig.get("platform"):
                            gig["platform"] = original.get("platform", "linkedin")
                # Sort by match_score
                scored.sort(key=lambda g: g.get("match_score", 0), reverse=True)
                return scored
        except Exception:
            # Fallback: return raw gigs with basic scoring
            for gig in raw_gigs:
                gig["match_score"] = 50
                gig["match_reasoning"] = "AI scoring unavailable — manual review recommended"
                gig["skills_matched"] = []
                gig["skills_missing"] = []
                gig["proposal_angle"] = ""

        return raw_gigs
