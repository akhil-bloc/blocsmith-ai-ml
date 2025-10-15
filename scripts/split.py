#!/usr/bin/env python3
"""
Split script: Split dataset into train/val/test.
"""
import sys
from pathlib import Path
from typing import Dict, List

import click

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from golden.lib.digest import sha256_digest
from golden.lib.io_utils import read_jsonl, write_json
from golden.lib.splits import band_aware_round_robin_split


@click.command()
@click.option("--in", "input_file", required=True, help="Input JSONL file path")
@click.option("--splits", required=True, help="Splits JSON file path")
@click.option("--seed", type=int, help="Random seed (will be ignored)")
def main(input_file: str, splits: str, seed: int = None):
    """Split dataset into train/val/test."""
    # Warn if seed is provided
    if seed is not None:
        print(f"WARN SPLIT_SEED_IGNORED {seed}")
    
    # Load items
    items = read_jsonl(input_file)
    print(f"Loaded {len(items)} items")
    
    # Perform band-aware round-robin split
    split_assignments = band_aware_round_robin_split(
        items, 
        train_cap=42, 
        val_cap=14, 
        test_cap=14
    )
    
    # Count items per split
    split_counts = {split: len(ids) for split, ids in split_assignments.items()}
    
    # Calculate digest of splits
    splits_digest = sha256_digest(str(split_assignments))
    
    # Create splits object
    splits_obj = {
        "splits": split_assignments,
        "counts": split_counts,
        "digest": splits_digest
    }
    
    # Write splits
    write_json(splits, splits_obj)
    
    # Print stats
    print("Split counts:")
    for split, count in split_counts.items():
        print(f"  {split}: {count}")
    print(f"Total: {sum(split_counts.values())}")
    print(f"Wrote splits to {splits}")
    print(f"Splits digest: {splits_digest}")


if __name__ == "__main__":
    main()
