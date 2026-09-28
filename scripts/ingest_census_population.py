#!/usr/bin/env python3
import argparse, json
from app.data_ingestion.census_population import ingest_to_evidence

p = argparse.ArgumentParser(description="Ingest official Census 2011 PCA village population into YUKTI evidence")
p.add_argument("path")
p.add_argument("--context", required=True, help="JSON file containing canonical location context")
a = p.parse_args()
ctx = json.load(open(a.context, encoding="utf-8"))
print(json.dumps(ingest_to_evidence(a.path, ctx), indent=2, ensure_ascii=False))
