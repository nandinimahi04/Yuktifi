from __future__ import annotations

# Eligibility is deliberately conservative. Unknown profile fields produce UNKNOWN,
# not an AI guess. Rule records carry source/effective metadata.
RULES = [
    {"id":"pmegp_project_band","scheme":"PMEGP","rule":"Project-cost ceiling depends on activity; current official ceiling must be verified before use.","source":"KVIC PMEGP portal","source_url":"https://www.kviconline.gov.in/pmegpeportal/","status":"VERIFY"},
    {"id":"mudra_ceiling","scheme":"MUDRA","rule":"Loan-product ceiling and Tarun Plus conditions must be checked against current official guidance.","source":"PMMY/MUDRA official information","source_url":"https://www.mudra.org.in/","status":"VERIFY"},
    {"id":"nsfdc","scheme":"NSFDC","rule":"Eligibility depends on beneficiary/category and lending-channel rules; project cost alone is insufficient.","source":"NSFDC","source_url":"https://nsfdc.nic.in/","status":"VERIFY"},
]

def evaluate(profile: dict, project_cost: float) -> list[dict]:
    out=[]
    for r in RULES:
        required = ["social_category"] if r["scheme"] in {"NSFDC"} else []
        missing=[k for k in required if not profile.get(k)]
        out.append({"scheme":r["scheme"],"status":"UNKNOWN" if missing or r["status"]=="VERIFY" else "POTENTIAL",
                    "missing_fields":missing,"reason":r["rule"],"source":r["source"],"source_url":r["source_url"]})
    return out
