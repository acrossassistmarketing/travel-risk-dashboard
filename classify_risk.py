"""
classify_risk.py
Uses Claude API to classify/enrich each country's risk level with
simple human-readable reasoning across security, health, and crime dimensions.
"""

import anthropic
import json
import time

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

SYSTEM_PROMPT = """You are a corporate travel risk analyst. Given a country name and its 
US State Department travel advisory level and summary, produce a concise risk classification 
for corporate travel advisory purposes.

Always respond with a valid JSON object and nothing else. No markdown, no backticks, no preamble.

Output format:
{
  "level": <1|2|3|4>,
  "level_label": "<Exercise Normal Precautions|Exercise Increased Caution|Reconsider Travel|Do Not Travel>",
  "overall_risk": "<Low|Moderate|High|Extreme>",
  "security": "<one sentence max>",
  "health": "<one sentence max>",
  "crime": "<one sentence max>",
  "summary": "<2-3 sentence plain English summary for a corporate traveller>"
}

Risk mapping: Level 1 = Low, Level 2 = Moderate, Level 3 = High, Level 4 = Extreme.
If advisory data is missing, use your knowledge to make a best-effort classification.
Keep all text concise and factual. Avoid alarmist language."""


def classify_country(country_data):
    """Call Claude API to enrich a single country's risk data."""
    name = country_data["country"]
    level = country_data["level"]
    label = country_data["level_label"]
    summary = country_data["raw_summary"]

    user_message = f"""Country: {name}
US State Dept Level: {level} — {label}
Advisory summary: {summary if summary else "No advisory text available."}

Classify this country's travel risk for corporate travellers."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=400,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}]
        )
        text = response.content[0].text.strip()
        result = json.loads(text)

        # Ensure level from State Dept takes precedence if available
        if level and level > 0:
            result["level"] = level
            result["level_label"] = label

        return result

    except json.JSONDecodeError as e:
        print(f"  JSON parse error for {name}: {e}")
        return _fallback_classification(level, label)
    except Exception as e:
        print(f"  API error for {name}: {e}")
        return _fallback_classification(level, label)


def _fallback_classification(level, label):
    overall_map = {1: "Low", 2: "Moderate", 3: "High", 4: "Extreme"}
    return {
        "level": level or 2,
        "level_label": label or "Exercise Increased Caution",
        "overall_risk": overall_map.get(level, "Moderate"),
        "security": "Refer to latest US State Department advisory.",
        "health": "Standard health precautions recommended.",
        "crime": "Exercise normal vigilance.",
        "summary": "Advisory data unavailable. Please check travel.state.gov for the latest information."
    }


def classify_all(countries_with_advisories):
    """Classify all countries, returns enriched list."""
    print(f"Classifying {len(countries_with_advisories)} countries via Claude API...")
    results = []

    for i, country in enumerate(countries_with_advisories):
        print(f"  [{i+1}/{len(countries_with_advisories)}] {country['country']}...")
        classification = classify_country(country)
        enriched = {**country, **classification}
        results.append(enriched)
        time.sleep(0.3)  # avoid rate limiting

    print(f"  Classification complete.")
    return results


if __name__ == "__main__":
    sample = [
        {"country": "France", "region": "Europe", "level": 2,
         "level_label": "Exercise Increased Caution",
         "raw_summary": "Exercise increased caution due to terrorism.", "source": "US State Dept", "url": ""},
        {"country": "Afghanistan", "region": "South Asia", "level": 4,
         "level_label": "Do Not Travel",
         "raw_summary": "Do not travel due to terrorism, kidnapping, civil unrest.", "source": "US State Dept", "url": ""},
    ]
    results = classify_all(sample)
    print(json.dumps(results, indent=2))
