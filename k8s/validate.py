#!/usr/bin/env python3
"""Structural validation for the manifests in this directory.

Not a substitute for `kubectl apply --dry-run=server`, but catches YAML
syntax errors and missing required top-level fields without needing a
cluster, kubectl, or podman available.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

REQUIRED_TOP_LEVEL = ("apiVersion", "kind", "metadata")


def validate_file(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        docs = [doc for doc in yaml.safe_load_all(path.read_text()) if doc is not None]
    except yaml.YAMLError as exc:
        return [f"{path}: YAML parse error: {exc}"]

    if not docs:
        errors.append(f"{path}: file contains no documents")

    for i, doc in enumerate(docs):
        if not isinstance(doc, dict):
            errors.append(f"{path}[{i}]: document is not a mapping")
            continue
        for field in REQUIRED_TOP_LEVEL:
            if field not in doc:
                errors.append(f"{path}[{i}]: missing required field {field!r}")
        metadata = doc.get("metadata")
        if isinstance(metadata, dict) and "name" not in metadata:
            errors.append(f"{path}[{i}]: metadata missing 'name'")
    return errors


def main() -> int:
    k8s_dir = Path(__file__).parent
    files = sorted(k8s_dir.glob("*.yaml"))
    all_errors: list[str] = []
    for path in files:
        all_errors.extend(validate_file(path))

    if all_errors:
        for error in all_errors:
            print(error)
        return 1

    print(f"OK: {len(files)} manifest file(s) validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
