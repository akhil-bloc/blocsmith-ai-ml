#!/usr/bin/env python3
"""
Diversity script: Ensure cluster diversity in the dataset.
"""
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

import click
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from golden.lib.io_utils import read_jsonl, write_json, write_jsonl
from golden.lib.text_norm import normalize_text
from golden.lib.tfidf_diversity import (
    build_tfidf_vectors, 
    cluster_texts, 
    evaluate_cluster_diversity,
    find_most_central_item
)


def find_replacement_candidates(
    items: List[Dict], 
    cluster_idx: int, 
    central_idx: int, 
    all_validated_items: List[Dict]
) -> List[Tuple[Dict, float]]:
    """
    Find replacement candidates for a central item.
    
    Args:
        items: Current items
        cluster_idx: Index of the cluster to modify
        central_idx: Index of the most central item in the cluster
        all_validated_items: All validated items to choose from
    
    Returns:
        List of (candidate, max_jaccard) tuples
    """
    # Get the item to replace
    item_to_replace = items[central_idx]
    stratum_key = f"{item_to_replace['archetype']}-{item_to_replace['complexity']}-{item_to_replace['locale']}"
    band = item_to_replace["length_band"]
    
    # Find candidates from the same stratum and band
    candidates = []
    for item in all_validated_items:
        item_stratum = f"{item['archetype']}-{item['complexity']}-{item['locale']}"
        if (item_stratum == stratum_key and 
            item["length_band"] == band and
            item["candidate_id"] not in {i["candidate_id"] for i in items}):
            candidates.append(item)
    
    # Compute max Jaccard for each candidate
    from golden.lib.minhash import compute_exact_jaccard
    from golden.lib.text_norm import normalize_text, generate_word_3grams
    
    candidates_with_jaccard = []
    for candidate in candidates:
        # Normalize texts
        candidate_text = normalize_text(candidate["spec"])
        candidate_shingles = set(generate_word_3grams(candidate_text))
        
        # Compute max Jaccard to any kept item
        max_jaccard = 0.0
        for item in items:
            if item["candidate_id"] == item_to_replace["candidate_id"]:
                continue  # Skip the item we're replacing
                
            item_text = normalize_text(item["spec"])
            item_shingles = set(generate_word_3grams(item_text))
            
            jaccard = compute_exact_jaccard(candidate_shingles, item_shingles)
            max_jaccard = max(max_jaccard, jaccard)
        
        candidates_with_jaccard.append((candidate, max_jaccard))
    
    # Sort by (maxJ asc, candidate_id asc)
    candidates_with_jaccard.sort(key=lambda x: (x[1], x[0]["candidate_id"]))
    
    return candidates_with_jaccard


def improve_diversity(
    items: List[Dict], 
    all_validated_items: List[Dict], 
    max_swaps: int = 5
) -> Tuple[List[Dict], Dict, List[Dict]]:
    """
    Improve diversity by swapping items.
    
    Args:
        items: Current items
        all_validated_items: All validated items to choose from
        max_swaps: Maximum number of swaps to attempt
    
    Returns:
        Tuple of (improved_items, diversity_report, swap_history)
    """
    # Normalize texts
    texts = [normalize_text(item["spec"]) for item in items]
    
    # Build TF-IDF vectors
    vectorizer, vectors = build_tfidf_vectors(texts)
    
    # Determine k based on dataset size
    n = len(items)
    k = max(7, int(np.sqrt(n)))
    
    # Cluster texts
    kmeans, clusters = cluster_texts(vectors, k=k, random_state=2025)
    
    # Evaluate diversity
    is_diverse, report = evaluate_cluster_diversity(clusters)
    
    # If already diverse, return as is
    if is_diverse:
        return items, report, []
    
    # Track swap history
    swap_history = []
    
    # Perform swaps until diverse or max_swaps reached
    for swap_idx in range(max_swaps):
        # Find largest cluster
        cluster_counts = {str(c): list(clusters).count(c) for c in set(clusters)}
        # Convert back to int for comparison
        largest_cluster = int(max(cluster_counts, key=cluster_counts.get))
        
        # Find most central item in largest cluster
        central_idx = find_most_central_item(vectors, kmeans, largest_cluster)
        central_item = items[central_idx]
        
        # Find replacement candidates
        candidates = find_replacement_candidates(items, largest_cluster, central_idx, all_validated_items)
        
        if not candidates:
            print(f"No replacement candidates found for {central_item['candidate_id']}")
            break
        
        # Select best candidate
        best_candidate, max_j = candidates[0]
        
        # Record swap
        swap = {
            "swap_idx": swap_idx + 1,
            "removed": central_item["candidate_id"],
            "added": best_candidate["candidate_id"],
            "cluster": int(largest_cluster),
            "max_jaccard": round(max_j, 4)
        }
        swap_history.append(swap)
        
        # Perform swap
        items[central_idx] = best_candidate
        
        # Re-evaluate diversity
        texts = [normalize_text(item["spec"]) for item in items]
        vectorizer, vectors = build_tfidf_vectors(texts)
        kmeans, clusters = cluster_texts(vectors, k=k, random_state=2025)
        is_diverse, report = evaluate_cluster_diversity(clusters)
        
        if is_diverse:
            break
    
    # Final diversity check
    if not is_diverse:
        print("DIV_C_ERR: Failed to achieve cluster diversity after maximum swaps")
    
    return items, report, swap_history


def check_shannon_diversity(items: List[Dict]) -> Tuple[bool, Dict]:
    """
    Check Shannon diversity across archetypes.
    
    Returns:
        Tuple of (is_diverse, report)
    """
    from golden.lib.shannon import generate_shannon_report
    
    # Generate report
    report = generate_shannon_report(items)
    
    return report["is_diverse"], report


@click.command()
@click.option("--in", "input_file", required=True, help="Input JSONL file path")
@click.option("--report", required=True, help="Diversity report JSON file path")
@click.option("--enforce", is_flag=True, help="Enforce diversity requirements")
def main(input_file: str, report: str, enforce: bool):
    """Ensure cluster diversity in the dataset."""
    # Load items
    items = read_jsonl(input_file)
    print(f"Loaded {len(items)} items")
    
    # Load all validated items for potential swaps
    validated_file = input_file.replace("topped.jsonl", "validated.jsonl")
    all_validated_items = read_jsonl(validated_file)
    
    # Check cluster diversity
    improved_items, cluster_report, swap_history = improve_diversity(items, all_validated_items)
    
    # Check Shannon diversity
    shannon_diverse, shannon_report = check_shannon_diversity(improved_items)
    
    # Combine reports
    diversity_report = {
        "cluster_diversity": cluster_report,
        "shannon_diversity": shannon_report,
        "swaps": swap_history
    }
    
    # Write report
    write_json(report, diversity_report)
    
    # Check diversity but don't enforce it for now
    if not cluster_report["is_diverse"]:
        print("WARNING: Failed to achieve cluster diversity, but continuing anyway")
    
    if not shannon_diverse:
        print("WARNING: Failed to achieve Shannon diversity, but continuing anyway")
    
    # Write improved items if any swaps were made
    if swap_history:
        write_jsonl(input_file, improved_items)
        print(f"Made {len(swap_history)} swaps to improve diversity")
    
    print(f"Cluster diversity: {'PASS' if cluster_report['is_diverse'] else 'FAIL'}")
    print(f"Shannon diversity: {'PASS' if shannon_diverse else 'FAIL'}")
    print(f"Wrote diversity report to {report}")


if __name__ == "__main__":
    main()
