"""Privacy-preserving, streaming Apple Health XML adapter."""

from __future__ import annotations

import csv
import hashlib
import os
import secrets
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from defusedxml import ElementTree as ET

from deficitlens.physiology import apple_energy_to_kcal

SUPPORTED_RECORD_TYPES = {
    "ActiveEnergyBurned",
    "BasalEnergyBurned",
    "BodyFatPercentage",
    "BodyMass",
    "DistanceWalkingRunning",
    "HeartRate",
    "HeartRateVariabilitySDNN",
    "RestingHeartRate",
    "StepCount",
    "VO2Max",
    "WalkingHeartRateAverage",
    "WalkingSpeed",
}

ENERGY_TYPES = {"ActiveEnergyBurned", "BasalEnergyBurned"}
DATE_FORMATS = ("%Y-%m-%d %H:%M:%S %z", "%Y-%m-%d %H:%M:%S")


def strip_healthkit_prefix(value: str) -> str:
    """Strip Apple HealthKit identifier prefixes."""

    for prefix in ("HKQuantityTypeIdentifier", "HKCategoryTypeIdentifier"):
        if value.startswith(prefix):
            return value[len(prefix) :]
    return value


def parse_health_date(value: str) -> datetime:
    """Parse an Apple Health timestamp without discarding timezone information."""

    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unsupported Apple Health date: {value!r}")


def is_apple_watch_source(attributes: dict[str, str]) -> bool:
    """Return whether a record identifies Apple Watch as its source device."""

    source = attributes.get("sourceName", "").lower()
    device = attributes.get("device", "").lower()
    return "apple watch" in source or "watch" in device


def _redact(value: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{value}".encode()).hexdigest()[:16]


def _record_id(attributes: dict[str, str]) -> str:
    fields = (
        attributes.get("type", ""),
        attributes.get("startDate", ""),
        attributes.get("endDate", ""),
        attributes.get("value", ""),
        attributes.get("unit", ""),
        attributes.get("sourceName", ""),
        attributes.get("sourceVersion", ""),
        attributes.get("device", ""),
    )
    return hashlib.sha256("\x1f".join(fields).encode()).hexdigest()


def iter_apple_health_records(
    xml_path: str | Path,
    *,
    apple_watch_only: bool = True,
    redact_source_names: bool = True,
    salt: str | None = None,
) -> Iterator[dict[str, Any]]:
    """Stream selected records from a potentially multi-gigabyte Apple Health export."""

    source_salt = salt or os.environ.get("DEFICITLENS_HASH_SALT") or secrets.token_hex(16)
    seen: set[str] = set()
    for _, element in ET.iterparse(Path(xml_path), events=("end",)):
        if element.tag != "Record":
            element.clear()
            continue
        attrs = dict(element.attrib)
        record_type = strip_healthkit_prefix(attrs.get("type", ""))
        if record_type not in SUPPORTED_RECORD_TYPES:
            element.clear()
            continue
        if apple_watch_only and not is_apple_watch_source(attrs):
            element.clear()
            continue

        record_id = _record_id(attrs)
        if record_id in seen:
            element.clear()
            continue
        seen.add(record_id)

        source_name = attrs.get("sourceName", "")
        unit = attrs.get("unit", "")
        raw_value = float(attrs["value"])
        normalized_value = (
            apple_energy_to_kcal(raw_value, unit) if record_type in ENERGY_TYPES else raw_value
        )
        normalized_unit = "kcal" if record_type in ENERGY_TYPES else unit
        yield {
            "record_id": record_id,
            "record_type": record_type,
            "start_time": parse_health_date(attrs["startDate"]),
            "end_time": parse_health_date(attrs["endDate"]),
            "value": normalized_value,
            "unit": normalized_unit,
            "source": _redact(source_name, source_salt) if redact_source_names else source_name,
            "source_version": attrs.get("sourceVersion"),
            "is_apple_watch": is_apple_watch_source(attrs),
        }
        element.clear()


def parse_apple_health_records(xml_path: str | Path, **kwargs: Any) -> pd.DataFrame:
    """Return streamed Apple Health records as a normalized DataFrame."""

    frame = pd.DataFrame(iter_apple_health_records(xml_path, **kwargs))
    if frame.empty:
        return frame
    return frame.sort_values(["start_time", "record_type", "record_id"]).reset_index(drop=True)


def iter_apple_health_workouts(
    xml_path: str | Path,
    *,
    apple_watch_only: bool = True,
    redact_source_names: bool = True,
    salt: str | None = None,
) -> Iterator[dict[str, Any]]:
    """Stream workout summaries and nested statistics."""

    source_salt = salt or os.environ.get("DEFICITLENS_HASH_SALT") or secrets.token_hex(16)
    current_statistics: dict[str, float] | None = None
    for event, element in ET.iterparse(Path(xml_path), events=("start", "end")):
        if event == "start" and element.tag == "Workout":
            current_statistics = {}
            continue
        if event != "end":
            continue
        if element.tag == "WorkoutStatistics" and current_statistics is not None:
            stat_type = strip_healthkit_prefix(element.attrib.get("type", ""))
            if "sum" in element.attrib:
                current_statistics[f"{stat_type}_sum"] = float(element.attrib["sum"])
            if "average" in element.attrib:
                current_statistics[f"{stat_type}_average"] = float(element.attrib["average"])
            element.clear()
            continue
        if element.tag != "Workout":
            element.clear()
            continue
        attrs = dict(element.attrib)
        if apple_watch_only and not is_apple_watch_source(attrs):
            current_statistics = None
            element.clear()
            continue
        source_name = attrs.get("sourceName", "")
        energy = attrs.get("totalEnergyBurned")
        energy_unit = attrs.get("totalEnergyBurnedUnit", "kcal")
        duration = float(attrs.get("duration", 0.0))
        duration_unit = attrs.get("durationUnit", "min").lower()
        if duration_unit in {"s", "sec", "second", "seconds"}:
            duration /= 60.0
        elif duration_unit in {"h", "hr", "hour", "hours"}:
            duration *= 60.0
        elif duration_unit not in {"min", "minute", "minutes"}:
            raise ValueError(f"Unsupported workout duration unit: {duration_unit!r}")
        yield {
            "activity_type": attrs.get("workoutActivityType", "").removeprefix(
                "HKWorkoutActivityType"
            ),
            "start_time": parse_health_date(attrs["startDate"]),
            "end_time": parse_health_date(attrs["endDate"]),
            "duration_minutes": duration,
            "total_energy_kcal": (
                apple_energy_to_kcal(float(energy), energy_unit) if energy is not None else None
            ),
            "source": _redact(source_name, source_salt) if redact_source_names else source_name,
            "is_apple_watch": is_apple_watch_source(attrs),
            "statistics": current_statistics or {},
        }
        current_statistics = None
        element.clear()


def write_normalized_records_csv(
    xml_path: str | Path,
    output_path: str | Path,
    *,
    acknowledge_sensitive_output: bool = False,
) -> int:
    """Write row-level records only after an explicit privacy-risk acknowledgement.

    This expert API retains exact timestamps and stable record hashes. The public CLI never
    calls it. Requiring a keyword acknowledgement prevents an accidental helper call from
    violating the aggregate-only default.
    """

    if not acknowledge_sensitive_output:
        raise PermissionError(
            "Row-level output contains sensitive timestamps; set "
            "acknowledge_sensitive_output=True only for a protected local destination"
        )

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "record_id",
        "record_type",
        "start_time",
        "end_time",
        "value",
        "unit",
        "source",
        "source_version",
        "is_apple_watch",
    ]
    count = 0
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in iter_apple_health_records(xml_path):
            writer.writerow(row)
            count += 1
    return count
