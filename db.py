import logging
import os

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

logger = logging.getLogger(__name__)

_client: Client | None = None

# Supabase has a default row limit per request — stay well under it
BATCH_SIZE = 500


def _get_client() -> Client:
    global _client
    if _client is None:
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_KEY"]
        _client = create_client(url, key)
    return _client


def get_seen_ids() -> set[str]:
    """
    Fetch ALL previously seen job IDs from the database.

    Supabase returns at most 1000 rows per request by default, so we paginate
    using .range() until we get an empty page.
    """
    client = _get_client()
    seen: set[str] = set()
    page = 0

    while True:
        start = page * BATCH_SIZE
        end = start + BATCH_SIZE - 1
        response = (
            client.table("seen_jobs")
            .select("job_id")
            .range(start, end)
            .execute()
        )
        rows = response.data
        if not rows:
            break
        seen.update(row["job_id"] for row in rows)
        if len(rows) < BATCH_SIZE:
            # Last partial page — no more data
            break
        page += 1

    logger.info(f"[db] Loaded {len(seen)} seen job IDs from Supabase")
    return seen


def mark_seen_batch(jobs: list[dict]) -> None:
    """
    Bulk upsert a list of jobs into seen_jobs.

    Splits into chunks of BATCH_SIZE to avoid hitting Supabase request size limits.
    Logs a warning on failure but does NOT raise — a failed write means duplicates
    next run (annoying), not data loss.
    """
    if not jobs:
        return

    client = _get_client()
    total = len(jobs)
    written = 0

    for i in range(0, total, BATCH_SIZE):
        chunk = jobs[i : i + BATCH_SIZE]
        rows = [
            {
                "job_id": j["id"],
                "source": j.get("source", ""),
                "title": j.get("title", ""),
                "company": j.get("company", ""),
                "url": j.get("url", ""),
            }
            for j in chunk
        ]
        try:
            client.table("seen_jobs").upsert(rows).execute()
            written += len(chunk)
        except Exception as e:
            logger.warning(
                f"[db] Failed to write chunk {i}–{i + len(chunk)} to Supabase: {e}"
            )

    logger.info(f"[db] Marked {written}/{total} jobs as seen in Supabase")
