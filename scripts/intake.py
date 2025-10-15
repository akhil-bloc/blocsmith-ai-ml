#!/usr/bin/env python3
"""
Intake script: Generate the initial set of strata.
"""
import sys
from pathlib import Path
from typing import Dict, List

import click

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from golden.lib.io_utils import write_json


def generate_strata() -> List[Dict]:
    """
    Generate the 14 strata with desired counts.
    
    Returns:
        List of stratum dictionaries
    """
    archetypes = ["blog", "guestbook", "chat", "notes", "dashboard", "store", "gallery"]
    complexities = ["MVP", "Pro"]
    locale = "en"
    
    strata = []
    for archetype in archetypes:
        for complexity in complexities:
            stratum = {
                "archetype": archetype,
                "complexity": complexity,
                "locale": locale,
                "count": 5,  # R=5 per stratum
                "platform": "replit"
            }
            strata.append(stratum)
    
    return strata


@click.command()
@click.option("--out", required=True, help="Output JSON file path")
def main(out: str):
    """Generate the initial set of strata."""
    strata = generate_strata()
    write_json(out, strata)
    print(f"Generated {len(strata)} strata with R=5 per stratum")
    print(f"Total slots: {sum(s['count'] for s in strata)}")
    print(f"Wrote output to {out}")


if __name__ == "__main__":
    main()
