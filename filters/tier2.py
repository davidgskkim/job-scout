"""
tier2.py

LLM-based soft filter using Gemini Flash (free tier).
Only runs on jobs that pass Tier 1, keeping API usage minimal.

Evaluates:
- Is this genuinely an entry-level / 0-2 YOE role?
- Is it actually a Software Engineering or AI role (not mislabeled)?
- Is the location consistent with Canada or United States (or Remote)?

On any API error, defaults to RELEVANT — we'd rather over-deliver
a job than silently drop one you should have applied to.
"""

import json
import logging
import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

logger = logging.getLogger(__name__)

_client: genai.Client | None = None

# gemini-2.0-flash-lite: much higher free-tier quota than gemini-2.0-flash
GEMINI_MODEL = "gemini-2.0-flash-lite"

# Minimum delay between consecutive Gemini calls to stay under RPM limits
_RATE_LIMIT_DELAY = 1.0  # seconds


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


PROMPT_TEMPLATE = """\
You are a job relevance classifier for a recent Computer Science graduate seeking their first or second full-time software engineering role.

The candidate's profile:
- 0-2 years of professional experience (internship experience counts)
- Targeting Software Engineering, Full Stack, Backend, Python, or AI/ML Engineer roles
- Interested in positions in Canada or the United States (or Remote globally)
- NOT interested in: QA, DevOps, Mobile, iOS/Android, Data Analyst, Security, Infra/Platform, or Senior+ roles

Classify the following job posting:

Title: {title}
Company: {company}
Location: {location}
Description (excerpt):
{description}

Respond ONLY with a valid JSON object in this exact format (no markdown, no code fences):
{{"decision": "RELEVANT" or "SKIP", "reason": "one concise sentence explaining why"}}

Be strict — only mark RELEVANT if you are confident this is a genuine 0-2 YOE SWE or AI role in the target regions.\
"""


def classify(job: dict) -> tuple[str, str]:
    """
    Returns (decision, reason) where decision is "RELEVANT" or "SKIP".
    Defaults to ("RELEVANT", "...) on error to avoid silent misses.
    """
    title = job.get("title", "")
    company = job.get("company", "")
    location = job.get("location", "")
    # Do not truncate description! Minimum requirements are often at the bottom.
    # gemini-2.0-flash-lite has a massive context window, tokens are not an issue.
    description = job.get("description") or ""

    prompt = PROMPT_TEMPLATE.format(
        title=title,
        company=company,
        location=location,
        description=description or "(no description available)",
    )

    try:
        client = _get_client()
        time.sleep(_RATE_LIMIT_DELAY)  # Respect free-tier RPM limits
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,  # Low temp for consistent, deterministic classification
                max_output_tokens=100,
            ),
        )
        text = (response.text or "").strip()

        # Strip markdown code fences if the model wraps output anyway
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(
                line for line in lines if not line.startswith("```")
            ).strip()

        result = json.loads(text)
        decision = str(result.get("decision", "RELEVANT")).upper()
        reason = str(result.get("reason", ""))

        if decision not in ("RELEVANT", "SKIP"):
            decision = "RELEVANT"

        return decision, reason

    except Exception as e:
        logger.warning(f"[tier2] Classification failed for '{title}' — defaulting RELEVANT: {e}")
        return "RELEVANT", "Classification unavailable — included by default"
