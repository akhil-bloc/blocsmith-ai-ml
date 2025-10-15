#!/usr/bin/env python3
"""
Expand script: Assign rep and seq numbers to slots.
"""
import sys
from pathlib import Path
from typing import Dict, List

import click

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from golden.lib.io_utils import read_json, write_json


def expand_slots(strata: List[Dict]) -> List[Dict]:
    """
    Expand strata into individual slots with rep and seq numbers.
    
    Args:
        strata: List of stratum dictionaries
    
    Returns:
        List of expanded slot dictionaries
    """
    slots = []
    seq = 1
    
    for stratum in strata:
        archetype = stratum["archetype"]
        complexity = stratum["complexity"]
        locale = stratum["locale"]
        platform = stratum["platform"]
        count = stratum["count"]
        
        for rep in range(1, count + 1):
            # Generate slot_id
            slot_id = f"golden_{archetype}{complexity}{locale}_{platform}_rep{rep:02d}_seq{seq:03d}"
            
            slot = {
                "slot_id": slot_id,
                "archetype": archetype,
                "complexity": complexity,
                "locale": locale,
                "platform": platform,
                "rep": rep,
                "seq": seq
            }
            
            slots.append(slot)
            seq += 1
    
    return slots


@click.command()
@click.option("--in", "input_file", required=True, help="Input JSON file path")
@click.option("--out", required=True, help="Output JSON file path")
def main(input_file: str, out: str):
    """Expand strata into individual slots."""
    strata = read_json(input_file)
    slots = expand_slots(strata)
    write_json(out, slots)
    print(f"Expanded {len(strata)} strata into {len(slots)} slots")
    print(f"Wrote output to {out}")


if __name__ == "__main__":
    main()
