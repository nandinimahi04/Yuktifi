"""
Inventory and Classification Scanner for Documents SIH 26.
Discovers every file, computes SHA-256 hashes, extracts format metadata,
and classifies into universal dataset and document records.
"""
import hashlib
import json
import mimetypes
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Classification constants
OFFICIAL_STATISTICAL = "OFFICIAL_STATISTICAL"
OFFICIAL_GEOGRAPHIC = "OFFICIAL_GEOGRAPHIC"
OFFICIAL_MARKET = "OFFICIAL_MARKET"
OFFICIAL_SCHEME = "OFFICIAL_SCHEME"
OFFICIAL_INFRASTRUCTURE = "OFFICIAL_INFRASTRUCTURE"
REMOTE_SENSING = "REMOTE_SENSING"
OPEN_GEOSPATIAL = "OPEN_GEOSPATIAL"
SURVEY = "SURVEY"
ADMINISTRATIVE = "ADMINISTRATIVE"
RESEARCH = "RESEARCH"
USER_PROVIDED = "USER_PROVIDED"
CALCULATED = "CALCULATED"
ASSUMED = "ASSUMED"
UNKNOWN = "UNKNOWN"

def compute_sha256(filepath: Path) -> str:
    sha = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha.update(chunk)
        return sha.hexdigest()
    except Exception:
        return "ERROR_COMPUTING_HASH"

def classify_file(filename: str, ext: str, size: int) -> tuple[str, str, str, str, str]:
    """
    Returns (source_type, dataset_name, organization, geo_scope, geo_resolution).
    """
    fn = filename.lower()
    
    # 0-byte files
    if size == 0:
        return (UNKNOWN, "Empty / Incomplete Download", "Unknown", "UNKNOWN", "UNKNOWN")

    # Census 2011 files
    if "pca" in fn or "census" in fn:
        return (OFFICIAL_STATISTICAL, "Census 2011 Primary Census Abstract (PCA)", "Census of India, MoHA", "Solapur / Maharashtra", "VILLAGE_TOWN")
    if "dchb" in fn or "2730" in fn or fn.startswith("t") and any(fn.startswith(f"t{i:02d}") for i in range(1, 46)):
        return (OFFICIAL_STATISTICAL, "District Census Handbook 2011 (DCHB Solapur)", "Directorate of Census Operations, Maharashtra", "Solapur District", "VILLAGE_TOWN_SUBDISTRICT")
    if "indiastatedistsbdistvill" in fn:
        return (OFFICIAL_STATISTICAL, "Census 2011 India Administrative Hierarchy & Population", "Office of the Registrar General & Census Commissioner, India", "India National", "VILLAGE")

    # Local Government Directory (LGD) files
    if "villageofspecificstate" in fn:
        return (OFFICIAL_GEOGRAPHIC, "LGD Master Directory - Villages List", "Ministry of Panchayati Raj (MoPR)", "Maharashtra State", "VILLAGE")
    if "subdistrictofspecificstate" in fn:
        return (OFFICIAL_GEOGRAPHIC, "LGD Master Directory - Sub-Districts / Talukas", "Ministry of Panchayati Raj (MoPR)", "Maharashtra State", "SUBDISTRICT")
    if "villagegrampanchayatmapping" in fn:
        return (OFFICIAL_GEOGRAPHIC, "LGD Master Directory - Village to Gram Panchayat Mapping", "Ministry of Panchayati Raj (MoPR)", "Maharashtra State", "GRAM_PANCHAYAT")
    if "ulbspecificstate" in fn:
        return (OFFICIAL_GEOGRAPHIC, "LGD Master Directory - Urban Local Bodies (ULBs)", "Ministry of Housing and Urban Affairs (MoHUA)", "Maharashtra State", "MUNICIPALITY")
    if "ulbwardforstate" in fn:
        return (OFFICIAL_GEOGRAPHIC, "LGD Master Directory - ULB Municipal Wards", "Ministry of Housing and Urban Affairs (MoHUA)", "Maharashtra State", "WARD")

    # MoSPI HCES Survey
    if "hces" in fn:
        return (SURVEY, "Household Consumption Expenditure Survey (HCES 2022-23 / 2023-24)", "National Sample Survey Office (NSSO), MoSPI", "India National & State", "STATE_DISTRICT")

    # NFHS-5 Survey
    if "nfhs" in fn:
        return (SURVEY, "National Family Health Survey (NFHS-5, 2019-21)", "International Institute for Population Sciences (IIPS) & MoHFW", "India All Districts", "DISTRICT")

    # Remote Sensing / WorldPop
    if "ind_pop" in fn or "worldpop" in fn or ext in [".tif", ".tiff"]:
        return (REMOTE_SENSING, "WorldPop India 2025 High-Resolution Population Density Raster", "WorldPop / University of Southampton", "India National", "1KM_RASTER_GRID")

    # Irrigation / Agriculture
    if "irrigation" in fn:
        return (OFFICIAL_STATISTICAL, "Area Under Irrigation & Water Source Statistics", "Ministry of Agriculture & Farmers Welfare / DES", "Maharashtra / Ahmadnagar / Solapur", "DISTRICT")

    # Geospatial / ISRO Bhuvan
    if "bhuvan" in fn:
        return (OPEN_GEOSPATIAL, "ISRO Bhuvan Spatial Data Content & Map Standards", "National Remote Sensing Centre (NRSC), ISRO", "India National", "GEOSPATIAL_STANDARDS")

    # Economic & Research reports
    if "economic" in fn or "ecnomic" in fn:
        return (OFFICIAL_STATISTICAL, "Economic Statistics and Operational Baselines", "Ministry of Statistics & Programme Implementation", "India State / District", "DISTRICT")
    if "wri" in fn:
        return (RESEARCH, "WRI Rural Micro-Enterprise & Clean Energy Infrastructure Study", "World Resources Institute (WRI)", "India Regional", "REGIONAL")
    if "f8cd85a1" in fn:
        return (OFFICIAL_MARKET, "Open Government Data Market Prices & Commodity Baseline", "Open Government Data (OGD) Platform India (data.gov.in)", "India District", "MARKET")

    return (ADMINISTRATIVE, f"Document/Dataset ({filename})", "Official Source / Unknown", "India", "DISTRICT")

def inspect_source_directory(source_dir: Path) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Scans source_dir recursively, extracts metadata, and returns (files, datasets, documents).
    """
    files_inventory = []
    datasets_inventory = []
    documents_inventory = []
    
    seen_hashes = {}

    for root, _, filenames in os.walk(source_dir):
        for fname in sorted(filenames):
            full_path = Path(root) / fname
            rel_path = full_path.relative_to(source_dir).as_posix()
            ext = full_path.suffix.lower()
            size = full_path.stat().st_size
            sha = compute_sha256(full_path)
            
            # Detect duplicates by hash
            is_duplicate = sha in seen_hashes and size > 0
            original_of_duplicate = seen_hashes.get(sha)
            if not is_duplicate and size > 0:
                seen_hashes[sha] = rel_path

            # MIME type detection
            mime_type, _ = mimetypes.guess_type(str(full_path))
            if not mime_type:
                if ext == ".xls": mime_type = "application/vnd.ms-excel"
                elif ext == ".xlsx": mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                elif ext in [".tif", ".tiff"]: mime_type = "image/tiff"
                elif ext == ".xml": mime_type = "application/xml"
                elif ext == ".csv": mime_type = "text/csv"
                elif ext == ".pdf": mime_type = "application/pdf"
                else: mime_type = "application/octet-stream"

            source_type, dataset_name, org, geo_scope, geo_res = classify_file(fname, ext, size)
            
            # Estimate structured vs document vs geospatial
            is_structured = ext in [".csv", ".xls", ".xlsx", ".xml", ".json", ".parquet"]
            is_document = ext in [".pdf", ".docx", ".doc", ".txt", ".md"]
            is_geospatial = ext in [".tif", ".tiff", ".geojson", ".shp", ".gpkg"]

            # Quick structural inspection
            row_count_est = None
            page_count_est = None
            sheet_names = []
            parsing_status = "READY"
            limitations = []

            if size == 0:
                parsing_status = "EMPTY_FILE_ZERO_BYTES"
                limitations.append("File has 0 bytes (corrupted or incomplete download). Quarantined.")

            file_record = {
                "file_id": f"file_{sha[:16]}" if size > 0 else f"file_empty_{hashlib.md5(rel_path.encode()).hexdigest()[:12]}",
                "relative_path": rel_path,
                "filename": fname,
                "extension": ext,
                "mime_type": mime_type,
                "size_bytes": size,
                "sha256": sha,
                "is_duplicate": is_duplicate,
                "duplicate_of": original_of_duplicate if is_duplicate else None,
                "source_organization": org,
                "dataset_name": dataset_name,
                "source_type": source_type,
                "geographic_scope": geo_scope,
                "geographic_resolution": geo_res,
                "classification": "GEOSPATIAL" if is_geospatial else ("STRUCTURED" if is_structured else "UNSTRUCTURED_DOCUMENT"),
                "parsing_status": parsing_status,
                "validation_status": "QUARANTINED" if size == 0 else "VALID",
                "relevance": "HIGH" if "solapur" in rel_path.lower() or "hces" in rel_path.lower() or "census" in rel_path.lower() or "lgd" in rel_path.lower() else "MEDIUM",
                "limitations": limitations,
                "discovered_at": datetime.now(timezone.utc).isoformat()
            }
            files_inventory.append(file_record)

            # Separate into datasets vs documents
            if is_document and size > 0:
                doc_record = {
                    "document_id": f"doc_{sha[:16]}",
                    "file_id": file_record["file_id"],
                    "filename": fname,
                    "relative_path": rel_path,
                    "title": dataset_name,
                    "organization": org,
                    "extension": ext,
                    "source_type": source_type,
                    "geographic_scope": geo_scope,
                    "sha256": sha,
                    "status": parsing_status
                }
                documents_inventory.append(doc_record)
            elif (is_structured or is_geospatial) and size > 0:
                ds_record = {
                    "dataset_id": f"ds_{sha[:16]}",
                    "file_id": file_record["file_id"],
                    "dataset_name": dataset_name,
                    "filename": fname,
                    "relative_path": rel_path,
                    "organization": org,
                    "format": ext.lstrip("."),
                    "source_type": source_type,
                    "geographic_scope": geo_scope,
                    "geographic_resolution": geo_res,
                    "sha256": sha,
                    "is_geospatial": is_geospatial,
                    "status": parsing_status
                }
                datasets_inventory.append(ds_record)

    return files_inventory, datasets_inventory, documents_inventory
