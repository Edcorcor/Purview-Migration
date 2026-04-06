from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from purview_migration.exporter import export_manifest
from purview_migration.importer import import_manifest
from purview_migration.io_utils import read_json, write_json
from purview_migration.lakehouse_export import package_manifest_for_lakehouse
from purview_migration.models import MigrationManifest
from purview_migration.relink import build_relink_plan
from purview_migration.relink_executor import apply_relink_plan
from purview_migration.report_generator import export_report
from purview_migration.script_generator import generate_permission_scripts
from purview_migration.validator import validate_completeness


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="purview-migrate",
        description="Export and import Microsoft Purview artifacts between tenants/accounts.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    export_parser = subparsers.add_parser("export", help="Export artifacts from source Purview account")
    export_parser.add_argument("--source-account", required=True, help="Source Purview account name")
    export_parser.add_argument("--output", required=True, help="Output manifest JSON path")
    export_parser.add_argument(
        "--max-entities",
        type=int,
        default=2000,
        help="Maximum number of entities to export via search snapshot",
    )
    export_parser.add_argument(
        "--lakehouse-output-dir",
        help="Optional output directory for Lakehouse JSON, table files, semantic model, and report spec",
    )
    export_parser.add_argument(
        "--no-table-exports",
        action="store_true",
        help="Skip table CSV generation when using --lakehouse-output-dir",
    )
    export_parser.add_argument(
        "--no-semantic-report",
        action="store_true",
        help="Skip semantic model/report artifact generation when using --lakehouse-output-dir",
    )

    import_parser = subparsers.add_parser("import", help="Import artifacts into target Purview account")
    import_parser.add_argument("--target-account", required=True, help="Target Purview account name")
    import_parser.add_argument("--input", required=True, help="Input manifest JSON path")
    import_parser.add_argument(
        "--apply",
        action="store_true",
        help="Perform writes. If omitted, import runs in dry-run mode.",
    )

    relink_parser = subparsers.add_parser("relink", help="Generate a relink plan from manifest")
    relink_parser.add_argument("--input", required=True, help="Input manifest JSON path")
    relink_parser.add_argument("--output", required=True, help="Output relink plan JSON path")

    relink_apply_parser = subparsers.add_parser(
        "relink-apply",
        help="Validate and optionally apply relink plan to target Purview account",
    )
    relink_apply_parser.add_argument("--target-account", required=True, help="Target Purview account name")
    relink_apply_parser.add_argument("--input", required=True, help="Input relink plan JSON path")
    relink_apply_parser.add_argument(
        "--output",
        help="Optional output path for updated relink plan with statuses",
    )
    relink_apply_parser.add_argument(
        "--apply",
        action="store_true",
        help="Perform writes. If omitted, execution runs in dry-run mode.",
    )
    relink_apply_parser.add_argument(
        "--max-entity-validation",
        type=int,
        default=2000,
        help="Maximum number of entities to validate in target account",
    )
    relink_apply_parser.add_argument(
        "--report-format",
        choices=["json", "csv"],
        default="json",
        help="Report export format (json or csv)",
    )
    relink_apply_parser.add_argument(
        "--report-output",
        help="Path to export status report grouped by outcome",
    )

    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate manifest completeness before account deletion",
    )
    validate_parser.add_argument("--input", required=True, help="Input manifest JSON path")
    validate_parser.add_argument(
        "--output",
        help="Optional output path for validation report JSON",
    )

    generate_scripts_parser = subparsers.add_parser(
        "generate-scripts",
        help="Generate permission and linkage scripts for restoration",
    )
    generate_scripts_parser.add_argument("--input", required=True, help="Input manifest JSON path")
    generate_scripts_parser.add_argument(
        "--new-account-name",
        required=True,
        help="Name of the new Purview account to create",
    )
    generate_scripts_parser.add_argument(
        "--subscription-id",
        required=True,
        help="Azure subscription ID for new account",
    )
    generate_scripts_parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory to write generated scripts",
    )

    lakehouse_parser = subparsers.add_parser(
        "lakehouse-package",
        help="Create Lakehouse JSON files, table exports, and semantic/report artifacts from a manifest",
    )
    lakehouse_parser.add_argument("--input", required=True, help="Input manifest JSON path")
    lakehouse_parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory to write Lakehouse package files",
    )
    lakehouse_parser.add_argument(
        "--no-table-exports",
        action="store_true",
        help="Skip table CSV generation",
    )
    lakehouse_parser.add_argument(
        "--no-semantic-report",
        action="store_true",
        help="Skip semantic model and report artifact generation",
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    handlers = {
        "export": _handle_export,
        "lakehouse-package": _handle_lakehouse_package,
        "import": _handle_import,
        "relink": _handle_relink,
        "relink-apply": _handle_relink_apply,
        "validate": _handle_validate,
        "generate-scripts": _handle_generate_scripts,
    }

    handler = handlers.get(args.command)
    if not handler:
        print("Unknown command", file=sys.stderr)
        sys.exit(2)

    handler(args)


def _normalize_manifest_document(data: dict[str, Any]) -> dict[str, Any]:
    """
    Accept either a full manifest document or a raw artifacts object.

    Some workflows pass the whole manifest shape:
    {
      "metadata": ...,
      "artifacts": ...,
      "warnings": ...
    }
    while others may pass just the artifacts object. Normalize both here.
    """
    if "artifacts" in data:
        return data

    return {
        "metadata": {},
        "artifacts": data,
        "warnings": [],
    }


def _handle_export(args: argparse.Namespace) -> None:
    manifest = export_manifest(args.source_account, max_entities=args.max_entities)
    manifest_dict = manifest.to_dict()
    write_json(args.output, manifest_dict)

    lakehouse_outputs = None
    if args.lakehouse_output_dir:
        lakehouse_outputs = package_manifest_for_lakehouse(
            manifest_dict,
            args.lakehouse_output_dir,
            include_tables=not args.no_table_exports,
            include_semantic_model=not args.no_semantic_report,
        )

    print(
        json.dumps(
            {
                "status": "ok",
                "output": args.output,
                "lakehouse": lakehouse_outputs,
                "warnings": manifest.warnings,
                "counts": {
                    "collections": len(manifest.collections),
                    "dataSources": len(manifest.data_sources),
                    "scans": sum(len(x) for x in manifest.scans_by_source.values()),
                    "glossaryCategories": len(manifest.glossary_categories),
                    "glossaryTerms": len(manifest.glossary_terms),
                    "classifications": len(manifest.classifications),
                    "scanRulesets": len(manifest.scan_rulesets),
                    "scanCredentials": len(manifest.scan_credentials),
                    "entities": len(manifest.entities),
                },
            },
            indent=2,
        )
    )


def _handle_lakehouse_package(args: argparse.Namespace) -> None:
    manifest_data = _normalize_manifest_document(read_json(args.input))
    outputs = package_manifest_for_lakehouse(
        manifest_data,
        args.output_dir,
        include_tables=not args.no_table_exports,
        include_semantic_model=not args.no_semantic_report,
    )
    print(json.dumps({"status": "ok", "input": args.input, "lakehouse": outputs}, indent=2))


def _handle_import(args: argparse.Namespace) -> None:
    manifest = MigrationManifest.from_dict(_normalize_manifest_document(read_json(args.input)))
    result = import_manifest(args.target_account, manifest, dry_run=not args.apply)
    print(json.dumps({"status": "ok", "result": result.as_dict()}, indent=2))


def _handle_relink(args: argparse.Namespace) -> None:
    manifest = MigrationManifest.from_dict(_normalize_manifest_document(read_json(args.input)))
    plan = build_relink_plan(manifest)
    write_json(args.output, plan)
    print(json.dumps({"status": "ok", "output": args.output, "summary": plan["summary"]}, indent=2))


def _handle_relink_apply(args: argparse.Namespace) -> None:
    plan = read_json(args.input)
    result = apply_relink_plan(
        args.target_account,
        plan,
        dry_run=not args.apply,
        max_entity_validation=args.max_entity_validation,
    )

    if args.output:
        write_json(args.output, plan)
    if args.report_output:
        export_report(plan, args.report_output, format_type=args.report_format)

    print(
        json.dumps(
            {
                "status": "ok",
                "mode": "apply" if args.apply else "dry-run",
                "plan_output": args.output,
                "report_output": args.report_output,
                "result": result.as_dict(),
            },
            indent=2,
        )
    )


def _handle_validate(args: argparse.Namespace) -> None:
    manifest_dict = _normalize_manifest_document(read_json(args.input))
    report = validate_completeness(manifest_dict)

    if args.output:
        write_json(args.output, report)

    print(json.dumps(report, indent=2))

    if not report["deletion_ready"]:
        sys.exit(1)


def _handle_generate_scripts(args: argparse.Namespace) -> None:
    manifest_dict = _normalize_manifest_document(read_json(args.input))
    scripts = generate_permission_scripts(
        manifest_dict,
        args.new_account_name,
        args.subscription_id,
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    files_created: list[str] = []
    for filename, content in scripts.items():
        file_path = output_dir / filename
        file_path.write_text(content, encoding="utf-8")
        files_created.append(str(file_path))

    print(
        json.dumps(
            {
                "status": "ok",
                "output_dir": str(output_dir),
                "files_created": files_created,
                "message": "Scripts generated successfully. Review RESTORATION_GUIDE.md for step-by-step instructions.",
            },
            indent=2,
        )
    )
