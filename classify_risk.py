"""
classify_risk.py
Uses Claude API with web_search tool to fetch LIVE travel advisory data.
Parallel batches of 5 with timeouts. Detects API balance exhaustion.
"""

import anthropic
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

SYSTEM_PROMPT = """You are a corporate travel risk analyst. For the country provided, 
search for the CURRENT US State Department travel advisory level and classify it.

Always respond with a valid JSON object and nothing else. No markdown, no backticks, no preamble.

Output format:
{
  "level": <1|2|3|4>,
  "level_label": "<Exercise Normal Precautions|Exercise Increased Caution|Reconsider Travel|Do Not Travel>",
  "overall_risk": "<Low|Moderate|High|Extreme>",
  "security": "<one specific sentence about current security situation>",
  "health": "<one specific sentence about health risks>",
  "crime": "<one specific sentence about crime situation>",
  "summary": "<2-3 sentence plain English summary for a corporate traveller>"
}

Risk mapping: Level 1=Low, Level 2=Moderate, Level 3=High, Level 4=Extreme.
Always base your classification on the web search results."""


# Raised when API balance is exhausted — stops the entire pipeline
class APIBalanceError(Exception):
    pass


def classify_one(args):
    """Classify a single country. Runs in a thread."""
    country, api_key = args
    name   = country["country"]
    region = country["region"]
    client = anthropic.Anthropic(api_key=api_key)

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=600,
            system=SYSTEM_PROMPT,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[{
                "role": "user",
                "content": f"Search and classify current US State Department travel advisory for: {name} ({region}). Return JSON only."
            }],
            timeout=25
        )

        text = ""
        for block in response.content:
            if block.type == "text":
                text = block.text.strip()

        # Strip markdown fences
        if "```" in text:
            for part in text.split("```"):
                if "{" in part:
                    text = part.replace("json", "").strip()
                    break

        # Extract JSON object
        start = text.find("{")
        end   = text.rfind("}") + 1
        if start >= 0 and end > start:
            text = text[start:end]

        classification = json.loads(text)

        # Validate level is a real number
        if not isinstance(classification.get("level"), int) or classification["level"] not in [1,2,3,4]:
            raise ValueError(f"Invalid level: {classification.get('level')}")

        return {**country, **classification}, None  # (result, error)

    except anthropic.AuthenticationError as e:
        return None, ("auth", str(e))
    except anthropic.PermissionDeniedError as e:
        return None, ("balance", str(e))
    except Exception as e:
        err_str = str(e).lower()
        # Detect balance/billing errors
        if any(x in err_str for x in ["credit", "balance", "billing", "quota", "rate_limit", "529", "overloaded"]):
            return None, ("balance", str(e))
        return {**country, **_fallback(name)}, None


def _fallback(name):
    return {
        "level": 2,
        "level_label": "Exercise Increased Caution",
        "overall_risk": "Moderate",
        "security": "Check latest US State Department advisory before travel.",
        "health": "Standard health precautions recommended.",
        "crime": "Exercise normal vigilance.",
        "summary": f"Live data unavailable. Please check travel.state.gov for {name}."
    }


def send_balance_alert(api_key_preview, error_msg):
    """Send email alert when API balance runs out."""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    sender       = os.environ.get("SENDER_EMAIL", "")
    recipients   = os.environ.get("RECIPIENT_EMAILS", "")
    app_password = os.environ.get("GMAIL_APP_PASSWORD", "")

    if not all([sender, recipients, app_password]):
        print("  ⚠ Cannot send alert — email credentials missing")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "⚠️ Travel Risk Report — API Balance Alert"
    msg["From"]    = f"Across Assist Travel Risk <{sender}>"
    msg["To"]      = recipients

    html = f"""
    <div style="font-family:Arial,sans-serif; max-width:500px; margin:0 auto; padding:24px;">
      <div style="background:#B71C1C; color:white; padding:20px; border-radius:8px 8px 0 0;">
        <h2 style="margin:0;">⚠️ Travel Risk Report Alert</h2>
      </div>
      <div style="background:#fff; border:1px solid #eee; padding:20px; border-radius:0 0 8px 8px;">
        <p style="color:#333;">The Travel Risk Report pipeline was <b>interrupted</b> because the Claude API balance is exhausted.</p>
        <p style="color:#333;">The report for today has <b>not been generated</b>.</p>
        <p style="color:#666; font-size:13px;">Error: {error_msg}</p>
        <p style="margin-top:20px;">
          <a href="https://console.anthropic.com" 
             style="background:#1a1a2e; color:white; padding:12px 24px; 
                    border-radius:6px; text-decoration:none; font-weight:600;">
            Top Up API Credits →
          </a>
        </p>
        <p style="font-size:12px; color:#999; margin-top:20px;">
          For internal use only — Across Assist Private Limited
        </p>
      </div>
    </div>"""

    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, app_password)
            server.sendmail(sender, recipients.split(","), msg.as_string())
        print("  ⚠ Balance alert email sent!")
    except Exception as e:
        print(f"  Could not send alert email: {e}")


def classify_all(countries_with_advisories):
    """Classify all countries in parallel batches of 5."""
    api_key = os.environ.get("API_KEY")
    if not api_key:
        raise ValueError("API_KEY environment variable not set!")

    print(f"  API key loaded: {api_key[:12]}...")
    print(f"  Classifying {len(countries_with_advisories)} countries (parallel batches of 5)...")

    results_map = {}
    args = [(c, api_key) for c in countries_with_advisories]
    BATCH_SIZE = 5

    for batch_start in range(0, len(args), BATCH_SIZE):
        batch = args[batch_start:batch_start + BATCH_SIZE]
        batch_num    = batch_start // BATCH_SIZE + 1
        total_batches = (len(args) + BATCH_SIZE - 1) // BATCH_SIZE
        names = [b[0]["country"] for b in batch]
        print(f"  Batch {batch_num}/{total_batches}: {names}")

        with ThreadPoolExecutor(max_workers=BATCH_SIZE) as executor:
            futures = {executor.submit(classify_one, arg): arg[0] for arg in batch}
            for future in as_completed(futures, timeout=45):
                country = futures[future]
                try:
                    result, error = future.result(timeout=40)

                    if error:
                        err_type, err_msg = error
                        if err_type == "balance":
                            print(f"\n  ❌ API BALANCE EXHAUSTED: {err_msg}")
                            print("  Sending alert email and stopping pipeline...")
                            send_balance_alert(api_key[:12], err_msg)
                            raise APIBalanceError(f"API balance exhausted: {err_msg}")
                        elif err_type == "auth":
                            raise RuntimeError(f"API authentication failed: {err_msg}")

                    level = result.get("level", "?")
                    risk  = result.get("overall_risk", "?")
                    print(f"      ✓ {country['country']} → Level {level} ({risk})")
                    results_map[country["country"]] = result

                except APIBalanceError:
                    raise  # stop everything
                except Exception as e:
                    print(f"      ⚠ {country['country']}: timeout — using fallback")
                    results_map[country["country"]] = {**country, **_fallback(country["country"])}

        time.sleep(1)

    results = [results_map.get(c["country"], {**c, **_fallback(c["country"])})
               for c in countries_with_advisories]

    print(f"  Classification complete!")
    return results
