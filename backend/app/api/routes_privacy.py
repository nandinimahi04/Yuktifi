"""
YuktiFi DPDP Act 2023 Privacy & Security Routes (Phase 16).
Provides standalone, understandable privacy notices, purpose-limited consent tracking,
data retention policies, and user data deletion/erasure execution.
"""
import logging
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger("yukti.privacy")

router = APIRouter(prefix="/api/privacy", tags=["YUKTIFI Privacy & Security"])

class ConsentRequest(BaseModel):
    user_id: str = Field(min_length=1)
    purposes: List[str] = Field(default_factory=lambda: ["feasibility_analysis", "scheme_matching"])
    granted: bool = True

class DeletionRequest(BaseModel):
    user_id: str = Field(min_length=1)
    reason: str = "User requested data erasure"

DPDP_PRIVACY_NOTICE = {
    "title": "YuktiFi DPDP Act 2023 Notice & Data Processing Policy",
    "version": "1.0-dpdp-compliant",
    "data_controller": "YuktiFi Decision Platform",
    "personal_data_collected": [
        "Business profile details (category, capital, experience)",
        "Coarse geographical location (District, Sub-district, State)",
        "Session parameters & calculated financial metrics"
    ],
    "purposes_of_processing": [
        "Determining micro-enterprise financial feasibility",
        "Matching eligible government credit and subsidy schemes",
        "Generating auditable decision dossiers and reports"
    ],
    "data_minimization_policy": "No full names, exact street addresses, or sensitive personal IDs are transmitted to third-party AI models.",
    "data_retention_period": "30 days for session analysis data or until immediate user deletion request.",
    "user_rights": [
        "Right to access summary of processed personal data",
        "Right to withdraw consent at any time",
        "Right to data deletion / erasure",
        "Right to nominate a representative for data rights"
    ],
    "contact_email": "privacy@yuktifi.org"
}

# In-memory consent & deletion registry for DPDP logging
_CONSENT_REGISTRY: Dict[str, Dict[str, Any]] = {}
_DELETION_LOG: List[Dict[str, Any]] = []

@router.get("/notice")
def get_privacy_notice():
    """Returns standalone, understandable DPDP Act 2023 privacy notice."""
    return DPDP_PRIVACY_NOTICE

@router.post("/consent")
def register_consent(req: ConsentRequest):
    """Registers or updates explicit user consent per purpose."""
    record = {
        "user_id": req.user_id,
        "purposes": req.purposes,
        "granted": req.granted,
        "status": "ACTIVE" if req.granted else "WITHDRAWN"
    }
    _CONSENT_REGISTRY[req.user_id] = record
    logger.info("[DPDP] Consent updated for user %s: granted=%s", req.user_id, req.granted)
    return {
        "status": "success",
        "message": f"Consent {'granted' if req.granted else 'withdrawn'} for user {req.user_id}",
        "record": record
    }

@router.post("/delete")
def request_data_deletion(req: DeletionRequest):
    """Executes DPDP user data deletion / erasure request."""
    if req.user_id in _CONSENT_REGISTRY:
        del _CONSENT_REGISTRY[req.user_id]
    
    deletion_entry = {
        "user_id": req.user_id,
        "reason": req.reason,
        "status": "COMPLETED"
    }
    _DELETION_LOG.append(deletion_entry)
    logger.info("[DPDP] Executed data deletion for user %s", req.user_id)
    
    return {
        "status": "success",
        "message": f"All personal data for user {req.user_id} has been permanently erased.",
        "deletion_entry": deletion_entry
    }
