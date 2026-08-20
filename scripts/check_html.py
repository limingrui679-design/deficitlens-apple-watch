#!/usr/bin/env python3
"""Audit generated HTML for portable assets and baseline accessibility semantics."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
from pathlib import Path


class DocumentAudit(HTMLParser):
    """Collect deterministic structural checks from one HTML document."""

    def __init__(self) -> None:
        super().__init__()
        self.lang = ""
        self.in_title = False
        self.title = ""
        self.has_main = False
        self.has_skip = False
        self.image_count = 0
        self.image_alt_failures = 0
        self.external_assets: list[str] = []
        self.local_assets: list[str] = []
        self.ids: list[str] = []
        self.labels_for: set[str] = set()
        self.controls: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {name: value or "" for name, value in attrs}
        if tag == "html":
            self.lang = values.get("lang", "")
        elif tag == "title":
            self.in_title = True
        elif tag == "main":
            self.has_main = True
        elif tag == "a" and values.get("href") == "#main":
            self.has_skip = True
        elif tag == "img":
            self.image_count += 1
            if not values.get("alt", "").strip():
                self.image_alt_failures += 1
        if values.get("id"):
            self.ids.append(values["id"])
        if tag == "label" and values.get("for"):
            self.labels_for.add(values["for"])
        if tag in {"input", "select", "textarea"} and values.get("id"):
            self.controls.add(values["id"])
        asset = ""
        if tag in {"img", "script", "source"}:
            asset = values.get("src", "")
        elif tag == "link" and values.get("rel") in {"stylesheet", "icon"}:
            asset = values.get("href", "")
        if asset.startswith(("http://", "https://", "//")):
            self.external_assets.append(asset)
        elif asset and not asset.startswith(("#", "data:")):
            self.local_assets.append(asset.split("?", 1)[0].split("#", 1)[0])

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title += data


def audit_html(path: Path) -> list[str]:
    """Return structural failures for one generated document."""

    parser = DocumentAudit()
    parser.feed(path.read_text(encoding="utf-8"))
    failures: list[str] = []
    if not parser.lang.strip():
        failures.append("missing html lang")
    if not parser.title.strip():
        failures.append("missing title")
    if not parser.has_main:
        failures.append("missing main landmark")
    if not parser.has_skip:
        failures.append("missing skip link to #main")
    if parser.image_alt_failures:
        failures.append(f"{parser.image_alt_failures} images lack non-empty alt text")
    if parser.external_assets:
        failures.append(f"external runtime assets: {sorted(set(parser.external_assets))}")
    missing_assets = sorted(
        asset for asset in set(parser.local_assets) if not (path.parent / asset).is_file()
    )
    if missing_assets:
        failures.append(f"missing local assets: {missing_assets}")
    duplicate_ids = sorted({item for item in parser.ids if parser.ids.count(item) > 1})
    if duplicate_ids:
        failures.append(f"duplicate ids: {duplicate_ids}")
    unlabelled = sorted(parser.controls - parser.labels_for)
    if unlabelled:
        failures.append(f"unlabelled controls: {unlabelled}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()
    failed = False
    for path in args.paths:
        if not path.is_file():
            print(f"FAIL missing HTML: {path}")
            failed = True
            continue
        failures = audit_html(path)
        if failures:
            failed = True
            for failure in failures:
                print(f"FAIL {path}: {failure}")
        else:
            print(f"PASS {path}")
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
