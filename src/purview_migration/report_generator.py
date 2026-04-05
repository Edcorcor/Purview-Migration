from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def export_report(plan: dict[str, Any], output_path: str, format_type: str = "json") -> None:
    """Export relink plan with status groupings to CSV or JSON report."""

    grouped = _group_by_status(plan)

    if format_type.lower() == "csv":
        _export_csv(grouped, output_path)
    else:
        _export_json(grouped, output_path)


def _group_by_status(plan: dict[str, Any]) -> dict[str, dict[str, list[dict[str, Any]]]]:
    """Group all artifacts by their status (linked, created, missing, failed, unresolved)."""

    grouped: dict[str, dict[str, list[dict[str, Any]]]] = {
        "linked": {},
        "created": {},
        "missing": {},
        "failed": {},
        "unresolved": {},
        "pending": {},
    }

    for status in grouped:
        grouped[status] = {
            "collections": [],
            "dataSources": [],
            "scans": [],
            "glossaryCategories": [],
            "glossaryTerms": [],
            "classifications": [],
            "scanRulesets": [],
            "scanCredentials": [],
            "entities": [],
        }

    def classify_item(item: dict[str, Any], artifact_type: str, status: str | None) -> None:
        actual_status = item.get("status", "pending")
        if actual_status not in grouped:
            actual_status = "pending"
        grouped[actual_status][artifact_type].append(item)

    for item in plan.get("collections", []):
        classify_item(item, "collections", item.get("status"))

    for item in plan.get("dataSources", []):
        classify_item(item, "dataSources", item.get("status"))

    for item in plan.get("scans", []):
        classify_item(item, "scans", item.get("status"))

    for item in plan.get("glossaryCategories", []):
        classify_item(item, "glossaryCategories", item.get("status"))

    for item in plan.get("glossaryTerms", []):
        classify_item(item, "glossaryTerms", item.get("status"))

    for item in plan.get("classifications", []):
        classify_item(item, "classifications", item.get("status"))

    for item in plan.get("scanRulesets", []):
        classify_item(item, "scanRulesets", item.get("status"))

    for item in plan.get("scanCredentials", []):
        classify_item(item, "scanCredentials", item.get("status"))

    for item in plan.get("entities", []):
        classify_item(item, "entities", item.get("status"))

    return grouped


def _export_json(grouped: dict[str, dict[str, list[dict[str, Any]]]], output_path: str) -> None:
    """Export grouped report as JSON."""

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "reportType": "RelinkStatusReport",
        "exportedAt": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat(),
        "summary": _compute_summary(grouped),
        "statuses": grouped,
    }

    output.write_text(json.dumps(report, indent=2), encoding="utf-8")


def _export_csv(grouped: dict[str, dict[str, list[dict[str, Any]]]], output_path: str) -> None:
    """Export grouped report as CSV (one file per artifact type)."""

    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    for artifact_type in grouped[list(grouped.keys())[0]]:
        csv_path = output_dir / f"relink-{artifact_type}.csv"

        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Status", "Source", "Target", "Collection", "Errors"])

            for status in grouped:
                for item in grouped[status][artifact_type]:
                    source_key = item.get("sourceName") or item.get("sourceDisplayText") or item.get("sourceQualifiedName")
                    target_key = item.get("targetName") or item.get("targetDisplayText") or item.get("targetQualifiedName")
                    collection = item.get("collection", "")
                    error_msg = ""

                    writer.writerow([status, source_key or "", target_key or "", collection, error_msg])


def _compute_summary(grouped: dict[str, dict[str, list[dict[str, Any]]]]) -> dict[str, Any]:
    """Compute summary counts by status and artifact type."""

    summary: dict[str, Any] = {"byStatus": {}, "byType": {}}

    for status in grouped:
        summary["byStatus"][status] = sum(
            len(grouped[status][artifact_type]) for artifact_type in grouped[status]
        )

    artifact_types = list(grouped[list(grouped.keys())[0]].keys())
    for artifact_type in artifact_types:
        summary["byType"][artifact_type] = sum(
            len(grouped[status][artifact_type]) for status in grouped
        )

    return summary
