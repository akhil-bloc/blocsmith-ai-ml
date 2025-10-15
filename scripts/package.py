#!/usr/bin/env python3
"""
Package script: Create final dataset files.
"""
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import click
import jsonschema

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from golden.lib.io_utils import read_json, read_jsonl, write_jsonl


def prepare_final_item(item: Dict, split: str) -> Dict:
    """
    Prepare an item for the final dataset.
    
    Args:
        item: Input item
        split: Split assignment
    
    Returns:
        Final item
    """
    # Create a copy to modify
    final_item = dict(item)
    
    # Set id equal to slot_id
    final_item["id"] = item["slot_id"]
    
    # Add split
    final_item["split"] = split
    
    # Ensure source_candidate_id is present
    if "source_candidate_id" not in final_item:
        final_item["source_candidate_id"] = item["candidate_id"]
    
    # Remove candidate_id as it's not allowed in the final schema
    if "candidate_id" in final_item:
        del final_item["candidate_id"]
    
    return final_item


def validate_final_items(items: List[Dict], schema_path: str) -> Tuple[bool, List[str]]:
    """
    Validate items against the final schema.
    
    Args:
        items: List of items to validate
        schema_path: Path to JSON schema
    
    Returns:
        Tuple of (is_valid, errors)
    """
    # Load schema
    with open(schema_path, "r") as f:
        schema = json.load(f)
    
    # Validate each item
    errors = []
    for i, item in enumerate(items):
        try:
            jsonschema.validate(item, schema)
        except jsonschema.exceptions.ValidationError as e:
            errors.append(f"Item {i} ({item.get('id', 'unknown')}): {e.message}")
    
    return len(errors) == 0, errors


@click.command()
@click.option("--in", "input_file", required=True, help="Input JSONL file path")
@click.option("--splits", required=True, help="Splits JSON file path")
@click.option("--out-train", required=True, help="Output train JSONL file path")
@click.option("--out-val", required=True, help="Output validation JSONL file path")
@click.option("--out-test", required=True, help="Output test JSONL file path")
@click.option("--out-all", required=True, help="Output combined JSONL file path")
@click.option("--schema", default="schemas/golden.final.schema.json", help="Final schema path")
def main(input_file: str, splits: str, out_train: str, out_val: str, out_test: str, out_all: str, schema: str):
    """Create final dataset files."""
    # Load items
    items = read_jsonl(input_file)
    print(f"Loaded {len(items)} items")
    
    # Load splits
    splits_data = read_json(splits)
    split_assignments = splits_data["splits"]
    
    # Create a mapping from slot_id to item
    item_map = {item["slot_id"]: item for item in items}
    
    # Create split datasets
    train_items = []
    val_items = []
    test_items = []
    
    for split, slot_ids in split_assignments.items():
        for slot_id in slot_ids:
            if slot_id not in item_map:
                print(f"ERROR: Slot ID {slot_id} not found in items")
                continue
                
            item = item_map[slot_id]
            final_item = prepare_final_item(item, split)
            
            if split == "train":
                train_items.append(final_item)
            elif split == "val":
                val_items.append(final_item)
            elif split == "test":
                test_items.append(final_item)
    
    # Sort items by id
    train_items.sort(key=lambda x: x["id"])
    val_items.sort(key=lambda x: x["id"])
    test_items.sort(key=lambda x: x["id"])
    
    # Combine all items
    all_items = train_items + val_items + test_items
    all_items.sort(key=lambda x: x["id"])
    
    # Validate against final schema
    is_valid, errors = validate_final_items(all_items, schema)
    if not is_valid:
        print("PKG_ERR: Validation against final schema failed")
        for error in errors:
            print(f"  {error}")
        sys.exit(1)
    
    # Write output files
    write_jsonl(out_train, train_items)
    write_jsonl(out_val, val_items)
    write_jsonl(out_test, test_items)
    write_jsonl(out_all, all_items)
    
    # Print stats
    print(f"Train: {len(train_items)} items")
    print(f"Val: {len(val_items)} items")
    print(f"Test: {len(test_items)} items")
    print(f"Total: {len(all_items)} items")
    print(f"Wrote output files:")
    print(f"  {out_train}")
    print(f"  {out_val}")
    print(f"  {out_test}")
    print(f"  {out_all}")


if __name__ == "__main__":
    main()