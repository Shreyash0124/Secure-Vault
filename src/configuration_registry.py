"""Persistent local metadata for SecureVault-generated configurations.

This registry stores metadata and audit summaries only. Terraform files remain
unchanged, and no AWS APIs or cloud resources are accessed.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from infrastructure_viewer import GENERATED_DIR, PROJECT_ROOT, inspect_configuration

REGISTRY_FILE = GENERATED_DIR / ".securevault_registry.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load() -> dict[str, dict[str, Any]]:
    if not REGISTRY_FILE.exists():
        return {}
    try:
        data = json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, UnicodeError, json.JSONDecodeError):
        # Do not crash inventory if the optional metadata file is damaged.
        return {}


def _save(data: dict[str, dict[str, Any]]) -> None:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    temporary = REGISTRY_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(REGISTRY_FILE)


def _key(terraform_file: str | Path) -> str:
    path = Path(terraform_file).resolve()
    try:
        return path.relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def record_configuration(terraform_file: str | Path) -> dict[str, Any]:
    """Record a generated configuration without modifying its Terraform file."""
    path = Path(terraform_file).resolve()
    details = inspect_configuration(path)
    data = _load()
    key = _key(path)
    previous = data.get(key, {})
    data[key] = {
        "terraform_file": key,
        "bucket_name": details.get("bucket_name", "Unknown"),
        "encryption": details.get("encryption", "Unknown"),
        "versioning": details.get("versioning", "Unknown"),
        "public_access": details.get("public_access", "Unknown"),
        "generated_at": previous.get("generated_at", _now()),
        "latest_audit": previous.get("latest_audit"),
    }
    _save(data)
    return data[key]


def record_audit(terraform_file: str | Path, report: dict[str, Any]) -> dict[str, Any]:
    """Persist the latest local audit summary for a configuration."""
    path = Path(terraform_file).resolve()
    data = _load()
    key = _key(path)
    if key not in data:
        record_configuration(path)
        data = _load()
    entry = data[key]
    entry["latest_audit"] = {**report, "audited_at": _now()}
    data[key] = entry
    _save(data)
    return entry


def get_configuration_record(terraform_file: str | Path) -> dict[str, Any] | None:
    """Return saved metadata, refreshing from the local file if unregistered."""
    key = _key(terraform_file)
    data = _load()
    if key in data:
        return data[key]
    try:
        return record_configuration(terraform_file)
    except (OSError, UnicodeError, KeyError, ValueError):
        return None


def list_configuration_records() -> list[dict[str, Any]]:
    """Return records for generated files that still exist, ordered by bucket."""
    files = sorted(GENERATED_DIR.rglob("main.tf")) if GENERATED_DIR.is_dir() else []
    records = []
    for path in files:
        record = get_configuration_record(path)
        if record:
            records.append(record)
    return records
