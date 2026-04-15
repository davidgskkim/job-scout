import requests
import re
resp = requests.get('https://boards-api.greenhouse.io/v1/boards/stripe/jobs?content=true')
data = resp.json()
print("jobs" in data and len(data["jobs"]) > 0)
if "jobs" in data and len(data["jobs"]) > 0:
    content = data['jobs'][0].get('content', '')
    if content:
        text = re.sub(r'<[^>]+>', ' ', content)
        print(len(text))
        print(text[:200])
    print("\nContent lengths:")
    for j in data["jobs"][:5]:
        print(len(j.get("content", "")))
