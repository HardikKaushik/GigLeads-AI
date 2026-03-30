"""Cover Letter Agent — writes personalized cover letters for job applications."""

from .base import BaseAgent

SYSTEM_PROMPT = """You are an expert cover letter writer. You write compelling,
personalized cover letters that get interviews. Your letters are NEVER generic.

Rules:
- Address the hiring manager or company BY NAME
- Reference the SPECIFIC job title and company
- Reference SPECIFIC requirements from the job description
- Highlight relevant experience with concrete examples
- Show enthusiasm for the company/role specifically
- Include a brief "Why this company?" section
- 250-400 words
- Professional but genuine tone — not overly formal
- NEVER use placeholder brackets like [X] — write real content
- NEVER use generic phrases like "I am writing to express my interest"

Structure:
1. Strong opening — why you're excited about THIS role at THIS company
2. 2-3 paragraphs showing relevant experience matching job requirements
3. Why this company specifically (culture, mission, product)
4. Confident closing with call to action"""


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

Write the cover letter now. Make it specific, genuine, and compelling.
Show you've researched the company and understand the role."""

        return await self.call_claude(SYSTEM_PROMPT, user_prompt, max_tokens=1500)
