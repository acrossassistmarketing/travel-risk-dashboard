"""
classify_risk.py
Uses Claude API with web_search tool to fetch LIVE travel advisory data
for each country from the US State Department and classify risk levels.
"""

import anthropic
import json
import os
import time

SYSTEM_PROMPT = """You are a corporate travel risk analyst. For each country provided, 
use the web_search tool to find the CURRENT US State Department travel advisory level.

Search for: "US State Department travel advisory [country name] 2025 level"

Based on the search results, classify using the official US State Department Level 1-4 system.

Always respond with a valid JSON object and nothing else. No markdown, no backticks, no preamble.

Output format:
{
  "level": <1|2|3|4>,
  "level_label": "<Exercise Normal Precautions|Exercise Increased Caution|Reconsider Travel|Do Not Travel>",
  "overall_risk": "<Low|Moderate|High|Extreme>",
  "security": "<one specific sentence about current security situation based on search results>",
  "health": "<one specific sentence about health risks based on search results>",
  "crime": "<one specific sentence about crime situation based on search results>",
  "summary": "<2-3 sentence plain English summary for a corporate traveller based on latest advisory>"
}

Risk mapping: Level 1=Low, Level 2=Moderate, Level 3=High, Level 4=Extreme.
Always base your answer on the search results, not prior knowledge."""


def classify_all(countries_with_advisories):
    """Classify all countries using Claude API with live web search."""
    api_key = os.environ.get("API_KEY")
    if not api_key:
        raise ValueError("API_KEY environment variable not set!")

    client = anthropic.Anthropic(api_key=api_key)
    print(f"  API key loaded: {api_key[:12]}...")
    print(f"  Classifying {len(countries_with_advisories)} countries with live web search...")

    results = []
    for i, country in enumerate(countries_with_advisories):
        name   = country["country"]
        region = country["region"]
        print(f"  [{i+1}/{len(countries_with_advisories)}] {name}...")

        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1000,
                system=SYSTEM_PROMPT,
                tools=[{
                    "type": "web_search_20250305",
                    "name": "web_search"
                }],
                messages=[{
                    "role": "user",
                    "content": f"Search for and classify the current US State Department travel advisory for: {name} (Region: {region}). Return JSON only."
                }]
            )

            # Extract the final text response (after tool use)
            text = ""
            for block in response.content:
                if block.type == "text":
                    text = block.text.strip()

            # Strip accidental markdown fences
            if "```" in text:
                parts = text.split("```")
                for part in parts:
                    if part.startswith("json"):
                        text = part[4:].strip()
                        break
                    elif "{" in part:
                        text = part.strip()
                        break

            # Find JSON object in text
            start = text.find("{")
            end   = text.rfind("}") + 1
            if start >= 0 and end > start:
                text = text[start:end]

            classification = json.loads(text)
            print(f"      → Level {classification.get('level')} ({classification.get('overall_risk')})")

        except json.JSONDecodeError as e:
            print(f"      ⚠ JSON parse error: {e} — using fallback")
            classification = _fallback(name)
        except anthropic.AuthenticationError as e:
            raise RuntimeError(f"API authentication failed: {e}")
        except Exception as e:
            print(f"      ⚠ API error: {type(e).__name__}: {e} — using fallback")
            classification = _fallback(name)

        results.append({**country, **classification})
        time.sleep(1)  # be polite, avoid rate limiting

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
        "summary": f"Live data unavailable. Please check travel.state.gov for {name}."
    }


if __name__ == "__main__":
    sample = [
        {"country": "UAE", "region": "Middle East", "level": 0, "level_label": "", "raw_summary": ""},
        {"country": "Afghanistan", "region": "South Asia", "level": 0, "level_label": "", "raw_summary": ""},
        {"country": "Japan", "region": "East Asia", "level": 0, "level_label": "", "raw_summary": ""},
    ]
    results = classify_all(sample)
    print(json.dumps(results, indent=2))
