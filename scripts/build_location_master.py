"""Normalize an official LGD/Census location export into YUKTI's canonical CSV."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from app.location.resolver import read_master


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("output")
    args = ap.parse_args()
    rows = read_master(args.source)
    fields = [
        "state", "district", "subdistrict", "block", "village",
        "state_code", "district_code", "subdistrict_code", "block_code", "village_code", "location_code",
        "lat", "lng", "admin_level",
    ]
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})
    print(f"wrote {len(rows)} normalized location rows to {out}")


if __name__ == "__main__":
    main()
