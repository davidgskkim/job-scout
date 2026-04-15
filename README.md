# 🚀 Job Scout

An automated job alert pipeline that delivers fresh entry-level SWE and AI roles straight to your Gmail — within an hour of posting, for free.

## How It Works

Every hour, GitHub Actions runs the pipeline:

1. **Fetch** — pulls jobs from LinkedIn, Indeed, Glassdoor (via `jobspy`), Indeed RSS feeds, and 100+ company ATS boards (Greenhouse, Lever, Ashby)
2. **Deduplicate** — checks Supabase to skip jobs you've already seen
3. **Tier 1 Filter** — fast regex checks: correct role type, no senior/QA/mobile/DevOps, no 3+ YOE requirements, valid location
4. **Tier 2 Filter** — Gemini Flash LLM confirms it's genuinely 0-2 YOE and relevant
5. **Email** — one clean HTML email per job lands in your Gmail, auto-labelled by `email_sort`

**Total cost: $0/month.**

---

## Setup

### 1. Clone & Install

```bash
git clone https://github.com/YOUR_USERNAME/job_scout.git
cd job_scout
pip install -r requirements.txt
```

### 2. Supabase (Free Database)

1. Create a free project at [supabase.com](https://supabase.com)
2. Go to **SQL Editor** and run:

```sql
CREATE TABLE seen_jobs (
  job_id      TEXT PRIMARY KEY,
  source      TEXT,
  title       TEXT,
  company     TEXT,
  url         TEXT,
  discovered_at TIMESTAMPTZ DEFAULT NOW()
);
```

3. Copy your **Project URL** and **anon public key** from Settings → API

### 3. Gmail App Password

1. Enable 2-Factor Authentication on your Google account
2. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. Create an App Password for "Mail"
4. Save the 16-character password

### 4. Gemini API Key

1. Go to [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Create a free API key (Gemini Flash is on the free tier)

### 5. Environment Variables

```bash
cp .env.example .env
# Fill in all values in .env
```

### 6. Test Locally

```bash
python main.py
```

You should see logs and receive a test email if any new relevant jobs are found.

---

## Deploy to GitHub Actions

1. Push this repo to GitHub
2. Go to **Settings → Secrets and variables → Actions**
3. Add these secrets:

| Secret | Value |
|---|---|
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_KEY` | Your Supabase anon key |
| `GEMINI_API_KEY` | Your Gemini API key |
| `GMAIL_USER` | your@gmail.com |
| `GMAIL_APP_PASSWORD` | 16-char app password |
| `TO_EMAIL` | Where to send alerts (usually same as above) |

4. The workflow in `.github/workflows/scout.yml` will automatically run every hour.
5. You can also trigger it manually from the **Actions** tab → **Job Scout** → **Run workflow**

---

## Customization

### Add More Companies (ATS)
Edit `data/companies.json` to add company board slugs:
- **Greenhouse**: Find the slug at `boards.greenhouse.io/{slug}`
- **Lever**: Find the slug at `jobs.lever.co/{slug}`
- **Ashby**: Find the slug at `jobs.ashbyhq.com/{slug}`

### Adjust Filters
- **Tier 1** — Edit patterns in `filters/tier1.py`
- **Tier 2** — Edit the prompt in `filters/tier2.py`

### Change Polling Interval
Edit the cron expression in `.github/workflows/scout.yml`:
```yaml
- cron: "0 * * * *"   # every hour (current)
- cron: "*/30 * * * *" # every 30 minutes
```

---

## Project Structure

```
job_scout/
├── .github/workflows/scout.yml   # GitHub Actions cron job
├── data/companies.json           # ATS company slug lists
├── fetchers/
│   ├── jobspy_fetcher.py         # LinkedIn + Indeed + Glassdoor
│   ├── rss_fetcher.py            # Indeed RSS feeds
│   └── ats_fetcher.py            # Greenhouse / Lever / Ashby
├── filters/
│   ├── tier1.py                  # Hard regex filters
│   └── tier2.py                  # Gemini Flash LLM filter
├── notify/
│   └── email_sender.py           # Gmail SMTP, HTML email
├── db.py                         # Supabase deduplication
├── main.py                       # Orchestrator
└── requirements.txt
```
