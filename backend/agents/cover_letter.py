"""Cover Letter Agent — writes personalized cover letters for job applications."""

from .base import BaseAgent

SYSTEM_PROMPT = """You are an expert cover letter writer. Write a SHORT, punchy cover letter.

CRITICAL RULES:
- EXACTLY 50-70 words. No more. Count carefully.
- Address the company BY NAME
- Reference the SPECIFIC job title
- Mention 1-2 matching skills from the job
- One sentence on relevant experience
- Confident closing
- Professional but warm tone
- NEVER use placeholder brackets like [X]
- NEVER use generic phrases like "I am writing to express my interest"
- NO fluff, NO filler — every word must earn its place

Format: 3-4 short sentences. That's it."""


class CoverLetterAgent(BaseAgent):
    name = "cover_letter"

    async def write_cover_letter(
        self,
        job_description: str,
        company: str,
        job_title: str,
        portfolio: str,
        user_skills: list[str] | None = None,
        desired_role: str = "",
    ) -> str:
        """Write a personalized cover letter for a job application.

        Args:
            job_description: Full job description text
            company: Company name
            job_title: Job title
            portfolio: User's portfolio/experience summary
            user_skills: List of user skills
            desired_role: User's desired role/title

        Returns:
            The full cover letter text.
        """
        user_prompt = f"""Write a winning cover letter for this job:

## Job Title
{job_title}

## Company
{company}

## Job Description
{job_description}

## My Experience & Portfolio
{portfolio or 'Experienced professional with strong technical background.'}

## My Skills
{', '.join(user_skills) if user_skills else 'Relevant technical and soft skills'}

## My Target Role
{desired_role or job_title}

Write a SHORT cover letter (50-70 words ONLY). 3-4 punchy sentences. No fluff."""

        return await self.call_claude(SYSTEM_PROMPT, user_prompt, max_tokens=200)
