from jobspy import scrape_jobs
import json
try:
    df = scrape_jobs(
        site_name=['linkedin', 'indeed'], 
        search_term='software engineer', 
        location='United States', 
        results_wanted=10, 
        linkedin_fetch_description=True
    )
    jobs = df.to_dict('records')
    res = []
    for j in jobs:
        res.append({'title': j.get('title'), 'desc': str(j.get('description'))})
    with open('jobs_test_data.json', 'w', encoding='utf-8') as f:
        json.dump(res, f, indent=2)
except Exception as e:
    print(f"Error scraping: {e}")
