"""Reviewer Agent — quality-gates proposals before sending."""

from .base import BaseAgent

SYSTEM_PROMPT = """You are a senior proposal reviewer and quality assurance specialist for
freelance proposals. You evaluate proposals for effectiveness and provide actionable feedback.

You MUST respond with valid JSON only.

JSON schema:
{
  "score": number (0-100),
  "verdict": "approve" | "needs_revision" | "reject",
  "issues": [
    {"severity": "critical|major|minor", "issue": "description", "suggestion": "how to fix"}
  ],
  "strengths": ["what the proposal does well"],
  "improved_version": "the full improved proposal text (always provide this)"
}

Scoring rubric:
- Personalization (0-25): Does it reference client name, company, specific needs?
- Relevance (0-25): Does it address the actual job requirements?
- Credibility (0-20): Does it showcase relevant experience convincingly?
- Clarity (0-15): Is the approach/timeline clear and realistic?
- Tone (0-15): Professional, warm, not generic or desperate?

Score thresholds:
- 80-100: Approve — ready to send
- 70-79: Approve with minor edits — provide improved version
- 50-69: Needs revision — significant issues found
- Below 50: Reject — rewrite needed

CRITICAL: Proposals scoring below 70 MUST be rejected or marked needs_revision.
Always provide an improved_version regardless of score."""


class ReviewerAgent(BaseAgent):
    name = "reviewer"

    async def review_proposal(
        self,
        proposal_text: str,
        job_description: str = "",
        client_info: dict | None = None,
    ) -> dict:
        """Review a proposal for quality, spam signals, and effectiveness.

        Args:
            proposal_text: The proposal text to review
            job_description: Original job description for context
            client_info: Client details to check personalization

        Returns:
            Review dict with score, verdict, issues, strengths, improved_version.
        """
        client_context = ""
        if client_info:
            client_context = (
                f"\n## Client Info (check personalization against this)\n"
                f"- Name: {client_info.get('name', 'N/A')}\n"
                f"- Company: {client_info.get('company', 'N/A')}\n"
                f"- Role: {client_info.get('role', 'N/A')}"
            )

        user_prompt = f"""Review this freelance proposal:

## Proposal
{proposal_text}

## Original Job Description
{job_description or 'Not provided — evaluate proposal on its own merits.'}
{client_context}

Evaluate thoroughly. Be strict — only approve truly strong proposals.
If the score is below 70, provide a significantly improved version."""

        result = await self.call_claude_json(
            SYSTEM_PROMPT, user_prompt, max_tokens=3000
        )

        # Enforce the 70-point quality gate
        score = result.get("score", 0)
        if score < 70 and result.get("verdict") == "approve":
            result["verdict"] = "needs_revision"

        return result
