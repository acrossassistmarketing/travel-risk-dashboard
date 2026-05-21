"""
fetch_advisories.py
Fetches travel advisory data from the US State Department API.
Returns a dict of {country_name: {level, summary}} for all tracked countries.
"""

import requests
import json
import time

STATE_DEPT_API = "https://travel.state.gov/content/travel/en/traveladvisories/traveladvisories.json/_jcr_content/data.json"

# Mapping for countries whose names differ between our list and State Dept
NAME_MAP = {
    "UAE": "United Arab Emirates",
    "USA": "United States",
    "UK": "United Kingdom",
    "South Korea": "Korea, South",
    "Czech Republic": "Czechia",
    "Hong Kong": "China - Hong Kong",
    "Macau": "China - Macau",
    "Taiwan": "Taiwan",
}

LEVEL_LABELS = {
    1: "Exercise Normal Precautions",
    2: "Exercise Increased Caution",
    3: "Reconsider Travel",
    4: "Do Not Travel",
}


def fetch_state_dept_advisories():
    """Fetch all advisories from US State Dept JSON feed."""
    print("Fetching US State Department advisories...")
    try:
        resp = requests.get(STATE_DEPT_API, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        advisories = {}
        for item in data.get("advisories", {}).values():
            name = item.get("name", "")
            level = item.get("level", 0)
            message = item.get("message", "")
            advisories[name.lower()] = {
                "level": int(level) if level else 0,
                "level_label": LEVEL_LABELS.get(int(level), "Unknown") if level else "Unknown",
                "summary": message[:500] if message else "",
                "source": "US State Department",
                "url": f"https://travel.state.gov/content/travel/en/traveladvisories/traveladvisories/{name.lower().replace(' ', '-')}.html"
            }
        print(f"  Fetched {len(advisories)} advisories from US State Dept")
        return advisories
    except Exception as e:
        print(f"  Error fetching State Dept data: {e}")
        return {}


def match_country(country_name, advisories_dict):
    """Try to find a country in the advisories dict using fuzzy matching."""
    # Direct lookup (normalised)
    search_name = NAME_MAP.get(country_name, country_name).lower()
    if search_name in advisories_dict:
        return advisories_dict[search_name]

    # Partial match fallback
    for key, val in advisories_dict.items():
        if search_name in key or key in search_name:
            return val

    return None


def get_advisories_for_countries(countries):
    """
    Given a list of {name, region} dicts, return enriched list
    with advisory data attached.
    """
    raw = fetch_state_dept_advisories()
    results = []

    for country in countries:
        name = country["name"]
        region = country["region"]
        match = match_country(name, raw)

        if match:
            results.append({
                "country": name,
                "region": region,
                "level": match["level"],
                "level_label": match["level_label"],
                "raw_summary": match["summary"],
                "source": match["source"],
                "url": match["url"],
            })
        else:
            # Country not found — will be handled by Claude classification
            results.append({
                "country": name,
                "region": region,
                "level": 0,
                "level_label": "Unknown",
                "raw_summary": "",
                "source": "Not found",
                "url": "",
            })
        time.sleep(0.05)  # be polite

    found = sum(1 for r in results if r["level"] > 0)
    print(f"  Matched {found}/{len(countries)} countries with advisory data")
    return results


if __name__ == "__main__":
    with open("countries.json") as f:
        data = json.load(f)
    results = get_advisories_for_countries(data["countries"])
    print(json.dumps(results[:3], indent=2))
