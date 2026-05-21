"""
send_email.py
Sends travel risk report via Gmail SMTP with mobile-optimised email.
"""

import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

DASHBOARD_URL = "https://{MY_GITHUB_USERNAME}.github.io/travel-risk-dashboard"

LEVEL_COLORS = {1: "#2E7D32", 2: "#F57F17", 3: "#E65100", 4: "#B71C1C"}
LEVEL_BG     = {1: "#E8F5E9", 2: "#FFF8E1", 3: "#FBE9E7", 4: "#FFEBEE"}
LEVEL_NAMES  = {1: "Low Risk", 2: "Moderate Risk", 3: "High Risk", 4: "Extreme Risk"}


def build_email_html(date_str, stats, dashboard_url):
    # Build stat rows as a single-column stacked table for mobile compatibility
    stat_rows = ""
    for l in [1, 2, 3, 4]:
        count = stats.get(l, 0)
        stat_rows += f"""
        <tr>
          <td align="center" style="padding:8px 0;">
            <table width="100%" cellpadding="0" cellspacing="0" border="0"
                   style="background:{LEVEL_BG[l]}; border-radius:8px; border-left:4px solid {LEVEL_COLORS[l]};">
              <tr>
                <td style="padding:12px 16px;">
                  <span style="font-size:28px; font-weight:700; color:{LEVEL_COLORS[l]}; font-family:Arial,sans-serif;">{count}</span>
                  <span style="font-size:13px; color:#555; font-family:Arial,sans-serif; margin-left:10px;">Level {l} — {LEVEL_NAMES[l]}</span>
                </td>
              </tr>
            </table>
          </td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <meta http-equiv="X-UA-Compatible" content="IE=edge"/>
  <title>Travel Risk Advisory Report</title>
</head>
<body style="margin:0; padding:0; background-color:#f0f2f5; font-family:Arial,Helvetica,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f0f2f5;">
    <tr>
      <td align="center" style="padding:24px 16px;">

        <!-- Main container -->
        <table width="100%" cellpadding="0" cellspacing="0" border="0"
               style="max-width:560px; background:#ffffff; border-radius:12px;
                      overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,0.08);">

          <!-- Header -->
          <tr>
            <td style="background:#1a1a2e; padding:24px 28px;">
              <p style="margin:0; font-size:22px; font-weight:700;
                        color:#ffffff; font-family:Arial,sans-serif;">Across Assist</p>
              <p style="margin:6px 0 0; font-size:13px; color:#aabbcc;
                        font-family:Arial,sans-serif;">Travel Risk Advisory Report</p>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:24px 28px;">
              <p style="margin:0 0 20px; font-size:14px; color:#444444;
                        font-family:Arial,sans-serif; line-height:1.6;">
                Your travel risk report has been updated. Here's a summary of the latest classifications:
              </p>

              <!-- Stats — stacked rows, mobile friendly -->
              <table width="100%" cellpadding="0" cellspacing="0" border="0">
                {stat_rows}
              </table>

              <!-- CTA Button -->
              <table width="100%" cellpadding="0" cellspacing="0" border="0"
                     style="margin-top:24px;">
                <tr>
                  <td align="center">
                    <a href="{dashboard_url}"
                       style="display:inline-block; background:#1a1a2e; color:#ffffff;
                              padding:14px 32px; border-radius:8px; text-decoration:none;
                              font-size:15px; font-weight:600; font-family:Arial,sans-serif;">
                      View Live Dashboard →
                    </a>
                  </td>
                </tr>
              </table>

              <!-- Footer note -->
              <table width="100%" cellpadding="0" cellspacing="0" border="0"
                     style="margin-top:24px; border-top:1px solid #eeeeee;">
                <tr>
                  <td style="padding-top:16px;">
                    <p style="margin:0; font-size:12px; color:#999999;
                               font-family:Arial,sans-serif; line-height:1.7;">
                      The full PDF report is attached to this email.<br/>
                      Last updated: {date_str}<br/>
                      Source: US State Department<br/>
                      For internal use only — Across Assist Private Limited
                    </p>
                  </td>
                </tr>
              </table>

            </td>
          </tr>
        </table>
        <!-- End main container -->

      </td>
    </tr>
  </table>
</body>
</html>"""


def send_report(pdf_path, classified_data):
    sender        = os.environ["SENDER_EMAIL"]
    recipients_raw= os.environ["RECIPIENT_EMAILS"]
    app_password  = os.environ["GMAIL_APP_PASSWORD"]
    github_username = os.environ.get("MY_GITHUB_USERNAME", "YOUR_USERNAME")

    recipients    = [r.strip() for r in recipients_raw.split(",") if r.strip()]
    dashboard_url = DASHBOARD_URL.replace("{MY_GITHUB_USERNAME}", github_username)

    now      = datetime.now()
    date_str = now.strftime("%d %B %Y, %I:%M %p IST")
    subject  = f"Travel Risk Advisory Report — {now.strftime('%d %b %Y')}"

    stats = {}
    for c in classified_data:
        l = c.get("level", 2)
        stats[l] = stats.get(l, 0) + 1

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"Across Assist Travel Risk <{sender}>"
    msg["To"]      = ", ".join(recipients)

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

    print(f"  Sending email to: {', '.join(recipients)}")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, app_password)
        server.sendmail(sender, recipients, msg.as_string())
    print("  Email sent successfully!")


if __name__ == "__main__":
    import json
    with open("classified_data.json") as f:
        data = json.load(f)
    send_report("travel_risk_report.pdf", data)
