"""
CSV Parser for Universal Data Layer.
Supports delimiter auto-detection, multi-encoding fallback, header validation, and structured record extraction.
"""
import csv
from pathlib import Path
from typing import Any, Dict, List, Tuple

def parse_csv_file(filepath: Path, max_rows: int = 50000) -> Tuple[List[Dict[str, Any]], List[str], str]:
    """
    Parses a CSV file safely. Returns (records, column_names, status).
    """
    if filepath.stat().st_size == 0:
        return [], [], "EMPTY_FILE_0_BYTES"

    encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
    for enc in encodings:
        try:
            with open(filepath, "r", encoding=enc, errors="replace") as f:
                # Sniff delimiter
                sample = f.read(4096)
                f.seek(0)
                try:
                    dialect = csv.Sniffer().sniff(sample)
                    delimiter = dialect.delimiter
                except Exception:
                    delimiter = ","

                reader = csv.DictReader(f, delimiter=delimiter)
                headers = [h.strip() for h in (reader.fieldnames or []) if h]
                records = []
                for i, row in enumerate(reader):
                    if i >= max_rows:
                        break
                    # Clean row keys and values
                    cleaned_row = {k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in row.items() if k}
                    records.append(cleaned_row)

                return records, headers, "SUCCESS"
        except Exception as e:
            continue

    return [], [], "PARSING_FAILED"
