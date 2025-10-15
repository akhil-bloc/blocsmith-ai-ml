#!/usr/bin/env python3
"""
Digest utilities for file checksums and verification.
"""
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Union


def sha256_digest(content: Union[str, bytes]) -> str:
    """
    Calculate SHA256 digest of content.
    
    Args:
        content: String or bytes to digest
    
    Returns:
        Lowercase hex digest
    """
    if isinstance(content, str):
        content = content.encode('utf-8')
    return hashlib.sha256(content).hexdigest().lower()


def file_sha256(file_path: Union[str, Path]) -> str:
    """
    Calculate SHA256 digest of a file.
    
    Args:
        file_path: Path to file
    
    Returns:
        Lowercase hex digest
    """
    with open(file_path, 'rb') as f:
        return sha256_digest(f.read())


def sha256_prefix8(text: str) -> str:
    """
    Calculate first 8 characters of SHA256 digest.
    
    Args:
        text: String to digest
    
    Returns:
        First 8 characters of lowercase hex digest
    """
    return sha256_digest(text)[:8]


def generate_lockfile(
    schemas: List[Path],
    reports: List[Path],
    splits: Path,
    artifacts: List[Path]
) -> Dict:
    """
    Generate lockfile with digests of all files.
    
    Args:
        schemas: List of schema file paths
        reports: List of report file paths
        splits: Path to splits file
        artifacts: List of artifact file paths
    
    Returns:
        Lockfile dictionary
    """
    lockfile = {
        "schemas": {},
        "reports": {},
        "splits": {},
        "artifacts": {}
    }
    
    # Add schema digests
    for schema_path in schemas:
        name = schema_path.name
        lockfile["schemas"][name] = file_sha256(schema_path)
    
    # Add report digests
    for report_path in reports:
        name = report_path.name
        lockfile["reports"][name] = file_sha256(report_path)
    
    # Add splits digest
    lockfile["splits"][splits.name] = file_sha256(splits)
    
    # Add artifact digests
    for artifact_path in artifacts:
        name = artifact_path.name
        lockfile["artifacts"][name] = file_sha256(artifact_path)
    
    return lockfile
