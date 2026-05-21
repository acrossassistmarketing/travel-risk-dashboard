"""
send_email.py
Sends the travel risk report PDF and dashboard link via Gmail SMTP.
Reads credentials from environment variables (set via GitHub Secrets).
"""

import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime


DASHBOARD_URL = "https://{MY_GITHUB_USERNAME}.github.io/travel-risk-dashboard"


def build_email_html(date_str, stats, dashboard_url):
    level_colors = {1: "#2E7D32", 2: "#F57F17", 3: "#E65100", 4: "#B71C1C"}
    level_bg = {1: "#E8F5E9", 2: "#FFF8E1", 3: "#FBE9E7", 4: "#FFEBEE"}
    level_names = {1: "Low Risk", 2: "Moderate Risk", 3: "High Risk", 4: "Extreme Risk"}

    stat_cells = "".join([
        f"""<td style="text-align:center; padding:12px 16px; background:{level_bg[l]};
            border-radius:8px; margin:4px;">
          <div style="font-size:26px; font-weight:700; color:{level_colors[l]};">{stats.get(l,0)}</div>
          <div style="font-size:11px; color:#666; margin-top:2px;">Level {l} — {level_names[l]}</div>
        </td>"""
        for l in [1, 2, 3, 4]
    ])

    return f"""
    <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
                max-width:600px; margin:0 auto; background:#f0f2f5; padding:24px;">
      <div style="background:#1a1a2e; border-radius:12px 12px 0 0; padding:24px 32px; color:white;">
        <h1 style="margin:0; font-size:20px; font-weight:700;">Across Assist</h1>
        <p style="margin:4px 0 0; font-size:13px; color:#aab;">Travel Risk Advisory Report</p>
      </div>
      <div style="background:white; padding:28px 32px; border-radius:0 0 12px 12px;">
        <p style="font-size:14px; color:#444; margin-bottom:20px;">
          Your travel risk report has been updated. Here's a summary of the latest classifications:
        </p>
        <table width="100%" cellspacing="6" cellpadding="0" style="border-collapse:separate;">
          <tr>{stat_cells}</tr>
        </table>
        <div style="margin:24px 0; text-align:center;">
          <a href="{dashboard_url}"
             style="background:#1a1a2e; color:white; padding:12px 28px; border-radius:8px;
                    text-decoration:none; font-size:14px; font-weight:600; display:inline-block;">
            View Live Dashboard →
          </a>
        </div>
        <p style="font-size:12px; color:#999; border-top:1px solid #eee; padding-top:14px; margin:0;">
          The full PDF report is attached to this email.<br/>
          Last updated: {date_str} · Source: US State Department<br/>
          For internal use only — Across Assist Private Limited
        </p>
      </div>
    </div>
    """


def send_report(pdf_path, classified_data):
    """Send the report email with PDF attachment."""
    sender = os.environ["SENDER_EMAIL"]
    recipients_raw = os.environ["RECIPIENT_EMAILS"]
    app_password = os.environ["GMAIL_APP_PASSWORD"]
    github_username = os.environ.get("MY_GITHUB_USERNAME", "YOUR_USERNAME")

    recipients = [r.strip() for r in recipients_raw.split(",") if r.strip()]
    dashboard_url = DASHBOARD_URL.replace("{MY_GITHUB_USERNAME}", github_username)

    now = datetime.now()
    date_str = now.strftime("%d %B %Y, %I:%M %p IST")
    subject = f"Travel Risk Advisory Report — {now.strftime('%d %b %Y')}"

    # Build stats summary
    stats = {}
    for c in classified_data:
        l = c.get("level", 2)
        stats[l] = stats.get(l, 0) + 1

    # Build email
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Across Assist Travel Risk <{sender}>"
    msg["To"] = ", ".join(recipients)

    html_body = build_email_html(date_str, stats, dashboard_url)
    msg.attach(MIMEText(html_body, "html"))

    # Attach PDF
    if pdf_path and os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        filename = f"Travel_Risk_Report_{now.strftime('%Y%m%d')}.pdf"
        part.add_header("Content-Disposition", f"attachment; filename={filename}")
        msg.attach(part)

    # Send via Gmail SMTP
    print(f"Sending email to: {', '.join(recipients)}")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, app_password)
        server.sendmail(sender, recipients, msg.as_string())

    print("Email sent successfully!")


if __name__ == "__main__":
    import json
    with open("classified_data.json") as f:
        data = json.load(f)
    send_report("travel_risk_report.pdf", data)
