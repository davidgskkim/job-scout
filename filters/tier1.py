"""
tier1.py

Rule-based hard filter. Fast, regex-powered, no API calls.
Runs before Tier 2 to eliminate obvious mismatches cheaply.

Logic:
  1. Title must match at least one INCLUDE role pattern
  2. Title must NOT match any EXCLUDE role pattern (senior, QA, etc.)
  3. Description must NOT mention high YOE requirements (3+ years, 2+ years, etc.)
  4. Location must NOT be an explicitly non-target country (India, UK, etc.)
  5. Location must be Canada, United States, or Remote (or unknown = pass)
"""

import logging
import re

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Title patterns — INCLUDE (at least one must match)
# ---------------------------------------------------------------------------
INCLUDE_TITLE_PATTERNS = [
    r"\bsoftware\s+(engineer|developer|dev)\b",
    r"\bfull[\s\-]?stack\s+(engineer|developer|dev)\b",
    r"\bback[\s\-]?end\s+(engineer|developer|dev)\b",
    r"\bpython\s+(engineer|developer|dev)\b",
    r"\bai\s+(engineer|developer|researcher)\b",
    r"\bweb\s+(developer|dev|engineer)\b",
    r"\bapplication\s+(developer|engineer)\b",
]

# ---------------------------------------------------------------------------
# Title patterns — EXCLUDE (any match = reject)
# ---------------------------------------------------------------------------
EXCLUDE_TITLE_PATTERNS = [
    # Seniority & Levels
    r"\bsenior\b", r"\bsr\.?\b", r"\bstaff\b", r"\bprincipal\b",
    r"\blead\b", r"\barchitect\b", r"\bhead\s+of\b", r"\bdirector\b",
    r"\bmanager\b", r"\bvp\b", r"\bvice\s+president\b",
    r"\bintern\b", r"\binternship\b", r"\bco-?op\b",  # Block interns
    r"\bsoftware (?:engineer|developer|dev)\s*(?:ii|iii|iv|v|vi|2|3|4|5|6)\b", 
    r"\b(?:ii|iii|iv|v|vi)\b",  # Standalone suffix like "Engineer II" is caught too
    # Wrong roles
    r"\bqa\b", r"\bquality\s+assurance\b", r"\btest\s+engineer\b",
    r"\bsdet\b", r"\bautomation\s+engineer\b",
    r"\bdevops\b", r"\bsite\s+reliability\b", r"\bsre\b",
    r"\bplatform\s+engineer\b", r"\binfrastructure\s+engineer\b",
    r"\bcloud\s+engineer\b", r"\bnetwork\s+engineer\b",
    r"\bios\b", r"\bandroid\b",  # catches suffix-style: "Software Engineer, iOS"
    r"\bios\s+(engineer|developer)\b", r"\bandroid\s+(engineer|developer)\b",
    r"\bmobile\s+(engineer|developer)\b",
    r"\bdata\s+analyst\b", r"\bdata\s+scientist\b", r"\bdata\s+engineer\b",
    r"\bbusiness\s+analyst\b", r"\bsecurity\s+engineer\b", r"\bcybersecurity\b",
    r"\bembedded\s+(systems|engineer|developer)\b",
    r"\bhardware\s+engineer\b", r"\bfirmware\s+engineer\b",
    r"\bjava\b",  # Exclude strictly backend Java roles
]

# ---------------------------------------------------------------------------
# Company patterns — EXCLUDE (any match = reject)
# ---------------------------------------------------------------------------
EXCLUDE_COMPANY_PATTERNS = [
    r"\bmercor\b", 
    r"\bdataannotation\b", r"\bdata\s*annotation\b",
    r"\bremotehunter\b", r"\bremote\s*hunter\b",
    r"\bhunter\s*bond\b",
]

# ---------------------------------------------------------------------------
# Title patterns — AUTO PASS (bypass Tier 2 directly to RELEVANT)
# ---------------------------------------------------------------------------
AUTO_PASS_TITLE_PATTERNS = [
    r"\bjunior\b", r"\bjr\.?\b", r"\bentry[\s\-]?level\b",
    r"\b(?:new\s+)?grad(s|uates?)?\b", r"\bassociate\b",
    r"\bsoftware (?:engineer|developer|dev)\s*(?:i|1)\b",
]

# ---------------------------------------------------------------------------
# YOE patterns in DESCRIPTION — any match = reject
#
# Core logic: David has 1-2 YOE. Only reject if the job's MINIMUM requirement
# puts 2 YOE outside their acceptable range.
#
# KEEP:   "0-2 years", "1-3 years", "2 years experience", "up to 2 years"
# REJECT: "3+ years", "3-5 years", "2+ years", "minimum 3 years", etc.
#
# "2+" is rejected because job postings use it to mean "experienced hire, not entry-level"
# "1-3" is kept because 2 YOE sits inside [1, 3]
# ---------------------------------------------------------------------------
EXCLUDE_YOE_PATTERNS = [

    # ── Minimum required is 3+ ───────────────────────────────────────────────

    # Minimum required is 3+
    # Scan up to 120 chars on the same line to match "experience"
    # (?<![0-9\-\u2013]) prevents matching the upper bound of a range like "1-3 years"
    r"(?<![0-9\-\u2013])[3-9]\+?\s*years?(?:.{0,120}?)\b(?:experience|exp)\b",
    r"(?<![0-9\-\u2013])[1-9][0-9]\+?\s*years?(?:.{0,120}?)\b(?:experience|exp)\b",

    # "3+ years" with explicit "+" even without the word "experience"
    r"(?<![0-9\-\u2013])[3-9]\+\s*years?\b",
    r"(?<![0-9\-\u2013])[1-9][0-9]\+\s*years?\b",

    # Ranges: "3-5 years", "4–6 yrs", "10-12 years of experience"
    # Handling -, to, and, through
    r"(?<![0-9\-\u2013])[3-9]\s*(?:-|–|to|and|through)\s*\d+\s*(?:years?|yrs?|yoe)\b",
    r"(?<![0-9\-\u2013])[1-9][0-9]\s*(?:-|–|to|and|through)\s*\d+\s*(?:years?|yrs?|yoe)\b",
    r"\b2\s*(?:-|–|to|and|through)\s*[3-9]\d*\s*(?:years?|yrs?|yoe)\b",       # "2-3 years", "2 to 5 years" (reject)

    # "3+ yrs", "5 yrs of experience"
    # Making (years?|yrs?) optional if experience/exp is present to catch "5+ experience"
    r"(?<![0-9\-\u2013])[3-9]\+?\s*(?:years?|yrs?|yoe)?(?:.{0,120}?)\b(?:experience|exp)\b",
    r"(?<![0-9\-\u2013])[3-9]\+\s*(?:years?|yrs?|yoe)?\b",
    r"(?<![0-9\-\u2013])[1-9][0-9]\+?\s*(?:years?|yrs?|yoe)?(?:.{0,120}?)\b(?:experience|exp)\b",

    # YOE abbreviation: "3 YOE", "5+ YOE", "3-7 YOE"
    r"(?<![0-9\-\u2013])[3-9]\+?\s*yoe\b",
    r"(?<![0-9\-\u2013])[1-9][0-9]\+?\s*yoe\b",

    # Written-out numbers: "three years", "five or more years of experience"
    r"\b(three|four|five|six|seven|eight|nine|ten)\s+(or\s+more\s+)?years?\b",

    # Explicit minimum language with 3+:
    # "minimum 3 years", "at least 4 years", "more than 3 years",
    # "over 5 years", "minimum of 3 years", "a minimum of 4 years"
    r"\b(?:minimum|at\s+least|more\s+than|over|exceeding)\s+(?:of\s+)?(?<![0-9\-\u2013])[3-9]\+?\s*years?\b",
    r"\b(?:minimum|at\s+least|more\s+than|over)\s+(?:of\s+)?(?<![0-9\-\u2013])[1-9][0-9]\+?\s*years?\b",

    # "requires 3 years", "requiring 5+ years"
    r"\brequires?\s+(?<![0-9\-\u2013])[3-9]\+?\s*years?\b",
    r"\brequires?\s+(?<![0-9\-\u2013])[1-9][0-9]\+?\s*years?\b",

    # "X years required" (reversed phrasing)
    r"(?<![0-9\-\u2013])[3-9]\+?\s*years?\s+required\b",
    r"(?<![0-9\-\u2013])[1-9][0-9]\+?\s*years?\s+required\b",

    # ── Open-ended 2+ (signals "experienced hire", not entry-level) ─────────

    # "2+ years", "2+ years of experience", "2+ years of work experience"
    r"\b2\s*\+\s*years?\b",

    # "2+ yrs", "2+ YOE"
    r"\b2\+\s*yrs?\b",
    r"\b2\s*\+\s*yoe\b",

    # "2 to 3 years", "2 to 5 years"
    r"\b2\s+(or\s+more|\+)\s*(?:years?|yrs?|yoe)\b",
    r"\b(?:minimum|at\s+least|requires?|more\s+than|over|exceeding)\s+(?:of\s+)?2\+\s*(?:years?|yrs?|yoe)\b",
]

# ---------------------------------------------------------------------------
# Location patterns — EXCLUDE first (checked before valid patterns)
# Catches geo-restricted "Remote" roles like "Remote - India"
# ---------------------------------------------------------------------------
EXCLUDE_LOCATION_PATTERNS = [
    r"\bindia\b", r"\bindian\b",
    r"\buk\b", r"\bunited\s+kingdom\b", r"\bengland\b", r"\bscotland\b", r"\bwales\b",
    r"\baustralia\b", r"\bnew\s+zealand\b",
    r"\beurope\b", r"\beuropa\b", r"\bemea\b",
    r"\bgermany\b", r"\bfrance\b", r"\bspain\b", r"\bitaly\b",
    r"\bnetherlands\b", r"\bpoland\b", r"\bportugal\b", r"\bsweden\b",
    r"\bireland\b", r"\bdenmark\b", r"\bfinland\b", r"\bnorway\b",
    r"\bsingapore\b", r"\bjapan\b", r"\bchina\b", r"\bkorea\b",
    r"\bbrazil\b", r"\bmexico\b", r"\blatam\b", r"\blatin\s+america\b",
    r"\bapac\b", r"\basia\b", r"\bafrica\b", r"\bmiddle\s+east\b",
    r"\bpakistan\b", r"\bbangladesh\b", r"\bphilippines\b", r"\bvietnam\b",
    r"\bindonesia\b", r"\bmalaysia\b", r"\bnigeria\b", r"\bghana\b",
]

# ---------------------------------------------------------------------------
# Location patterns — INCLUDE (empty/unknown location defaults to pass)
# ---------------------------------------------------------------------------
VALID_LOCATION_PATTERNS = [
    # Canada
    r"\bcanada\b", r"\bcanadian\b",
    r"\bontario\b", r"\btoronto\b", r"\bvancouver\b", r"\bcalgary\b",
    r"\bmontreal\b", r"\bottawa\b", r"\bwaterloo\b", r"\bbc\b",
    r"\balberta\b", r"\bquebec\b", r"\bmanitoba\b",
    # United States
    r"\bunited\s+states\b", r"\busa\b", r"\bu\.s\.a?\b", r"\bamerica\b",
    r"\bnew\s+york\b", r"\bsan\s+francisco\b", r"\bseattle\b",
    r"\blos\s+angeles\b", r"\bchicago\b", r"\baustin\b", r"\bboston\b",
    r"\bdenver\b", r"\batl\b", r"\batlanta\b",
    # Remote / flexible (geographic exclusions checked first, above)
    r"\bremote\b", r"\bhybrid\b", r"\bwork\s+from\s+home\b", r"\bwfh\b",
    r"\banywhere\b", r"\bnorth\s+america\b", r"\bglobal\b",
]


def _matches_any(text: str, patterns: list[str]) -> bool:
    text_lower = text.lower()
    return any(re.search(p, text_lower) for p in patterns)


def is_relevant(job: dict) -> tuple[bool, str, bool]:
    """
    Returns (is_relevant, reason, auto_pass)
    - auto_pass is True if Tier 2 should be skipped
    """
    title = job.get("title", "")
    description = job.get("description", "")
    location = job.get("location", "")
    company = job.get("company", "")

    # 1. Company must not be in the exclude list
    if _matches_any(company, EXCLUDE_COMPANY_PATTERNS):
        return False, f"Company is excluded: '{company}'", False

    # 2. Title must match a valid role
    if not _matches_any(title, INCLUDE_TITLE_PATTERNS):
        return False, f"Title not a target role: '{title}'", False

    # 2. Title must not contain exclusion terms
    if _matches_any(title, EXCLUDE_TITLE_PATTERNS):
        return False, f"Title has excluded term: '{title}'", False

    # 3. Description must not require >2 YOE (only check if description exists)
    if description:
        # Matches "1 to 5 years", "0-3 yoe", "one through ten years", "zero to four", etc.
        # This prevents the filters from seeing a high number that is just the upper bound of a safe range.
        nums_and_words = r"(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)"
        safe_range_pattern = rf"\b(?:zero|0|one|1)\b\s*(?:-|–|to|and|through)\s*{nums_and_words}\s*(?:years?|yrs?|yoe)\b"
        muzzled_desc = re.sub(safe_range_pattern, "1 year experience", description, flags=re.IGNORECASE)
        
        if _matches_any(muzzled_desc, EXCLUDE_YOE_PATTERNS):
            return False, "Description requires too many years of experience", False

    # 4. Explicitly exclude non-target countries BEFORE checking valid locations.
    if location and _matches_any(location, EXCLUDE_LOCATION_PATTERNS):
        return False, f"Location is a non-target country: '{location}'", False

    # 5. Location must be Canada, US, or Remote (empty location = pass through)
    if location and not _matches_any(location, VALID_LOCATION_PATTERNS):
        return False, f"Location not targeted: '{location}'", False

    # 6. Auto-pass check
    if _matches_any(title, AUTO_PASS_TITLE_PATTERNS):
        return True, "Auto-passed based on Junior/Entry title", True

    return True, "", False
