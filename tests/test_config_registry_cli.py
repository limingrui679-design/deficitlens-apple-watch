from __future__ import annotations

from pathlib import Path

import pytest

from deficitlens.cli import main
from deficitlens.config import load_settings
from deficitlens.data import registry as registry_module
from deficitlens.data.registry import fetch_registered_dataset


def test_default_config_and_cli(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = Path(__file__).resolve().parents[1]
    settings = load_settings(root / "configs" / "default.yml")
    assert settings.seed == 20260820
    assert settings.model.minimum_mondrian_clusters == 3
    assert main(["registry"]) == 0
    assert "weee" in capsys.readouterr().out
    output = tmp_path / "demo"
    assert main(["demo", "--output", str(output)]) == 0
    assert (output / "summary.json").exists()


def test_fetch_registered_dataset_with_mock_download(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import hashlib

    content = b"registered"
    digest = hashlib.sha256(content).hexdigest()
    registry = tmp_path / "registry.yml"
    registry.write_text(
        "\n".join(
            [
                "schema_version: 1",
                "datasets:",
                "  sample:",
                "    file_name: sample.bin",
                "    download_url: https://example.invalid/sample.bin",
                f"    checksum: sha256:{digest}",
            ]
        ),
        encoding="utf-8",
    )

    def fake_download(url: str, destination: str | Path, *, timeout: int = 120) -> Path:
        del url, timeout
        target = Path(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return target

    monkeypatch.setattr(registry_module, "download", fake_download)
    outputs = fetch_registered_dataset("sample", registry, tmp_path / "out")
    assert outputs[0].read_bytes() == content
    with pytest.raises(KeyError):
        fetch_registered_dataset("missing", registry, tmp_path / "out")
