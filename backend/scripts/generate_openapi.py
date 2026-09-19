#!/usr/bin/env python3
"""
Export OpenAPI 3.1 schema for VeriTrace AI FastAPI backend.

Used for contract validation, SDK generation, and frontend schema compatibility.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

# Ensure backend root is on PYTHONPATH
BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import app  # noqa: E402


def generate_openapi_schema(output_path: Path | str | None = None) -> dict:
    """Generate and write the OpenAPI JSON specification."""
    schema = app.openapi()
    
    if output_path is None:
        output_path = BACKEND_ROOT / "openapi.json"
    else:
        output_path = Path(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)

    print(f"OpenAPI schema successfully written to: {output_path}")
    return schema


if __name__ == "__main__":
    generate_openapi_schema()
