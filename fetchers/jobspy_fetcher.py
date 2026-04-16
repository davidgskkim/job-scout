"""
jobspy_fetcher.py

Fetches jobs from LinkedIn, Indeed, and Glassdoor using the python-jobspy library.
Runs 8 role-type search queries across 2 locations (Canada, United States).
Uses jobspy's built-in hours_old filter to only surface recent postings.
"""

import hashlib
import logging
import math
import time
from datetime import date, datetime, timedelta

from jobspy import scrape_jobs

logger = logging.getLogger(__name__)

QUERIES = [
    "junior software engineer",
    "entry level software engineer",
    "new grad software engineer",
    "associate software engineer",
    "junior full stack engineer",
    "junior backend engineer",
    "software engineer"
]

SITES = ["linkedin", "indeed"]
LOCATIONS = ["Canada", "United States"]

# Fetch jobs posted within the last 3 hours (generous buffer against GitHub Actions cron delays)
HOURS_OLD = 3
RESULTS_PER_QUERY = 30

# Hard cap: Indeed lets employers "refresh" old listings so they appear in recent
# results with their original (stale) date. Drop anything older than this.
MAX_AGE_DAYS = 3


def _make_job_id(title: str, company: str, url: str) -> str:
    raw = f"{title.lower().strip()}{company.lower().strip()}{url.strip()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:20]


def fetch_jobs() -> list[dict]:
    all_jobs: list[dict] = []
    seen_urls: set[str] = set()

    for query in QUERIES:
        for location in LOCATIONS:
            try:
                logger.info(f"[jobspy] Fetching: '{query}' in {location}")
                df = scrape_jobs(
                    site_name=SITES,
                    search_term=query,
                    location=location,
                    results_wanted=RESULTS_PER_QUERY,
                    hours_old=HOURS_OLD,
                    country_indeed="USA" if location == "United States" else "Canada",
                    linkedin_fetch_description=True,  # fetch full job page, not just preview
                )

                for _, row in df.iterrows():
                    url = str(row.get("job_url") or "").strip()
                    if not url or url in seen_urls:
                        continue
                    seen_urls.add(url)

                    title = str(row.get("title") or "")
                    company = str(row.get("company") or "")
                    job_id = _make_job_id(title, company, url)

                    # Drop stale refreshed listings (Indeed re-surfaces old jobs)
                    raw_date = row.get("date_posted")
                    if raw_date is not None:
                        try:
                            if isinstance(raw_date, (date, datetime)):
                                posted = raw_date if isinstance(raw_date, date) else raw_date.date()
                            else:
                                posted = datetime.strptime(str(raw_date).strip(), "%Y-%m-%d").date()
                            if (date.today() - posted).days > MAX_AGE_DAYS:
                                logger.debug(f"[jobspy] Skipping stale listing ({posted}): {title} @ {company}")
                                continue
                        except (ValueError, TypeError):
                            pass  # Unparseable date — let it through, Tier 1/2 will judge

                    # Build salary string (guard against NaN from jobspy)
                    try:
                        min_amt = row.get("min_amount")
                        max_amt = row.get("max_amount")
                        currency = str(row.get("currency") or "")
                        interval = str(row.get("interval") or "")
                        salary = None
                        if min_amt and not math.isnan(float(min_amt)) and max_amt and not math.isnan(float(max_amt)):
                            salary = f"{currency}{int(min_amt):,} – {currency}{int(max_amt):,} / {interval}"
                        elif min_amt and not math.isnan(float(min_amt)):
                            salary = f"{currency}{int(min_amt):,}+ / {interval}"
                    except (TypeError, ValueError):
                        salary = None

                    all_jobs.append({
                        "id": job_id,
                        "title": title,
                        "company": company,
                        "location": str(row.get("location") or location),
                        "description": str(row.get("description") or ""),
                        "url": url,
                        "salary": salary,
                        "date_posted": str(row.get("date_posted") or ""),
                        "source": str(row.get("site") or "jobspy"),
                    })

            except Exception as e:
                logger.warning(f"[jobspy] Error — query='{query}', location='{location}': {e}")

            # Small delay between queries to be a polite scraper
            time.sleep(2)

    logger.info(f"[jobspy] Total fetched: {len(all_jobs)}")
    return all_jobs
