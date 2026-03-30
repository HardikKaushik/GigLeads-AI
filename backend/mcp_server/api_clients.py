"""API clients for lead enrichment and data discovery.

Integrates with:
- RapidAPI (PRIMARY) — LinkedIn people search, LinkedIn jobs, Indeed, Naukri, Internshala
- Apollo.io (OPTIONAL) — people/company search and lead enrichment
- Hunter.io (OPTIONAL) — email finding and verification

All clients gracefully degrade when API keys are missing.
"""

import os
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# ── Apollo.io Client ─────────────────────────────────────────────────────


class ApolloClient:
    """Apollo.io API client for people search and lead enrichment.

    Docs: https://apolloio.github.io/apollo-api-docs/
    Free tier: 10,000 credits/month, 5 mobile credits/month
    """

    BASE_URL = "https://api.apollo.io/v1"

    def __init__(self):
        self.api_key = os.getenv("APOLLO_API_KEY", "")
        self.enabled = bool(self.api_key)
        if not self.enabled:
            logger.warning("APOLLO_API_KEY not set — Apollo.io integration disabled")

    async def search_people(
        self,
        industry: str = "",
        role: str = "",
        location: str = "",
        count: int = 10,
        keywords: list[str] | None = None,
    ) -> list[dict]:
        """Search for people matching criteria using Apollo's people search API.

        Returns list of lead dicts with real names, companies, roles, emails, LinkedIn URLs.
        """
        if not self.enabled:
            return []

        # Build person titles from role
        person_titles = []
        if role:
            person_titles = [role]
        else:
            # Default to decision-maker roles
            person_titles = [
                "CTO", "VP of Engineering", "Head of Product",
                "Director of Technology", "Engineering Manager",
                "Founder", "CEO",
            ]

        payload: dict[str, Any] = {
            "api_key": self.api_key,
            "page": 1,
            "per_page": min(count, 25),
            "person_titles": person_titles,
        }

        if industry:
            payload["organization_industry_tag_ids"] = []
            # Apollo uses keyword-based industry matching
            payload["q_organization_keyword_tags"] = [industry]

        if location:
            payload["person_locations"] = [location]

        if keywords:
            payload["q_keywords"] = " ".join(keywords)

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self.BASE_URL}/mixed_people/search",
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()

            people = data.get("people", [])
            results = []
            for person in people:
                org = person.get("organization", {}) or {}
                lead = {
                    "name": f"{person.get('first_name', '')} {person.get('last_name', '')}".strip(),
                    "company": org.get("name", person.get("organization_name", "")),
                    "role": person.get("title", ""),
                    "email": person.get("email", ""),
                    "linkedin_url": person.get("linkedin_url", ""),
                    "phone": person.get("phone_number", ""),
                    "city": person.get("city", ""),
                    "state": person.get("state", ""),
                    "country": person.get("country", ""),
                    "company_website": org.get("website_url", ""),
                    "company_size": org.get("estimated_num_employees", None),
                    "company_industry": org.get("industry", ""),
                    "source": "apollo",
                    "apollo_id": person.get("id", ""),
                }
                # Only include leads with at least a name
                if lead["name"] and lead["name"] != " ":
                    results.append(lead)

            logger.info("Apollo search returned %d people", len(results))
            return results

        except httpx.HTTPStatusError as e:
            logger.error("Apollo API error: %s — %s", e.response.status_code, e.response.text[:200])
            return []
        except Exception as e:
            logger.error("Apollo search failed: %s", e)
            return []

    async def enrich_person(self, email: str = "", linkedin_url: str = "") -> dict | None:
        """Enrich a person's data by email or LinkedIn URL.

        Returns full person data or None if not found.
        """
        if not self.enabled:
            return None

        payload: dict[str, Any] = {"api_key": self.api_key}
        if email:
            payload["email"] = email
        elif linkedin_url:
            payload["linkedin_url"] = linkedin_url
        else:
            return None

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{self.BASE_URL}/people/match",
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()

            person = data.get("person")
            if not person:
                return None

            org = person.get("organization", {}) or {}
            return {
                "name": f"{person.get('first_name', '')} {person.get('last_name', '')}".strip(),
                "company": org.get("name", ""),
                "role": person.get("title", ""),
                "email": person.get("email", ""),
                "linkedin_url": person.get("linkedin_url", ""),
                "phone": person.get("phone_number", ""),
                "city": person.get("city", ""),
                "company_website": org.get("website_url", ""),
                "company_size": org.get("estimated_num_employees"),
                "company_industry": org.get("industry", ""),
                "source": "apollo",
            }
        except Exception as e:
            logger.error("Apollo enrich failed: %s", e)
            return None

    async def search_organizations(
        self,
        industry: str = "",
        keywords: list[str] | None = None,
        min_employees: int = 10,
        max_employees: int = 1000,
        count: int = 10,
    ) -> list[dict]:
        """Search for companies/organizations."""
        if not self.enabled:
            return []

        payload: dict[str, Any] = {
            "api_key": self.api_key,
            "page": 1,
            "per_page": min(count, 25),
            "organization_num_employees_ranges": [f"{min_employees},{max_employees}"],
        }

        if industry:
            payload["q_organization_keyword_tags"] = [industry]
        if keywords:
            payload["q_organization_name"] = " ".join(keywords)

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self.BASE_URL}/mixed_companies/search",
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()

            orgs = data.get("organizations", [])
            return [
                {
                    "name": org.get("name", ""),
                    "website": org.get("website_url", ""),
                    "industry": org.get("industry", ""),
                    "size": org.get("estimated_num_employees"),
                    "linkedin_url": org.get("linkedin_url", ""),
                    "city": org.get("city", ""),
                    "country": org.get("country", ""),
                }
                for org in orgs
                if org.get("name")
            ]
        except Exception as e:
            logger.error("Apollo org search failed: %s", e)
            return []


# ── Hunter.io Client ─────────────────────────────────────────────────────


class HunterClient:
    """Hunter.io API client for email finding and verification.

    Docs: https://hunter.io/api-documentation/v2
    Free tier: 25 searches/month, 50 verifications/month
    """

    BASE_URL = "https://api.hunter.io/v2"

    def __init__(self):
        self.api_key = os.getenv("HUNTER_API_KEY", "")
        self.enabled = bool(self.api_key)
        if not self.enabled:
            logger.warning("HUNTER_API_KEY not set — Hunter.io integration disabled")

    async def find_email(
        self, domain: str, first_name: str = "", last_name: str = ""
    ) -> dict | None:
        """Find an email address for a person at a specific company domain.

        Returns dict with email, score, sources, or None.
        """
        if not self.enabled:
            return None

        params: dict[str, Any] = {
            "api_key": self.api_key,
            "domain": domain,
        }
        if first_name:
            params["first_name"] = first_name
        if last_name:
            params["last_name"] = last_name

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"{self.BASE_URL}/email-finder",
                    params=params,
                )
                resp.raise_for_status()
                data = resp.json().get("data", {})

            if data.get("email"):
                return {
                    "email": data["email"],
                    "score": data.get("score", 0),
                    "position": data.get("position", ""),
                    "linkedin": data.get("linkedin", ""),
                    "sources": data.get("sources", []),
                    "verified": data.get("verification", {}).get("status") == "valid",
                }
            return None
        except Exception as e:
            logger.error("Hunter email-finder failed: %s", e)
            return None

    async def verify_email(self, email: str) -> dict | None:
        """Verify if an email address is deliverable.

        Returns dict with result, score, or None.
        """
        if not self.enabled:
            return None

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"{self.BASE_URL}/email-verifier",
                    params={"api_key": self.api_key, "email": email},
                )
                resp.raise_for_status()
                data = resp.json().get("data", {})

            return {
                "email": data.get("email", email),
                "result": data.get("result", "unknown"),
                "score": data.get("score", 0),
                "status": data.get("status", "unknown"),
                "disposable": data.get("disposable", False),
                "webmail": data.get("webmail", False),
            }
        except Exception as e:
            logger.error("Hunter verify failed: %s", e)
            return None

    async def domain_search(self, domain: str, limit: int = 10) -> list[dict]:
        """Search for all email addresses at a domain.

        Returns list of email info dicts.
        """
        if not self.enabled:
            return []

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"{self.BASE_URL}/domain-search",
                    params={
                        "api_key": self.api_key,
                        "domain": domain,
                        "limit": min(limit, 100),
                    },
                )
                resp.raise_for_status()
                data = resp.json().get("data", {})

            emails = data.get("emails", [])
            return [
                {
                    "email": e.get("value", ""),
                    "type": e.get("type", ""),
                    "first_name": e.get("first_name", ""),
                    "last_name": e.get("last_name", ""),
                    "position": e.get("position", ""),
                    "linkedin": e.get("linkedin", ""),
                    "confidence": e.get("confidence", 0),
                }
                for e in emails
                if e.get("value")
            ]
        except Exception as e:
            logger.error("Hunter domain-search failed: %s", e)
            return []


# ── Combined Lead Finder ─────────────────────────────────────────────────


class LeadDataService:
    """High-level service that combines RapidAPI + Apollo + Hunter for lead discovery.

    Priority: RapidAPI (LinkedIn) → Apollo → Hunter enrichment

    Usage:
        service = LeadDataService()
        leads = await service.find_leads(industry="SaaS", role="CTO", count=10)
    """

    def __init__(self):
        self.apollo = ApolloClient()
        self.hunter = HunterClient()
        # Lazy import to avoid circular imports
        self._rapidapi = None

    @property
    def rapidapi(self):
        if self._rapidapi is None:
            from .rapidapi_clients import RapidAPIService
            self._rapidapi = RapidAPIService()
        return self._rapidapi

    @property
    def has_real_apis(self) -> bool:
        """Returns True if at least one real API is configured."""
        return self.rapidapi.enabled or self.apollo.enabled or self.hunter.enabled

    async def find_leads(
        self,
        industry: str = "",
        role: str = "",
        count: int = 10,
        keywords: list[str] | None = None,
    ) -> list[dict]:
        """Find leads using available APIs.

        Priority: RapidAPI LinkedIn → Apollo → Hunter enrichment.
        """
        leads = []

        # Try RapidAPI LinkedIn first (primary source)
        if self.rapidapi.enabled:
            leads = await self.rapidapi.search_leads(
                keywords=" ".join(keywords) if keywords else "",
                industry=industry,
                role=role,
                count=count,
            )

        # Fallback to Apollo if RapidAPI returned nothing
        if not leads and self.apollo.enabled:
            leads = await self.apollo.search_people(
                industry=industry,
                role=role,
                count=count,
                keywords=keywords,
            )

        # Try to fill missing emails via Hunter
        if self.hunter.enabled:
            for lead in leads:
                if not lead.get("email") and lead.get("company_website"):
                    domain = lead["company_website"].replace("https://", "").replace("http://", "").split("/")[0]
                    name_parts = lead.get("name", "").split()
                    if len(name_parts) >= 2:
                        result = await self.hunter.find_email(
                            domain=domain,
                            first_name=name_parts[0],
                            last_name=name_parts[-1],
                        )
                        if result and result.get("email"):
                            lead["email"] = result["email"]
                            lead["email_verified"] = result.get("verified", False)
                            if result.get("linkedin") and not lead.get("linkedin_url"):
                                lead["linkedin_url"] = result["linkedin"]

        return leads

    async def enrich_lead(self, email: str = "", linkedin_url: str = "") -> dict | None:
        """Enrich a single lead by email or LinkedIn URL."""
        return await self.apollo.enrich_person(email=email, linkedin_url=linkedin_url)

    async def verify_email(self, email: str) -> dict | None:
        """Verify an email address."""
        return await self.hunter.verify_email(email)
