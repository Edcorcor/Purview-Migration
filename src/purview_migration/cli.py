from __future__ import annotations

import argparse
import json
import sys

from purview_migration.exporter import export_manifest
from purview_migration.importer import import_manifest
from purview_migration.io_utils import read_json, write_json
from purview_migration.models import MigrationManifest
from purview_migration.relink import build_relink_plan
from purview_migration.relink_executor import apply_relink_plan
from purview_migration.report_generator import export_report


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

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "export":
        manifest = export_manifest(args.source_account, max_entities=args.max_entities)
        write_json(args.output, manifest.to_dict())
        print(
            json.dumps(
                {
                    "status": "ok",
                    "output": args.output,
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
        return

    if args.command == "import":
        data = read_json(args.input)
        manifest = MigrationManifest.from_dict(data)
        result = import_manifest(args.target_account, manifest, dry_run=not args.apply)
        print(json.dumps({"status": "ok", "result": result.as_dict()}, indent=2))
        return

    if args.command == "relink":
        data = read_json(args.input)
        manifest = MigrationManifest.from_dict(data)
        plan = build_relink_plan(manifest)
        write_json(args.output, plan)
        print(json.dumps({"status": "ok", "output": args.output, "summary": plan["summary"]}, indent=2))
        return

    if args.command == "relink-apply":
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
        return

    print("Unknown command", file=sys.stderr)
    sys.exit(2)
