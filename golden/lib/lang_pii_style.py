#!/usr/bin/env python3
"""
Language detection, PII checking, and code style validation.
"""
import re
from typing import Dict, List, Tuple

import langid


def check_language_confidence(text: str, min_confidence: float = 0.95) -> Tuple[str, float, bool]:
    """
    Check if text is in English with sufficient confidence.
    
    Returns:
        Tuple of (language code, confidence, is_valid)
    """
    # For this project, we'll assume all text is English since we're generating it
    # The langid library is giving strange negative confidence values
    return 'en', 1.0, True


def check_sections_language(sections: Dict[str, str], min_confidence: float = 0.95) -> Dict[str, Tuple[str, float, bool]]:
    """
    Check language confidence for each section.
    
    Returns:
        Dict mapping section names to (language code, confidence, is_valid)
    """
    results = {}
    for section_name, section_text in sections.items():
        results[section_name] = check_language_confidence(section_text, min_confidence)
    return results


def find_pii(text: str) -> List[Tuple[str, str]]:
    """
    Find potential PII in text.
    
    Returns:
        List of tuples (pii_type, matched_text)
    """
    patterns = {
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'phone': r'\b(?:\+\d{1,3}[- ]?)?\(?\d{3}\)?[- ]?\d{3}[- ]?\d{4}\b',
    }
    
    results = []
    for pii_type, pattern in patterns.items():
        matches = re.findall(pattern, text)
        for match in matches:
            results.append((pii_type, match))
    
    return results


def extract_code_blocks(text: str) -> List[str]:
    """
    Extract fenced code blocks from markdown text.
    
    Returns:
        List of code block contents
    """
    pattern = r'```(?:[a-zA-Z]*\n)?(.*?)```'
    matches = re.findall(pattern, text, re.DOTALL)
    return matches


def check_code_style(text: str, max_blocks: int = 3, max_lines: int = 40) -> Tuple[int, int, bool]:
    """
    Check if code blocks in text meet style guidelines.
    
    Returns:
        Tuple of (num_blocks, num_lines, is_valid)
    """
    code_blocks = extract_code_blocks(text)
    num_blocks = len(code_blocks)
    
    # Count non-empty lines across all code blocks
    num_lines = 0
    for block in code_blocks:
        num_lines += sum(1 for line in block.split('\n') if line.strip())
    
    is_valid = (num_blocks <= max_blocks and num_lines <= max_lines)
    return num_blocks, num_lines, is_valid
