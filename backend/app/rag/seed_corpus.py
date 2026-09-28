"""
YuktiFi RAG Official Government Corpus Auto-Seeder (Phase 12).
Indexes official scheme guidelines, credit rules, and agricultural manuals into RAG knowledge store.
"""
import logging
import sys
from pathlib import Path

# Ensure backend root directory is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.rag.store import add_document

logger = logging.getLogger("yukti.rag_seed")

OFFICIAL_CORPUS_DOCUMENTS = [
    {
        "title": "NSFDC Micro Credit Finance Scheme Guidelines",
        "source": "National Scheduled Castes Finance and Development Corporation (NSFDC)",
        "source_url": "https://nsfdc.nic.in/",
        "effective_date": "2023-04-01",
        "content": """
NSFDC Micro Credit Finance (MCF) Scheme Guidelines:
1. Eligibility: Beneficiaries belonging to Scheduled Castes living below double the poverty line threshold.
2. Maximum Project Cost: Up to ₹1,40,000 per unit.
3. Maximum Loan Amount: Up to ₹1,25,000 (90% scheme financing).
4. Interest Rate: 6.5% per annum to the final beneficiary.
5. Repayment Tenure: Up to 36 months (3 years) including a moratorium period of 3 months.
6. Beneficiary Contribution: Minimum 10% of total project cost.
7. Promoted Sectors: Micro-retail, tea/snack stalls, tailoring, small repair shops, and village artisan units.
"""
    },
    {
        "title": "NSFDC Term Loan Scheme Guidelines",
        "source": "National Scheduled Castes Finance and Development Corporation (NSFDC)",
        "source_url": "https://nsfdc.nic.in/",
        "effective_date": "2023-04-01",
        "content": """
NSFDC Term Loan Scheme Guidelines:
1. Maximum Project Cost: Up to ₹50,00,000 per unit for commercial & manufacturing enterprises.
2. Maximum Loan Amount: Up to ₹45,00,000 (90% scheme financing).
3. Interest Rate: 8.0% per annum for loan amounts up to ₹50 Lakhs.
4. Repayment Tenure: Up to 84 months (7 years) including a moratorium period of up to 6 months.
5. Beneficiary Contribution: Minimum 10% of project cost.
6. Promoted Sectors: Dairy processing, commercial agri-machinery hiring, micro food processing, diagnostic collection centres.
"""
    },
    {
        "title": "PMEGP Prime Minister Employment Generation Programme Guidelines",
        "source": "Khadi and Village Industries Commission (KVIC) / Ministry of MSME",
        "source_url": "https://www.kviconline.gov.in/pmegpeportal/",
        "effective_date": "2024-01-01",
        "content": """
PMEGP Subsidy & Credit Guidelines:
1. Maximum Project Cost: ₹50,00,000 for Manufacturing Sector and ₹20,00,000 for Service / Business Sector.
2. Subsidy (Margin Money):
   - General Category: 15% (Urban) / 25% (Rural).
   - Special Category (SC/ST/OBC/Minorities/Women/Ex-servicemen): 25% (Urban) / 35% (Rural).
3. Own Contribution: 10% for General Category; 5% for Special Categories.
4. Eligible Beneficiaries: Any individual above 18 years of age. Minimum VIII class pass for projects above ₹10L in manufacturing or ₹5L in service.
"""
    },
    {
        "title": "MUDRA Pradhan Mantri Mudra Yojana Scheme Guidelines",
        "source": "Micro Units Development & Refinance Agency Ltd. (MUDRA)",
        "source_url": "https://www.mudra.org.in/",
        "effective_date": "2023-10-01",
        "content": """
Pradhan Mantri MUDRA Yojana (PMMY) Categories:
1. Shishu Category: Loans up to ₹50,000 for micro-starters and small vendors.
2. Kishore Category: Loans above ₹50,000 and up to ₹5,00,000 for growing micro-units.
3. Tarun Category: Loans above ₹5,00,000 and up to ₹10,00,000 for established small enterprises.
4. Collateral Requirement: No collateral security required for MUDRA loans.
5. Tenure & Repayment: 36 to 60 months with flexible repayment schedules.
"""
    },
    {
        "title": "ICAR Small Dairy & Micro Food Processing Technical Manual",
        "source": "Indian Council of Agricultural Research (ICAR)",
        "source_url": "https://icar.org.in/",
        "effective_date": "2023-01-01",
        "content": """
ICAR Micro-Enterprise Technical Parameters:
1. Small Dairy Unit:
   - Average yield per crossbred cow: 10-12 litres per day.
   - Average feed cost ratio: 55-65% of gross milk revenue.
   - Chilling/Refrigeration electricity requirement: 3-5 kWh per 100 litres.
2. Micro Food Processing (Atta Chakki / Spices):
   - 3-Phase Commercial Power connection required for 5HP+ motors.
   - Average processing capacity: 80-120 kg per hour for flour milling.
   - Expected gross margin: 35-45% over raw grain/spice procurement cost.
"""
    }
]

def seed_rag_corpus() -> int:
    """Auto-seeds official documents into RAG SQLite knowledge store."""
    indexed_count = 0
    for doc in OFFICIAL_CORPUS_DOCUMENTS:
        try:
            res = add_document(
                title=doc["title"],
                content=doc["content"],
                source=doc["source"],
                source_url=doc["source_url"],
                effective_date=doc["effective_date"]
            )
            indexed_count += 1
            logger.info("[RAG SEED] Indexed %s (%d chunks)", doc["title"], res.get("chunks", 0))
        except Exception as e:
            logger.error("[RAG SEED] Failed to index %s: %s", doc["title"], str(e))
    return indexed_count

if __name__ == "__main__":
    count = seed_rag_corpus()
    print(f"Successfully seeded {count} official government documents into RAG store.")
