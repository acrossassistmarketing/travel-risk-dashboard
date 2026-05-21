"""
classify_risk.py
Uses Claude API to classify each country's travel risk level.
"""

import anthropic
import json
import os
import time

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

Be specific and accurate per country. Examples:
- UAE: Level 1, very safe, low crime, good healthcare
- Afghanistan: Level 4, active armed conflict, do not travel under any circumstances
- Russia: Level 4, ongoing war with Ukraine, sanctions, do not travel
- Ukraine: Level 4, active war zone
- Mexico: Level 2 overall but Level 3 in northern states due to cartel violence
- France: Level 2, terrorism threat in major cities, generally safe
- Japan: Level 1, very safe, low crime, excellent healthcare
- Nigeria: Level 3, high crime, terrorism risk in north
- Pakistan: Level 3, terrorism and civil unrest
- Myanmar: Level 4, military coup, civil war

Use your knowledge of actual current advisory levels. Be country-specific always."""


def classify_all(countries_with_advisories):
    """Classify all countries using Claude API."""
    api_key = os.environ.get("API_KEY")
    if not api_key:
        raise ValueError("API_KEY environment variable not set!")

    client = anthropic.Anthropic(api_key=api_key)
    print(f"  API key loaded: {api_key[:12]}...")
    print(f"  Classifying {len(countries_with_advisories)} countries...")

    results = []
    for i, country in enumerate(countries_with_advisories):
        name   = country["country"]
        region = country["region"]
        print(f"  [{i+1}/{len(countries_with_advisories)}] {name}...")

        try:
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=400,
                system=SYSTEM_PROMPT,
                messages=[{
                    "role": "user",
                    "content": f"Classify travel risk for: {name} (Region: {region}). Provide US State Department advisory level and specific risk details for corporate travellers."
                }]
            )
            text = response.content[0].text.strip()

            # Strip accidental markdown fences
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()

            classification = json.loads(text)
            print(f"      → Level {classification.get('level')} ({classification.get('overall_risk')})")

        except json.JSONDecodeError as e:
            print(f"      ⚠ JSON parse error: {e} — using fallback")
            classification = _fallback(name)
        except anthropic.AuthenticationError as e:
            raise RuntimeError(f"API authentication failed — check your API_KEY secret: {e}")
        except Exception as e:
            print(f"      ⚠ API error: {e} — using fallback")
            classification = _fallback(name)

        results.append({**country, **classification})
        time.sleep(0.5)

    print(f"  Classification complete!")
    return results


def _fallback(name):
    return {
        "level": 2,
        "level_label": "Exercise Increased Caution",
        "overall_risk": "Moderate",
        "security": "Check latest US State Department advisory before travel.",
        "health": "Standard health precautions recommended.",
        "crime": "Exercise normal vigilance.",
        "summary": f"Please check the latest US State Department advisory for {name} before travel."
    }


if __name__ == "__main__":
    sample = [
        {"country": "UAE", "region": "Middle East", "level": 0, "level_label": "", "raw_summary": ""},
        {"country": "Afghanistan", "region": "South Asia", "level": 0, "level_label": "", "raw_summary": ""},
        {"country": "Japan", "region": "East Asia", "level": 0, "level_label": "", "raw_summary": ""},
        {"country": "Russia", "region": "Europe", "level": 0, "level_label": "", "raw_summary": ""},
    ]
    results = classify_all(sample)
    print(json.dumps(results, indent=2))
