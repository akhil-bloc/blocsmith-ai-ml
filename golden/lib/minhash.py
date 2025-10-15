#!/usr/bin/env python3
"""
MinHash implementation for near-duplicate detection.
"""
import hashlib
from typing import Dict, List, Set, Tuple

import numpy as np
from datasketch import MinHash


def create_minhash(shingles: List[str], num_perm: int = 128, seed: int = 2025) -> MinHash:
    """
    Create a MinHash object from a list of shingles.
    
    Args:
        shingles: List of shingles (e.g., 3-grams)
        num_perm: Number of permutations
        seed: Random seed for hash functions
    
    Returns:
        MinHash object
    """
    m = MinHash(num_perm=num_perm, seed=seed)
    for s in shingles:
        # Use sha1 as specified in requirements
        m.update(s.encode('utf-8'))
    return m


def estimate_jaccard(minhash1: MinHash, minhash2: MinHash) -> float:
    """
    Estimate Jaccard similarity between two MinHash objects.
    
    Returns:
        Estimated Jaccard similarity [0.0, 1.0]
    """
    return minhash1.jaccard(minhash2)


def compute_exact_jaccard(set1: Set[str], set2: Set[str]) -> float:
    """
    Compute exact Jaccard similarity between two sets.
    
    Returns:
        Exact Jaccard similarity [0.0, 1.0]
    """
    if not set1 and not set2:
        return 1.0
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    return intersection / union if union > 0 else 0.0


def find_near_duplicates(
    items: List[Dict], 
    threshold: float = 0.85, 
    num_perm: int = 128, 
    seed: int = 2025
) -> Tuple[List[Dict], Dict]:
    """
    Find near-duplicates in a list of items using MinHash.
    
    Args:
        items: List of items with 'candidate_id' and 'spec' fields
        threshold: Jaccard similarity threshold for near-duplicates
        num_perm: Number of permutations for MinHash
        seed: Random seed for hash functions
    
    Returns:
        Tuple of (deduplicated_items, report)
    """
    from .text_norm import normalize_text, generate_word_3grams
    
    # Prepare data
    candidate_ids = [item["candidate_id"] for item in items]
    normalized_texts = [normalize_text(item["spec"]) for item in items]
    shingle_sets = [set(generate_word_3grams(text)) for text in normalized_texts]
    minhashes = [create_minhash(list(shingles), num_perm, seed) for shingles in shingle_sets]
    
    # Find connected components (clusters of near-duplicates)
    n = len(items)
    adjacency = np.zeros((n, n), dtype=bool)
    
    # Compute similarity matrix and exact Jaccard for reporting
    edges = []
    for i in range(n):
        for j in range(i+1, n):
            est_jaccard = estimate_jaccard(minhashes[i], minhashes[j])
            if est_jaccard >= threshold:
                # Compute exact Jaccard for the report
                exact_jaccard = compute_exact_jaccard(shingle_sets[i], shingle_sets[j])
                edges.append({
                    "source": candidate_ids[i],
                    "target": candidate_ids[j],
                    "jaccard": round(exact_jaccard, 4)
                })
                adjacency[i, j] = adjacency[j, i] = True
    
    # Find connected components
    components = []
    visited = np.zeros(n, dtype=bool)
    
    for i in range(n):
        if visited[i]:
            continue
            
        # BFS to find connected component
        component = []
        queue = [i]
        visited[i] = True
        
        while queue:
            node = queue.pop(0)
            component.append(node)
            
            for j in range(n):
                if adjacency[node, j] and not visited[j]:
                    visited[j] = True
                    queue.append(j)
        
        components.append(sorted(component))
    
    # For each component, keep only the item with lexicographically smallest candidate_id
    keep_indices = set()
    component_info = []
    
    for component in components:
        if len(component) == 1:
            # Single-item component, keep it
            keep_indices.add(component[0])
            component_info.append({
                "items": [candidate_ids[i] for i in component],
                "kept": candidate_ids[component[0]]
            })
        else:
            # Multi-item component, keep smallest candidate_id
            candidates = [(candidate_ids[i], i) for i in component]
            candidates.sort()  # Sort by candidate_id lexicographically
            keep_indices.add(candidates[0][1])
            component_info.append({
                "items": [cid for cid, _ in candidates],
                "kept": candidates[0][0]
            })
    
    # Create the report
    report = {
        "components": component_info,
        "edges": edges
    }
    
    # Filter items to keep
    deduplicated_items = [items[i] for i in range(n) if i in keep_indices]
    
    return deduplicated_items, report
