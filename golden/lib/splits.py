#!/usr/bin/env python3
"""
Utilities for deterministic dataset splitting.
"""
from typing import Dict, List, Tuple


def stratify_items(items: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Stratify items by archetype, complexity, and locale.
    
    Returns:
        Dict mapping stratum key to list of items
    """
    strata = {}
    for item in items:
        # Create stratum key
        key = f"{item['archetype']}-{item['complexity']}-{item['locale']}"
        if key not in strata:
            strata[key] = []
        strata[key].append(item)
    
    # Sort items within each stratum by slot_id
    for key in strata:
        strata[key].sort(key=lambda x: x["slot_id"])
    
    return strata


def band_aware_round_robin_split(
    items: List[Dict], 
    train_cap: int = 42, 
    val_cap: int = 14, 
    test_cap: int = 14
) -> Dict[str, List[str]]:
    """
    Perform band-aware round-robin splitting.
    
    Args:
        items: List of items to split
        train_cap: Maximum number of items in train split
        val_cap: Maximum number of items in validation split
        test_cap: Maximum number of items in test split
    
    Returns:
        Dict mapping split name to list of slot_ids
    """
    # Initialize split counts and assignments
    split_counts = {"train": 0, "val": 0, "test": 0}
    split_caps = {"train": train_cap, "val": val_cap, "test": test_cap}
    assignments = {"train": [], "val": [], "test": []}
    
    # Stratify items
    strata = stratify_items(items)
    
    # Define band order
    bands = ["SHORT", "STANDARD", "EXTENDED"]
    
    # Define split order
    split_order = ["train", "val", "test"]
    
    # For each stratum
    for stratum_key, stratum_items in sorted(strata.items()):
        # Group items by band
        band_items = {band: [] for band in bands}
        for item in stratum_items:
            band = item.get("length_band")
            if band in band_items:
                band_items[band].append(item)
        
        # Sort items within each band by slot_id
        for band in bands:
            band_items[band].sort(key=lambda x: x["slot_id"])
        
        # Assign items using round-robin
        for band in bands:
            for item in band_items[band]:
                # Find next available split
                assigned = False
                for _ in range(len(split_order)):
                    for split in split_order:
                        if split_counts[split] < split_caps[split]:
                            assignments[split].append(item["slot_id"])
                            split_counts[split] += 1
                            assigned = True
                            break
                    if assigned:
                        break
                
                # If all splits are full, assign to train anyway
                if not assigned:
                    assignments["train"].append(item["slot_id"])
                    split_counts["train"] += 1
    
    return assignments
