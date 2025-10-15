#!/usr/bin/env python3
"""
Unit tests for MinHash functionality.
"""
import sys
import unittest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from golden.lib.minhash import (
    create_minhash,
    estimate_jaccard,
    compute_exact_jaccard,
    find_near_duplicates
)


class TestMinHash(unittest.TestCase):
    """Test MinHash functionality."""
    
    def test_create_minhash(self):
        """Test MinHash creation."""
        # Create MinHash objects
        shingles1 = ["a b c", "b c d", "c d e"]
        minhash1 = create_minhash(shingles1, num_perm=128, seed=2025)
        
        # Check that we get the same hash with the same input and seed
        minhash2 = create_minhash(shingles1, num_perm=128, seed=2025)
        self.assertEqual(minhash1.digest(), minhash2.digest())
        
        # Check that we get a different hash with a different seed
        minhash3 = create_minhash(shingles1, num_perm=128, seed=1234)
        self.assertNotEqual(minhash1.digest(), minhash3.digest())
    
    def test_jaccard_estimation(self):
        """Test Jaccard similarity estimation."""
        # Create sets with known Jaccard similarity
        set1 = set(["a", "b", "c", "d", "e"])
        set2 = set(["c", "d", "e", "f", "g"])
        exact_jaccard = 3 / 7  # |intersection| / |union| = 3 / 7
        
        # Create MinHash objects
        minhash1 = create_minhash(list(set1), num_perm=128, seed=2025)
        minhash2 = create_minhash(list(set2), num_perm=128, seed=2025)
        
        # Estimate Jaccard similarity
        estimated_jaccard = estimate_jaccard(minhash1, minhash2)
        
        # Check that estimation is close to exact value
        self.assertAlmostEqual(estimated_jaccard, exact_jaccard, delta=0.1)
    
    def test_compute_exact_jaccard(self):
        """Test exact Jaccard computation."""
        # Test with non-empty sets
        set1 = set(["a", "b", "c", "d", "e"])
        set2 = set(["c", "d", "e", "f", "g"])
        self.assertEqual(compute_exact_jaccard(set1, set2), 3 / 7)
        
        # Test with empty sets
        self.assertEqual(compute_exact_jaccard(set(), set()), 1.0)
        self.assertEqual(compute_exact_jaccard(set(["a"]), set()), 0.0)
    
    def test_find_near_duplicates(self):
        """Test near-duplicate detection."""
        # Create test items
        items = [
            {"candidate_id": "item1", "spec": "This is a test document about cats and dogs."},
            {"candidate_id": "item2", "spec": "This is a test document about cats and dogs."},  # Duplicate of item1
            {"candidate_id": "item3", "spec": "This document is about birds and fish."},
            {"candidate_id": "item4", "spec": "This document discusses birds and their habitats."}  # Similar to item3
        ]
        
        # Find near-duplicates
        deduplicated, report = find_near_duplicates(items, threshold=0.5, num_perm=128, seed=2025)
        
        # Check that we found the expected duplicates
        self.assertEqual(len(deduplicated), 2)  # Should keep item1 and item3
        self.assertEqual(deduplicated[0]["candidate_id"], "item1")
        self.assertEqual(deduplicated[1]["candidate_id"], "item3")
        
        # Check the report
        self.assertEqual(len(report["components"]), 2)  # Two components
        
        # Check edges
        edges = report["edges"]
        self.assertEqual(len(edges), 2)  # Two edges: item1-item2 and item3-item4


if __name__ == "__main__":
    unittest.main()
