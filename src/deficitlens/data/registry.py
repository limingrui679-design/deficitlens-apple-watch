"""Dataset registry, download, and checksum verification."""

from __future__ import annotations

import hashlib
import shutil
import urllib.request
from pathlib import Path
from typing import Any, cast

import yaml


def load_registry(path: str | Path) -> dict[str, Any]:
    """Load the versioned dataset registry."""

    registry = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(registry, dict):
        raise ValueError("Unsupported or malformed dataset registry")
    if registry.get("schema_version") != 1 or "datasets" not in registry:
        raise ValueError("Unsupported or malformed dataset registry")
    return cast(dict[str, Any], registry)


def checksum(path: str | Path, algorithm: str = "sha256", chunk_size: int = 1 << 20) -> str:
    """Calculate a streaming checksum."""

    digest = hashlib.new(algorithm)
    with Path(path).open("rb") as handle:
        while block := handle.read(chunk_size):
            digest.update(block)
    return digest.hexdigest()


def verify_checksum(path: str | Path, expected: str) -> bool:
    """Verify an `algorithm:hex` checksum."""

    try:
        algorithm, expected_hex = expected.split(":", 1)
    except ValueError as exc:
        raise ValueError("Checksum must use algorithm:hex format") from exc
    return checksum(path, algorithm) == expected_hex.lower()


def download(url: str, destination: str | Path, *, timeout: int = 120) -> Path:
    """Download a file atomically to `destination`."""

    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(target.suffix + ".partial")
    request = urllib.request.Request(url, headers={"User-Agent": "DeficitLens/1.0"})
    try:
        with (
            urllib.request.urlopen(request, timeout=timeout) as response,
            partial.open("wb") as out,
        ):
            shutil.copyfileobj(response, out)
        partial.replace(target)
    except Exception:
        partial.unlink(missing_ok=True)
        raise
    return target


def fetch_registered_dataset(
    dataset_id: str, registry_path: str | Path, destination_dir: str | Path
) -> list[Path]:
    """Fetch and verify all registered files for one dataset."""

    registry = load_registry(registry_path)
    try:
        entry = registry["datasets"][dataset_id]
    except KeyError as exc:
        raise KeyError(f"Unknown dataset: {dataset_id}") from exc

    output_dir = Path(destination_dir)
    files = entry.get("files")
    if files is None:
        files = [
            {
                "name": entry["file_name"],
                "download_url": entry["download_url"],
                "checksum": entry["checksum"],
            }
        ]

    outputs: list[Path] = []
    for item in files:
        target = output_dir / item["name"]
        if not target.exists() or not verify_checksum(target, item["checksum"]):
            download(item["download_url"], target)
        if not verify_checksum(target, item["checksum"]):
            target.unlink(missing_ok=True)
            raise ValueError(f"Checksum verification failed for {target.name}")
        outputs.append(target)
    return outputs
