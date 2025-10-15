#!/usr/bin/env python3
"""
Validate script: Validate specs against schema and additional checks.
"""
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import click
import jsonschema

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from golden.lib.bands import count_tokens, determine_band
from golden.lib.io_utils import read_json, read_jsonl, write_jsonl
from golden.lib.lang_pii_style import check_language_confidence, check_code_style, find_pii
from golden.lib.text_norm import check_banned_network_terms


def extract_sections(spec: str) -> Dict[str, str]:
    """
    Extract H2 sections from spec.
    
    Returns:
        Dict mapping section names to content
    """
    # First, remove any H3 sections to avoid confusion
    # Replace H3 sections with their content but mark them
    spec_no_h3 = re.sub(r'###\s+([^\n]+)', r'__H3__\1', spec)
    
    # Use a more robust approach to extract H2 sections
    section_pattern = r'##\s+([^\n]+)(.*?)(?=##\s+|$)'
    matches = re.finditer(section_pattern, spec_no_h3, re.DOTALL)
    
    sections = {}
    for match in matches:
        header = match.group(1).strip()
        content = match.group(2).strip()
        sections[header] = content
    
    # Check for H3 Access Control section separately in original spec
    # This is a subsection of Feature Plan, not a main section
    acl_pattern = r'###\s+Access Control(.*?)(?=##\s+|$)'
    acl_match = re.search(acl_pattern, spec, re.DOTALL)
    if acl_match:
        # Store it separately but don't count it as a main section
        sections["_ACL"] = acl_match.group(1).strip()
    
    return sections


def validate_h2_sections(spec: str) -> Tuple[bool, str]:
    """
    Validate that spec has exactly the required H2 sections.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    required_sections = [
        "Vision",
        "Tech Stack",
        "Data Models",
        "Pages & Routes",
        "Feature Plan",
        "NFR & SLOs"
    ]
    
    # Extract sections
    sections = extract_sections(spec)
    
    # Filter out special sections like _ACL that aren't main H2 sections
    section_names = [name for name in sections.keys() if not name.startswith('_')]
    
    # Check if all required sections are present
    missing = set(required_sections) - set(section_names)
    extra = set(section_names) - set(required_sections)
    
    if missing or extra:
        error_msg = "Section validation failed: "
        if missing:
            error_msg += f"Missing sections: {', '.join(missing)}. "
        if extra:
            error_msg += f"Extra sections: {', '.join(extra)}. "
        return False, error_msg
    
    # Check if all sections have content
    empty_sections = [name for name, content in sections.items() 
                     if not content.strip() and name in required_sections]
    if empty_sections:
        error_msg = f"Section validation failed: Empty sections: {', '.join(empty_sections)}."
        return False, error_msg
    
    return True, ""


def validate_acl_block(spec: str) -> Tuple[bool, str]:
    """
    Validate that spec has ACL block with required roles and permissions.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Extract sections to check for ACL
    sections = extract_sections(spec)
    
    # Check if ACL section exists
    if "_ACL" not in sections and "### Access Control" not in spec:
        return False, "Missing Access Control section"
    
    # Check for roles
    if not re.search(r'\*\*Member\*\*:', spec, re.IGNORECASE) or \
       not re.search(r'\*\*Admin\*\*:', spec, re.IGNORECASE):
        return False, "Missing required roles (Member and Admin)"
    
    # Check for permissions
    member_permissions = re.search(r'\*\*Member\*\*:.*?`read:self`.*?`write:self`', spec, re.DOTALL)
    admin_permissions = re.search(r'\*\*Admin\*\*:.*?`read:any`.*?`write:any`.*?`manage`', spec, re.DOTALL)
    
    if not member_permissions:
        return False, "Missing required Member permissions (read:self, write:self)"
    
    if not admin_permissions:
        return False, "Missing required Admin permissions (read:any, write:any, manage)"
    
    return True, ""


def validate_platform_rules(item: Dict) -> Tuple[bool, str]:
    """
    Validate platform rules.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    platform = item.get("platform", {})
    
    # Check platform.name == "replit"
    if platform.get("name") != "replit":
        return False, "Platform name must be 'replit'"
    
    # Check server and bind consistency
    if platform.get("server") is True and platform.get("bind") != "0.0.0.0":
        return False, "If server is true, bind must be '0.0.0.0'"
    
    if platform.get("server") is False and platform.get("bind") is not None:
        return False, "If server is false, bind must be null"
    
    # Check banned network terms for non-server specs
    if platform.get("server") is False:
        if check_banned_network_terms(item.get("spec", "")):
            return False, "Non-server spec contains banned network binding terms"
    
    return True, ""


def validate_length_band(item: Dict) -> Tuple[bool, str, str]:
    """
    Validate and potentially correct length band.
    
    Returns:
        Tuple of (is_valid, error_message, corrected_band)
    """
    spec = item.get("spec", "")
    token_count = count_tokens(spec)
    declared_band = item.get("length_band")
    actual_band = determine_band(token_count)
    
    if not actual_band:
        return False, f"Token count {token_count} does not fall into any band", declared_band
    
    if declared_band != actual_band:
        return False, f"Declared band {declared_band} does not match actual band {actual_band} (token count: {token_count})", actual_band
    
    return True, "", declared_band


def validate_item(item: Dict, schema: Dict) -> Tuple[bool, List[str], Dict]:
    """
    Validate an item against schema and additional checks.
    
    Returns:
        Tuple of (is_valid, error_messages, corrected_item)
    """
    errors = []
    corrected_item = dict(item)  # Create a copy to potentially modify
    
    # Validate against JSON schema
    try:
        jsonschema.validate(item, schema)
    except jsonschema.exceptions.ValidationError as e:
        errors.append(f"Schema validation failed: {e.message}")
    
    # Validate H2 sections
    sections_valid, sections_error = validate_h2_sections(item.get("spec", ""))
    if not sections_valid:
        errors.append(sections_error)
    
    # Validate ACL block
    acl_valid, acl_error = validate_acl_block(item.get("spec", ""))
    if not acl_valid:
        errors.append(acl_error)
    
    # Validate platform rules
    platform_valid, platform_error = validate_platform_rules(item)
    if not platform_valid:
        errors.append(f"PLATFORM_ERR: {platform_error}")
    
    # Validate length band
    band_valid, band_error, corrected_band = validate_length_band(item)
    if not band_valid:
        errors.append(f"Band validation failed: {band_error}")
        corrected_item["length_band"] = corrected_band
    
    # Extract sections for language and PII checks
    spec = item.get("spec", "")
    sections = extract_sections(spec)
    
    # Check language confidence
    for section_name, section_text in sections.items():
        lang, confidence, is_valid = check_language_confidence(section_text)
        if not is_valid:
            errors.append(f"LANG_ERR: Section '{section_name}' has language '{lang}' with confidence {confidence:.4f} < 0.95")
    
    # Check for PII
    pii_matches = []
    for section_name, section_text in sections.items():
        matches = find_pii(section_text)
        if matches:
            pii_matches.extend(matches)
    
    if pii_matches:
        pii_types = set(match[0] for match in pii_matches)
        errors.append(f"PII_ERR: Found potential PII: {', '.join(pii_types)}")
    
    # Check code style
    num_blocks, num_lines, style_valid = check_code_style(spec)
    if not style_valid:
        errors.append(f"STYLE_ERR: Code blocks ({num_blocks}) or lines ({num_lines}) exceed limits (max 3 blocks, 40 lines)")
    
    return len(errors) == 0, errors, corrected_item


@click.command()
@click.option("--in", "input_file", required=True, help="Input JSONL file path")
@click.option("--schema", required=True, help="JSON schema file path")
@click.option("--out", required=True, help="Output JSONL file path")
def main(input_file: str, schema: str, out: str):
    """Validate specs against schema and additional checks."""
    # Load schema
    schema_data = read_json(schema)
    
    # Load items
    items = read_jsonl(input_file)
    
    # Validate items
    valid_items = []
    invalid_count = 0
    
    for item in items:
        is_valid, errors, corrected_item = validate_item(item, schema_data)
        
        if is_valid:
            valid_items.append(corrected_item)
        else:
            invalid_count += 1
            print(f"Invalid item {item.get('candidate_id')}:")
            for error in errors:
                print(f"  - {error}")
    
    # Write valid items
    write_jsonl(out, valid_items)
    print(f"Validated {len(items)} items: {len(valid_items)} valid, {invalid_count} invalid")
    print(f"Wrote valid items to {out}")


if __name__ == "__main__":
    main()
