# Purview Migration Toolkit (Python)

This project exports and replays Microsoft Purview artifacts so you can migrate non-tenant-persistent configuration from one Purview account/tenant to another.

## Scope covered by this scaffold

- Collections
- Scan data sources
- Scans per data source
- Glossary categories
- Glossary terms
- Classification definitions
- Scan rulesets
- Scan credentials
- Data map assets (entity search snapshot)

## Important notes

- API coverage varies across Purview versions and permissions. This toolkit logs warnings and continues when specific API calls fail.
- Start with `--dry-run` import mode to validate planned writes.
- For full-fidelity migrations, you may need to extend endpoint payload transforms for your environment.

## Prerequisites

- Python 3.10+
- Access to source and target Purview accounts
- RBAC permissions in both accounts
- Azure CLI login (`az login`) or managed identity / service principal available to `DefaultAzureCredential`

## Install

```bash
cd "C:\Users\edcorcor\VSCode\Purview Migration"
python -m pip install -e .
```

## Export from source Purview

```bash
purview-migrate export \
  --source-account <source-purview-account-name> \
  --output manifests/source-export.json
```

## Import into target Purview

Dry run (default):

```bash
purview-migrate import \
  --target-account <target-purview-account-name> \
  --input manifests/source-export.json
```

Apply changes:

```bash
purview-migrate import \
  --target-account <target-purview-account-name> \
  --input manifests/source-export.json \
  --apply
```

## Build relink map

```bash
purview-migrate relink \
  --input manifests/source-export.json \
  --output manifests/relink-plan.json
```

This creates a name-based relink plan (collections, data sources, scans, glossary entities) that you can extend for your specific data product/domain mappings.

## Execute relink plan

Dry run (default):

```bash
purview-migrate relink-apply \
  --target-account <target-purview-account-name> \
  --input manifests/relink-plan.json \
  --output manifests/relink-status.json
```

Apply relink/create of missing mapped objects:

```bash
purview-migrate relink-apply \
  --target-account <target-purview-account-name> \
  --input manifests/relink-plan.json \
  --output manifests/relink-status.json \
  --apply
```

`relink-apply` currently performs full create/link logic for collections, data sources, scans, glossary categories/terms, classifications, rulesets, and credentials.
Entity relink remains validation-only and marks unresolved qualified names for follow-up (for example, re-scan in target).

## Suggested workflow

1. Export source account artifacts.
2. Run import with dry-run against target account.
3. Run import with `--apply` after reviewing output.
4. Generate relink plan and edit target names/mappings if needed.
5. Run `relink-apply` in dry-run mode and inspect unresolved items.
6. Run `relink-apply --apply` to create/link missing mapped artifacts.

## Security

- Avoid committing manifests that contain sensitive metadata.
- Store secrets outside source control.
