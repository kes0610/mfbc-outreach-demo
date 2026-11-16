"""Generate clearly-labeled synthetic outreach data for the public repo.

This is fake data with a plausible-looking reply pattern, meant only so
someone cloning the repo can run the app and the model without needing
MFBC's real outreach history. Run it, then import the CSV from the
Outreach History page's "Import CSV / Excel" tab.

    python seed_synthetic.py
"""

import random
from datetime import date, timedelta

import pandas as pd

random.seed(7)

COMPANIES = [
    ("Fortune 500 Retailer", "low"),
    ("Regional Boutique Chain", "high"),
    ("UW Alumni Fashion Startup", "high"),
    ("National Denim Brand", "low"),
    ("Local Design Studio", "high"),
    ("Luxury Accessories House", "low"),
    ("Sustainable Apparel Co", "medium"),
    ("Campus-Area Boutique", "high"),
    ("Big Box Department Store", "low"),
    ("Independent Jewelry Designer", "high"),
]
ROLES = ["Marketing Manager", "Founder/Owner", "Brand Partnerships", "PR Coordinator", "CEO"]
ASK_TYPES = ["sponsorship", "speaker", "partnership", "other"]
SENDERS = ["Avery", "Jordan", "Sam", "Priya", "Kiera"]

N = 120
rows = []
start = date(2024, 1, 15)

for i in range(N):
    company, reply_tendency = random.choice(COMPANIES)
    contact_role = random.choice(ROLES)
    ask_type = random.choice(ASK_TYPES)
    sent = start + timedelta(days=random.randint(0, 600))
    is_follow_up = random.random() < 0.25
    has_connection = random.random() < (0.5 if reply_tendency == "high" else 0.15)
    has_prior = random.random() < 0.2

    base_p = {"high": 0.55, "medium": 0.35, "low": 0.15}[reply_tendency]
    p_reply = base_p
    if has_connection:
        p_reply += 0.2
    if has_prior:
        p_reply += 0.1
    if is_follow_up:
        p_reply += 0.08
    p_reply = min(max(p_reply, 0.03), 0.92)

    replied = random.random() < p_reply
    if not replied:
        outcome = "no_reply"
        reply_date = None
    else:
        outcome = random.choices(
            ["replied", "declined", "meeting_booked"], weights=[0.4, 0.25, 0.35]
        )[0]
        reply_date = sent + timedelta(days=random.randint(1, 14))

    rows.append(
        {
            "company": f"{company} (synthetic)",
            "contact_name": f"Synthetic Contact {i}",
            "contact_role": contact_role,
            "ask_type": ask_type,
            "date_sent": sent.isoformat(),
            "sender": random.choice(SENDERS),
            "is_follow_up": is_follow_up,
            "has_uw_mfbc_connection": has_connection,
            "has_prior_relationship": has_prior,
            "email_text": "",
            "notes": "Synthetic sample row — not a real MFBC outreach record.",
            "outcome": outcome,
            "reply_date": reply_date.isoformat() if reply_date else "",
        }
    )

out_path = "sample_synthetic_outreach.csv"
pd.DataFrame(rows).to_csv(out_path, index=False)
print(f"Wrote {len(rows)} synthetic rows to {out_path}")
print("Import it from the app's Outreach History page -> Import CSV / Excel tab.")
