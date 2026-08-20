"""Portable, dependency-free personal audit report rendering."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape

from deficitlens.reporting.report import accessible_table


def render_personal_report(
    *,
    daily: pd.DataFrame,
    workouts: pd.DataFrame,
    scenarios: pd.DataFrame,
    summary: dict[str, Any],
    output_path: str | Path,
) -> Path:
    """Render an offline HTML report without network-loaded scripts or fonts."""

    template_dir = Path(__file__).parent / "templates"
    environment = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = environment.get_template("personal_audit.html.j2")
    observed_energy = (
        float(daily["active_energy_kcal"].sum())
        if not daily.empty and "active_energy_kcal" in daily
        else 0.0
    )
    context = {
        "summary": summary,
        "observed_energy": observed_energy,
        "daily_table": accessible_table(daily.round(3).to_html(index=False, classes="data-table")),
        "workout_table": accessible_table(
            workouts.round(3).to_html(index=False, classes="data-table")
        ),
        "scenario_table": accessible_table(
            scenarios.round(3).to_html(index=False, classes="data-table")
        ),
    }
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(template.render(**context), encoding="utf-8")
    return target
