#!/usr/bin/env python3
"""Import the official Maharashtra 20th Livestock Census into YUKTI evidence."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.data_ingestion.livestock import ingest_to_evidence  # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument("path", help="Official downloaded CSV/XLSX/ZIP")
parser.add_argument("--district", default="Solapur")
parser.add_argument("--block", default="Akkalkot")
parser.add_argument("--village")
args = parser.parse_args()

result = ingest_to_evidence(args.path, args.district, args.block, args.village)
print(json.dumps(result, indent=2, ensure_ascii=False))
