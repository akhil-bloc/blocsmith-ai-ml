#!/usr/bin/env python3
"""
Text normalization utilities for consistent processing.
"""
import re
from typing import List, Set

import regex
from bs4 import BeautifulSoup


def html_unescape(text: str) -> str:
    """Unescape HTML entities."""
    return BeautifulSoup(text, "html.parser").get_text()


def strip_yaml_frontmatter(text: str) -> str:
    """Remove YAML frontmatter from markdown text."""
    pattern = r'^---\s*\n.*?\n---\s*\n'
    return re.sub(pattern, '', text, flags=re.DOTALL)


def strip_h2_headers(text: str) -> str:
    """Remove H2 headers from markdown text."""
    return re.sub(r'^##\s+.*$', '', text, flags=re.MULTILINE)


def strip_literals(text: str, literals: List[str]) -> str:
    """Remove specific literal strings from text."""
    result = text
    for literal in literals:
        result = result.replace(literal, '')
    return result


def strip_fenced_code(text: str) -> str:
    """Remove fenced code blocks from markdown text."""
    return re.sub(r'```[^`]*```', '', text, flags=re.DOTALL)


def normalize_text(text: str) -> str:
    """
    Apply all normalization steps:
    - HTML unescape
    - Strip YAML frontmatter
    - Drop H2 headers
    - Drop literals ["replit.toml", "replit.nix", "0.0.0.0"]
    - Drop all fenced code
    """
    literals = ["replit.toml", "replit.nix", "0.0.0.0"]
    
    text = html_unescape(text)
    text = strip_yaml_frontmatter(text)
    text = strip_h2_headers(text)
    text = strip_literals(text, literals)
    text = strip_fenced_code(text)
    
    return text


def tokenize_text(text: str) -> List[str]:
    """
    Tokenize text into lowercase ASCII word tokens.
    """
    # Extract ASCII word tokens and convert to lowercase
    tokens = re.findall(r'\b[a-zA-Z0-9_]+\b', text.lower())
    return tokens


def generate_ngrams(tokens: List[str], n: int) -> List[str]:
    """Generate n-grams from tokens."""
    return [' '.join(tokens[i:i+n]) for i in range(len(tokens) - n + 1)]


def generate_word_3grams(text: str) -> List[str]:
    """
    Generate stride-1 word 3-grams from normalized text.
    """
    tokens = tokenize_text(text)
    return generate_ngrams(tokens, 3)


def check_banned_network_terms(text: str) -> bool:
    """
    Check if text contains banned network binding terms (case-insensitive):
    - \bserver(?!less)\b
    - \bsockets?\b
    - \bbind(?:ing)?\s+0.0.0.0\b
    - \b(?:listen|socket|port|host)\b
    
    Returns True if banned terms are found, False otherwise.
    """
    # Ignore the term "hosting" which might be part of legitimate content
    text = re.sub(r'\bhosting\b', '', text, flags=re.IGNORECASE)
    
    patterns = [
        r'\bserver(?!less)\b',
        r'\bsockets?\b',
        r'\bbind(?:ing)?\s+0\.0\.0\.0\b',
        r'\b(?:listen|socket|port)\b',
        r'\bhost\b(?!ing)'  # Match 'host' but not as part of 'hosting'
    ]
    
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    
    return False
