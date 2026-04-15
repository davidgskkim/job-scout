"""
ats_fetcher.py

Polls Greenhouse, Lever, and Ashby ATS APIs directly using their
official public endpoints. Each platform uses a per-company slug,
and we maintain a starter list of ~100+ tech companies in data/companies.json.

Since these are official APIs (not scraping), they are stable and free.
Greenhouse/Ashby don't return full descriptions from the list endpoint,
so we filter on title/location only — Tier 2 handles semantic relevance.
Lever DOES return descriptions in the list endpoint, so we pass those through.
"""

import hashlib
import json
import logging
import os
import time
from pathlib import Path

import re
import requests

logger = logging.getLogger(__name__)

# Load company lists
_data_path = Path(__file__).parent.parent / "data" / "companies.json"
with open(_data_path) as f:
    COMPANIES = json.load(f)

REQUEST_TIMEOUT = 10
DELAY_BETWEEN_REQUESTS = 0.3  # seconds — be kind to these APIs


def _make_job_id(title: str, company: str, url: str) -> str:
    raw = f"{title.lower().strip()}{company.lower().strip()}{url.strip()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:20]


# ---------------------------------------------------------------------------
# Greenhouse
# ---------------------------------------------------------------------------

def _fetch_greenhouse(board_token: str) -> list[dict]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            return []
        data = resp.json()
    except Exception as e:
        logger.debug(f"[greenhouse] {board_token}: {e}")
        return []

    jobs = []
    for job in data.get("jobs", []):
        title = str(job.get("title") or "")
        job_url = str(job.get("absolute_url") or "")
        location = str((job.get("location") or {}).get("name") or "")
        company = board_token.replace("-", " ").title()
        
        # Clean HTML from description
        raw_content = str(job.get("content") or "")
        description = re.sub(r'<[^>]+>', ' ', raw_content)

        job_id = _make_job_id(title, company, job_url)

        jobs.append({
            "id": job_id,
            "title": title,
            "company": company,
            "location": location,
            "description": description,
            "url": job_url,
            "salary": None,
            "date_posted": None,
            "source": "greenhouse",
        })
    return jobs


# ---------------------------------------------------------------------------
# Lever
# ---------------------------------------------------------------------------

def _fetch_lever(company_slug: str) -> list[dict]:
    url = f"https://api.lever.co/v0/postings/{company_slug}?mode=json"
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            return []
        data = resp.json()
    except Exception as e:
        logger.debug(f"[lever] {company_slug}: {e}")
        return []

    jobs = []
    for posting in data:
        title = str(posting.get("text") or "")
        job_url = str(posting.get("hostedUrl") or "")
        categories = posting.get("categories") or {}
        location = str(categories.get("location") or categories.get("allLocations") or "")
        company = company_slug.replace("-", " ").title()

        # Lever returns description content in 'lists' and 'descriptionPlain'
        desc_parts = [str(posting.get("descriptionPlain") or "")]
        for section in posting.get("lists") or []:
            desc_parts.append(str(section.get("content") or ""))
        description = " ".join(desc_parts)

        job_id = _make_job_id(title, company, job_url)

        jobs.append({
            "id": job_id,
            "title": title,
            "company": company,
            "location": location,
            "description": description,
            "url": job_url,
            "salary": None,
            "date_posted": None,
            "source": "lever",
        })
    return jobs


# ---------------------------------------------------------------------------
# Ashby
# ---------------------------------------------------------------------------

def _fetch_ashby(org_slug: str) -> list[dict]:
    url = (
        "https://jobs.ashbyhq.com/api/non-user-facing/posting-board/job-postings"
        f"?organizationHostedJobsPageName={org_slug}"
    )
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            return []
        data = resp.json()
    except Exception as e:
        logger.debug(f"[ashby] {org_slug}: {e}")
        return []

    jobs = []
    for posting in data.get("jobPostings") or []:
        title = str(posting.get("title") or "")
        job_url = f"https://jobs.ashbyhq.com/{org_slug}/{posting.get('id', '')}"
        location = str(posting.get("locationName") or "")
        company = org_slug.replace("-", " ").title()
        description = str(posting.get("descriptionPlain") or "")
        job_id = _make_job_id(title, company, job_url)

        jobs.append({
            "id": job_id,
            "title": title,
            "company": company,
            "location": location,
            "description": description,
            "url": job_url,
            "salary": None,
            "date_posted": None,
            "source": "ashby",
        })
    return jobs


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def fetch_jobs() -> list[dict]:
    all_jobs: list[dict] = []

    logger.info(f"[ats] Polling {len(COMPANIES['greenhouse'])} Greenhouse boards...")
    for slug in COMPANIES["greenhouse"]:
        all_jobs.extend(_fetch_greenhouse(slug))
        time.sleep(DELAY_BETWEEN_REQUESTS)

    logger.info(f"[ats] Polling {len(COMPANIES['lever'])} Lever boards...")
    for slug in COMPANIES["lever"]:
        all_jobs.extend(_fetch_lever(slug))
        time.sleep(DELAY_BETWEEN_REQUESTS)

    logger.info(f"[ats] Polling {len(COMPANIES['ashby'])} Ashby boards...")
    for slug in COMPANIES["ashby"]:
        all_jobs.extend(_fetch_ashby(slug))
        time.sleep(DELAY_BETWEEN_REQUESTS)

    logger.info(f"[ats] Total fetched: {len(all_jobs)}")
    return all_jobs
