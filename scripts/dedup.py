#!/usr/bin/env python3
"""
Dedup script: Remove near-duplicate specs using MinHash.
"""
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

import click

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from golden.lib.io_utils import read_jsonl, write_json, write_jsonl
from golden.lib.minhash import find_near_duplicates
from golden.lib.text_norm import normalize_text, generate_word_3grams


@click.command()
@click.option("--in", "input_file", required=True, help="Input JSONL file path")
@click.option("--out", required=True, help="Output JSONL file path")
@click.option("--report", required=True, help="Deduplication report JSON file path")
@click.option("--seed", type=int, default=2025, help="Random seed for MinHash")
@click.option("--threshold", type=float, default=0.85, help="Jaccard similarity threshold")
def main(input_file: str, out: str, report: str, seed: int, threshold: float):
    """Remove near-duplicate specs using MinHash."""
    # Load items
    items = read_jsonl(input_file)
    print(f"Loaded {len(items)} items")
    
    # Find near-duplicates
    deduplicated_items, dedup_report = find_near_duplicates(
        items, 
        threshold=threshold, 
        num_perm=128, 
        seed=seed
    )
    
    # Write deduplicated items
    write_jsonl(out, deduplicated_items)
    
    # Write report
    write_json(report, dedup_report)
    
    # Print stats
    num_dropped = len(items) - len(deduplicated_items)
    print(f"Removed {num_dropped} near-duplicate items")
    print(f"Kept {len(deduplicated_items)} unique items")
    
    # Log drops
    for component in dedup_report["components"]:
        if len(component["items"]) > 1:
            kept = component["kept"]
            dropped = [item for item in component["items"] if item != kept]
            for item in dropped:
                print(f"DEDUP_DROP: {item} (kept {kept})")
    
    print(f"Wrote deduplicated items to {out}")
    print(f"Wrote deduplication report to {report}")


if __name__ == "__main__":
    main()
