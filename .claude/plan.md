# Plan: Integrate RapidAPI for Real Data (LinkedIn, Indeed, Naukri, Internshala)

## What Changes

Replace all AI-generated/mock leads, gigs, and jobs with **real data** from RapidAPI endpoints:

### Data Sources (via RapidAPI)

| Module | API | RapidAPI Endpoint | What it fetches |
|--------|-----|-------------------|-----------------|
| **Leads** | Fresh LinkedIn Scraper | `fresh-linkedin-scraper-api.p.rapidapi.com` | Real LinkedIn profiles (people search) |
| **Leads** | LinkedIn Data API (RockAPIs) | `linkedin-data-api.p.rapidapi.com` | Profile enrichment, company data |
| **Jobs** | LinkedIn Jobs Search | `linkedin-jobs-search.p.rapidapi.com` | LinkedIn job listings |
| **Jobs** | Indeed Jobs API | `indeed-jobs-api-india.p.rapidapi.com` | Indeed job listings (India) |
| **Jobs** | JSearch (multi-platform) | `jsearch.p.rapidapi.com` | Indeed + Glassdoor + others |
| **Gigs** | LinkedIn Job Search API | `linkedin-job-search-api.p.rapidapi.com` | Freelance/contract gigs from LinkedIn |
| **Internships** | Internships API | `internships-api.p.rapidapi.com` | Internshala + other internship sites |

### Files to Create/Modify

#### 1. NEW: `backend/mcp_server/rapidapi_clients.py`
- `LinkedInLeadsClient` — search people on LinkedIn via Fresh LinkedIn Scraper API
- `LinkedInJobsClient` — search LinkedIn jobs via Jobs Scanner API
- `IndeedClient` — search Indeed jobs via JSearch or Indeed Jobs API
- `NaukriClient` — search Naukri jobs (via JSearch with India location filter)
- `InternshalaClient` — search internships via Internships API
- All clients use a single `RAPIDAPI_KEY` env var
- Each client has `async search()` method returning normalized dicts

#### 2. MODIFY: `backend/mcp_server/api_clients.py`
- Add `RapidAPILeadService` that uses LinkedIn people search
- Update `LeadDataService` to try RapidAPI → Apollo → AI fallback

#### 3. MODIFY: `backend/mcp_server/server.py`
- `find_leads()` → uses RapidAPI LinkedIn people search (real profiles)
- `search_gigs()` → uses RapidAPI LinkedIn for freelance/contract gigs
- NEW: `search_jobs()` tool → searches LinkedIn + Indeed + Naukri + Internshala
- Remove all AI-generated fallback data — only real API data

#### 4. MODIFY: `backend/agents/lead_finder.py`
- Use RapidAPI LinkedIn client instead of Apollo/AI fallback
- AI still scores and enriches the real leads

#### 5. MODIFY: `backend/agents/gig_finder.py`
- Fetch real gigs from LinkedIn via RapidAPI
- AI still scores and ranks them against user skills

#### 6. MODIFY: `backend/agents/job_finder.py`
- Fetch real jobs from LinkedIn + Indeed + Naukri + Internshala via RapidAPI
- AI still scores and ranks
- Add `platform` field mapping: "linkedin", "indeed", "naukri", "internshala"

#### 7. MODIFY: `backend/pipeline/orchestrator.py`
- Job pipeline passes platform sources to job_finder
- Gig pipeline uses real LinkedIn gig data

#### 8. MODIFY: `backend/db/models.py`
- Add "naukri" and "internshala" to Job platform field (already flexible string)
- No schema changes needed

#### 9. MODIFY: `.env`
- Add `RAPIDAPI_KEY=` (user provides their key)

#### 10. MODIFY: Frontend
- No major changes needed — frontend already renders whatever backend returns
- LinkedIn URLs will now be real and clickable
- Add "naukri" and "internshala" platform badges to Jobs page

### Architecture Flow

```
User triggers pipeline
  → PlannerAgent creates strategy
  → LeadFinderAgent:
      → RapidAPI: LinkedIn People Search (real profiles with real LinkedIn URLs)
      → AI: Scores leads, generates talking points
  → GigFinderAgent:
      → RapidAPI: LinkedIn Jobs (filter: contract/freelance)
      → AI: Scores & ranks by skill match
  → JobFinderAgent:
      → RapidAPI: LinkedIn Jobs + Indeed + Naukri + Internshala (parallel)
      → AI: Scores & ranks all jobs together
  → ProposalAgent + ReviewerAgent (unchanged)
  → CommunicationAgent (unchanged)
```

### ENV Variables Needed
```
RAPIDAPI_KEY=your_rapidapi_key_here
```

User needs to subscribe (free tier available) to these RapidAPI APIs:
1. Fresh LinkedIn Scraper API
2. LinkedIn Jobs Search (jaypat87)
3. JSearch API (for Indeed/Glassdoor)
4. Internships API (for Internshala)

### No Mock Data
- Delete `backend/mcp_server/mock_data.py` entirely
- All data comes from RapidAPI calls
- If RapidAPI call fails → return empty list with error message (no fake data)
