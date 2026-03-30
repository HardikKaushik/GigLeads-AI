"""Job Finder Agent — finds real jobs from LinkedIn, Indeed, Naukri, Internshala via RapidAPI."""

from .base import BaseAgent
from ..mcp_server.rapidapi_clients import RapidAPIService

SYSTEM_PROMPT = """You are an expert job search specialist. Given REAL job listings fetched from job platforms
(LinkedIn, Indeed, Naukri, Internshala), you score and rank them based on the candidate's profile.

You MUST respond with valid JSON only — a list of job objects.

Each job object schema:
{
  "title": "string (keep EXACT original title)",
  "company": "string (keep original company name)",
  "platform": "string (keep original platform: linkedin, indeed, naukri, internshala, glassdoor)",
  "job_type": "string (full-time, part-time, contract, internship)",
  "salary_min": number or null,
  "salary_max": number or null,
  "location": "string (keep original)",
  "remote": boolean,
  "description": "string (keep original description)",
  "url": "string (keep EXACT original URL — do NOT modify)",
  "match_score": number (0-100),
  "skills_matched": ["skills from user that match"],
  "skills_missing": ["required skills user lacks"],
  "match_reasoning": "1-2 sentences on why this is a good/bad fit"
}

CRITICAL RULES:
- Keep ALL original data (title, company, url, platform, description, salary) EXACTLY as provided
- Do NOT invent or modify URLs
- ONLY add: match_score, skills_matched, skills_missing, match_reasoning

Scoring:
- 85-100: Perfect match — skills align, experience level fits
- 70-84: Strong match with minor gaps
- 50-69: Moderate match, stretch opportunity
- Below 50: Poor fit"""


class JobFinderAgent(BaseAgent):
    name = "job_finder"

    def __init__(self):
        super().__init__()
        self.rapidapi = RapidAPIService()

    async def find_and_rank_jobs(
        self,
        skills: list[str],
        desired_role: str = "",
        experience_level: str = "",
        location_preference: str = "",
        salary_range: str = "",
        count: int = 8,
        platforms: list[str] | None = None,
    ) -> list[dict]:
        """Find real jobs from LinkedIn, Indeed, Naukri, Internshala and rank them.

        1. Searches all platforms in parallel via RapidAPI
        2. AI scores each job against candidate's profile
        3. Returns scored jobs sorted by match_score

        Args:
            skills: User's skill list
            desired_role: Target job title/role
            experience_level: e.g. "Senior", "Mid-level", "Junior"
            location_preference: e.g. "Remote", "New York", "India"
            salary_range: e.g. "$120k-$180k"
            count: Max jobs to return
            platforms: Specific platforms to search (default: all)

        Returns:
            List of ranked job dicts with real URLs from real platforms.
        """
        # Step 1: Build CONCISE search query
        # JSearch works best with short queries like "Senior Python Developer"
        if desired_role:
            # Use the role directly — it's already a good search query
            query = desired_role
        else:
            # Use primary skill + generic title
            primary_skill = skills[0] if skills else "developer"
            query = f"{primary_skill} developer"

        # Add experience level only if it's short
        if experience_level and experience_level.lower() in ("senior", "junior", "mid", "lead", "staff"):
            query = f"{experience_level} {query}"

        # Step 2: Search all platforms in parallel with MULTIPLE queries for coverage
        raw_jobs = []
        if self.rapidapi.enabled:
            import asyncio

            target_platforms = platforms or ["linkedin", "indeed", "naukri", "internshala"]

            # Primary search
            primary_results = await self.rapidapi.search_all_jobs(
                query=query,
                location=location_preference,
                platforms=target_platforms,
                count_per_platform=max(count // len(target_platforms), 5),
            )
            raw_jobs.extend(primary_results)

            # If we need more results and have additional skills, do a secondary search
            if len(raw_jobs) < count and len(skills) > 1:
                secondary_query = f"{skills[1]} developer"
                if experience_level:
                    secondary_query = f"{experience_level} {secondary_query}"
                more = await self.rapidapi.search_all_jobs(
                    query=secondary_query,
                    location=location_preference,
                    platforms=target_platforms,
                    count_per_platform=3,
                )
                # Deduplicate by URL
                seen_urls = {j.get("url", "") for j in raw_jobs if j.get("url")}
                for j in more:
                    if j.get("url") and j["url"] not in seen_urls:
                        raw_jobs.append(j)
                        seen_urls.add(j["url"])

        if not raw_jobs:
            return []

        # Step 3: Score with AI
        jobs_text = "\n".join(
            f"- \"{j['title']}\" at {j.get('company', 'N/A')} [{j.get('platform', '?')}]"
            f" | Type: {j.get('job_type', 'N/A')} | Location: {j.get('location', 'N/A')}"
            f" | Remote: {j.get('remote', False)}"
            f" | Salary: {j.get('salary_min', '?')}-{j.get('salary_max', '?')}"
            f" | URL: {j.get('url', 'N/A')}"
            f" | Description: {(j.get('description', '') or '')[:150]}"
            for j in raw_jobs[:20]  # Limit to 20 for AI context
        )

        user_prompt = f"""Score and rank these REAL job listings for this candidate:

## Candidate Skills
{', '.join(skills)}

## Desired Role
{desired_role or 'Matching skills'}

## Experience Level
{experience_level or 'Mid to Senior'}

## Location Preference
{location_preference or 'Any'}

## Salary Range
{salary_range or 'Market rate'}

## Real Job Listings (DO NOT modify URLs, titles, or any original data!)
{jobs_text}

Return EXACTLY {min(len(raw_jobs), 20)} jobs as a JSON array, sorted by match_score descending.
PRESERVE all original URLs and data exactly."""

        try:
            scored = await self.call_claude_json(SYSTEM_PROMPT, user_prompt)
            if isinstance(scored, list):
                # Ensure URLs and platforms weren't modified
                for i, job in enumerate(scored):
                    if i < len(raw_jobs):
                        original = raw_jobs[i]
                        job["url"] = original.get("url", job.get("url", ""))
                        job["source"] = original.get("source", "rapidapi")
                        if not job.get("platform"):
                            job["platform"] = original.get("platform", "indeed")
                        # Preserve salary data
                        if job.get("salary_min") is None:
                            job["salary_min"] = original.get("salary_min")
                        if job.get("salary_max") is None:
                            job["salary_max"] = original.get("salary_max")
                # Sort by match_score
                scored.sort(key=lambda j: j.get("match_score", 0), reverse=True)
                return scored[:count]
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("Job AI scoring failed: %s", e)
            # Fallback: basic keyword scoring instead of flat 50
            user_skills_lower = {s.lower() for s in skills}
            for job in raw_jobs:
                desc = (job.get("description", "") or "").lower()
                title = (job.get("title", "") or "").lower()
                text = f"{title} {desc}"
                matched = [s for s in skills if s.lower() in text]
                job["match_score"] = min(40 + len(matched) * 15, 95)
                job["skills_matched"] = matched
                job["skills_missing"] = [s for s in skills if s.lower() not in text]
                job["match_reasoning"] = f"Keyword match: {len(matched)}/{len(skills)} skills found"

        return raw_jobs[:count]
