"""
Master Universal Dataset Build Pipeline (UYDF-1.0).
Builds the complete Universal Yukti Data, Evidence, and Document Store from Documents SIH 26.
Can be executed via CLI:
python -m data_pipeline.build_universal_dataset --input "D:\\Ai workshop\\Documents SIH 26" --output "data/universal"
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

# Ensure backend root is in sys.path
repo_root = Path(__file__).resolve().parent.parent
backend_dir = repo_root / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from data_pipeline.inventory_scanner import inspect_source_directory
from data_pipeline.parsers.csv_parser import parse_csv_file
from data_pipeline.parsers.excel_parser import parse_excel_file
from data_pipeline.parsers.xml_parser import parse_xml_file
from data_pipeline.parsers.pdf_parser import parse_pdf_document
from data_pipeline.parsers.geotiff_parser import parse_geotiff_metadata
from data_pipeline.normalizers.unit_normalizer import normalize_currency_and_period
from data_pipeline.normalizers.time_normalizer import normalize_time_context
from data_pipeline.normalizers.geography_normalizer import normalize_geography
from data_pipeline.validators.quality_validator import DataQualityValidator
from data_pipeline.validators.duplicate_detector import DuplicateDetector
from app.data_layer.universal.business_mapping import BUSINESS_TAXONOMY
from app.rag.store import add_document, ensure_schema

def run_pipeline(input_dir: Path, output_dir: Path):
    print("=" * 70)
    print("YUKTIFI — BUILDING UNIVERSAL DATA & EVIDENCE LAYER (UYDF-1.0)")
    print(f"Source Directory: {input_dir}")
    print(f"Output Directory: {output_dir}")
    print("=" * 70)

    start_time = datetime.now(timezone.utc)

    # 1. Prepare target directories
    for sub in ["inventory", "catalog", "normalized", "evidence", "geography", "spatial", "documents", "mappings", "validation"]:
        (output_dir / sub).mkdir(parents=True, exist_ok=True)

    validator = DataQualityValidator()
    dup_detector = DuplicateDetector()

    # 2. Inventory & Classification Scan
    print("\n[Step 1/6] Scanning and fingerprinting all files...")
    files_inv, datasets_inv, docs_inv = inspect_source_directory(input_dir)
    print(f"-> Discovered {len(files_inv)} files ({len(datasets_inv)} datasets, {len(docs_inv)} documents).")

    with open(output_dir / "inventory" / "files.json", "w", encoding="utf-8") as f:
        json.dump(files_inv, f, indent=2)
    with open(output_dir / "inventory" / "datasets.json", "w", encoding="utf-8") as f:
        json.dump(datasets_inv, f, indent=2)
    with open(output_dir / "inventory" / "documents.json", "w", encoding="utf-8") as f:
        json.dump(docs_inv, f, indent=2)

    # 3. Process Structured Datasets into Universal Evidence
    print("\n[Step 2/6] Parsing structured datasets & normalizing evidence...")
    evidence_records: List[Dict[str, Any]] = []
    dataset_catalog_entries: List[Dict[str, Any]] = []
    geography_catalog_entries: Dict[str, Dict[str, Any]] = {}
    spatial_catalog_entries: List[Dict[str, Any]] = []

    for ds in datasets_inv:
        rel_p = ds["relative_path"]
        fpath = input_dir / rel_p
        ds_id = ds["dataset_id"]
        fmt = ds["format"]
        org = ds["organization"]
        ds_name = ds["dataset_name"]

        # Duplicate check
        if dup_detector.check_file(rel_p, ds["sha256"], fpath.stat().st_size):
            continue

        records_parsed: List[Dict[str, Any]] = []

        if fmt == "csv":
            recs, cols, status = parse_csv_file(fpath)
            records_parsed = recs
        elif fmt in ["xls", "xlsx"]:
            sheets, snames, status = parse_excel_file(fpath)
            for sname, s_recs in sheets.items():
                records_parsed.extend(s_recs)
        elif fmt == "xml":
            recs, cols, status = parse_xml_file(fpath)
            records_parsed = recs
        elif fmt in ["tif", "tiff"]:
            meta, status = parse_geotiff_metadata(fpath)
            spatial_catalog_entries.append({
                "spatial_id": f"spatial_{ds['sha256'][:16]}",
                "dataset_id": ds_id,
                "dataset_name": ds_name,
                "filepath": rel_p,
                **meta
            })
            status = "SUCCESS"

        # Validate records
        valid_recs, invalid_recs, rep = validator.validate_dataset_records(ds_id, records_parsed)

        # Build Catalog Entry
        catalog_entry = {
            "dataset_id": ds_id,
            "dataset_name": ds_name,
            "organization": org,
            "source_type": ds["source_type"],
            "original_filename": ds["filename"],
            "original_format": fmt,
            "geographic_scope": ds["geographic_scope"],
            "geographic_resolution": ds["geographic_resolution"],
            "checksum": ds["sha256"],
            "records_count": len(valid_recs),
            "status": "ACTIVE",
            "schema_version": "UYDF-1.0"
        }
        dataset_catalog_entries.append(catalog_entry)

        # Convert sample valid records to Universal Evidence records
        for i, rec in enumerate(valid_recs[:100]): # index top records per dataset into evidence store
            loc_name = str(rec.get("District", rec.get("district", rec.get("State", rec.get("state", "Solapur")))))
            geo_ctx = normalize_geography(loc_name, raw_district="Solapur")
            
            # Key geography entry
            geo_key = f"{geo_ctx['level']}_{geo_ctx['normalized_name']}"
            if geo_key not in geography_catalog_entries:
                geography_catalog_entries[geo_key] = {
                    "geography_id": f"geo_{hashlib.md5(geo_key.encode()).hexdigest()[:12]}",
                    **geo_ctx
                }

            # Extract metric observation
            first_metric_key = next((k for k in rec.keys() if any(t in str(k).lower() for t in ["pop", "total", "area", "price", "count", "margin"])), list(rec.keys())[0] if rec else "value")
            metric_val = rec.get(first_metric_key)
            norm_unit_info = normalize_currency_and_period(metric_val, "INR / Count")
            time_ctx = normalize_time_context(rec.get("Year", rec.get("year", 2011)), filename=ds["filename"])

            evi_record = {
                "evidence_id": f"evi_{ds_id[:8]}_{i:04d}",
                "dataset_id": ds_id,
                "entity": {
                    "type": geo_ctx["level"],
                    "name": geo_ctx["normalized_name"],
                    "country": "India",
                    "state": geo_ctx["state"],
                    "district": geo_ctx["district"],
                    "subdistrict": geo_ctx["subdistrict"],
                    "lgd_code": geo_ctx["lgd_code"]
                },
                "observation": {
                    "metric": first_metric_key,
                    "value": norm_unit_info["normalized_value"] or metric_val,
                    "unit": norm_unit_info["normalized_unit"],
                    "original_value": metric_val,
                    "conversion_method": norm_unit_info["conversion_method"]
                },
                "time": time_ctx,
                "provenance": {
                    "source": org,
                    "original_file": rel_p,
                    "method": "DIRECT_EXTRACTION",
                    "retrieved_at": datetime.now(timezone.utc).isoformat()
                },
                "quality": {
                    "source_type": ds["source_type"],
                    "origin": "DATASET_DERIVED",
                    "confidence": "HIGH",
                    "is_estimate": False,
                    "is_assumption": False
                },
                "business_context": {
                    "business_categories": ["kirana", "dairy", "agriculture"],
                    "relevance": "DIRECT"
                }
            }
            evidence_records.append(evi_record)

    print(f"-> Generated {len(evidence_records)} universal evidence records across {len(dataset_catalog_entries)} datasets.")

    # 4. Process Unstructured Documents for RAG Store
    print("\n[Step 3/6] Parsing official document monographs & generating RAG chunks...")
    ensure_schema()
    document_catalog_entries: List[Dict[str, Any]] = []
    total_rag_chunks = 0

    for doc in docs_inv:
        rel_p = doc["relative_path"]
        fpath = input_dir / rel_p
        doc_id = doc["document_id"]
        doc_title = doc["title"]
        org = doc["organization"]

        chunks, doc_meta, status = parse_pdf_document(fpath, max_pages=60)
        
        doc_catalog_entry = {
            "document_id": doc_id,
            "title": doc_title,
            "filename": doc["filename"],
            "organization": org,
            "source_type": doc["source_type"],
            "total_pages": doc_meta.get("total_pages", 0),
            "chunks_extracted": len(chunks),
            "status": status,
            "checksum": doc["sha256"]
        }
        document_catalog_entries.append(doc_catalog_entry)

        # Index into RAG Store (SQLite / Postgres)
        full_text = "\n\n".join([c["text"] for c in chunks])
        if full_text.strip():
            res = add_document(
                title=f"{doc_title} ({doc['filename']})",
                content=full_text,
                source=org,
                source_url=f"local://Documents_SIH_26/{rel_p}",
                effective_date="2023-01-01",
                metadata={"document_id": doc_id, "organization": org, "filename": doc["filename"]}
            )
            total_rag_chunks += res.get("chunks", len(chunks))

    print(f"-> Indexed {len(document_catalog_entries)} official monographs with {total_rag_chunks} semantic RAG chunks.")

    # 5. Write Catalog, Evidence, Geography, Spatial, Mappings
    print("\n[Step 4/6] Exporting structured catalogs, evidence envelopes, and mappings...")
    with open(output_dir / "catalog" / "dataset_catalog.json", "w", encoding="utf-8") as f:
        json.dump(dataset_catalog_entries, f, indent=2)

    with open(output_dir / "evidence" / "evidence_store.json", "w", encoding="utf-8") as f:
        json.dump(evidence_records, f, indent=2)

    with open(output_dir / "geography" / "geography_catalog.json", "w", encoding="utf-8") as f:
        json.dump(list(geography_catalog_entries.values()), f, indent=2)

    with open(output_dir / "spatial" / "spatial_catalog.json", "w", encoding="utf-8") as f:
        json.dump(spatial_catalog_entries, f, indent=2)

    with open(output_dir / "documents" / "document_catalog.json", "w", encoding="utf-8") as f:
        json.dump(document_catalog_entries, f, indent=2)

    with open(output_dir / "mappings" / "business_taxonomy.json", "w", encoding="utf-8") as f:
        json.dump(BUSINESS_TAXONOMY, f, indent=2)

    with open(output_dir / "mappings" / "business_dataset_mapping.json", "w", encoding="utf-8") as f:
        json.dump({cat["category_id"]: cat for cat in BUSINESS_TAXONOMY}, f, indent=2)

    # 6. Data Quality & Quarantine Report
    print("\n[Step 5/6] Generating validation and audit report...")
    quality_rep = validator.get_full_report()
    quality_rep["duplicates_detected"] = dup_detector.get_duplicates_report()
    
    with open(output_dir / "validation" / "validation_report.json", "w", encoding="utf-8") as f:
        json.dump(quality_rep, f, indent=2)

    # 7. Pipeline Manifest
    print("\n[Step 6/6] Generating master pipeline manifest.json...")
    end_time = datetime.now(timezone.utc)
    duration_s = (end_time - start_time).total_seconds()

    manifest = {
        "schema_version": "UYDF-1.0",
        "pipeline_version": "2.0.0-production",
        "source_archive": "Documents SIH 26",
        "source_directory": str(input_dir),
        "build_timestamp": end_time.isoformat(),
        "build_duration_seconds": round(duration_s, 2),
        "total_files_discovered": len(files_inv),
        "datasets_cataloged": len(dataset_catalog_entries),
        "documents_indexed": len(document_catalog_entries),
        "evidence_records_created": len(evidence_records),
        "geographies_normalized": len(geography_catalog_entries),
        "spatial_rasters_cataloged": len(spatial_catalog_entries),
        "rag_chunks_in_store": total_rag_chunks,
        "valid_records_processed": quality_rep["valid_records"],
        "duplicates_identified": len(quality_rep["duplicates_detected"]),
        "status": "SUCCESS"
    }

    with open(output_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print("=" * 70)
    print("PIPELINE COMPLETED SUCCESSFULLY!")
    print(f"Manifest written to: {output_dir / 'manifest.json'}")
    print(f"Total files: {manifest['total_files_discovered']} | Evidence records: {manifest['evidence_records_created']} | RAG chunks: {manifest['rag_chunks_in_store']}")
    print("=" * 70)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Universal Yukti Data Layer Builder")
    parser.add_argument("--input", default="D:\\Ai workshop\\Documents SIH 26", help="Path to Documents SIH 26 directory")
    parser.add_argument("--output", default="data/universal", help="Output path for universal data layer")
    args = parser.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.output)
    if not in_path.exists():
        print(f"Error: Input path {in_path} does not exist!")
        sys.exit(1)

    run_pipeline(in_path, out_path)
