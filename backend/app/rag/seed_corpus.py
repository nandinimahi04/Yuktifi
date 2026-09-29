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
    },
    {
        "title": "PMFME Scheme Guidelines for Micro Food Processing",
        "source": "Ministry of Food Processing Industries (MoFPI)",
        "source_url": "https://pmfme.mofpi.gov.in/",
        "effective_date": "2023-06-01",
        "content": """
PM Formalisation of Micro Food Processing Enterprises (PMFME) Scheme:
1. Eligibility: Individual micro food processing units, self-help groups (SHGs), and producer cooperatives.
2. Financial Support: Credit-linked capital subsidy at 35% of eligible project cost with a maximum ceiling of ₹10,00,000 (₹10 Lakhs) per unit.
3. Beneficiary Contribution: Minimum 10% of project cost from the promoter's own funds.
4. Covered Categories: Atta chakki, spices processing, oil extraction, bakery, dairy value-addition, fruit/vegetable processing, pickles, and snack manufacturing.
5. Capacity Building: Technical training, FSSAI compliance, brand development, and packaging support grants.
"""
    },
    {
        "title": "Stand-Up India Scheme Guidelines for SC ST and Women",
        "source": "Department of Financial Services, Ministry of Finance",
        "source_url": "https://www.standupmitra.in/",
        "effective_date": "2023-04-01",
        "content": """
Stand-Up India Scheme for Greenfield Enterprises:
1. Eligibility: Scheduled Caste (SC), Scheduled Tribe (ST), and Women entrepreneurs above 18 years of age.
2. Loan Quantum: Composite loan (term loan + working capital) between ₹10,00,000 (₹10 Lakhs) and ₹1,00,00,000 (₹1 Crore).
3. Margin Money & Subsidy: Borrower contribution is minimum 15% of project cost (can be converged with eligible central/state subsidies).
4. Covered Sectors: Manufacturing, services, trading, and agri-allied activities (greenfield ventures).
5. Repayment & Moratorium: Up to 7 years repayment with an initial moratorium period of up to 18 months.
"""
    },
    {
        "title": "PM SVANidhi Scheme Guidelines for Urban and Rural Vendors",
        "source": "Ministry of Housing and Urban Affairs (MoHUA)",
        "source_url": "https://pmsvanidhi.mohua.gov.in/",
        "effective_date": "2023-09-01",
        "content": """
PM Street Vendor's AtmaNirbhar Nidhi (PM SVANidhi):
1. Eligibility: Street food stalls, tea/snack kiosks, cart vendors, and micro hawkers operating in urban and peri-urban areas.
2. Loan Tranches: First tranche up to ₹10,000; Second tranche up to ₹20,000 upon timely repayment; Third tranche up to ₹50,000.
3. Interest Subsidy: 7% per annum interest subsidy directly credited to borrower account.
4. Collateral: Zero collateral security required; digital transaction cash-back incentives up to ₹1,200 per annum.
"""
    },
    {
        "title": "NSTFDC Adivasi Mahila and Term Loan Guidelines",
        "source": "National Scheduled Tribes Finance and Development Corporation (NSTFDC)",
        "source_url": "https://nstfdc.tribal.gov.in/",
        "effective_date": "2023-04-01",
        "content": """
NSTFDC Credit Support Schemes:
1. Adivasi Mahila Sashaktikaran Yojana (AMSY): Concessional loan up to ₹2,00,000 at 4% p.a. interest rate for Scheduled Tribe women.
2. Term Loan Scheme: Up to ₹50,00,000 for income generating activities at 6.0% - 8.0% p.a. interest rate.
3. Micro Credit Scheme for Self Help Groups: Up to ₹50,000 per member.
"""
    },
    {
        "title": "NBCFDC New Swarnima Scheme Guidelines for Backward Classes",
        "source": "National Backward Classes Finance & Development Corporation (NBCFDC)",
        "source_url": "https://nbcfdc.gov.in/",
        "effective_date": "2023-04-01",
        "content": """
NBCFDC Credit Support Schemes:
1. New Swarnima Special Scheme for Women: Term loan up to ₹2,00,000 at concessional 5.0% p.a. interest rate for OBC women.
2. General Term Loan Scheme: Loan up to ₹15,00,000 at 6.0% to 8.0% p.a. interest rate for target backward class entrepreneurs.
3. Micro Finance Scheme: Up to ₹1,25,000 per beneficiary at 6.5% p.a.
"""
    }
]

def seed_rag_corpus(force: bool = False) -> int:
    """Auto-seeds official documents into RAG SQLite knowledge store."""
    from app.rag.ingest import ingest_directory
    from app.core.db import engine
    from sqlalchemy import text
    
    if not force:
        try:
            with engine.begin() as conn:
                existing = conn.execute(text("SELECT count(*) FROM yukti_rag_documents")).scalar()
                if existing and existing >= 10:
                    return int(existing)
        except Exception:
            pass

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

    # Ingest project documents from D:\Ai workshop\Documents SIH 26 if available
    external_dir = r"D:\Ai workshop\Documents SIH 26"
    try:
        ext_count = ingest_directory(external_dir, source="Official SIH 2026 Knowledge Repository")
        indexed_count += ext_count
        logger.info("[RAG SEED] Ingested %d documents from %s", ext_count, external_dir)
    except Exception as exc:
        logger.warning("[RAG SEED] Could not ingest from %s: %s", external_dir, exc)

    return indexed_count

if __name__ == "__main__":
    count = seed_rag_corpus()
    print(f"Successfully seeded {count} official government documents into RAG store.")
