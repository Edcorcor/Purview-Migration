# Purview Migration Toolkit

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A comprehensive Python toolkit for migrating Microsoft Purview Data Governance artifacts between tenants and Azure Data Landing Zones. Supports export, import, automated relinking, and detailed status reporting with both CLI and Fabric Notebook interfaces.

## Overview

When migrating to Azure Data Landing Zones or consolidating Purview instances, tenant-level artifacts (collections, scans, glossaries, classifications) must be recreated. This toolkit automates the entire migration workflow:

1. **Export** - Enumerate all artifacts from source Purview account
2. **Import** - Recreate artifacts in target Purview account  
3. **Relink** - Validate and reconnect relationships between artifacts
4. **Report** - Generate detailed status reports grouped by outcome

Supports both command-line execution and Microsoft Fabric Lakehouse notebooks for integration with data engineering workflows.

## Features

### Artifact Coverage

- ✅ **Collections** - Hierarchical collection structures with parent/child relationships
- ✅ **Data Sources** - All registered scan sources (Azure SQL, ADLS, Blob, etc.)
- ✅ **Scans** - Scan configurations per data source
- ✅ **Glossary Categories** - Business glossary category definitions
- ✅ **Glossary Terms** - Business glossary term definitions and relationships
- ✅ **Classification Definitions** - Custom classification schemas
- ✅ **Scan Rulesets** - Custom scan rule configurations
- ✅ **Scan Credentials** - Credential references (secrets managed separately)
- ✅ **Entity Snapshot** - Data map asset inventory for validation

### Capabilities

- **Dry-Run Mode** - Validate all operations before applying changes
- **Incremental Import** - Skip existing artifacts, update only what changed
- **Automated Relinking** - Reconnect collections, scans, and glossary relationships
- **Entity Validation** - Verify data assets exist in target (configurable limit)
- **Status Reporting** - Export JSON/CSV reports grouped by outcome
- **Error Resilience** - Continue on failures, log warnings for review
- **Fabric Integration** - Jupyter notebook for Lakehouse-based execution

## Important notes

- API coverage varies across Purview versions and permissions. This toolkit logs warnings and continues when specific API calls fail.
- Start with `--dry-run` import mode to validate planned writes.
- For full-fidelity migrations, you may need to extend endpoint payload transforms for your environment.

## Prerequisites

- Python 3.10+
- Access to source and target Purview accounts
- RBAC permissions in both accounts
- Azure CLI login (`az login`) or managed identity / service principal available to `DefaultAzureCredential`

## Quickstart

### Installation

```bash
# Clone repository
git clone https://github.com/Edcorcor/Purview-Migration.git
cd Purview-Migration

# Install toolkit
python -m pip install -e .

# Verify installation
purview-migrate --help
```

### Basic Usage

```bash
# 1. Export source artifacts
purview-migrate export \
  --source-account source-purview \
  --output manifests/export.json

# 2. Import to target (dry-run first)
purview-migrate import \
  --target-account target-purview \
  --input manifests/export.json

# 3. Apply import
purview-migrate import \
  --target-account target-purview \
  --input manifests/export.json \
  --apply

# 4. Generate relink plan
purview-migrate relink \
  --input manifests/export.json \
  --output manifests/relink-plan.json

# 5. Execute relink with reports
purview-migrate relink-apply \
  --target-account target-purview \
  --input manifests/relink-plan.json \
  --output manifests/relink-status.json \
  --report-format csv \
  --report-output manifests/report.csv \
  --apply
```

## CLI Reference

### `purview-migrate export`

Export artifacts from source Purview account.

**Required Arguments**:
- `--source-account` - Source Purview account name (without `.purview.azure.com`)
- `--output` - Output path for JSON manifest

**Optional Arguments**:
- `--max-entities` - Maximum entities to export via search (default: 2000)

**Example**:
```bash
purview-migrate export \
  --source-account my-source-purview \
  --output manifests/source-export.json \
  --max-entities 5000
```

### `purview-migrate import`

Import artifacts into target Purview account.

**Required Arguments**:
- `--target-account` - Target Purview account name
- `--input` - Input manifest JSON path

**Optional Arguments**:
- `--apply` - Perform writes (omit for dry-run)

**Example**:
```bash
# Dry-run
purview-migrate import \
  --target-account my-target-purview \
  --input manifests/source-export.json

# Apply
purview-migrate import \
  --target-account my-target-purview \
  --input manifests/source-export.json \
  --apply
```

### `purview-migrate relink`

Generate relink plan from manifest.

**Required Arguments**:
- `--input` - Input manifest JSON path
- `--output` - Output relink plan JSON path

**Example**:
```bash
purview-migrate relink \
  --input manifests/source-export.json \
  --output manifests/relink-plan.json
```

### `purview-migrate relink-apply`

Validate and apply relink plan to target account.

**Required Arguments**:
- `--target-account` - Target Purview account name
- `--input` - Input relink plan JSON path

**Optional Arguments**:
- `--output` - Output path for updated plan with statuses
- `--apply` - Perform writes (omit for dry-run)
- `--max-entity-validation` - Max entities to validate (default: 2000)
- `--report-format` - Report format: `json`, `csv` (default: json)
- `--report-output` - Path to save status report

**Example**:
```bash
# Dry-run with JSON report
purview-migrate relink-apply \
  --target-account my-target-purview \
  --input manifests/relink-plan.json \
  --output manifests/relink-status.json \
  --report-format json \
  --report-output manifests/report.json

# Apply with CSV reports for large estate
purview-migrate relink-apply \
  --target-account my-target-purview \
  --input manifests/relink-plan.json \
  --output manifests/relink-status.json \
  --max-entity-validation 10000 \
  --report-format csv \
  --report-output manifests/report.csv \
  --apply
```

---

## Using with Microsoft Fabric

For Fabric Lakehouse environments, use the included Jupyter notebook:

**Location**: `examples/purview_migration_fabric.ipynb`

**Features**:
- Complete workflow in single notebook
- Stores all artifacts in Lakehouse Files area (`/lakehouse/default/Files/purview_migration/`)
- Uses NotebookUtils/mssparkutils for Fabric integration
- User-configurable settings for dry-run/apply modes
- Automatic directory structure and file management
- Progress tracking and error handling

**To Use**:
1. Upload notebook to Fabric workspace
2. Attach to Lakehouse with Files area
3. Edit configuration cell with your Purview account names
4. Run all cells or step through individually
5. Results persist in Files area for sharing/audit

See [examples/runbook.md](examples/runbook.md) for detailed step-by-step instructions.

## Suggested Workflow

### Command Line

1. **Export** source account artifacts to JSON manifest
2. **Review** manifest for warnings and artifact counts
3. **Import** (dry-run) to validate target compatibility
4. **Import** (apply) to create artifacts in target
5. **Generate** relink plan (edit target names if needed)
6. **Relink** (dry-run) to validate mappings
7. **Relink** (apply) to create/link missing artifacts
8. **Report** export for unresolved items handoff

### Fabric Notebook

1. Configure source/target account names and execution flags
2. Run all cells to execute complete workflow
3. Review reports in Lakehouse Files area
4. Use CSV reports for triage of unresolved/failed items

## Status Reports

Reports group artifacts by outcome for easy triage:

- **linked** - Artifact exists in target, successfully validated
- **created** - Artifact created in target during relink-apply
- **missing** - Artifact doesn't exist in target (dry-run detection)
- **failed** - Creation/linking failed due to error
- **unresolved** - Entity relationship cannot be validated
- **pending** - Not yet processed

**JSON Report** (`--report-format json`):
- Single file with summary counts and full artifact details
- Structured for programmatic analysis

**CSV Reports** (`--report-format csv`):
- One CSV per artifact type (collections, scans, entities, etc.)
- Easy filtering in Excel for handoff to data stewards

## Troubleshooting

### Authentication Issues

```bash
# Ensure Azure CLI login
az login
az account show

# Or use service principal
export AZURE_CLIENT_ID=<client-id>
export AZURE_CLIENT_SECRET=<secret>
export AZURE_TENANT_ID=<tenant-id>
```

### Permission Errors

Required RBAC roles:
- Source: `Purview Data Reader` or higher
- Target: `Purview Data Curator` or higher

### Large Estate Performance

For Purview instances with >2000 entities:

```bash
# Increase entity validation limit
purview-migrate export --max-entities 10000 ...
purview-migrate relink-apply --max-entity-validation 10000 ...
```

### API Version Compatibility

Some Purview API endpoints vary by version. If export/import fails:
- Check manifest warnings for specific endpoint errors
- Extend `client.py` with version-specific handling
- File issue with error details and Purview version

## Security

- **Manifests contain sensitive metadata** - Use `.gitignore` to exclude from version control
- **Credentials are references only** - Actual secrets must be configured separately in target Key Vault
- **Use managed identities** - Prefer MSI over service principals when possible
- **RBAC principle of least privilege** - Grant only required permissions

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit pull request with detailed description

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support

For issues, questions, or feature requests:
- **GitHub Issues**: [https://github.com/Edcorcor/Purview-Migration/issues](https://github.com/Edcorcor/Purview-Migration/issues)
- **Documentation**: See `examples/runbook.md` for detailed walkthrough
