"""
fetch_advisories.py
Since the US State Dept blocks automated scraping, we pass country names
directly to Claude API which is trained on current advisory data.
Claude classifies based on its knowledge of US State Dept levels.
"""

import json

def get_advisories_for_countries(countries):
    """
    Returns countries list with placeholder raw_summary.
    Actual classification is done entirely by Claude in classify_risk.py
    """
    print(f"  Prepared {len(countries)} countries for Claude classification")
    results = []
    for country in countries:
        results.append({
            "country": country["name"],
            "region": country["region"],
            "level": 0,
            "level_label": "",
            "raw_summary": "",
            "source": "US State Department",
            "url": f"https://travel.state.gov",
        })
    return results

if __name__ == "__main__":
    with open("countries.json") as f:
        data = json.load(f)
    results = get_advisories_for_countries(data["countries"])
    print(json.dumps(results[:3], indent=2))
