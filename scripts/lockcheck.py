#!/usr/bin/env python3
"""
Lockcheck script: Verify dataset integrity and generate lockfile.
"""
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Set

import click

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from golden.lib.digest import file_sha256, generate_lockfile
from golden.lib.io_utils import read_json, read_jsonl, write_json


def verify_counts(items: List[Dict]) -> bool:
    """
    Verify that we have at least N=70 items and R=5 per stratum.
    
    Returns:
        True if counts are valid, False otherwise
    """
    # Check minimum total count
    if len(items) < 70:
        print(f"LOCK_ERR: Expected at least 70 items, got {len(items)}")
        return False
    
    # Group by stratum
    strata = defaultdict(list)
    for item in items:
        key = f"{item['archetype']}-{item['complexity']}-{item['locale']}"
        strata[key].append(item)
    
    # Check minimum R=5 per stratum
    for stratum_key, stratum_items in strata.items():
        if len(stratum_items) < 5:
            print(f"LOCK_ERR: Stratum {stratum_key} has {len(stratum_items)} items, expected at least 5")
            return False
    
    # Check that we have all required strata
    required_archetypes = ["blog", "guestbook", "chat", "notes", "dashboard", "store", "gallery"]
    required_complexities = ["MVP", "Pro"]
    required_locales = ["en"]
    
    for archetype in required_archetypes:
        for complexity in required_complexities:
            for locale in required_locales:
                key = f"{archetype}-{complexity}-{locale}"
                if key not in strata:
                    print(f"LOCK_ERR: Missing stratum {key}")
                    return False
    
    return True


def verify_splits(splits_path: Path, artifacts: List[Path]) -> bool:
    """
    Verify that splits match artifacts.
    
    Returns:
        True if splits are valid, False otherwise
    """
    # Load splits
    splits_data = read_json(splits_path)
    split_assignments = splits_data["splits"]
    
    # Load artifacts
    train_items = read_jsonl([p for p in artifacts if p.name == "train.jsonl"][0])
    val_items = read_jsonl([p for p in artifacts if p.name == "val.jsonl"][0])
    test_items = read_jsonl([p for p in artifacts if p.name == "test.jsonl"][0])
    all_items = read_jsonl([p for p in artifacts if p.name == "golden.jsonl"][0])
    
    # Check counts
    if len(train_items) != len(split_assignments["train"]):
        print(f"LOCK_ERR: Train count mismatch: {len(train_items)} vs {len(split_assignments['train'])}")
        return False
    
    if len(val_items) != len(split_assignments["val"]):
        print(f"LOCK_ERR: Val count mismatch: {len(val_items)} vs {len(split_assignments['val'])}")
        return False
    
    if len(test_items) != len(split_assignments["test"]):
        print(f"LOCK_ERR: Test count mismatch: {len(test_items)} vs {len(split_assignments['test'])}")
        return False
    
    if len(all_items) != len(train_items) + len(val_items) + len(test_items):
        print(f"LOCK_ERR: All items count mismatch: {len(all_items)} vs {len(train_items) + len(val_items) + len(test_items)}")
        return False
    
    # Check assignments
    train_ids = {item["id"] for item in train_items}
    val_ids = {item["id"] for item in val_items}
    test_ids = {item["id"] for item in test_items}
    
    for split, slot_ids in split_assignments.items():
        expected_ids = set(slot_ids)
        if split == "train":
            if train_ids != expected_ids:
                print(f"LOCK_ERR: Train assignments mismatch")
                return False
        elif split == "val":
            if val_ids != expected_ids:
                print(f"LOCK_ERR: Val assignments mismatch")
                return False
        elif split == "test":
            if test_ids != expected_ids:
                print(f"LOCK_ERR: Test assignments mismatch")
                return False
    
    return True


@click.command()
@click.option("--schemas", required=True, help="Schemas directory path")
@click.option("--reports", required=True, help="Report file paths (comma-separated)")
@click.option("--splits", required=True, help="Splits JSON file path")
@click.option("--artifacts", required=True, help="Artifact file paths (comma-separated)")
@click.option("--out", required=True, help="Output lockfile path")
def main(schemas: str, reports: str, splits: str, artifacts: str, out: str):
    """Verify dataset integrity and generate lockfile."""
    # Convert paths
    schemas_path = Path(schemas)
    reports_paths = [Path(r.strip()) for r in reports.split(",")]
    splits_path = Path(splits)
    artifacts_paths = [Path(a.strip()) for a in artifacts.split(",")]
    
    # Find schema files
    schema_files = list(schemas_path.glob("*.schema.json"))
    
    # Load golden.jsonl to verify counts
    golden_path = [p for p in artifacts_paths if p.name == "golden.jsonl"][0]
    golden_items = read_jsonl(golden_path)
    
    # Verify counts
    if not verify_counts(golden_items):
        sys.exit(1)
    
    # Verify splits
    if not verify_splits(splits_path, artifacts_paths):
        sys.exit(1)
    
    # Generate lockfile
    lockfile = generate_lockfile(
        schemas=schema_files,
        reports=reports_paths,
        splits=splits_path,
        artifacts=artifacts_paths
    )
    
    # Write lockfile
    write_json(out, lockfile)
    
    print(f"Verified dataset integrity")
    print(f"Generated lockfile with:")
    print(f"  {len(schema_files)} schemas")
    print(f"  {len(reports_paths)} reports")
    print(f"  1 splits file")
    print(f"  {len(artifacts_paths)} artifacts")
    print(f"Wrote lockfile to {out}")


if __name__ == "__main__":
    main()
