"""
XML Parser for Statistical Datasets.
Extracts repeated data rows, attributes, and tags into tabular records.
"""
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Tuple

def parse_xml_file(filepath: Path, max_records: int = 20000) -> Tuple[List[Dict[str, Any]], List[str], str]:
    """
    Parses an XML statistical dataset into structured rows.
    """
    if filepath.stat().st_size == 0:
        return [], [], "EMPTY_FILE_0_BYTES"

    try:
        tree = ET.parse(filepath)
        root = tree.getroot()

        records = []
        headers_set = set()

        # Iterate through leaf/child elements
        for i, elem in enumerate(root.iter()):
            # Treat elements with multiple children as potential record rows
            children = list(elem)
            if children and not any(list(c) for c in children):
                rec = {}
                for c in children:
                    tag = c.tag.strip()
                    val = (c.text or "").strip()
                    rec[tag] = val
                    headers_set.add(tag)
                if rec:
                    records.append(rec)
                    if len(records) >= max_records:
                        break

        if not records:
            # Fallback: parse attributes of elements
            for elem in root.iter():
                if elem.attrib:
                    rec = dict(elem.attrib)
                    for k in rec.keys():
                        headers_set.add(k)
                    records.append(rec)
                    if len(records) >= max_records:
                        break

        return records, sorted(list(headers_set)), "SUCCESS" if records else "NO_RECORDS_FOUND"
    except Exception as e:
        return [], [], f"PARSING_FAILED: {str(e)}"
