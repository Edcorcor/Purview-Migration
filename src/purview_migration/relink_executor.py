from __future__ import annotations

from typing import Any

from purview_migration.client import PurviewClient
from purview_migration.models import RelinkResult


def apply_relink_plan(target_account: str, plan: dict[str, Any], dry_run: bool = True) -> RelinkResult:
    client = PurviewClient(target_account)
    result = RelinkResult()

    _apply_collections(client, plan, result, dry_run)
    _apply_data_sources(client, plan, result, dry_run)
    _apply_scans(client, plan, result, dry_run)
    _apply_glossary_categories(client, plan, result, dry_run)
    _apply_glossary_terms(client, plan, result, dry_run)
    _apply_classifications(client, plan, result, dry_run)
    _apply_scan_rulesets(client, plan, result, dry_run)
    _apply_scan_credentials(client, plan, result, dry_run)
    _validate_entities(client, plan, result)

    if dry_run:
        result.warnings.append("Dry-run mode enabled. No writes were performed.")

    return result


def _apply_collections(client: PurviewClient, plan: dict[str, Any], result: RelinkResult, dry_run: bool) -> None:
    existing = {item.get("name") for item in client.list_collections()}
    for item in plan.get("collections", []):
        target_name = item.get("targetName")
        source_definition = item.get("sourceDefinition") or {}
        if target_name in existing:
            item["status"] = "linked"
            result.linked += 1
            continue
        if dry_run:
            item["status"] = "missing"
            result.unresolved += 1
            result.skipped += 1
            continue
        try:
            payload = dict(source_definition)
            if target_name:
                payload["name"] = target_name
                payload["friendlyName"] = payload.get("friendlyName") or target_name
            client.create_or_update_collection(payload)
            item["status"] = "created"
            result.created += 1
        except Exception as exc:  # noqa: BLE001
            item["status"] = "failed"
            result.failed += 1
            result.warnings.append(f"Collection relink failed for {target_name}: {exc}")


def _apply_data_sources(client: PurviewClient, plan: dict[str, Any], result: RelinkResult, dry_run: bool) -> None:
    existing = {item.get("name") for item in client.list_data_sources()}
    for item in plan.get("dataSources", []):
        target_name = item.get("targetName")
        source_definition = item.get("sourceDefinition") or {}
        if target_name in existing:
            item["status"] = "linked"
            result.linked += 1
            continue
        if dry_run:
            item["status"] = "missing"
            result.unresolved += 1
            result.skipped += 1
            continue
        try:
            payload = dict(source_definition)
            if target_name:
                payload["name"] = target_name
            client.create_or_update_data_source(payload)
            item["status"] = "created"
            result.created += 1
        except Exception as exc:  # noqa: BLE001
            item["status"] = "failed"
            result.failed += 1
            result.warnings.append(f"Data source relink failed for {target_name}: {exc}")


def _apply_scans(client: PurviewClient, plan: dict[str, Any], result: RelinkResult, dry_run: bool) -> None:
    scans_by_source: dict[str, set[str]] = {}
    for ds in client.list_data_sources():
        ds_name = ds.get("name")
        if not ds_name:
            continue
        scan_names = {scan.get("name") for scan in client.list_scans(ds_name)}
        scans_by_source[ds_name] = scan_names

    for item in plan.get("scans", []):
        target_ds = item.get("targetDataSourceName")
        target_name = item.get("targetName")
        source_definition = item.get("sourceDefinition") or {}
        target_set = scans_by_source.get(target_ds, set())

        if target_name in target_set:
            item["status"] = "linked"
            result.linked += 1
            continue

        if dry_run:
            item["status"] = "missing"
            result.unresolved += 1
            result.skipped += 1
            continue

        try:
            payload = dict(source_definition)
            if target_name:
                payload["name"] = target_name
            client.create_or_update_scan(target_ds, payload)
            item["status"] = "created"
            result.created += 1
        except Exception as exc:  # noqa: BLE001
            item["status"] = "failed"
            result.failed += 1
            result.warnings.append(f"Scan relink failed for {target_ds}/{target_name}: {exc}")


def _apply_glossary_categories(client: PurviewClient, plan: dict[str, Any], result: RelinkResult, dry_run: bool) -> None:
    existing = {item.get("displayText") for item in client.list_glossary_categories()}
    for item in plan.get("glossaryCategories", []):
        target_text = item.get("targetDisplayText")
        source_definition = item.get("sourceDefinition") or {}
        if target_text in existing:
            item["status"] = "linked"
            result.linked += 1
            continue
        if dry_run:
            item["status"] = "missing"
            result.unresolved += 1
            result.skipped += 1
            continue
        try:
            payload = dict(source_definition)
            if target_text:
                payload["displayText"] = target_text
            client.create_glossary_category(payload)
            item["status"] = "created"
            result.created += 1
        except Exception as exc:  # noqa: BLE001
            item["status"] = "failed"
            result.failed += 1
            result.warnings.append(f"Glossary category relink failed for {target_text}: {exc}")


def _apply_glossary_terms(client: PurviewClient, plan: dict[str, Any], result: RelinkResult, dry_run: bool) -> None:
    existing = {item.get("displayText") for item in client.list_glossary_terms()}
    for item in plan.get("glossaryTerms", []):
        target_text = item.get("targetDisplayText")
        source_definition = item.get("sourceDefinition") or {}
        if target_text in existing:
            item["status"] = "linked"
            result.linked += 1
            continue
        if dry_run:
            item["status"] = "missing"
            result.unresolved += 1
            result.skipped += 1
            continue
        try:
            payload = dict(source_definition)
            if target_text:
                payload["displayText"] = target_text
            client.create_glossary_term(payload)
            item["status"] = "created"
            result.created += 1
        except Exception as exc:  # noqa: BLE001
            item["status"] = "failed"
            result.failed += 1
            result.warnings.append(f"Glossary term relink failed for {target_text}: {exc}")


def _apply_classifications(client: PurviewClient, plan: dict[str, Any], result: RelinkResult, dry_run: bool) -> None:
    existing = {item.get("name") for item in client.list_classifications()}
    for item in plan.get("classifications", []):
        target_name = item.get("targetName")
        source_definition = item.get("sourceDefinition") or {}
        if target_name in existing:
            item["status"] = "linked"
            result.linked += 1
            continue
        if dry_run:
            item["status"] = "missing"
            result.unresolved += 1
            result.skipped += 1
            continue
        try:
            payload = dict(source_definition)
            if target_name:
                payload["name"] = target_name
            client.upsert_classification(payload)
            item["status"] = "created"
            result.created += 1
        except Exception as exc:  # noqa: BLE001
            item["status"] = "failed"
            result.failed += 1
            result.warnings.append(f"Classification relink failed for {target_name}: {exc}")


def _apply_scan_rulesets(client: PurviewClient, plan: dict[str, Any], result: RelinkResult, dry_run: bool) -> None:
    existing = {item.get("name") for item in client.list_scan_rulesets()}
    for item in plan.get("scanRulesets", []):
        target_name = item.get("targetName")
        source_definition = item.get("sourceDefinition") or {}
        if target_name in existing:
            item["status"] = "linked"
            result.linked += 1
            continue
        if dry_run:
            item["status"] = "missing"
            result.unresolved += 1
            result.skipped += 1
            continue
        try:
            payload = dict(source_definition)
            if target_name:
                payload["name"] = target_name
            client.create_or_update_scan_ruleset(payload)
            item["status"] = "created"
            result.created += 1
        except Exception as exc:  # noqa: BLE001
            item["status"] = "failed"
            result.failed += 1
            result.warnings.append(f"Ruleset relink failed for {target_name}: {exc}")


def _apply_scan_credentials(client: PurviewClient, plan: dict[str, Any], result: RelinkResult, dry_run: bool) -> None:
    existing = {item.get("name") for item in client.list_scan_credentials()}
    for item in plan.get("scanCredentials", []):
        target_name = item.get("targetName")
        source_definition = item.get("sourceDefinition") or {}
        if target_name in existing:
            item["status"] = "linked"
            result.linked += 1
            continue
        if dry_run:
            item["status"] = "missing"
            result.unresolved += 1
            result.skipped += 1
            continue
        try:
            payload = dict(source_definition)
            if target_name:
                payload["name"] = target_name
            client.create_or_update_scan_credential(payload)
            item["status"] = "created"
            result.created += 1
        except Exception as exc:  # noqa: BLE001
            item["status"] = "failed"
            result.failed += 1
            result.warnings.append(f"Credential relink failed for {target_name}: {exc}")


def _validate_entities(client: PurviewClient, plan: dict[str, Any], result: RelinkResult) -> None:
    existing_qns: set[str] = set()
    offset = 0
    limit = 100
    max_entities = 2000

    while offset < max_entities:
        batch = client.search_entities(limit=limit, offset=offset)
        if not batch:
            break
        for entity in batch:
            qualified_name = entity.get("qualifiedName")
            if qualified_name:
                existing_qns.add(qualified_name)
        offset += len(batch)
        if len(batch) < limit:
            break

    for item in plan.get("entities", []):
        target_qn = item.get("targetQualifiedName")
        if target_qn in existing_qns:
            item["status"] = "linked"
            result.linked += 1
        else:
            item["status"] = "unresolved"
            result.unresolved += 1
