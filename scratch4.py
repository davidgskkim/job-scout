from jobspy import scrape_jobs

df = scrape_jobs(
    site_name=["linkedin"], 
    search_term="Ruby on Rails", 
    location="United States", 
    results_wanted=3, 
    linkedin_fetch_description=True
)
for _, row in df.iterrows():
    desc = str(row.get("description", ""))
    print(f"Title: {row.get('title')}")
    print("Requirements added by the job poster" in desc)
