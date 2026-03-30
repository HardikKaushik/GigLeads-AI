"""RapidAPI clients for real data fetching.

Integrates with:
- JSearch (RAPIDAPI_KEY) — Indeed, Glassdoor, LinkedIn, Naukri, multi-platform job search
- LinkedIn Job Search API (RAPIDAPI_KEY_2) — real LinkedIn job listings with filtering
- Internships API (RAPIDAPI_KEY_2) — real internship listings from LinkedIn job boards
- LinkedIn Data API (RAPIDAPI_KEY_2) — company enrichment by domain (deprecated)

Two separate RapidAPI keys are supported:
  RAPIDAPI_KEY   → JSearch
  RAPIDAPI_KEY_2 → LinkedIn Job Search API + Internships API
"""

import os
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


def _get_key() -> str:
    """Primary RapidAPI key (JSearch)."""
    return os.getenv("RAPIDAPI_KEY", "")


def _get_key2() -> str:
    """Secondary RapidAPI key (Internships API, LinkedIn Data API)."""
    return os.getenv("RAPIDAPI_KEY_2", "")


def _headers(host: str, key: str | None = None) -> dict[str, str]:
    return {
        "x-rapidapi-key": key or _get_key(),
        "x-rapidapi-host": host,
        "Content-Type": "application/json",
    }


# ═══════════════════════════════════════════════════════════════════════
# JSearch — Indeed, Glassdoor, LinkedIn, Naukri, and more
# ═══════════════════════════════════════════════════════════════════════


class JSearchClient:
    """Multi-platform job search using JSearch API.

    Covers: Indeed, Glassdoor, ZipRecruiter, LinkedIn, and more.
    Uses RAPIDAPI_KEY.
    """

    HOST = "jsearch.p.rapidapi.com"

    @property
    def enabled(self) -> bool:
        return bool(_get_key())

    async def search(
        self,
        query: str,
        country: str = "us",
        page: int = 1,
        num_pages: int = 1,
        date_posted: str = "all",
        remote_only: bool = False,
        employment_type: str = "",
    ) -> list[dict]:
        """Search jobs across Indeed, Glassdoor, and other platforms."""
        if not self.enabled:
            return []

        params: dict[str, Any] = {
            "query": query,
            "page": str(page),
            "num_pages": str(num_pages),
            "country": country,
            "date_posted": date_posted,
        }
        if remote_only:
            params["remote_jobs_only"] = "true"
        if employment_type:
            params["employment_types"] = employment_type

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    f"https://{self.HOST}/search",
                    headers=_headers(self.HOST, _get_key()),
                    params=params,
                )
                resp.raise_for_status()
                body = resp.json()

            jobs_data = body.get("data", [])
            if not isinstance(jobs_data, list):
                return []

            results = []
            for job in jobs_data:
                employer_url = (job.get("employer_website") or "").lower()
                job_apply_link = (job.get("job_apply_link") or "").lower()

                platform = "indeed"
                if "naukri" in employer_url or "naukri" in job_apply_link:
                    platform = "naukri"
                elif "shine.com" in job_apply_link or "foundit.in" in job_apply_link:
                    platform = "naukri"
                elif "internshala" in employer_url or "internshala" in job_apply_link:
                    platform = "internshala"
                elif "linkedin" in job_apply_link:
                    platform = "linkedin"
                elif "glassdoor" in job_apply_link:
                    platform = "glassdoor"
                elif "ziprecruiter" in job_apply_link:
                    platform = "ziprecruiter"

                job_type_raw = job.get("job_employment_type", "")
                job_type_map = {
                    "FULLTIME": "full-time",
                    "PARTTIME": "part-time",
                    "CONTRACTOR": "contract",
                    "INTERN": "internship",
                    "TEMPORARY": "contract",
                }
                job_type = job_type_map.get(job_type_raw, job_type_raw.lower() if job_type_raw else "full-time")

                normalized = {
                    "title": job.get("job_title", ""),
                    "company": job.get("employer_name", ""),
                    "platform": platform,
                    "job_type": job_type,
                    "location": f"{job.get('job_city', '')}, {job.get('job_state', '')}".strip(", "),
                    "remote": job.get("job_is_remote", False),
                    "description": (job.get("job_description", "") or "")[:500],
                    "url": job.get("job_apply_link", ""),
                    "posted_at": job.get("job_posted_at_datetime_utc", ""),
                    "salary_min": job.get("job_min_salary"),
                    "salary_max": job.get("job_max_salary"),
                    "salary_currency": job.get("job_salary_currency", "USD"),
                    "salary_period": job.get("job_salary_period", ""),
                    "employer_logo": job.get("employer_logo", ""),
                    "employer_website": job.get("employer_website", ""),
                    "job_highlights": {
                        "qualifications": (job.get("job_highlights", {}) or {}).get("Qualifications", []),
                        "responsibilities": (job.get("job_highlights", {}) or {}).get("Responsibilities", []),
                        "benefits": (job.get("job_highlights", {}) or {}).get("Benefits", []),
                    },
                    "source": f"jsearch_{platform}",
                }

                if normalized["title"]:
                    results.append(normalized)

            logger.info("JSearch returned %d results for query '%s'", len(results), query[:50])
            return results

        except httpx.HTTPStatusError as e:
            logger.error("JSearch API error: %s — %s", e.response.status_code, e.response.text[:300])
            return []
        except Exception as e:
            logger.error("JSearch search failed: %s", e)
            return []

    async def search_indeed(self, query: str, location: str = "", count: int = 10) -> list[dict]:
        full_query = f"{query} in {location}" if location else query
        return await self.search(query=full_query, country="us", num_pages=1)

    async def search_naukri(self, query: str, location: str = "", count: int = 10) -> list[dict]:
        full_query = f"{query} in {location}" if location else f"{query} in India"
        results = await self.search(query=full_query, country="in", num_pages=1)
        for r in results:
            if r["platform"] == "indeed":
                r["platform"] = "naukri"
                r["source"] = "jsearch_naukri"
        return results


# ═══════════════════════════════════════════════════════════════════════
# LinkedIn Job Search API — real LinkedIn jobs with server-side filtering
# Uses RAPIDAPI_KEY_2
# ═══════════════════════════════════════════════════════════════════════


class LinkedInJobSearchClient:
    """Search real LinkedIn jobs using LinkedIn Job Search API.

    Endpoints:
      GET /active-jb-7d  — jobs posted in last 7 days
      GET /active-jb-24h — jobs posted in last 24 hours

    Supports server-side filtering by title and location.
    Returns 100% LinkedIn-sourced jobs with real LinkedIn URLs.
    Uses RAPIDAPI_KEY_2.
    """

    HOST = "linkedin-job-search-api.p.rapidapi.com"

    @property
    def enabled(self) -> bool:
        return bool(_get_key2())

    async def search(
        self,
        title_filter: str = "",
        location_filter: str = "",
        limit: int = 50,
        offset: int = 0,
        timeframe: str = "7d",
    ) -> list[dict]:
        """Search LinkedIn jobs with optional title and location filters.

        Args:
            title_filter: Filter by job title (e.g., "python developer")
            location_filter: Filter by location (e.g., "United States", "India")
            limit: Max results (up to 100)
            offset: Pagination offset
            timeframe: "7d" for last 7 days, "24h" for last 24 hours

        Returns normalized job dicts with real LinkedIn URLs.
        """
        if not self.enabled:
            logger.info("RAPIDAPI_KEY_2 not set — LinkedIn Job Search API disabled")
            return []

        endpoint = "active-jb-24h" if timeframe == "24h" else "active-jb-7d"

        params: dict[str, Any] = {
            "limit": str(min(limit, 100)),
            "offset": str(offset),
            "description_type": "text",
        }
        if title_filter:
            params["title_filter"] = f'"{title_filter}"'
        if location_filter:
            params["location_filter"] = f'"{location_filter}"'

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    f"https://{self.HOST}/{endpoint}",
                    headers=_headers(self.HOST, _get_key2()),
                    params=params,
                )
                resp.raise_for_status()
                data = resp.json()

            if not isinstance(data, list):
                if isinstance(data, dict) and "message" in data:
                    logger.warning("LinkedIn Job Search API: %s", data["message"])
                return []

            results = []
            for item in data:
                title = item.get("title", "")
                locations = item.get("locations_derived", [])
                location_str = locations[0] if locations else ""

                # Parse employment type
                emp_types = item.get("employment_type") or []
                job_type = "full-time"
                if emp_types:
                    type_map = {
                        "FULL_TIME": "full-time",
                        "PART_TIME": "part-time",
                        "CONTRACTOR": "contract",
                        "INTERN": "internship",
                        "TEMPORARY": "contract",
                        "VOLUNTEER": "volunteer",
                    }
                    job_type = type_map.get(emp_types[0], emp_types[0].lower() if isinstance(emp_types[0], str) else "full-time")

                # Parse salary
                salary_raw = item.get("salary_raw")
                salary_min = None
                salary_max = None
                if isinstance(salary_raw, dict):
                    value = salary_raw.get("value", {})
                    if isinstance(value, dict):
                        salary_min = value.get("minValue")
                        salary_max = value.get("maxValue")

                # Check remote
                remote = item.get("remote_derived", False)
                if not remote and location_str:
                    remote = "remote" in location_str.lower()

                normalized = {
                    "title": title,
                    "company": item.get("organization", ""),
                    "platform": "linkedin",
                    "job_type": job_type,
                    "location": location_str,
                    "remote": remote,
                    "description": (item.get("description", "") or "")[:500],
                    "url": item.get("url", ""),
                    "posted_at": item.get("date_posted", ""),
                    "salary_min": salary_min,
                    "salary_max": salary_max,
                    "employer_logo": item.get("organization_logo", ""),
                    "employer_website": item.get("organization_url", ""),
                    "source": "linkedin_job_search_api",
                }

                if normalized["title"]:
                    results.append(normalized)

            logger.info(
                "LinkedIn Job Search API returned %d results (title='%s', location='%s')",
                len(results), title_filter[:30], location_filter[:30],
            )
            return results

        except httpx.HTTPStatusError as e:
            logger.error("LinkedIn Job Search API error: %s — %s", e.response.status_code, e.response.text[:300])
            return []
        except Exception as e:
            logger.error("LinkedIn Job Search failed: %s", e)
            return []


# ═══════════════════════════════════════════════════════════════════════
# Internships API — real LinkedIn internship listings
# Uses RAPIDAPI_KEY_2
# ═══════════════════════════════════════════════════════════════════════


class InternshipsClient:
    """Fetch real internship listings from LinkedIn job boards.

    Endpoint: GET /active-jb-7d (active internships from last 7 days)
    Uses RAPIDAPI_KEY_2.
    """

    HOST = "internships-api.p.rapidapi.com"

    @property
    def enabled(self) -> bool:
        return bool(_get_key2())

    async def search(
        self,
        keywords: str = "",
        location: str = "",
        count: int = 10,
    ) -> list[dict]:
        """Fetch active internships from the last 7 days.

        Returns normalized job dicts with real LinkedIn URLs.
        The API returns ALL recent internships — we filter client-side by keywords.
        """
        if not self.enabled:
            logger.info("RAPIDAPI_KEY_2 not set — Internships API disabled")
            return []

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    f"https://{self.HOST}/active-jb-7d",
                    headers=_headers(self.HOST, _get_key2()),
                )
                resp.raise_for_status()
                data = resp.json()

            if not isinstance(data, list):
                logger.warning("Internships API returned non-list: %s", type(data))
                return []

            # STRICT client-side filtering — only return tech/relevant internships
            # The API returns ALL internships (babysitters, nurses, etc.)
            # We MUST filter aggressively to only show relevant results
            keywords_lower = keywords.lower().split() if keywords else []
            location_lower = location.lower() if location else ""

            # Tech-related terms to identify relevant internships
            TECH_TERMS = {
                "software", "developer", "engineer", "data", "python", "java",
                "react", "web", "frontend", "backend", "fullstack", "full-stack",
                "devops", "cloud", "ai", "ml", "machine learning", "deep learning",
                "analytics", "database", "api", "mobile", "ios", "android",
                "javascript", "typescript", "node", "design", "ux", "ui",
                "product", "qa", "testing", "cyber", "security", "network",
                "system", "linux", "aws", "azure", "gcp", "docker", "kubernetes",
                "blockchain", "fintech", "saas", "startup", "tech", "it",
                "computer", "science", "information", "digital", "automation",
            }

            filtered = []
            for item in data:
                title = item.get("title", "")
                org = item.get("organization", "")
                locations = item.get("locations_derived", [])
                location_str = locations[0] if locations else ""
                searchable = f"{title} {org}".lower()

                # Must match at least one keyword if provided
                if keywords_lower:
                    matches_keyword = any(kw in searchable for kw in keywords_lower)
                else:
                    # No keywords — filter to tech-only internships
                    matches_keyword = any(term in searchable for term in TECH_TERMS)

                if not matches_keyword:
                    continue

                # Location filter
                if location_lower and location_str:
                    if location_lower not in location_str.lower():
                        continue

                filtered.append(item)

            # If no matches after strict filtering, return empty — don't show irrelevant results
            source_list = filtered

            results = []
            for item in source_list:
                title = item.get("title", "")
                org = item.get("organization", "")
                locations = item.get("locations_derived", [])
                location_str = locations[0] if locations else ""

                # Parse salary from salary_raw
                salary_raw = item.get("salary_raw")
                salary_min = None
                salary_max = None
                if isinstance(salary_raw, dict):
                    value = salary_raw.get("value", {})
                    if isinstance(value, dict):
                        salary_min = value.get("minValue")
                        salary_max = value.get("maxValue")

                # Determine platform from the actual URL
                item_url = item.get("url", "")
                item_source = item.get("source", "")
                if "linkedin.com" in item_url or item_source == "linkedin":
                    item_platform = "linkedin"
                elif "internshala" in item_url:
                    item_platform = "internshala"
                elif "indeed" in item_url:
                    item_platform = "indeed"
                else:
                    item_platform = "linkedin"  # Default — API sources from LinkedIn

                normalized = {
                    "title": title,
                    "company": org,
                    "platform": item_platform,
                    "job_type": "internship",
                    "location": location_str,
                    "remote": item.get("remote_derived", False),
                    "description": "",  # API doesn't provide descriptions in list view
                    "url": item.get("url", ""),
                    "posted_at": item.get("date_posted", ""),
                    "salary_min": salary_min,
                    "salary_max": salary_max,
                    "employer_logo": item.get("organization_logo", ""),
                    "employer_website": item.get("organization_url", ""),
                    "source": "internships_api",
                }

                if normalized["title"]:
                    results.append(normalized)

                if len(results) >= count:
                    break

            logger.info("Internships API returned %d results (filtered from %d)", len(results), len(data))
            return results

        except httpx.HTTPStatusError as e:
            logger.error("Internships API error: %s — %s", e.response.status_code, e.response.text[:300])
            return []
        except Exception as e:
            logger.error("Internships search failed: %s", e)
            return []


# ═══════════════════════════════════════════════════════════════════════
# Crunchbase — company/startup discovery and enrichment
# Uses RAPIDAPI_KEY (crunchbase4.p.rapidapi.com)
# ═══════════════════════════════════════════════════════════════════════


class CrunchbaseClient:
    """Lookup company data from Crunchbase — funding, industry, size.

    Endpoint: POST /company (lookup by domain)

    Use case for B2B leads:
      1. Find companies from job listings (JSearch/LinkedIn)
      2. Enrich with Crunchbase → get funding amount, industry, size
      3. Companies with recent funding = high-budget potential clients
    """

    HOST = "crunchbase4.p.rapidapi.com"

    @property
    def enabled(self) -> bool:
        return bool(_get_key())

    async def get_company(self, domain: str) -> dict | None:
        """Lookup company by domain.

        Args:
            domain: Company website domain (e.g., "stripe.com")

        Returns:
            Enriched company dict with funding, industries, location, etc.
        """
        if not self.enabled:
            return None

        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.post(
                    f"https://{self.HOST}/company",
                    headers=_headers(self.HOST, _get_key()),
                    json={"company_domain": domain},
                )
                resp.raise_for_status()
                body = resp.json()

            if body.get("err"):
                logger.debug("Crunchbase: no data for %s — %s", domain, body["err"])
                return None

            company = body.get("company", {})
            if not company:
                return None

            # Parse funding
            funding = company.get("funding", {})
            funding_amount = None
            if isinstance(funding, dict):
                funding_amount = funding.get("value_usd") or funding.get("value")

            # Parse founders/people
            founders = company.get("founders", [])
            people = []
            if isinstance(founders, list):
                for f in founders[:5]:
                    if isinstance(f, dict):
                        people.append({
                            "name": f.get("name", ""),
                            "title": f.get("title", ""),
                            "linkedin": f.get("linkedin", ""),
                        })

            return {
                "name": company.get("name", ""),
                "domain": domain,
                "about": (company.get("about", "") or "")[:300],
                "long_description": (company.get("long_description", "") or "")[:500],
                "founded_year": company.get("founded_year", ""),
                "funding_usd": funding_amount,
                "industries": company.get("industries", []),
                "location": company.get("location", ""),
                "num_employees": company.get("num_employees", ""),
                "website": company.get("website", f"https://{domain}"),
                "linkedin_url": company.get("linkedin", ""),
                "twitter_url": company.get("twitter", ""),
                "logo": company.get("logo", ""),
                "founders": people,
                "status": company.get("status", ""),
                "source": "crunchbase",
            }
        except httpx.HTTPStatusError as e:
            logger.warning("Crunchbase API error for %s: %s", domain, e.response.status_code)
            return None
        except Exception as e:
            logger.warning("Crunchbase lookup failed for %s: %s", domain, e)
            return None

    async def enrich_leads(self, leads: list[dict]) -> list[dict]:
        """Enrich a list of leads with Crunchbase data.

        For each lead that has a company_website, lookup Crunchbase
        and add funding, industry, founders data.
        """
        if not self.enabled:
            return leads

        import asyncio

        tasks = []
        for lead in leads:
            website = lead.get("company_website") or ""
            if website:
                domain = website.replace("https://", "").replace("http://", "").split("/")[0]
                if domain and "linkedin.com" not in domain:
                    tasks.append((lead, self.get_company(domain)))

        if not tasks:
            return leads

        results = await asyncio.gather(
            *[t[1] for t in tasks],
            return_exceptions=True,
        )

        enriched_count = 0
        for (lead, _), result in zip(tasks, results):
            if isinstance(result, dict) and result:
                enriched_count += 1
                lead["funding_usd"] = result.get("funding_usd")
                lead["industries"] = result.get("industries", [])
                lead["company_description"] = result.get("about", "")
                lead["num_employees"] = result.get("num_employees", "")
                lead["founded_year"] = result.get("founded_year", "")
                if result.get("linkedin_url") and not lead.get("linkedin_url"):
                    lead["linkedin_url"] = result["linkedin_url"]
                if result.get("logo") and not lead.get("company_logo"):
                    lead["company_logo"] = result["logo"]
                # Add founders as potential contacts
                if result.get("founders"):
                    lead["founders"] = result["founders"]
                lead["crunchbase_enriched"] = True

        logger.info("Crunchbase enriched %d/%d leads", enriched_count, len(tasks))
        return leads


# ═══════════════════════════════════════════════════════════════════════
# LinkedIn Data API — company enrichment
# Uses RAPIDAPI_KEY_2
# ═══════════════════════════════════════════════════════════════════════


class LinkedInCompanyClient:
    """Enrich company data using LinkedIn Data API.

    NOTE: The people search endpoint on this API is deprecated.
    Only company-by-domain may still work.
    Uses RAPIDAPI_KEY_2.
    """

    HOST = "linkedin-data-api.p.rapidapi.com"

    @property
    def enabled(self) -> bool:
        return bool(_get_key2())

    async def get_company_by_domain(self, domain: str) -> dict | None:
        """Look up a company's LinkedIn data by its website domain.

        Args:
            domain: Company website domain (e.g., "apple.com")

        Returns:
            Company info dict or None if not found / API unavailable.
        """
        if not self.enabled:
            return None

        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.get(
                    f"https://{self.HOST}/get-company-by-domain",
                    headers=_headers(self.HOST, _get_key2()),
                    params={"domain": domain},
                )
                resp.raise_for_status()
                body = resp.json()

            if not body.get("success", True):
                logger.warning("LinkedIn Data API: %s", body.get("message", "unknown error"))
                return None

            data = body.get("data", body)
            if not data or not isinstance(data, dict):
                return None

            return {
                "name": data.get("name", ""),
                "description": data.get("description", ""),
                "website": data.get("website", ""),
                "linkedin_url": data.get("linkedInUrl", data.get("url", "")),
                "industry": data.get("industry", ""),
                "company_size": data.get("companySize", ""),
                "headquarters": data.get("headquarter", {}).get("city", "") if isinstance(data.get("headquarter"), dict) else "",
                "logo": data.get("logo", ""),
                "founded": data.get("founded", ""),
                "source": "linkedin_data_api",
            }
        except Exception as e:
            logger.warning("LinkedIn company lookup failed for %s: %s", domain, e)
            return None


# ═══════════════════════════════════════════════════════════════════════
# Unified Service
# ═══════════════════════════════════════════════════════════════════════


class RapidAPIService:
    """Unified service combining all RapidAPI clients.

    Uses two API keys:
      RAPIDAPI_KEY   → JSearch (jobs from LinkedIn, Indeed, Naukri, Glassdoor)
      RAPIDAPI_KEY_2 → Internships API (real LinkedIn internships) + LinkedIn Data API

    Usage:
        service = RapidAPIService()
        jobs = await service.search_all_jobs(query="python developer", location="India")
        internships = await service.search_internships(keywords="data science")
        leads = await service.search_leads(keywords="Python FastAPI", industry="SaaS")
    """

    def __init__(self):
        self.jsearch = JSearchClient()
        self.linkedin_jobs = LinkedInJobSearchClient()
        self.internships = InternshipsClient()
        self.linkedin_company = LinkedInCompanyClient()
        self.crunchbase = CrunchbaseClient()

    @property
    def enabled(self) -> bool:
        return bool(_get_key()) or bool(_get_key2())

    async def search_leads(
        self,
        keywords: str = "",
        industry: str = "",
        role: str = "",
        location: str = "",
        count: int = 10,
    ) -> list[dict]:
        """Find B2B leads — companies/people who NEED your service built.

        Strategy:
          1. Search for companies actively looking to BUILD/BUY services
             (via job listings for freelance/contract work — signals they have budget + need)
          2. Extract unique companies with their details
          3. Enrich with Crunchbase (funding, industry, founders = decision makers)
          4. Prioritize recently funded companies (they have budget)

        This finds CLIENTS, not employers — people who need software built,
        websites designed, apps developed, etc.
        """
        import asyncio

        # Build search query focused on CLIENT NEEDS, not employment
        query_parts = [kw for kw in [keywords, industry] if kw]
        query = " ".join(query_parts) if query_parts else "technology startup"

        tasks = []

        # LinkedIn Job Search API — find companies posting contract/freelance work
        if self.linkedin_jobs.enabled:
            # Search for freelance/contract postings (= companies buying services)
            tasks.append(("linkedin_contract", self.linkedin_jobs.search(
                title_filter=f"{query} freelance",
                location_filter=location if location and location.lower() != "remote" else "",
                limit=min(count * 2, 50),
            )))
            # Also search for the skill directly (companies needing this skill)
            tasks.append(("linkedin_skill", self.linkedin_jobs.search(
                title_filter=query,
                location_filter=location if location and location.lower() != "remote" else "",
                limit=min(count * 2, 50),
            )))

        # JSearch — find companies posting projects on Indeed/Glassdoor
        country = "us"
        if location:
            loc_lower = location.lower()
            if "india" in loc_lower:
                country = "in"
            elif "uk" in loc_lower or "united kingdom" in loc_lower:
                country = "uk"

        tasks.append(("jsearch_projects", self.jsearch.search(
            query=f"{query} contract project freelance",
            country=country,
            num_pages=1,
        )))
        tasks.append(("jsearch_companies", self.jsearch.search(
            query=query,
            country=country,
            num_pages=1,
        )))

        results = await asyncio.gather(
            *[t[1] for t in tasks],
            return_exceptions=True,
        )

        # Collect all jobs, LinkedIn first (better company data)
        all_jobs: list[dict] = []
        for (source, _), result in zip(tasks, results):
            if isinstance(result, Exception):
                logger.warning("Lead source %s failed: %s", source, str(result)[:100])
                continue
            if isinstance(result, list):
                # LinkedIn results first for priority
                if "linkedin" in source:
                    all_jobs = result + all_jobs
                else:
                    all_jobs.extend(result)

        # Extract unique companies as B2B leads
        seen_companies: set[str] = set()
        extracted_leads: list[dict] = []
        for job in all_jobs:
            company = job.get("company", "")
            if not company or company.lower() in seen_companies:
                continue
            seen_companies.add(company.lower())

            employer_website = job.get("employer_website") or ""
            employer_logo = job.get("employer_logo") or ""

            # LinkedIn Job Search API provides organization_url (LinkedIn company page)
            linkedin_company_url = ""
            if job.get("source") == "linkedin_job_search_api":
                linkedin_company_url = employer_website
                employer_website = ""

            # Determine lead type based on job posting
            job_title = job.get("title", "")
            job_type = job.get("job_type", "")
            is_contract = job_type in ("contract", "freelance") or any(
                kw in job_title.lower() for kw in ["freelance", "contract", "project", "consultant"]
            )

            lead_signal = "Actively hiring freelancers" if is_contract else "Growing team — potential client"

            extracted_leads.append({
                "name": company,  # Company name as lead name
                "company": company,
                "role": lead_signal,
                "email": "",
                "linkedin_url": linkedin_company_url,
                "location": job.get("location", ""),
                "headline": f"{company} — {job_title}",
                "company_website": employer_website,
                "company_logo": employer_logo,
                "source": job.get("source", "jsearch"),
                "job_url": job.get("url", ""),
                "job_title": job_title,
                "job_type": job_type,
                "is_contract": is_contract,
            })
            if len(extracted_leads) >= count * 2:  # Fetch extra, will trim after enrichment
                break

        # Enrich with Crunchbase — adds funding, founders, industry
        if self.crunchbase.enabled and extracted_leads:
            extracted_leads = await self.crunchbase.enrich_leads(extracted_leads)

        # Sort: recently funded companies first, then contract posters, then rest
        def lead_sort_key(lead: dict) -> tuple:
            funding = lead.get("funding_usd") or 0
            is_contract = 1 if lead.get("is_contract") else 0
            has_founders = 1 if lead.get("founders") else 0
            return (-funding, -is_contract, -has_founders)

        extracted_leads.sort(key=lead_sort_key)

        logger.info(
            "Found %d B2B leads (%d Crunchbase-enriched)",
            len(extracted_leads),
            sum(1 for l in extracted_leads if l.get("crunchbase_enriched")),
        )
        return extracted_leads[:count]

    async def search_internships(
        self,
        keywords: str = "",
        location: str = "",
        count: int = 10,
    ) -> list[dict]:
        """Search real internship listings from LinkedIn job boards."""
        return await self.internships.search(keywords=keywords, location=location, count=count)

    async def search_all_jobs(
        self,
        query: str,
        location: str = "",
        platforms: list[str] | None = None,
        count_per_platform: int = 5,
    ) -> list[dict]:
        """Search across ALL platforms in parallel.

        Uses JSearch (LinkedIn + Indeed + Naukri) + Internships API.
        """
        import asyncio

        target_platforms = platforms or ["linkedin", "indeed", "naukri", "internshala"]
        tasks = []
        total_count = count_per_platform * len(target_platforms)

        # LinkedIn Job Search API — real LinkedIn jobs (uses RAPIDAPI_KEY_2)
        if "linkedin" in target_platforms and self.linkedin_jobs.enabled:
            # Don't pass "Remote" as location — the API expects a real place
            li_location = location if location and location.lower() not in ("remote", "anywhere", "") else ""
            tasks.append(("linkedin_job_search", self.linkedin_jobs.search(
                title_filter=query,
                location_filter=li_location,
                limit=min(count_per_platform * 3, 50),
            )))

        # Determine country code from location
        location_lower = (location or "").lower()
        if "india" in location_lower:
            country = "in"
        elif "united kingdom" in location_lower or "uk" in location_lower:
            country = "uk"
        elif "canada" in location_lower:
            country = "ca"
        elif "germany" in location_lower:
            country = "de"
        elif "australia" in location_lower:
            country = "au"
        elif "singapore" in location_lower:
            country = "sg"
        elif "france" in location_lower:
            country = "fr"
        elif location_lower in ("remote", "anywhere", ""):
            country = "us"  # Default to US for remote/empty
        else:
            country = "us"

        # JSearch — Indeed + Glassdoor + Naukri (uses RAPIDAPI_KEY)
        main_query = f"{query} in {location}" if location and location.lower() != "remote" else query
        tasks.append(("jsearch_page1", self.jsearch.search(
            query=main_query, country=country, page=1, num_pages=1,
        )))
        tasks.append(("jsearch_page2", self.jsearch.search(
            query=main_query, country=country, page=2, num_pages=1,
        )))

        # If naukri is targeted and user isn't already in India, also search India
        if "naukri" in target_platforms and country != "in":
            tasks.append(("jsearch_india", self.jsearch.search(
                query=f"{query} in India",
                country="in",
                num_pages=1,
            )))

        # Internships API — real LinkedIn internships (uses RAPIDAPI_KEY_2)
        if "internshala" in target_platforms and self.internships.enabled:
            tasks.append(("internships_api", self.internships.search(
                keywords=query,
                location=location,
                count=count_per_platform,
            )))

        all_jobs: list[dict] = []
        results = await asyncio.gather(
            *[t[1] for t in tasks],
            return_exceptions=True,
        )

        for (source_name, _), result in zip(tasks, results):
            if isinstance(result, Exception):
                logger.warning("Source %s failed: %s", source_name, str(result)[:100])
                continue
            if isinstance(result, list):
                all_jobs.extend(result)

        # Deduplicate by URL
        seen_urls: set[str] = set()
        unique_jobs: list[dict] = []
        for job in all_jobs:
            url = job.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_jobs.append(job)
            elif not url:
                unique_jobs.append(job)

        logger.info("search_all_jobs: %d unique results from %d sources", len(unique_jobs), len(tasks))
        return unique_jobs[:total_count]

    async def search_gigs(
        self,
        query: str,
        location: str = "",
        count: int = 10,
    ) -> list[dict]:
        """Search for freelance gigs (contract/freelance jobs via JSearch + LinkedIn)."""
        import asyncio

        tasks = []

        # JSearch for freelance gigs
        tasks.append(("jsearch", self.jsearch.search(
            query=f"{query} freelance OR contract OR remote project",
            num_pages=1,
        )))

        # LinkedIn Job Search API for contract roles
        if self.linkedin_jobs.enabled:
            tasks.append(("linkedin", self.linkedin_jobs.search(
                title_filter=f"{query} freelance",
                limit=count,
            )))

        results = await asyncio.gather(
            *[t[1] for t in tasks],
            return_exceptions=True,
        )

        gigs: list[dict] = []
        for (source, _), result in zip(tasks, results):
            if isinstance(result, list):
                gigs.extend(result)
            elif isinstance(result, Exception):
                logger.warning("Gig source %s failed: %s", source, str(result)[:100])

        # Deduplicate
        seen_urls: set[str] = set()
        unique: list[dict] = []
        for g in gigs:
            url = g.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique.append(g)
            elif not url:
                unique.append(g)

        logger.info("search_gigs: %d unique gig results", len(unique))
        return unique[:count]
