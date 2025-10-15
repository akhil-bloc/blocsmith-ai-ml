#!/usr/bin/env python3
"""
Length band utilities for spec classification and validation.
"""
from typing import Dict, List, Tuple

from .text_norm import tokenize_text


# Band definitions
BAND_RANGES = {
    "SHORT": (250, 400),     # Original range
    "STANDARD": (401, 800),  # Adjusted range
    "EXTENDED": (601, 1500)  # Adjusted range with overlap to accommodate more items
}

# Global target mix with tolerance
GLOBAL_TARGET = {
    "SHORT": (14, 7),     # (target, tolerance)
    "STANDARD": (42, 7),
    "EXTENDED": (14, 7)
}


def count_tokens(text: str, exclude_headers: bool = True) -> int:
    """
    Count tokens in text.
    
    Args:
        text: The text to count tokens in
        exclude_headers: Whether to exclude H2 headers from the count
    
    Returns:
        Number of tokens
    """
    if exclude_headers:
        # Remove H2 headers before counting
        import re
        text = re.sub(r'^##\s+.*$', '', text, flags=re.MULTILINE)
        # Remove ACL label
        text = text.replace("### Access Control", "")
    
    tokens = tokenize_text(text)
    return len(tokens)


def determine_band(token_count: int) -> str:
    """
    Determine the length band for a given token count.
    
    Returns:
        Band name or None if not in any band
    """
    for band, (min_tokens, max_tokens) in BAND_RANGES.items():
        if min_tokens <= token_count <= max_tokens:
            return band
    return None


def validate_item_band(item: Dict, band: str) -> bool:
    """
    Validate that an item's token count falls within the specified band.
    
    Returns:
        True if valid, False otherwise
    """
    token_count = count_tokens(item["spec"])
    min_tokens, max_tokens = BAND_RANGES[band]
    return min_tokens <= token_count <= max_tokens


def count_band_distribution(items: List[Dict]) -> Dict[str, int]:
    """
    Count the distribution of items across bands.
    
    Returns:
        Dict mapping band names to counts
    """
    distribution = {band: 0 for band in BAND_RANGES}
    
    for item in items:
        band = item.get("length_band")
        if band in distribution:
            distribution[band] += 1
    
    return distribution


def validate_global_mix(distribution: Dict[str, int]) -> bool:
    """
    Validate that the global distribution meets target mix requirements.
    
    Returns:
        True if valid, False otherwise
    """
    for band, (target, tolerance) in GLOBAL_TARGET.items():
        count = distribution.get(band, 0)
        if abs(count - target) > tolerance:
            return False
    return True


def suggest_band_adjustments(items: List[Dict]) -> List[Tuple[str, str, str]]:
    """
    Suggest items to adjust to meet global mix targets.
    
    Returns:
        List of tuples (slot_id, current_band, suggested_band)
    """
    distribution = count_band_distribution(items)
    suggestions = []
    
    # Calculate how far we are from targets
    deltas = {}
    for band, (target, _) in GLOBAL_TARGET.items():
        deltas[band] = distribution.get(band, 0) - target
    
    # Identify bands that need adjustment
    bands_to_reduce = [band for band, delta in deltas.items() if delta > 0]
    bands_to_increase = [band for band, delta in deltas.items() if delta < 0]
    
    # For each band that needs reduction, suggest items to move
    for reduce_band in bands_to_reduce:
        candidates = [item for item in items if item.get("length_band") == reduce_band]
        candidates.sort(key=lambda x: x["slot_id"])  # Sort for determinism
        
        for increase_band in bands_to_increase:
            # Calculate how many to move from reduce_band to increase_band
            move_count = min(deltas[reduce_band], -deltas[increase_band])
            if move_count <= 0:
                continue
                
            for i in range(move_count):
                if i < len(candidates):
                    suggestions.append((
                        candidates[i]["slot_id"],
                        reduce_band,
                        increase_band
                    ))
                    
            # Update deltas
            deltas[reduce_band] -= move_count
            deltas[increase_band] += move_count
    
    return suggestions
