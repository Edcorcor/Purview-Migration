from __future__ import annotations

from typing import Any

from purview_migration.models import MigrationManifest


def build_relink_plan(manifest: MigrationManifest) -> dict[str, Any]:
    """Generate a name-based relink plan for post-import validation and custom mapping."""

    collections = []
    for collection in manifest.collections:
        collections.append(
            {
                "sourceName": collection.get("name"),
                "friendlyName": collection.get("friendlyName"),
                "targetName": collection.get("name"),
                "status": "pending",
                "sourceDefinition": collection,
            }
        )

    data_sources = []
    scans = []
    for source in manifest.data_sources:
        source_name = source.get("name")
        data_sources.append(
            {
                "sourceName": source_name,
                "targetName": source_name,
                "status": "pending",
                "sourceDefinition": source,
            }
        )
        for scan in manifest.scans_by_source.get(source_name, []):
            scan_name = scan.get("name")
            scans.append(
                {
                    "sourceDataSourceName": source_name,
                    "targetDataSourceName": source_name,
                    "sourceName": scan_name,
                    "targetName": scan_name,
                    "status": "pending",
                    "sourceDefinition": scan,
                }
            )

    glossary_terms = []
    for term in manifest.glossary_terms:
        glossary_terms.append(
            {
                "sourceDisplayText": term.get("displayText"),
                "targetDisplayText": term.get("displayText"),
                "status": "pending",
                "sourceDefinition": term,
            }
        )

    glossary_categories = []
    for category in manifest.glossary_categories:
        glossary_categories.append(
            {
                "sourceDisplayText": category.get("displayText"),
                "targetDisplayText": category.get("displayText"),
                "status": "pending",
                "sourceDefinition": category,
            }
        )

    classifications = []
    for classification_def in manifest.classifications:
        classifications.append(
            {
                "sourceName": classification_def.get("name"),
                "targetName": classification_def.get("name"),
                "status": "pending",
                "sourceDefinition": classification_def,
            }
        )

    scan_rulesets = []
    for ruleset in manifest.scan_rulesets:
        scan_rulesets.append(
            {
                "sourceName": ruleset.get("name"),
                "targetName": ruleset.get("name"),
                "status": "pending",
                "sourceDefinition": ruleset,
            }
        )

    scan_credentials = []
    for credential in manifest.scan_credentials:
        scan_credentials.append(
            {
                "sourceName": credential.get("name"),
                "targetName": credential.get("name"),
                "status": "pending",
                "sourceDefinition": credential,
            }
        )

    entity_links = []
    for entity in manifest.entities:
        entity_links.append(
            {
                "sourceQualifiedName": entity.get("qualifiedName") or entity.get("id"),
                "targetQualifiedName": entity.get("qualifiedName"),
                "collection": entity.get("collectionId") or entity.get("collection"),
                "status": "pending",
            }
        )

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
