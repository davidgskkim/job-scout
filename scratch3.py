import re
def _matches_any(text, patterns):
    text_lower = text.lower()
    return any(re.search(p, text_lower) for p in patterns)

patterns = [r"\b[3-9]\+\s*years?\b"]
print(_matches_any("6+ years of programming experience", patterns))
