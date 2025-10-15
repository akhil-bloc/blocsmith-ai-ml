#!/usr/bin/env python3
"""
Shannon diversity calculations for archetype distribution.
"""
import math
from collections import Counter
from typing import Dict, List, Tuple


def calculate_shannon_diversity(items: List[Dict]) -> Tuple[float, float, bool]:
    """
    Calculate Shannon diversity for archetype distribution.
    
    Args:
        items: List of items with 'archetype' field
    
    Returns:
        Tuple of (H, H/Hmax, is_diverse)
    """
    # Count items per archetype
    archetypes = [item["archetype"] for item in items]
    counts = Counter(archetypes)
    
    # Calculate probabilities
    total = len(archetypes)
    probabilities = {arch: count / total for arch, count in counts.items()}
    
    # Calculate Shannon entropy H = -Σ p_a ln p_a
    h = -sum(p * math.log(p) for p in probabilities.values())
    
    # Calculate maximum possible entropy Hmax = ln(num_archetypes)
    num_archetypes = len(counts)
    h_max = math.log(num_archetypes) if num_archetypes > 0 else 0
    
    # Calculate normalized entropy H/Hmax
    h_norm = h / h_max if h_max > 0 else 0
    
    # Check if diversity threshold is met (H/Hmax ≥ 0.97)
    is_diverse = h_norm >= 0.97
    
    return round(h, 4), round(h_norm, 4), is_diverse


def generate_shannon_report(items: List[Dict]) -> Dict:
    """
    Generate a report on Shannon diversity.
    
    Args:
        items: List of items with 'archetype' field
    
    Returns:
        Report dictionary
    """
    # Count items per archetype
    archetypes = [item["archetype"] for item in items]
    counts = Counter(archetypes)
    
    # Calculate Shannon metrics
    h, h_norm, is_diverse = calculate_shannon_diversity(items)
    
    # Create report
    report = {
        "archetype_counts": dict(counts),
        "shannon_entropy": h,
        "normalized_entropy": h_norm,
        "threshold": 0.97,
        "is_diverse": is_diverse
    }
    
    return report
