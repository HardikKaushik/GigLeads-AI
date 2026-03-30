"""Proposal Agent — writes hyper-personalized freelance proposals using Claude."""

from .base import BaseAgent

SYSTEM_PROMPT = """You are an elite freelance proposal writer. You write compelling,
personalized proposals that win contracts. Your proposals are NEVER generic.

Rules:
- Address the client BY NAME
- Reference the COMPANY by name
- Reference SPECIFIC requirements from the job description
- Highlight relevant portfolio experience with concrete examples
- Include a clear timeline and approach (3-5 steps)
- Add a brief "Why me?" section
- Close with a clear call to action
- 300-500 words
- Professional but warm tone — not salesy or desperate
- NEVER use placeholder brackets like [X] — write real content
- NEVER use generic phrases like "I am writing to express my interest"

Structure your proposal as:
1. Personalized opening (reference client/company/role)
2. Understanding of their needs (quote specific requirements)
3. Proposed approach (3-5 concrete steps)
4. Relevant experience (specific past projects)
5. Timeline & availability
6. Call to action"""


class ProposalAgent(BaseAgent):
    name = "proposal"

    async def write_proposal(
        self,
        job_description: str,
        portfolio: str,
        client_info: dict,
        user_skills: list[str] | None = None,
    ) -> str:
        """Write a personalized proposal for a gig or lead.

        Args:
            job_description: Full job/gig description text
            portfolio: Freelancer's portfolio summary
            client_info: Dict with keys: name, company, role (all optional)
            user_skills: Optional list of user skills for context

        Returns:
            The full proposal text.
        """
        client_name = client_info.get("name", "")
        company = client_info.get("company", "")
        role = client_info.get("role", "")

        user_prompt = f"""Write a winning proposal for this opportunity:

## Job Description
{job_description}

## Client
- Name: {client_name or 'Not specified'}
- Company: {company or 'Not specified'}
- Role: {role or 'Not specified'}

## My Portfolio & Experience
{portfolio or 'Experienced full-stack developer with 5+ years of experience.'}

## My Skills
{', '.join(user_skills) if user_skills else 'Full-stack development'}

Write the proposal now. Make it specific and compelling."""

        return await self.call_claude(SYSTEM_PROMPT, user_prompt, max_tokens=1500)

    async def write_lead_proposal(
        self,
        lead_info: dict,
        portfolio: str,
        talking_points: list[str] | None = None,
        user_skills: list[str] | None = None,
    ) -> str:
        """Write an outreach proposal for a lead (not a posted gig).

        Args:
            lead_info: Dict with name, company, role, and optionally industry
            portfolio: Freelancer's portfolio summary
            talking_points: Specific points to mention
            user_skills: User's skills

        Returns:
            The outreach message text.
        """
        points = "\n".join(f"- {p}" for p in (talking_points or []))

        user_prompt = f"""Write a cold outreach message for a potential client:

## Lead
- Name: {lead_info.get('name', '')}
- Company: {lead_info.get('company', '')}
- Role: {lead_info.get('role', '')}

## My Portfolio
{portfolio or 'Experienced developer with 5+ years of experience.'}

## My Skills
{', '.join(user_skills) if user_skills else 'Full-stack development'}

## Talking Points to Include
{points or 'Focus on how my skills can add value to their company.'}

Write a concise, personalized outreach message (150-250 words).
It should feel like a real person wrote it — not AI-generated.
Include a specific value proposition for their company."""

        return await self.call_claude(SYSTEM_PROMPT, user_prompt, max_tokens=800)
