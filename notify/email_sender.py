"""
email_sender.py

Sends one clean HTML email per relevant job via Gmail SMTP.
Each email is self-contained: job title, company, location, salary,
Gemini's reason for relevance, and a direct "Apply Now" link.

Gmail setup required:
  1. Enable 2FA on your Google account
  2. Generate an App Password at: https://myaccount.google.com/apppasswords
  3. Set GMAIL_USER and GMAIL_APP_PASSWORD in your .env / GitHub secrets
"""

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

GMAIL_USER = os.environ.get("GMAIL_USER", "").strip()
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "").strip()
TO_EMAIL = os.environ.get("TO_EMAIL", GMAIL_USER).strip()

# Source → display label + colour
SOURCE_META: dict[str, dict] = {
    "linkedin":    {"label": "LinkedIn",    "color": "#0A66C2"},
    "indeed":      {"label": "Indeed",      "color": "#2164F3"},
    "indeed_us":   {"label": "Indeed",      "color": "#2164F3"},
    "indeed_ca":   {"label": "Indeed",      "color": "#2164F3"},
    "glassdoor":   {"label": "Glassdoor",   "color": "#0CAA41"},
    "greenhouse":  {"label": "Greenhouse",  "color": "#24A147"},
    "lever":       {"label": "Lever",       "color": "#5855D6"},
    "ashby":       {"label": "Ashby",       "color": "#F97316"},
}

DEFAULT_SOURCE_META = {"label": "Job Board", "color": "#6B7280"}


def _build_html(job: dict, reason: str) -> str:
    title = job.get("title", "Unknown Title")
    company = job.get("company", "Unknown Company")
    location = job.get("location") or "Location not specified"
    url = job.get("url", "#")
    salary = job.get("salary") or "Not listed"
    date_posted = job.get("date_posted") or ""
    source = (job.get("source") or "").lower()
    src = SOURCE_META.get(source, DEFAULT_SOURCE_META)

    date_line = f"<span>🗓 {date_posted}</span>" if date_posted else ""
    reason_block = (
        f"""
        <div style="background:#f0fdf4;border-left:4px solid #22c55e;
                    border-radius:4px;padding:12px 16px;margin-bottom:22px;">
          <p style="margin:0;font-size:13px;color:#15803d;line-height:1.5;">
            <strong>✅ Why this was flagged:</strong> {reason}
          </p>
        </div>"""
        if reason else ""
    )

    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>New Job: {title}</title>
</head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f3f4f6;padding:32px 16px;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0"
             style="background:#ffffff;border-radius:16px;overflow:hidden;
                    box-shadow:0 4px 24px rgba(0,0,0,0.08);max-width:600px;">

        <!-- Header bar -->
        <tr>
          <td style="background:linear-gradient(135deg,#1e293b 0%,#334155 100%);
                     padding:28px 32px;">
            <p style="margin:0 0 8px 0;font-size:11px;font-weight:700;
                      letter-spacing:2px;color:#94a3b8;text-transform:uppercase;">
              🚀 New Job Alert
            </p>
            <h1 style="margin:0;font-size:22px;font-weight:700;color:#f8fafc;
                       line-height:1.3;">
              {title}
            </h1>
            <p style="margin:8px 0 0;font-size:16px;color:#cbd5e1;font-weight:500;">
              {company}
            </p>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="padding:28px 32px;">

            <!-- Source badge -->
            <div style="margin-bottom:20px;">
              <span style="display:inline-block;background:{src['color']}18;
                           color:{src['color']};border:1px solid {src['color']}40;
                           padding:4px 12px;border-radius:20px;font-size:12px;
                           font-weight:700;letter-spacing:0.5px;">
                {src['label']}
              </span>
            </div>

            <!-- Meta grid -->
            <table width="100%" cellpadding="0" cellspacing="0"
                   style="background:#f8fafc;border-radius:10px;
                          padding:16px 20px;margin-bottom:22px;">
              <tr>
                <td style="padding:6px 0;">
                  <span style="font-size:13px;color:#64748b;">📍 Location</span><br/>
                  <span style="font-size:15px;color:#1e293b;font-weight:600;">{location}</span>
                </td>
                <td style="padding:6px 0;">
                  <span style="font-size:13px;color:#64748b;">💰 Salary</span><br/>
                  <span style="font-size:15px;color:#1e293b;font-weight:600;">{salary}</span>
                </td>
                {f'<td style="padding:6px 0;"><span style="font-size:13px;color:#64748b;">🗓 Posted</span><br/><span style="font-size:15px;color:#1e293b;font-weight:600;">{date_posted}</span></td>' if date_posted else ''}
              </tr>
            </table>

            <!-- Gemini reason -->
            {reason_block}

            <!-- CTA -->
            <a href="{url}"
               style="display:inline-block;background:linear-gradient(135deg,#2563eb,#4f46e5);
                      color:#ffffff;text-decoration:none;font-size:15px;font-weight:700;
                      padding:14px 32px;border-radius:10px;letter-spacing:0.3px;">
              Apply Now →
            </a>

            <!-- URL for copy-paste -->
            <p style="margin:16px 0 0;font-size:11px;color:#94a3b8;word-break:break-all;">
              {url}
            </p>

          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="background:#f8fafc;padding:16px 32px;
                     border-top:1px solid #e2e8f0;">
            <p style="margin:0;font-size:11px;color:#94a3b8;text-align:center;">
              Sent by <strong>Job Scout</strong> • Apply early, apply often.
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


def send_job_email(job: dict, reason: str = "") -> None:
    """Send a single job alert email via Gmail SMTP."""
    title = job.get("title", "Unknown Title")
    company = job.get("company", "Unknown Company")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🚀 {title} @ {company}"
    msg["From"] = f"Job Scout <{GMAIL_USER}>"
    msg["To"] = TO_EMAIL

    # Plain text fallback
    plain = (
        f"New Job: {title}\n"
        f"Company: {company}\n"
        f"Location: {job.get('location', '')}\n"
        f"Salary: {job.get('salary') or 'Not listed'}\n"
        f"Apply: {job.get('url', '')}\n"
        f"\nWhy flagged: {reason}"
    )
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(_build_html(job, reason), "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, TO_EMAIL, msg.as_string())

    logger.info(f"[email] Sent: '{title}' @ {company}")
