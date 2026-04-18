"""
main.py — Job Scout Orchestrator

Runs the full pipeline:
  1. Fetch jobs from all sources (jobspy, Indeed RSS, ATS APIs)
  2. Deduplicate against previously seen jobs (Supabase)
  3. Tier 1: Hard keyword/regex filter
  4. Tier 2: Gemini Flash LLM relevance classification
  5. Send one email per relevant job (Gmail SMTP)
  6. Mark ALL new jobs (including filtered ones) as seen to avoid re-processing

Run locally:    python main.py
GitHub Actions: triggered by cron schedule in .github/workflows/scout.yml
"""

import logging
import sys

import db
from fetchers import ats_fetcher, jobspy_fetcher, rss_fetcher
from filters import tier1, tier2
from notify import email_sender

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
    stream=open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1),
)
logger = logging.getLogger(__name__)


def run() -> None:
    logger.info("=" * 55)
    logger.info("  JOB SCOUT — run starting")
    logger.info("=" * 55)

    # ------------------------------------------------------------------
    # 1. Fetch from all sources
    # ------------------------------------------------------------------
    raw_jobs: list[dict] = []

    logger.info("-- Fetching: jobspy (LinkedIn / Indeed / Glassdoor)")
    raw_jobs.extend(jobspy_fetcher.fetch_jobs())

    logger.info("-- Fetching: Indeed RSS")
    raw_jobs.extend(rss_fetcher.fetch_jobs())

    logger.info("-- Fetching: ATS (Greenhouse / Lever / Ashby)")
    raw_jobs.extend(ats_fetcher.fetch_jobs())

    logger.info(f"Total raw jobs across all sources: {len(raw_jobs)}")

    # ------------------------------------------------------------------
    # 2. Deduplicate within this batch (same job from multiple sources)
    # ------------------------------------------------------------------
    unique: dict[str, dict] = {}
    for job in raw_jobs:
        unique.setdefault(job["id"], job)
    raw_jobs = list(unique.values())
    logger.info(f"After within-batch dedup: {len(raw_jobs)}")

    # ------------------------------------------------------------------
    # 3. Filter out already-seen jobs
    # ------------------------------------------------------------------
    seen_ids = db.get_seen_ids()
    new_jobs = [j for j in raw_jobs if j["id"] not in seen_ids]
    logger.info(f"New (unseen) jobs: {len(new_jobs)}")

    if not new_jobs:
        logger.info("Nothing new — exiting early.")
        return

    # ------------------------------------------------------------------
    # 4. Tier 1: Hard filter (fast, no API calls)
    # ------------------------------------------------------------------
    tier1_passed: list[dict] = []
    auto_pass_jobs: list[dict] = []
    
    for job in new_jobs:
        passed, reason, auto_pass = tier1.is_relevant(job)
        if passed and auto_pass:
            job["reason"] = f"Auto-passed by Tier 1: {reason}"
            auto_pass_jobs.append(job)
            logger.info(f"[T1 ✅ AUTO-PASS] {job['title']} @ {job['company']}")
        elif passed:
            tier1_passed.append(job)
        else:
            logger.debug(f"[T1 ❌ SKIP] {job['title']} @ {job['company']} — {reason}")

    logger.info(f"After Tier 1: {len(tier1_passed)} / {len(new_jobs)} passed")

    # ------------------------------------------------------------------
    # 5. Tier 2: LLM filter (Gemini Flash)
    # ------------------------------------------------------------------
    final_jobs: list[dict] = []
    
    # 1. Add auto pass jobs
    final_jobs.extend(auto_pass_jobs)
    
    # 2. Add LLM passed jobs
    for job in tier1_passed:
        decision, reason = tier2.classify(job)
        if decision == "RELEVANT":
            job["reason"] = reason
            final_jobs.append(job)
            logger.info(f"[T2 ✅] {job['title']} @ {job['company']}")
        else:
            logger.info(f"[T2 ❌] {job['title']} @ {job['company']} — {reason}")

    logger.info(f"After Tier 2: {len(final_jobs)} relevant jobs to deliver")

    # ------------------------------------------------------------------
    # 6. Send emails
    # ------------------------------------------------------------------
    sent = 0
    for job in final_jobs:
        try:
            email_sender.send_job_email(job, job.get("reason", ""))
            sent += 1
        except Exception as e:
            logger.error(f"[email] Failed for '{job['title']}' @ {job['company']}: {e}")

    # ------------------------------------------------------------------
    # 7. Mark ALL new jobs as seen (including filtered ones)
    #    This prevents re-evaluating the same rejected jobs next run.
    # ------------------------------------------------------------------
    db.mark_seen_batch(new_jobs)
    logger.info(f"Marked {len(new_jobs)} jobs as seen in Supabase")

    logger.info("=" * 55)
    logger.info(f"  Done. {sent} job alert(s) sent.")
    logger.info("=" * 55)


if __name__ == "__main__":
    run()
