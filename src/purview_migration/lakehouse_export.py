from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from purview_migration.constants import LIST_ARTIFACT_KEYS, SCANS_BY_SOURCE_KEY


def package_manifest_for_lakehouse(
    manifest: dict[str, Any],
    output_dir: str | Path,
    *,
    include_tables: bool = True,
    include_semantic_model: bool = True,
) -> dict[str, Any]:
    """Write JSON artifacts, table-ready files, and semantic/report metadata."""

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    metadata = manifest.get("metadata", {})
    artifacts = manifest.get("artifacts", {})
    warnings = manifest.get("warnings", [])

    json_outputs = _write_json_artifacts(output_root, metadata, artifacts, warnings)

    table_outputs: list[str] = []
    if include_tables:
        table_outputs = _write_table_exports(output_root, metadata, artifacts)

    semantic_outputs: list[str] = []
    if include_semantic_model:
        semantic_outputs = _write_semantic_outputs(output_root, metadata, artifacts)

    return {
        "outputDir": str(output_root),
        "jsonOutputs": json_outputs,
        "tableOutputs": table_outputs,
        "semanticOutputs": semantic_outputs,
    }


def _write_json_artifacts(
    output_root: Path,
    metadata: dict[str, Any],
    artifacts: dict[str, Any],
    warnings: list[str],
) -> list[str]:
    lakehouse_json_dir = output_root / "json"
    lakehouse_json_dir.mkdir(parents=True, exist_ok=True)

    outputs: list[str] = []
    outputs.append(_write_json(lakehouse_json_dir / "metadata.json", metadata))
    outputs.append(_write_json(lakehouse_json_dir / "warnings.json", warnings))

    for artifact_name, artifact_value in artifacts.items():
        outputs.append(_write_json(lakehouse_json_dir / f"{artifact_name}.json", artifact_value))

    return outputs


def _write_table_exports(
    output_root: Path,
    metadata: dict[str, Any],
    artifacts: dict[str, Any],
) -> list[str]:
    table_dir = output_root / "tables"
    table_dir.mkdir(parents=True, exist_ok=True)

    source_account = metadata.get("sourceAccount", "")
    exported_at_utc = metadata.get("exportedAtUtc", "")

    outputs: list[str] = []

    for artifact_name in LIST_ARTIFACT_KEYS:
        rows = _rows_for_list_artifact(
            artifacts.get(artifact_name, []),
            artifact_name,
            source_account,
            exported_at_utc,
        )
        outputs.append(_write_csv(table_dir / f"{artifact_name}.csv", rows, _list_headers()))

    scans_rows = _rows_for_scans_by_source(
        artifacts.get(SCANS_BY_SOURCE_KEY, {}),
        source_account,
        exported_at_utc,
    )
    outputs.append(_write_csv(table_dir / "scans.csv", scans_rows, _scan_headers()))

    summary_rows = _summary_rows(artifacts)
    outputs.append(_write_csv(table_dir / "artifact_summary.csv", summary_rows, ["artifactType", "count"]))

    return outputs


def _write_semantic_outputs(
    output_root: Path,
    metadata: dict[str, Any],
    artifacts: dict[str, Any],
) -> list[str]:
    semantic_dir = output_root / "semantic"
    semantic_dir.mkdir(parents=True, exist_ok=True)

    summary = {"artifactCounts": _artifact_counts(artifacts)}
    semantic_model = {
        "modelName": "PurviewMigrationCaptureModel",
        "description": "Logical semantic model over exported Purview migration artifacts.",
        "source": {
            "sourceAccount": metadata.get("sourceAccount", ""),
            "exportedAtUtc": metadata.get("exportedAtUtc", ""),
            "tableFolder": "tables",
        },
        "tables": [
            {
                "name": "collections",
                "file": "tables/collections.csv",
                "primaryKey": "artifact_key",
                "measures": ["count_rows"],
            },
            {
                "name": "data_sources",
                "file": "tables/dataSources.csv",
                "primaryKey": "artifact_key",
                "measures": ["count_rows"],
            },
            {
                "name": "scans",
                "file": "tables/scans.csv",
                "primaryKey": "scan_key",
                "measures": ["count_rows"],
            },
            {
                "name": "entities",
                "file": "tables/entities.csv",
                "primaryKey": "artifact_key",
                "measures": ["count_rows"],
            },
        ],
        "relationships": [
            {
                "fromTable": "scans",
                "fromColumn": "data_source_name",
                "toTable": "data_sources",
                "toColumn": "artifact_name",
                "type": "many-to-one",
            },
            {
                "fromTable": "entities",
                "fromColumn": "collection",
                "toTable": "collections",
                "toColumn": "artifact_name",
                "type": "many-to-one",
            },
        ],
    }

    report_spec = {
        "reportName": "Purview Migration Capture Overview",
        "description": "Suggested report layout for validating exported Purview assets, scans, and collections.",
        "pages": [
            {
                "name": "Overview",
                "visuals": [
                    "KPI: Total Collections",
                    "KPI: Total Data Sources",
                    "KPI: Total Scans",
                    "KPI: Total Entities",
                    "Bar: Artifact counts by type",
                ],
            },
            {
                "name": "Scans",
                "visuals": [
                    "Table: scans by data_source_name",
                    "Bar: scans per collection",
                    "Table: scan details",
                ],
            },
            {
                "name": "Assets",
                "visuals": [
                    "Table: entities by collection",
                    "Bar: entity counts by artifact_type",
                    "Drillthrough: payload_json",
                ],
            },
        ],
        "countsAtExport": summary["artifactCounts"],
    }

    outputs = [
        _write_json(semantic_dir / "semantic_model.json", semantic_model),
        _write_json(semantic_dir / "report_spec.json", report_spec),
        _write_json(semantic_dir / "capture_summary.json", summary),
    ]

    outputs.append(_write_markdown_summary(semantic_dir / "capture_summary.md", metadata, summary["artifactCounts"]))
    return outputs


def _write_markdown_summary(path: Path, metadata: dict[str, Any], counts: dict[str, int]) -> str:
    lines = [
        "# Purview Capture Summary",
        "",
        f"- Source Account: {metadata.get('sourceAccount', '')}",
        f"- Exported At (UTC): {metadata.get('exportedAtUtc', '')}",
        "",
        "## Artifact Counts",
        "",
        "| Artifact | Count |",
        "|---|---:|",
    ]

    for artifact, count in sorted(counts.items()):
        lines.append(f"| {artifact} | {count} |")

    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)


def _rows_for_list_artifact(
    items: list[dict[str, Any]],
    artifact_type: str,
    source_account: str,
    exported_at_utc: str,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for index, item in enumerate(items):
        rows.append(
            {
                "source_account": source_account,
                "exported_at_utc": exported_at_utc,
                "artifact_type": artifact_type,
                "artifact_index": str(index),
                "artifact_key": _as_str(item.get("id") or item.get("guid") or item.get("qualifiedName") or item.get("name")),
                "artifact_name": _as_str(item.get("name") or item.get("displayText") or item.get("qualifiedName")),
                "collection": _as_str(item.get("collection") or item.get("collectionName")),
                "status": _as_str(item.get("status")),
                "payload_json": json.dumps(item),
            }
        )
    return rows


def _rows_for_scans_by_source(
    scans_by_source: dict[str, list[dict[str, Any]]],
    source_account: str,
    exported_at_utc: str,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for source_name, scans in scans_by_source.items():
        for index, scan in enumerate(scans):
            rows.append(
                {
                    "source_account": source_account,
                    "exported_at_utc": exported_at_utc,
                    "data_source_name": source_name,
                    "scan_index": str(index),
                    "scan_key": _as_str(scan.get("id") or scan.get("name")),
                    "scan_name": _as_str(scan.get("name") or scan.get("displayName")),
                    "collection": _as_str(scan.get("collection") or scan.get("collectionName")),
                    "status": _as_str(scan.get("status")),
                    "payload_json": json.dumps(scan),
                }
            )
    return rows


def _artifact_counts(artifacts: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for name, value in artifacts.items():
        if isinstance(value, list):
            counts[name] = len(value)
        elif name == SCANS_BY_SOURCE_KEY and isinstance(value, dict):
            counts["scans"] = sum(len(scans) for scans in value.values())
        else:
            counts[name] = 0
    return counts


def _summary_rows(artifacts: dict[str, Any]) -> list[dict[str, int | str]]:
    counts = _artifact_counts(artifacts)
    return [{"artifactType": artifact_type, "count": count} for artifact_type, count in sorted(counts.items())]


def _list_headers() -> list[str]:
    return [
        "source_account",
        "exported_at_utc",
        "artifact_type",
        "artifact_index",
        "artifact_key",
        "artifact_name",
        "collection",
        "status",
        "payload_json",
    ]


def _scan_headers() -> list[str]:
    return [
        "source_account",
        "exported_at_utc",
        "data_source_name",
        "scan_index",
        "scan_key",
        "scan_name",
        "collection",
        "status",
        "payload_json",
    ]


def _write_csv(path: Path, rows: list[dict[str, Any]], headers: list[str]) -> str:
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return str(path)


def _write_json(path: Path, data: Any) -> str:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return str(path)


def _as_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value)
