import json
import os
from pathlib import Path

def merge_dicts(d1, d2):
    """Recursively merges d2 into d1. Prefers d1's values for primitives."""
    for k, v in d2.items():
        if isinstance(v, dict):
            d1[k] = merge_dicts(d1.get(k, {}), v)
        elif isinstance(v, list):
            # For lists of dicts (like competitors), merge by 'name'
            if all(isinstance(x, dict) and 'name' in x for x in d1.get(k, []) + v):
                merged_list = d1.get(k, []).copy()
                existing_names = {x['name']: i for i, x in enumerate(merged_list)}
                for item in v:
                    if item['name'] in existing_names:
                        idx = existing_names[item['name']]
                        merged_list[idx] = merge_dicts(merged_list[idx], item)
                    else:
                        merged_list.append(item)
                d1[k] = merged_list
            else:
                # Merge simple lists without duplicates
                # Note: list(set()) loses order and fails for unhashable types if they sneak in.
                # Since these are mostly strings (opportunity gaps, strengths), we handle them carefully:
                if all(isinstance(x, (str, int, float)) for x in d1.get(k, []) + v):
                    d1_list = d1.get(k, [])
                    for item in v:
                        if item not in d1_list:
                            d1_list.append(item)
                    d1[k] = d1_list
        else:
            if k not in d1:
                d1[k] = v
            # If primitive exists, we keep d1's.
    return d1

def normalize_datasets():
    base_dir = Path(__file__).resolve().parent.parent.parent.parent / "backend"
    source_dir = base_dir / "data" / "source"
    processed_dir = base_dir / "data" / "processed"
    
    detailed_path = source_dir / "solapur_business_dataset_detailed.json"
    strict_path = source_dir / "solapur_business_dataset_strict.json"
    combined_path = processed_dir / "solapur_combined.json"

    print(f"Loading {detailed_path}")
    with open(detailed_path, 'r', encoding='utf-8') as f:
        detailed_data = json.load(f)
        
    print(f"Loading {strict_path}")
    with open(strict_path, 'r', encoding='utf-8') as f:
        strict_data = json.load(f)

    # Detailed data is the base.
    combined_data = merge_dicts(detailed_data, strict_data)
    
    # Save the processed output
    print(f"Saving to {combined_path}")
    with open(combined_path, 'w', encoding='utf-8') as f:
        json.dump(combined_data, f, indent=2, ensure_ascii=False)
        
    print("Done.")

if __name__ == "__main__":
    normalize_datasets()
