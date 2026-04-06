from __future__ import annotations

from typing import Any

from purview_migration.models import MigrationManifest


def build_relink_plan(manifest: MigrationManifest) -> dict[str, Any]:
    """Generate a name-based relink plan for post-import validation and custom mapping."""

    collections = _map_name_based(
        manifest.collections,
        source_key="name",
        target_key="name",
        extra_fields={"friendlyName": "friendlyName"},
    )

    data_sources = _map_name_based(
        manifest.data_sources,
        source_key="name",
        target_key="name",
    )

    scans = [
        {
            "sourceDataSourceName": source_name,
            "targetDataSourceName": source_name,
            "sourceName": scan.get("name"),
            "targetName": scan.get("name"),
            "status": "pending",
            "sourceDefinition": scan,
        }
        for source_name in (source.get("name") for source in manifest.data_sources)
        if source_name
        for scan in manifest.scans_by_source.get(source_name, [])
    ]

    glossary_terms = _map_name_based(
        manifest.glossary_terms,
        source_key="displayText",
        target_key="displayText",
        source_field_name="sourceDisplayText",
        target_field_name="targetDisplayText",
    )

    glossary_categories = _map_name_based(
        manifest.glossary_categories,
        source_key="displayText",
        target_key="displayText",
        source_field_name="sourceDisplayText",
        target_field_name="targetDisplayText",
    )

    classifications = _map_name_based(
        manifest.classifications,
        source_key="name",
        target_key="name",
    )

    scan_rulesets = _map_name_based(
        manifest.scan_rulesets,
        source_key="name",
        target_key="name",
    )

    scan_credentials = _map_name_based(
        manifest.scan_credentials,
        source_key="name",
        target_key="name",
    )

    entity_links = [
        {
            "sourceQualifiedName": entity.get("qualifiedName") or entity.get("id"),
            "targetQualifiedName": entity.get("qualifiedName"),
            "collection": entity.get("collectionId") or entity.get("collection"),
            "status": "pending",
        }
        for entity in manifest.entities
    ]

    return {
        "summary": {
            "collections": len(collections),
            "dataSources": len(data_sources),
            "scans": len(scans),
            "glossaryCategories": len(glossary_categories),
            "glossaryTerms": len(glossary_terms),
            "classifications": len(classifications),
            "scanRulesets": len(scan_rulesets),
            "scanCredentials": len(scan_credentials),
            "entities": len(entity_links),
        },
        "collections": collections,
        "dataSources": data_sources,
        "scans": scans,
        "glossaryCategories": glossary_categories,
        "glossaryTerms": glossary_terms,
        "classifications": classifications,
        "scanRulesets": scan_rulesets,
        "scanCredentials": scan_credentials,
        "entities": entity_links,
        "notes": [
            "This plan is generated from source export and uses name-based matching.",
            "Edit target names as needed, then run relink-apply in dry-run mode first.",
            "Entity relink is validation-only in this version and flags unresolved qualified names.",
        ],
    }


def _map_name_based(
    items: list[dict[str, Any]],
    *,
    source_key: str,
    target_key: str,
    source_field_name: str = "sourceName",
    target_field_name: str = "targetName",
    extra_fields: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    mapped: list[dict[str, Any]] = []
    for item in items:
        row = {
            source_field_name: item.get(source_key),
            target_field_name: item.get(target_key),
            "status": "pending",
            "sourceDefinition": item,
        }
        if extra_fields:
            for output_field, input_key in extra_fields.items():
                row[output_field] = item.get(input_key)
        mapped.append(row)
    return mapped
