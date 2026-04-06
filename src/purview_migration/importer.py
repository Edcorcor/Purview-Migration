from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from purview_migration.client import PurviewClient
from purview_migration.models import ImportResult, MigrationManifest


def import_manifest(target_account: str, manifest: MigrationManifest, dry_run: bool = True) -> ImportResult:
    client = PurviewClient(target_account)
    result = ImportResult()

    _apply_items(
        items=_sorted_collections(manifest.collections),
        dry_run=dry_run,
        result=result,
        write_fn=client.create_or_update_collection,
        success_counter="updated",
        error_message=lambda item, exc: f"Collection import failed for {item.get('name')}: {exc}",
    )

    _apply_items(
        items=manifest.data_sources,
        dry_run=dry_run,
        result=result,
        write_fn=client.create_or_update_data_source,
        success_counter="updated",
        error_message=lambda item, exc: f"Data source import failed for {item.get('name')}: {exc}",
    )

    scan_items = [
        {"sourceName": source_name, "scan": scan}
        for source_name, scans in manifest.scans_by_source.items()
        for scan in scans
    ]
    _apply_items(
        items=scan_items,
        dry_run=dry_run,
        result=result,
        write_fn=lambda item: client.create_or_update_scan(item["sourceName"], item["scan"]),
        success_counter="updated",
        error_message=lambda item, exc: (
            f"Scan import failed for {item['sourceName']}/{item['scan'].get('name')}: {exc}"
        ),
    )

    _apply_items(
        items=manifest.glossary_categories,
        dry_run=dry_run,
        result=result,
        write_fn=client.create_glossary_category,
        success_counter="created",
        error_message=lambda item, exc: (
            f"Glossary category import failed for {item.get('displayText')}: {exc}"
        ),
    )

    _apply_items(
        items=manifest.glossary_terms,
        dry_run=dry_run,
        result=result,
        write_fn=client.create_glossary_term,
        success_counter="created",
        error_message=lambda item, exc: f"Glossary term import failed for {item.get('displayText')}: {exc}",
    )

    _apply_items(
        items=manifest.classifications,
        dry_run=dry_run,
        result=result,
        write_fn=client.upsert_classification,
        success_counter="updated",
        error_message=lambda item, exc: f"Classification import failed for {item.get('name')}: {exc}",
    )

    _apply_items(
        items=manifest.scan_rulesets,
        dry_run=dry_run,
        result=result,
        write_fn=client.create_or_update_scan_ruleset,
        success_counter="updated",
        error_message=lambda item, exc: f"Ruleset import failed for {item.get('name')}: {exc}",
    )

    _apply_items(
        items=manifest.scan_credentials,
        dry_run=dry_run,
        result=result,
        write_fn=client.create_or_update_scan_credential,
        success_counter="updated",
        error_message=lambda item, exc: f"Credential import failed for {item.get('name')}: {exc}",
    )

    if dry_run:
        result.warnings.append("Dry-run mode enabled. No writes were performed.")

    return result


def _sorted_collections(collections: list[dict]) -> list[dict]:
    by_name = {c.get("name") or c.get("friendlyName"): c for c in collections}
    visited: set[str] = set()
    ordered: list[dict] = []

    def visit(name: str | None) -> None:
        if not name or name in visited or name not in by_name:
            return
        parent = by_name[name].get("parentCollection", {}).get("referenceName")
        visit(parent)
        visited.add(name)
        ordered.append(by_name[name])

    for collection_name in by_name:
        visit(collection_name)

    return ordered


def _apply_items(
    *,
    items: Iterable[dict[str, Any]],
    dry_run: bool,
    result: ImportResult,
    write_fn: Callable[[dict[str, Any]], Any],
    success_counter: str,
    error_message: Callable[[dict[str, Any], Exception], str],
) -> None:
    for item in items:
        if dry_run:
            result.skipped += 1
            continue

        try:
            write_fn(item)
            setattr(result, success_counter, getattr(result, success_counter) + 1)
        except Exception as exc:  # noqa: BLE001
            result.failed += 1
            result.warnings.append(error_message(item, exc))
