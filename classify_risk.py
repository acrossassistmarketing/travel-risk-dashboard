"""
classify_risk.py
Uses Claude API to classify each country's travel risk level
based on its knowledge of US State Department advisory levels.
"""

import anthropic
import json
import os
import time

client = anthropic.Anthropic(api_key=os.environ["API_KEY"])

SYSTEM_PROMPT = """You are a corporate travel risk analyst with expert knowledge of 
US State Department travel advisories. Classify each country using the official 
US State Department Level 1-4 system based on your knowledge of current advisories.

Always respond with a valid JSON object and nothing else. No markdown, no backticks, no preamble.

Output format:
{
  "level": <1|2|3|4>,
  "level_label": "<Exercise Normal Precautions|Exercise Increased Caution|Reconsider Travel|Do Not Travel>",
  "overall_risk": "<Low|Moderate|High|Extreme>",
  "security": "<one specific sentence about current security situation>",
  "health": "<one specific sentence about health risks or requirements>",
  "crime": "<one specific sentence about crime situation>",
  "summary": "<2-3 sentence plain English summary for a corporate traveller, specific to this country>"
}

Risk mapping: Level 1=Low, Level 2=Moderate, Level 3=High, Level 4=Extreme.

Be specific and accurate per country. For example:
- UAE: Level 1, low crime, safe for business travel
- Afghanistan: Level 4, active conflict, do not travel
- Mexico: Level 2-3 depending on region, cartel violence concern
- Russia: Level 4, war with Ukraine, do not travel
- France: Level 2, terrorism risk in major cities
Use your knowledge of actual current advisory levels. Do NOT give generic responses."""


def classify_country(country_data):
    """Call Claude API to classify a single country."""
    name = country_data["country"]
    region = country_data["region"]

    user_message = f"""Classify travel risk for: {name} (Region: {region})
    
Provide the current US State Department advisory level and specific risk details for corporate travellers."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=400,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}]
        )
        text = response.content[0].text.strip()
        # Strip any accidental markdown
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        result = json.loads(text.strip())
        return result

    except json.JSONDecodeError as e:
        print(f"  JSON parse error for {name}: {e}")
        return _fallback_classification(name)
    except Exception as e:
        print(f"  API error for {name}: {e}")
        return _fallback_classification(name)


def _fallback_classification(name):
    return {
        "level": 2,
        "level_label": "Exercise Increased Caution",
        "overall_risk": "Moderate",
        "security": "Check latest US State Department advisory before travel.",
        "health": "Standard health precautions recommended.",
        "crime": "Exercise normal vigilance.",
        "summary": f"Please check the latest US State Department advisory for {name} before travel."
    }


def classify_all(countries_with_advisories):
    """Classify all countries, returns enriched list."""
    print(f"  Classifying {len(countries_with_advisories)} countries via Claude API...")
    results = []

    for i, country in enumerate(countries_with_advisories):
        print(f"  [{i+1}/{len(countries_with_advisories)}] {country['country']}...")
        classification = classify_country(country)
        enriched = {**country, **classification}
        results.append(enriched)
        time.sleep(0.5)  # avoid rate limiting

    print(f"  Classification complete.")
    return results


if __name__ == "__main__":
    sample = [
        {"country": "UAE", "region": "Middle East", "level": 0, "level_label": "", "raw_summary": ""},
        {"country": "Afghanistan", "region": "South Asia", "level": 0, "level_label": "", "raw_summary": ""},
        {"country": "France", "region": "Europe", "level": 0, "level_label": "", "raw_summary": ""},
    ]
    results = classify_all(sample)
    print(json.dumps(results, indent=2))
