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

# gemini-2.5-flash-lite: Best for high-volume classification on strict budgets.
GEMINI_MODEL = "gemini-2.5-flash-lite"

# Increased delay (10.1s) to safely stay below the 10 RPM Free Tier limit
# even if runs overlap or latency is low.
_RATE_LIMIT_DELAY = 10.1  # seconds

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

CRITICAL RULES:
1. If the job description does NOT explicitly state required Years of Experience (YOE), you MUST assume it is 0-2 YOE and mark it RELEVANT.
2. Only mark SKIP if you explicitly see a requirement for 3+ years of experience, or if it is an internship, or clearly a senior/mislabeled role.\
"""

def classify(job: dict) -> tuple[str, str]:
    """
    Returns (decision, reason) where decision is "RELEVANT" or "SKIP".
    Now uses max 3 retries for quota errors 429, and defaults to RELEVANT
    so you never miss a job if the server crashes.
    """
    title = job.get("title", "")
    company = job.get("company", "")
    location = job.get("location", "")
    description = job.get("description") or ""

    prompt = PROMPT_TEMPLATE.format(
        title=title,
        company=company,
        location=location,
        description=description or "(no description available)",
    )

    client = _get_client()

    for attempt in range(3):
        try:
            time.sleep(_RATE_LIMIT_DELAY)  # Respect free-tier 15 RPM limits
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=200,
                    safety_settings=[
                        types.SafetySetting(
                            category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                            threshold=types.HarmBlockThreshold.BLOCK_NONE,
                        ),
                        types.SafetySetting(
                            category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                            threshold=types.HarmBlockThreshold.BLOCK_NONE,
                        ),
                        types.SafetySetting(
                            category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                            threshold=types.HarmBlockThreshold.BLOCK_NONE,
                        ),
                        types.SafetySetting(
                            category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                            threshold=types.HarmBlockThreshold.BLOCK_NONE,
                        ),
                    ],
                ),
            )
            
            # Check for safety blocks or empty responses
            if not response.text:
                logger.warning(f"[tier2] Empty response/Safety block for '{title}'. candidates: {len(response.candidates)}")
                raise ValueError("Empty response or safety block triggered")

            text = response.text.strip()
            
            # Remove any markdown code fences if present
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(
                    line for line in lines if not line.startswith("```")
                ).strip()

            try:
                result = json.loads(text)
                decision = str(result.get("decision", "RELEVANT")).upper()
                reason = str(result.get("reason", ""))
            except json.JSONDecodeError as e:
                logger.error(f"[tier2] JSON Parse Error for '{title}': {e}. Raw text: {text[:200]}")
                raise


            if decision not in ("RELEVANT", "SKIP"):
                decision = "RELEVANT"

            return decision, reason

        except Exception as e:
            err_str = str(e)
            if "429" in err_str and attempt < 2:
                logger.warning(f"[tier2] 429 Rate limit hit for '{title}'. Retrying in 15 seconds...")
                time.sleep(15)
                continue
            
            logger.warning(f"[tier2] Classification failed for '{title}' (attempt {attempt+1}) — defaulting RELEVANT: {e}")
            # Fail open so the user NEVER misses a job!
            return "RELEVANT", "Classification unavailable — included by default to prevent missing an opportunity"
