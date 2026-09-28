"""
Standard Data Provider Interface (Phase 4).
Enforces consistent return schema across all data ingestion providers:
{ "value": {}, "provenance": {}, "confidence": {} }
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
from app.evidence.schema import EvidenceRecord

class BaseDataProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    def fetch_data(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Must return standard dictionary structure:
        {
            "value": dict,
            "provenance": EvidenceRecord.to_dict(),
            "confidence": {
                "overall": "HIGH" | "MEDIUM" | "LOW",
                "score": float,
                "coverage": "HIGH" | "MEDIUM" | "LOW"
            }
        }
        """
        pass

    def format_response(self, value: Dict[str, Any], provenance: EvidenceRecord, overall_confidence: str = "MEDIUM", confidence_score: float = 0.8, coverage: str = "HIGH") -> Dict[str, Any]:
        return {
            "value": value,
            "provenance": provenance.to_dict(),
            "confidence": {
                "overall": overall_confidence.upper(),
                "score": round(confidence_score, 2),
                "coverage": coverage.upper()
            }
        }
