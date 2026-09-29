"""
Duplicate Detection Engine.
Identifies identical files, schema collisions, and version duplicates using cryptographic fingerprints.
"""
from typing import Any, Dict, List, Set

class DuplicateDetector:
    def __init__(self):
        self.seen_hashes: Dict[str, str] = {} # sha256 -> first_seen_filepath
        self.duplicates_found: List[Dict[str, str]] = []

    def check_file(self, filepath_str: str, sha256: str, size: int) -> bool:
        """
        Returns True if this file is a duplicate of a previously seen file.
        """
        if size == 0:
            return False # 0-byte handled separately

        if sha256 in self.seen_hashes:
            orig = self.seen_hashes[sha256]
            self.duplicates_found.append({
                "duplicate_file": filepath_str,
                "original_file": orig,
                "sha256": sha256,
                "size_bytes": size
            })
            return True
        else:
            self.seen_hashes[sha256] = filepath_str
            return False

    def get_duplicates_report(self) -> List[Dict[str, str]]:
        return self.duplicates_found
