from jobspy import scrape_jobs
try:
    df = scrape_jobs(
        site_name=["linkedin"], 
        search_term="software engineer", 
        location="United States", 
        results_wanted=5, 
        linkedin_fetch_description=True
    )
    for _, row in df.iterrows():
        desc = str(row.get("description", ""))
        print(f"Title: {row.get('title')}")
        print(f"Desc Length: {len(desc)}")
        print(f"Desc Snippet: {desc[:200]}...\n")
except Exception as e:
    print(e)
