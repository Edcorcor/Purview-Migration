from __future__ import annotations

from purview_migration.client import PurviewClient
from purview_migration.models import ImportResult, MigrationManifest


def import_manifest(target_account: str, manifest: MigrationManifest, dry_run: bool = True) -> ImportResult:
    client = PurviewClient(target_account)
    result = ImportResult()

    for collection in _sorted_collections(manifest.collections):
        if dry_run:
            result.skipped += 1
            continue
        try:
            client.create_or_update_collection(collection)
            result.updated += 1
        except Exception as exc:  # noqa: BLE001
            result.failed += 1
            result.warnings.append(f"Collection import failed for {collection.get('name')}: {exc}")

    for data_source in manifest.data_sources:
        if dry_run:
            result.skipped += 1
            continue
        try:
            client.create_or_update_data_source(data_source)
            result.updated += 1
        except Exception as exc:  # noqa: BLE001
            result.failed += 1
            result.warnings.append(f"Data source import failed for {data_source.get('name')}: {exc}")

    for source_name, scans in manifest.scans_by_source.items():
        for scan in scans:
            if dry_run:
                result.skipped += 1
                continue
            try:
                client.create_or_update_scan(source_name, scan)
                result.updated += 1
            except Exception as exc:  # noqa: BLE001
                result.failed += 1
                result.warnings.append(f"Scan import failed for {source_name}/{scan.get('name')}: {exc}")

    for category in manifest.glossary_categories:
        if dry_run:
            result.skipped += 1
            continue
        try:
            client.create_glossary_category(category)
            result.created += 1
        except Exception as exc:  # noqa: BLE001
            result.failed += 1
            result.warnings.append(f"Glossary category import failed for {category.get('displayText')}: {exc}")

    for term in manifest.glossary_terms:
        if dry_run:
            result.skipped += 1
            continue
        try:
            client.create_glossary_term(term)
            result.created += 1
        except Exception as exc:  # noqa: BLE001
            result.failed += 1
            result.warnings.append(f"Glossary term import failed for {term.get('displayText')}: {exc}")

    for classification_def in manifest.classifications:
        if dry_run:
            result.skipped += 1
            continue
        try:
            client.upsert_classification(classification_def)
            result.updated += 1
        except Exception as exc:  # noqa: BLE001
            result.failed += 1
            result.warnings.append(f"Classification import failed for {classification_def.get('name')}: {exc}")

    for ruleset in manifest.scan_rulesets:
        if dry_run:
            result.skipped += 1
            continue
        try:
            client.create_or_update_scan_ruleset(ruleset)
            result.updated += 1
        except Exception as exc:  # noqa: BLE001
            result.failed += 1
            result.warnings.append(f"Ruleset import failed for {ruleset.get('name')}: {exc}")

    for credential in manifest.scan_credentials:
        if dry_run:
            result.skipped += 1
            continue
        try:
            client.create_or_update_scan_credential(credential)
            result.updated += 1
        except Exception as exc:  # noqa: BLE001
            result.failed += 1
            result.warnings.append(f"Credential import failed for {credential.get('name')}: {exc}")

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
