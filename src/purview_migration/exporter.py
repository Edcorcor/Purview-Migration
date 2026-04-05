from __future__ import annotations

from purview_migration.client import PurviewClient
from purview_migration.models import MigrationManifest


def export_manifest(source_account: str, max_entities: int = 2000) -> MigrationManifest:
    client = PurviewClient(source_account)
    manifest = MigrationManifest(source_account=source_account)

    try:
        manifest.collections = client.list_collections()
    except Exception as exc:  # noqa: BLE001
        manifest.warnings.append(f"Failed to export collections: {exc}")

    try:
        manifest.data_sources = client.list_data_sources()
    except Exception as exc:  # noqa: BLE001
        manifest.warnings.append(f"Failed to export data sources: {exc}")

    if manifest.data_sources:
        for source in manifest.data_sources:
            source_name = source.get("name")
            if not source_name:
                continue
            try:
                manifest.scans_by_source[source_name] = client.list_scans(source_name)
            except Exception as exc:  # noqa: BLE001
                manifest.warnings.append(f"Failed to export scans for datasource {source_name}: {exc}")

    try:
        manifest.glossary_categories = client.list_glossary_categories()
    except Exception as exc:  # noqa: BLE001
        manifest.warnings.append(f"Failed to export glossary categories: {exc}")

    try:
        manifest.glossary_terms = client.list_glossary_terms()
    except Exception as exc:  # noqa: BLE001
        manifest.warnings.append(f"Failed to export glossary terms: {exc}")

    try:
        manifest.classifications = client.list_classifications()
    except Exception as exc:  # noqa: BLE001
        manifest.warnings.append(f"Failed to export classifications: {exc}")

    try:
        manifest.scan_rulesets = client.list_scan_rulesets()
    except Exception as exc:  # noqa: BLE001
        manifest.warnings.append(f"Failed to export scan rulesets: {exc}")

    try:
        manifest.scan_credentials = client.list_scan_credentials()
    except Exception as exc:  # noqa: BLE001
        manifest.warnings.append(f"Failed to export scan credentials: {exc}")

    # Pull entity snapshot in batches using search endpoint for later relinking.
    offset = 0
    batch_size = 100
    while offset < max_entities:
        try:
            entities = client.search_entities(limit=batch_size, offset=offset)
        except Exception as exc:  # noqa: BLE001
            manifest.warnings.append(f"Failed to export entities at offset {offset}: {exc}")
            break

        if not entities:
            break

        manifest.entities.extend(entities)
        offset += len(entities)
        if len(entities) < batch_size:
            break

    if len(manifest.entities) >= max_entities:
        manifest.warnings.append(
            f"Entity export reached max_entities={max_entities}. Increase if you need complete coverage."
        )

    return manifest
