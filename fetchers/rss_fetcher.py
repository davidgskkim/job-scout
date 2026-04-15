"""
rss_fetcher.py

Polls Indeed's official RSS feeds for fresh job postings.
Useful as a fast, lightweight supplement to jobspy — RSS results often
appear minutes earlier than search-page results.
"""

import hashlib
import logging
from urllib.parse import quote_plus

import feedparser

logger = logging.getLogger(__name__)

QUERIES = [
    "software engineer",
    "software developer",
    "full stack engineer",
    "full stack developer",
    "backend engineer",
    "backend developer",
    "python developer",
    "AI engineer",
]

# (label, RSS base URL)
FEEDS = [
    ("indeed_us", "https://www.indeed.com/rss?q={query}&l=United+States&sort=date&fromage=1"),
    ("indeed_ca", "https://ca.indeed.com/rss?q={query}&l=Canada&sort=date&fromage=1"),
]


def _make_job_id(title: str, company: str, url: str) -> str:
    raw = f"{title.lower().strip()}{company.lower().strip()}{url.strip()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:20]


def _parse_title_company(raw_title: str) -> tuple[str, str]:
    """
    Indeed RSS titles often follow the format: 'Title - Company - Location'
    We extract title and company from this pattern.
    """
    parts = [p.strip() for p in raw_title.split(" - ")]
    title = parts[0] if parts else raw_title
    company = parts[1] if len(parts) > 1 else ""
    return title, company


def fetch_jobs() -> list[dict]:
    all_jobs: list[dict] = []
    seen_urls: set[str] = set()

    for query in QUERIES:
        encoded = quote_plus(query)
        for source_label, url_template in FEEDS:
            feed_url = url_template.format(query=encoded)
            location_hint = "United States" if "indeed_us" in source_label else "Canada"

            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries:
                    job_url = str(entry.get("link", "")).strip()
                    if not job_url or job_url in seen_urls:
                        continue
                    seen_urls.add(job_url)

                    raw_title = str(entry.get("title", ""))
                    title, company = _parse_title_company(raw_title)
                    description = str(entry.get("summary", ""))
                    date_posted = str(entry.get("published", ""))
                    job_id = _make_job_id(title, company, job_url)

                    all_jobs.append({
                        "id": job_id,
                        "title": title,
                        "company": company,
                        "location": location_hint,
                        "description": description,
                        "url": job_url,
                        "salary": None,
                        "date_posted": date_posted,
                        "source": source_label,
                    })

            except Exception as e:
                logger.warning(f"[rss] Error — query='{query}', feed='{source_label}': {e}")

    logger.info(f"[rss] Total fetched: {len(all_jobs)}")
    return all_jobs
