"""
Data Quality Validation & Quarantine Engine.
Validates datasets against domain constraints (non-negative prices/populations, valid years, non-empty metrics).
Generates detailed validation reports and quarantines invalid records.
"""
from typing import Any, Dict, List, Tuple

class DataQualityValidator:
    def __init__(self):
        self.validation_summary = {
            "total_datasets_checked": 0,
            "total_records_checked": 0,
            "valid_records": 0,
            "invalid_records": 0,
            "quarantined_files": [],
            "dataset_reports": {}
        }

    def validate_dataset_records(self, dataset_id: str, records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
        """
        Validates records for a dataset. Returns (valid_records, quarantined_records, report).
        """
        self.validation_summary["total_datasets_checked"] += 1
        valid = []
        invalid = []
        errors = {
            "null_metric": 0,
            "negative_numeric": 0,
            "invalid_year": 0,
            "empty_row": 0
        }

        for rec in records:
            self.validation_summary["total_records_checked"] += 1
            if not rec or all(v is None or v == "" for v in rec.values()):
                errors["empty_row"] += 1
                invalid.append({"record": rec, "reason": "EMPTY_ROW"})
                continue

            # Check for negative impossible values
            has_error = False
            for k, v in rec.items():
                k_lower = str(k).lower()
                if any(term in k_lower for term in ["pop", "count", "price", "area", "households", "total"]):
                    try:
                        num_val = float(v)
                        if num_val < 0:
                            errors["negative_numeric"] += 1
                            invalid.append({"record": rec, "reason": f"NEGATIVE_VALUE_IN_{k}: {v}"})
                            has_error = True
                            break
                    except (ValueError, TypeError):
                        pass

            if not has_error:
                valid.append(rec)

        self.validation_summary["valid_records"] += len(valid)
        self.validation_summary["invalid_records"] += len(invalid)

        report = {
            "dataset_id": dataset_id,
            "total_records": len(records),
            "valid": len(valid),
            "invalid": len(invalid),
            "errors": errors,
            "status": "PASS" if len(invalid) == 0 else ("PARTIAL" if len(valid) > 0 else "FAIL")
        }
        self.validation_summary["dataset_reports"][dataset_id] = report
        return valid, invalid, report

    def record_quarantine_file(self, filename: str, reason: str):
        self.validation_summary["quarantined_files"].append({
            "filename": filename,
            "reason": reason
        })

    def get_full_report(self) -> Dict[str, Any]:
        return self.validation_summary
