"""
main.py
Orchestrates the full travel risk report pipeline:
1. Load country list
2. Fetch advisories from US State Dept
3. Classify via Claude API
4. Generate PDF report
5. Generate web dashboard
6. Send email
7. Save classified data for GitHub Pages
"""

import json
import os
from datetime import datetime

from fetch_advisories import get_advisories_for_countries
from classify_risk import classify_all
from generate_pdf import generate_pdf
from generate_dashboard import generate_dashboard
from send_email import send_report


def run():
    print("=" * 55)
    print("  Across Assist — Travel Risk Report Pipeline")
    print(f"  {datetime.now().strftime('%d %B %Y, %I:%M %p')}")
    print("=" * 55)

    # 1. Load country list
    print("\n[1/6] Loading country list...")
    with open("countries.json") as f:
        data = json.load(f)
    countries = data["countries"]
    print(f"  Loaded {len(countries)} countries")

    # 2. Fetch advisories
    print("\n[2/6] Fetching travel advisories...")
    countries_with_advisories = get_advisories_for_countries(countries)

    # 3. Classify with Claude
    print("\n[3/6] Classifying risk levels via Claude API...")
    classified = classify_all(countries_with_advisories)

    # Save classified data (used by dashboard & email)
    os.makedirs("docs", exist_ok=True)
    with open("docs/data.json", "w") as f:
        json.dump(classified, f, indent=2)
    print(f"  Saved classified data for {len(classified)} countries")

    # 4. Generate PDF
    print("\n[4/6] Generating PDF report...")
    pdf_path = generate_pdf(classified, "travel_risk_report.pdf")

    # 5. Generate dashboard
    print("\n[5/6] Generating web dashboard...")
    generate_dashboard(classified, "docs/index.html")

    # 6. Send email
    print("\n[6/6] Sending email...")
    send_report(pdf_path, classified)

    print("\n" + "=" * 55)
    print("  Pipeline complete!")
    print("=" * 55)


if __name__ == "__main__":
    run()
