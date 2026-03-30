"""Planner Agent — creates a freelance strategy based on user profile."""

from .base import BaseAgent

SYSTEM_PROMPT = """You are an expert freelance business strategist. Given a freelancer's skills,
target industry, and income goal, you create a detailed, realistic acquisition strategy.

You MUST respond with valid JSON only — no markdown, no explanation outside the JSON.

JSON schema:
{
  "strategy_summary": "2-3 sentence overview",
  "monthly_income_target": number,
  "recommended_platforms": [
    {"platform": "upwork|linkedin|freelancer|direct_outreach", "priority": "high|medium|low", "reason": "..."}
  ],
  "target_client_profile": {
    "industries": ["..."],
    "company_sizes": ["startup|smb|enterprise"],
    "decision_maker_roles": ["CTO", "VP Engineering", ...]
  },
  "daily_action_plan": [
    {"action": "...", "time_minutes": number, "platform": "..."}
  ],
  "weekly_targets": {
    "leads_to_find": number,
    "proposals_to_send": number,
    "follow_ups": number
  },
  "pricing_suggestion": {
    "hourly_rate_range": [min, max],
    "project_rate_range": [min, max],
    "rationale": "..."
  }
}"""


class PlannerAgent(BaseAgent):
    name = "planner"

    async def create_strategy(
        self,
        skills: list[str],
        target_industry: str,
        income_goal: float,
        portfolio: str = "",
    ) -> dict:
        """Generate a comprehensive freelance strategy.

        Args:
            skills: User's skill list, e.g. ["Python", "FastAPI", "React"]
            target_industry: Industry to target, e.g. "FinTech"
            income_goal: Monthly income target in USD
            portfolio: Optional portfolio summary text

        Returns:
            Strategy dict with platforms, targets, daily plan, pricing.
        """
        user_prompt = f"""Create a freelance acquisition strategy for this profile:

## Skills
{', '.join(skills)}

## Target Industry
{target_industry}

## Monthly Income Goal
${income_goal:,.0f}

## Portfolio Summary
{portfolio or 'No portfolio provided yet — suggest building one.'}

Be realistic about timelines. Factor in the current market for these skills.
Suggest specific daily actions with time estimates."""

        return await self.call_claude_json(SYSTEM_PROMPT, user_prompt)
