import re
print(re.search(r'\b[3-9]\+\s*years?\b', '5+ years of professional full-stack software development experience.'))
print(re.search(r'\b[3-9]\+?\s*years?(?:\s+[a-zA-Z0-9-]+){0,6}\s+(experience|exp)\b', '5+ years of professional full-stack software development experience.'))
