#!/usr/bin/env python3
"""
Unit tests for band counting functionality.
"""
import sys
import unittest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from golden.lib.bands import (
    BAND_RANGES,
    count_tokens,
    determine_band,
    validate_item_band,
    count_band_distribution,
    validate_global_mix
)


class TestBands(unittest.TestCase):
    """Test band counting functionality."""
    
    def test_count_tokens(self):
        """Test token counting."""
        # Test with simple text
        text = "This is a simple test."
        self.assertEqual(count_tokens(text), 5)
        
        # Test with headers
        text = "## This is a header\nThis is content."
        self.assertEqual(count_tokens(text), 3)  # "This is content"
        self.assertEqual(count_tokens(text, exclude_headers=False), 7)  # Include header
        
        # Test with ACL label
        text = "Some text.\n### Access Control\nMore text."
        self.assertEqual(count_tokens(text), 5)  # "Some text More text"
    
    def test_determine_band(self):
        """Test band determination."""
        # Test each band
        self.assertEqual(determine_band(250), "SHORT")
        self.assertEqual(determine_band(400), "SHORT")
        self.assertEqual(determine_band(600), "STANDARD")
        self.assertEqual(determine_band(900), "STANDARD")
        self.assertEqual(determine_band(1100), "EXTENDED")
        self.assertEqual(determine_band(1500), "EXTENDED")
        
        # Test out of range
        self.assertIsNone(determine_band(200))
        self.assertIsNone(determine_band(500))
        self.assertIsNone(determine_band(1000))
        self.assertIsNone(determine_band(1600))
    
    def test_validate_item_band(self):
        """Test item band validation."""
        # Create test items
        short_item = {"spec": " ".join(["word"] * 300)}
        standard_item = {"spec": " ".join(["word"] * 700)}
        extended_item = {"spec": " ".join(["word"] * 1200)}
        
        # Test validation
        self.assertTrue(validate_item_band(short_item, "SHORT"))
        self.assertFalse(validate_item_band(short_item, "STANDARD"))
        self.assertFalse(validate_item_band(short_item, "EXTENDED"))
        
        self.assertFalse(validate_item_band(standard_item, "SHORT"))
        self.assertTrue(validate_item_band(standard_item, "STANDARD"))
        self.assertFalse(validate_item_band(standard_item, "EXTENDED"))
        
        self.assertFalse(validate_item_band(extended_item, "SHORT"))
        self.assertFalse(validate_item_band(extended_item, "STANDARD"))
        self.assertTrue(validate_item_band(extended_item, "EXTENDED"))
    
    def test_count_band_distribution(self):
        """Test band distribution counting."""
        # Create test items
        items = [
            {"length_band": "SHORT"},
            {"length_band": "SHORT"},
            {"length_band": "STANDARD"},
            {"length_band": "STANDARD"},
            {"length_band": "STANDARD"},
            {"length_band": "EXTENDED"}
        ]
        
        # Test distribution
        distribution = count_band_distribution(items)
        self.assertEqual(distribution["SHORT"], 2)
        self.assertEqual(distribution["STANDARD"], 3)
        self.assertEqual(distribution["EXTENDED"], 1)
    
    def test_validate_global_mix(self):
        """Test global mix validation."""
        # Test valid distribution (within tolerance)
        valid_distribution = {"SHORT": 10, "STANDARD": 45, "EXTENDED": 15}
        self.assertTrue(validate_global_mix(valid_distribution))
        
        # Test invalid distributions
        invalid_short = {"SHORT": 5, "STANDARD": 45, "EXTENDED": 20}  # SHORT too low
        self.assertFalse(validate_global_mix(invalid_short))
        
        invalid_standard = {"SHORT": 14, "STANDARD": 30, "EXTENDED": 26}  # STANDARD too low
        self.assertFalse(validate_global_mix(invalid_standard))
        
        invalid_extended = {"SHORT": 20, "STANDARD": 45, "EXTENDED": 5}  # EXTENDED too low
        self.assertFalse(validate_global_mix(invalid_extended))


if __name__ == "__main__":
    unittest.main()
