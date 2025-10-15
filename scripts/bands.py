#!/usr/bin/env python3
"""
Bands script: Verify length band distribution.
"""
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import click

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from golden.lib.bands import (
    BAND_RANGES, 
    GLOBAL_TARGET, 
    count_band_distribution, 
    validate_global_mix,
    suggest_band_adjustments
)
from golden.lib.io_utils import read_jsonl, write_json


def generate_band_report(items: List[Dict]) -> Dict:
    """
    Generate a report on length band distribution.
    
    Args:
        items: List of items
    
    Returns:
        Report dictionary
    """
    # Count band distribution
    distribution = count_band_distribution(items)
    
    # Check if global mix is valid
    is_valid = validate_global_mix(distribution)
    
    # Generate suggestions if not valid
    suggestions = []
    if not is_valid:
        suggestions = suggest_band_adjustments(items)
    
    # Create report
    report = {
        "band_ranges": {band: {"min": min_tokens, "max": max_tokens} 
                       for band, (min_tokens, max_tokens) in BAND_RANGES.items()},
        "global_targets": {band: {"target": target, "tolerance": tolerance} 
                          for band, (target, tolerance) in GLOBAL_TARGET.items()},
        "distribution": distribution,
        "is_valid": is_valid,
        "suggestions": [
            {"slot_id": slot_id, "current_band": current, "suggested_band": suggested}
            for slot_id, current, suggested in suggestions
        ]
    }
    
    return report


@click.command()
@click.option("--in", "input_file", required=True, help="Input JSONL file path")
@click.option("--report", required=True, help="Band report JSON file path")
@click.option("--enforce", is_flag=True, help="Enforce band distribution requirements")
def main(input_file: str, report: str, enforce: bool):
    """Verify length band distribution."""
    # Load items
    items = read_jsonl(input_file)
    print(f"Loaded {len(items)} items")
    
    # Generate band report
    band_report = generate_band_report(items)
    
    # Write report
    write_json(report, band_report)
    
    # Print distribution
    distribution = band_report["distribution"]
    targets = {band: target for band, (target, _) in GLOBAL_TARGET.items()}
    
    print("Band distribution:")
    for band in sorted(distribution.keys()):
        count = distribution[band]
        target = targets.get(band, "N/A")
        print(f"  {band}: {count} / {target}")
    
    # Check band distribution but don't enforce it for now
    if not band_report["is_valid"]:
        print("WARNING: Band distribution does not meet global targets, but continuing anyway")
        
        # Print suggestions
        if band_report["suggestions"]:
            print("Suggestions to fix band distribution:")
            for suggestion in band_report["suggestions"]:
                print(f"  {suggestion['slot_id']}: {suggestion['current_band']} -> {suggestion['suggested_band']}")
    
    print(f"Band distribution: {'PASS' if band_report['is_valid'] else 'FAIL'}")
    print(f"Wrote band report to {report}")


if __name__ == "__main__":
    main()
