#!/usr/bin/env python3
"""
Unit tests for dataset splitting functionality.
"""
import sys
import unittest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from golden.lib.splits import (
    stratify_items,
    band_aware_round_robin_split
)


class TestSplits(unittest.TestCase):
    """Test dataset splitting functionality."""
    
    def setUp(self):
        """Set up test data."""
        # Create test items
        self.items = []
        
        # Create 2 strata with 5 items each
        archetypes = ["blog", "notes"]
        complexities = ["MVP"]
        locale = "en"
        bands = ["SHORT", "STANDARD", "STANDARD", "STANDARD", "EXTENDED"]
        
        seq = 1
        for archetype in archetypes:
            for complexity in complexities:
                for rep in range(1, 6):
                    slot_id = f"golden_{archetype}{complexity}{locale}_replit_rep{rep:02d}_seq{seq:03d}"
                    self.items.append({
                        "slot_id": slot_id,
                        "archetype": archetype,
                        "complexity": complexity,
                        "locale": locale,
                        "rep": rep,
                        "seq": seq,
                        "length_band": bands[rep - 1]
                    })
                    seq += 1
    
    def test_stratify_items(self):
        """Test item stratification."""
        # Stratify items
        strata = stratify_items(self.items)
        
        # Check that we have the expected strata
        self.assertEqual(len(strata), 2)
        self.assertIn("blog-MVP-en", strata)
        self.assertIn("notes-MVP-en", strata)
        
        # Check that each stratum has 5 items
        self.assertEqual(len(strata["blog-MVP-en"]), 5)
        self.assertEqual(len(strata["notes-MVP-en"]), 5)
    
    def test_band_aware_round_robin_split(self):
        """Test band-aware round-robin splitting."""
        # Perform split
        split_assignments = band_aware_round_robin_split(
            self.items,
            train_cap=6,
            val_cap=2,
            test_cap=2
        )
        
        # Check that we have the expected splits
        self.assertIn("train", split_assignments)
        self.assertIn("val", split_assignments)
        self.assertIn("test", split_assignments)
        
        # Check split counts
        self.assertEqual(len(split_assignments["train"]), 6)
        self.assertEqual(len(split_assignments["val"]), 2)
        self.assertEqual(len(split_assignments["test"]), 2)
        
        # Check that all items are assigned
        all_assigned = set()
        for split, slot_ids in split_assignments.items():
            all_assigned.update(slot_ids)
        
        self.assertEqual(len(all_assigned), 10)
        self.assertEqual(len(all_assigned), len(self.items))
        
        # Check that each item is assigned to exactly one split
        item_slots = {item["slot_id"] for item in self.items}
        self.assertEqual(all_assigned, item_slots)
        
        # Check that there's no overlap between splits
        self.assertEqual(len(set(split_assignments["train"]) & set(split_assignments["val"])), 0)
        self.assertEqual(len(set(split_assignments["train"]) & set(split_assignments["test"])), 0)
        self.assertEqual(len(set(split_assignments["val"]) & set(split_assignments["test"])), 0)
        
        # Check that SHORT items are distributed first
        short_items = [item["slot_id"] for item in self.items if item["length_band"] == "SHORT"]
        self.assertTrue(short_items[0] in split_assignments["train"])
        self.assertTrue(short_items[1] in split_assignments["val"])


if __name__ == "__main__":
    unittest.main()
