#!/usr/bin/env python3
"""
Utilities for canonical I/O operations with consistent formatting.
"""
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import orjson


def ensure_dir(path: Union[str, Path]) -> Path:
    """Ensure a directory exists."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def canonical_json_dumps(obj: Any) -> str:
    """
    Dump object to canonical JSON format:
    - UTF-8
    - sorted keys
    - indent=2
    - LF line endings
    - trailing LF
    """
    # Convert numpy types to Python native types
    def numpy_converter(o):
        import numpy as np
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, np.bool_):
            return bool(o)
        return o
    
    # Convert all numpy types in the object
    import json
    obj_str = json.dumps(obj, default=numpy_converter)
    obj = json.loads(obj_str)
    
    # Use orjson for performance and consistent sorting
    json_bytes = orjson.dumps(
        obj,
        option=orjson.OPT_SORT_KEYS | orjson.OPT_INDENT_2
    )
    # Convert to string and ensure trailing LF
    json_str = json_bytes.decode('utf-8')
    if not json_str.endswith('\n'):
        json_str += '\n'
    return json_str


def read_json(file_path: Union[str, Path]) -> Any:
    """Read JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def write_json(file_path: Union[str, Path], data: Any) -> None:
    """Write data to JSON file in canonical format."""
    ensure_dir(Path(file_path).parent)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(canonical_json_dumps(data))


def read_jsonl(file_path: Union[str, Path]) -> List[Dict]:
    """Read JSONL file."""
    results = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                results.append(json.loads(line))
    return results


def write_jsonl(file_path: Union[str, Path], data: List[Dict]) -> None:
    """Write data to JSONL file in canonical format."""
    ensure_dir(Path(file_path).parent)
    with open(file_path, 'w', encoding='utf-8') as f:
        for item in data:
            # Use json.dumps for JSONL (no indentation, one line per item)
            json_str = json.dumps(item, sort_keys=True, ensure_ascii=False)
            f.write(json_str + '\n')


def read_text(file_path: Union[str, Path]) -> str:
    """Read text file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def write_text(file_path: Union[str, Path], text: str) -> None:
    """Write text to file."""
    ensure_dir(Path(file_path).parent)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(text)
        if not text.endswith('\n'):
            f.write('\n')
