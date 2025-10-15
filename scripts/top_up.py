#!/usr/bin/env python3
"""
Top-up script: Restore R=5 per stratum after deduplication.
"""
import hashlib
import sys
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

import click

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from golden.lib.digest import sha256_prefix8
from golden.lib.io_utils import read_jsonl, write_json, write_jsonl
from golden.lib.minhash import find_near_duplicates
from golden.lib.text_norm import normalize_text, generate_word_3grams


def group_by_stratum(items: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Group items by stratum (archetype, complexity, locale).
    
    Returns:
        Dict mapping stratum key to list of items
    """
    strata = defaultdict(list)
    for item in items:
        key = f"{item['archetype']}-{item['complexity']}-{item['locale']}"
        strata[key].append(item)
    return strata


def compute_max_jaccard(
    candidate: Dict, 
    kept_items: List[Dict]
) -> float:
    """
    Compute maximum Jaccard similarity between a candidate and kept items.
    
    Returns:
        Maximum Jaccard similarity
    """
    if not kept_items:
        return 0.0
    
    # Normalize and generate shingles
    candidate_text = normalize_text(candidate["spec"])
    candidate_shingles = set(generate_word_3grams(candidate_text))
    
    max_jaccard = 0.0
    for item in kept_items:
        item_text = normalize_text(item["spec"])
        item_shingles = set(generate_word_3grams(item_text))
        
        # Compute Jaccard similarity
        if not candidate_shingles and not item_shingles:
            jaccard = 1.0
        else:
            intersection = len(candidate_shingles.intersection(item_shingles))
            union = len(candidate_shingles.union(item_shingles))
            jaccard = intersection / union if union > 0 else 0.0
        
        max_jaccard = max(max_jaccard, jaccard)
    
    return max_jaccard


def find_top_up_candidates(
    deduped_items: List[Dict],
    all_items: List[Dict],
    target_count: int = 5
) -> Tuple[List[Dict], List[Dict]]:
    """
    Find candidates to top up strata to target count.
    
    Args:
        deduped_items: Items that survived deduplication
        all_items: All items including those that were deduplicated
        target_count: Target count per stratum (default: 5)
    
    Returns:
        Tuple of (topped_up_items, trace)
    """
    # Group by stratum
    deduped_by_stratum = group_by_stratum(deduped_items)
    all_by_stratum = group_by_stratum(all_items)
    
    # Track topped-up items and trace
    topped_up_items = list(deduped_items)
    trace = []
    
    # Process each stratum
    for stratum_key, stratum_items in deduped_by_stratum.items():
        archetype, complexity, locale = stratum_key.split("-")
        
        # Check if we need to top up
        current_count = len(stratum_items)
        if current_count >= target_count:
            continue
        
        # Find candidates from the same stratum that were dropped
        kept_ids = {item["candidate_id"] for item in stratum_items}
        candidates = [
            item for item in all_by_stratum[stratum_key]
            if item["candidate_id"] not in kept_ids
        ]
        
        # Compute max Jaccard for each candidate
        candidates_with_jaccard = []
        for candidate in candidates:
            max_j = compute_max_jaccard(candidate, stratum_items)
            candidates_with_jaccard.append((candidate, max_j))
        
        # Sort by (maxJ asc, candidate_id asc)
        candidates_with_jaccard.sort(key=lambda x: (x[1], x[0]["candidate_id"]))
        
        # Select candidates to fill up to target_count
        needed = target_count - current_count
        selected_candidates = []
        
        for i, (candidate, max_j) in enumerate(candidates_with_jaccard):
            if i < needed:
                # Record in trace
                trace_entry = {
                    "stratum": stratum_key,
                    "candidate_id": candidate["candidate_id"],
                    "max_jaccard": round(max_j, 4),
                    "selected": True,
                    "reason": "top_up"
                }
                trace.append(trace_entry)
                
                # Add to selected candidates
                selected_candidates.append(candidate)
            else:
                # Record rejected candidates in trace
                trace_entry = {
                    "stratum": stratum_key,
                    "candidate_id": candidate["candidate_id"],
                    "max_jaccard": round(max_j, 4),
                    "selected": False,
                    "reason": "not_needed"
                }
                trace.append(trace_entry)
        
        # If we still need more, we'll need to regenerate
        if len(selected_candidates) < needed:
            trace_entry = {
                "stratum": stratum_key,
                "message": f"Need to regenerate {needed - len(selected_candidates)} items",
                "reason": "pool_empty"
            }
            trace.append(trace_entry)
        
        # Add selected candidates to topped-up items
        topped_up_items.extend(selected_candidates)
    
    return topped_up_items, trace


def regenerate_for_stratum(
    stratum_key: str,
    attempt: int,
    seed: int
) -> List[Dict]:
    """
    Regenerate items for a stratum.
    
    Args:
        stratum_key: Stratum key (archetype-complexity-locale)
        attempt: Attempt number
        seed: Base seed
    
    Returns:
        List of regenerated items
    """
    archetype, complexity, locale = stratum_key.split("-")
    
    # Generate seed for this attempt
    attempt_seed = sha256_prefix8(f"{seed}|{archetype}|{complexity}|{attempt}")
    attempt_seed_int = int(attempt_seed, 16)
    
    # Create a temporary slot for regeneration
    slot = {
        "slot_id": f"golden_{archetype}{complexity}{locale}_replit_rep01_seq001",
        "archetype": archetype,
        "complexity": complexity,
        "locale": locale,
        "platform": "replit",
        "rep": 1,
        "seq": 1
    }
    
    # Write slot to temporary file
    temp_slot_file = Path("dist/temp_slot.json")
    write_json(temp_slot_file, [slot])
    
    # Run write script to generate variants
    temp_written_file = Path("dist/temp_written.jsonl")
    subprocess.run([
        "python", "scripts/write.py",
        "--in", str(temp_slot_file),
        "--out", str(temp_written_file),
        "--oversub", "5",  # Generate 5 variants
        "--seed", str(attempt_seed_int)
    ], check=True)
    
    # Run validate script
    temp_validated_file = Path("dist/temp_validated.jsonl")
    subprocess.run([
        "python", "scripts/validate.py",
        "--in", str(temp_written_file),
        "--schema", "schemas/golden.pre_split.schema.json",
        "--out", str(temp_validated_file)
    ], check=True)
    
    # Load validated items
    regenerated_items = read_jsonl(temp_validated_file)
    
    return regenerated_items


def assign_rep_seq(items: List[Dict]) -> List[Dict]:
    """
    Assign rep and seq numbers to topped-up items.
    
    Args:
        items: List of items
    
    Returns:
        List of items with assigned rep and seq
    """
    # Group by stratum
    by_stratum = group_by_stratum(items)
    
    # Track assigned items
    assigned_items = []
    
    # Process each stratum
    seq = 1
    for stratum_key, stratum_items in sorted(by_stratum.items()):
        # Sort by candidate_id for determinism
        stratum_items.sort(key=lambda x: x["candidate_id"])
        
        # Assign rep numbers (1 to 5)
        for rep, item in enumerate(stratum_items, 1):
            # Update rep and seq
            item["rep"] = rep
            item["seq"] = seq
            
            # Update slot_id to reflect new rep and seq
            archetype = item["archetype"]
            complexity = item["complexity"]
            locale = item["locale"]
            platform = "replit"
            
            item["slot_id"] = f"golden_{archetype}{complexity}{locale}_{platform}_rep{rep:02d}_seq{seq:03d}"
            
            # Add to assigned items
            assigned_items.append(item)
            seq += 1
    
    return assigned_items


@click.command()
@click.option("--in", "input_file", required=True, help="Input JSONL file path")
@click.option("--out", required=True, help="Output JSONL file path")
@click.option("--trace", required=True, help="Top-up trace JSON file path")
@click.option("--seed", type=int, default=2025, help="Random seed")
@click.option("--max-attempts", type=int, default=2, help="Maximum regeneration attempts per stratum")
def main(input_file: str, out: str, trace: str, seed: int, max_attempts: int):
    """Restore R=5 per stratum after deduplication."""
    # Load deduped items
    deduped_items = read_jsonl(input_file)
    print(f"Loaded {len(deduped_items)} deduplicated items")
    
    # Load all items (including those that were deduplicated)
    # For simplicity, we'll assume the validated items are at a predictable path
    validated_file = input_file.replace("deduped.jsonl", "validated.jsonl")
    all_items = read_jsonl(validated_file)
    print(f"Loaded {len(all_items)} total validated items")
    
    # Find top-up candidates
    topped_up_items, trace_entries = find_top_up_candidates(deduped_items, all_items)
    
    # Check if we need to regenerate for any strata
    by_stratum = group_by_stratum(topped_up_items)
    regeneration_needed = False
    
    for stratum_key, stratum_items in by_stratum.items():
        if len(stratum_items) < 5:
            regeneration_needed = True
            print(f"Stratum {stratum_key} has only {len(stratum_items)} items, need to regenerate")
    
    # Regenerate if needed
    if regeneration_needed:
        for stratum_key, stratum_items in by_stratum.items():
            if len(stratum_items) >= 5:
                continue
                
            needed = 5 - len(stratum_items)
            print(f"Regenerating {needed} items for stratum {stratum_key}")
            
            for attempt in range(1, max_attempts + 1):
                # Regenerate items
                regenerated = regenerate_for_stratum(stratum_key, attempt, seed)
                
                # Run deduplication against current items
                combined = list(topped_up_items) + regenerated
                deduplicated, _ = find_near_duplicates(combined, threshold=0.85, num_perm=128, seed=seed)
                
                # Check if we got new items
                new_items = [item for item in deduplicated if item["candidate_id"] not in {i["candidate_id"] for i in topped_up_items}]
                
                # Record in trace
                for item in regenerated:
                    is_kept = item["candidate_id"] in {i["candidate_id"] for i in new_items}
                    trace_entry = {
                        "stratum": stratum_key,
                        "candidate_id": item["candidate_id"],
                        "selected": is_kept,
                        "reason": "regenerated",
                        "attempt": attempt
                    }
                    trace_entries.append(trace_entry)
                
                # Add new items to topped-up items
                topped_up_items.extend(new_items)
                
                # Check if we have enough
                current_count = len([item for item in topped_up_items if f"{item['archetype']}-{item['complexity']}-{item['locale']}" == stratum_key])
                if current_count >= 5:
                    break
            
            # Check if we still don't have enough
            current_count = len([item for item in topped_up_items if f"{item['archetype']}-{item['complexity']}-{item['locale']}" == stratum_key])
            if current_count < 5:
                print(f"TOPUP_ERR: Failed to top up stratum {stratum_key} to 5 items")
                sys.exit(1)
    
    # Assign rep and seq numbers
    final_items = assign_rep_seq(topped_up_items)
    
    # Add source_candidate_id for items that were topped up
    for item in final_items:
        if "source_candidate_id" not in item:
            item["source_candidate_id"] = item["candidate_id"]
    
    # Write topped-up items
    write_jsonl(out, final_items)
    
    # Write trace
    write_json(trace, trace_entries)
    
    # Print stats
    print(f"Topped up to {len(final_items)} items")
    print(f"Wrote topped-up items to {out}")
    print(f"Wrote top-up trace to {trace}")


if __name__ == "__main__":
    main()
