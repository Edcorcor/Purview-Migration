# Purview Migration Toolkit

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A comprehensive Python toolkit for migrating Microsoft Purview Data Governance artifacts between tenants and Azure Data Landing Zones. Supports export, import, automated relinking, and detailed status reporting with both CLI and Fabric Notebook interfaces.

## Recent Updates (April 2026)

- Added Lakehouse analytics packaging from export manifests:
  - `json/` raw artifact files
  - `tables/` CSV files for collections, data sources, scans, entities, and summary
  - `semantic/` semantic model and report specification files
- Added CLI support for direct Lakehouse packaging:
  - `purview-migrate export --lakehouse-output-dir ...`
  - `purview-migrate lakehouse-package --input ... --output-dir ...`
- Expanded Fabric notebook workflow (`examples/purview_migration_fabric.ipynb`) with:
  - Step 1b: Create managed Lakehouse Delta tables from generated CSV files
  - Step 1c: Validate semantic model table bindings before reporting
- Refactored internals for readability and maintainability:
  - Command handlers split in CLI
  - Import and relink builders simplified with shared helper patterns
  - Script generator split into focused template builder functions
  - Shared artifact key constants introduced
- Added lightweight unit tests:
  - `tests/test_script_generator.py`
  - `tests/test_cli_helpers.py`

## Overview

**⚠️ Critical Constraint: Only ONE Purview Data Governance account can exist at a time in your Azure environment.**

When migrating to Azure Data Landing Zones or recreating Purview accounts, you must **delete the existing account before creating a new one**. All tenant-level artifacts (collections, data sources, scans, glossaries, classifications, data products, data quality rules) will be lost unless backed up first.

This toolkit solves that problem by automating the complete backup-delete-restore workflow:

1. **Export** - Capture all metadata from your current Purview account
2. **Validate** - Verify completeness before deletion (with exit codes for safety)
3. **Generate Scripts** - Auto-create permission grants and dependency linkage scripts
4. **Delete & Recreate** - Remove old account, create new account (manual Azure CLI steps)
5. **Import** - Restore all artifacts to the new account
6. **Relink** - Reconnect relationships between collections, scans, glossary terms, data products, and data quality rules
7. **Report** - Generate detailed status reports for verification

Supports both command-line execution and Microsoft Fabric Lakehouse notebooks for integration with data engineering workflows.

## The Problem This Solves

**You cannot have two Purview Data Governance accounts simultaneously.** When you need to:
- Migrate to an Azure Data Landing Zone architecture
- Change Purview account names or regions
- Consolidate governance across tenants
- Recover from configuration issues

You must:
You must:
1. Export ALL metadata first (or lose it permanently)
2. Delete the old Purview account
3. Create the new Purview account
4. Restore ALL metadata to the new account
5. Relink data sources, scans, data products, data quality rules, and Key Vault credentials

**Without this toolkit, you'd lose:** Collections, data source registrations, scan configurations, business glossary, custom classifications, scan rulesets, scan credentials, data products, data quality rules, and all relationships between them.

## Complete Workflow

```bash
# 1. Export everything from current account
purview-migrate export \
  --source-account current-account \
  --output backup.json \
  --max-entities 10000

# 2. Validate completeness (MUST PASS before deletion!)
purview-migrate validate \
  --input backup.json \
  --output validation.json
# Exit code 0 = safe to delete, Exit code 1 = DO NOT DELETE

# 3. Generate restoration scripts
purview-migrate generate-scripts \
  --input backup.json \
  --new-account-name new-account \
  --subscription-id <sub-id> \
  --output-dir scripts/

# ⚠️ POINT OF NO RETURN ⚠️
# 4. Delete old account (cannot be undone!)
az purview account delete --name current-account --resource-group <rg> --yes

# 5. Create new account
az purview account create \
  --name new-account \
  --resource-group <rg> \
  --location <location> \
  --managed-resource-group-name <mrg-name>

# 6. Restore all metadata
purview-migrate import \
  --target-account new-account \
  --input backup.json \
  --apply

# 7. Relink artifacts and validate
purview-migrate relink \
  --input backup.json \
  --output relink-plan.json

purview-migrate relink-apply \
  --target-account new-account \
  --input relink-plan.json \
  --apply \
  --report-output report.csv

# 8. Grant managed identity permissions to data sources
bash scripts/permissions.sh

# 9. Link Key Vault for scan credentials
bash scripts/link-keyvault.sh

# 10. Recreate scan credentials in Purview Portal
# (Secrets cannot be exported, must be manually reconfigured)

# 11. Test scans and verify data products/data quality rules
```

**📖 Detailed Guide:** [DELETE-AND-RECREATE-WORKFLOW.md](examples/DELETE-AND-RECREATE-WORKFLOW.md)  
**✅ Pre-Flight Checklist:** [PRE-FLIGHT-CHECKLIST.md](docs/PRE-FLIGHT-CHECKLIST.md)

## What Gets Migrated

### Artifact Coverage

- ✅ **Collections** - Hierarchical collection structures with parent/child relationships
- ✅ **Data Sources** - All registered scan sources (Azure SQL, ADLS, Blob, etc.)
- ✅ **Scans** - Scan configurations per data source
- ✅ **Glossary Categories** - Business glossary category definitions
- ✅ **Glossary Terms** - Business glossary term definitions and relationships
- ✅ **Classification Definitions** - Custom classification schemas
- ✅ **Scan Rulesets** - Custom scan rule configurations
- ✅ **Scan Credentials** - Credential references (secrets managed separately in Key Vault)
- ✅ **Entity Snapshot** - Data map asset inventory for validation
- ⚠️ **Data Products** - Captured via entity relationships (requires manual verification)
- ⚠️ **Data Quality Rules** - Captured via scan configurations (requires relinking to data sources)

### What Requires Manual Steps

- **Scan Credential Secrets** - Key Vault secrets cannot be exported; must be recreated in Portal
- **Managed Identity Permissions** - New account needs RBAC grants (automated via generated scripts)
- **Integration Runtimes** - Self-hosted IR must be reconfigured on host machines
- **Private Endpoints** - Network connections must be recreated (ARM templates generated)
- **Key Vault Linkage** - Connection to Key Vault must be reestablished (script generated)

### Capabilities

- **Validation Before Deletion** - Exit codes prevent deletion if backup incomplete
- **Script Generation** - Auto-create permission grants, Key Vault linkage, ARM templates
- **Dry-Run Mode** - Validate all operations before applying changes
- **Automated Relinking** - Reconnect collections, scans, glossary terms, data products, and data quality rules
- **Entity Validation** - Verify data assets exist after restoration (configurable limit)
- **Status Reporting** - Export JSON/CSV reports grouped by outcome (linked/created/missing/failed)
- **Error Resilience** - Continue on failures, accumulate warnings for review
- **Fabric Integration** - Jupyter notebook for Lakehouse-based execution with NotebookUtils

## Important notes

- API coverage varies across Purview versions and permissions. This toolkit logs warnings and continues when specific API calls fail.
- Start with `--dry-run` import mode to validate planned writes.
- For full-fidelity migrations, you may need to extend endpoint payload transforms for your environment.

## Prerequisites

- Python 3.10+
- Access to current Purview account with read permissions
- RBAC permissions to delete and create Purview accounts (Owner or Contributor on resource group)
- RBAC permissions on data sources for managed identity grants after recreation
- Access to Key Vault(s) containing scan credential secrets
- Azure CLI installed and authenticated (`az login`)
- DefaultAzureCredential authentication available (Azure CLI, managed identity, or service principal)

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
# 1. Export current account artifacts
purview-migrate export \
  --source-account current-purview \
  --output manifests/backup.json \
  --max-entities 10000

# 2. Validate backup completeness (CRITICAL!)
purview-migrate validate \
  --input manifests/backup.json \
  --output manifests/validation.json
# Must exit with code 0 (PASS) before proceeding to deletion!

# 3. Generate restoration scripts
purview-migrate generate-scripts \
  --input manifests/backup.json \
  --new-account-name new-purview \
  --subscription-id <your-subscription-id> \
  --output-dir scripts/

# ⚠️ POINT OF NO RETURN - Verify backup before proceeding! ⚠️

# 4. Delete old account
az purview account delete \
  --name current-purview \
  --resource-group <resource-group> \
  --yes

# 5. Create new account
az purview account create \
  --name new-purview \
  --resource-group <resource-group> \
  --location <location> \
  --managed-resource-group-name <mrg-name>

# 6. Import all metadata
purview-migrate import \
  --target-account new-purview \
  --input manifests/backup.json \
  --apply

# 7. Generate and apply relink plan
purview-migrate relink \
  --input manifests/backup.json \
  --output manifests/relink-plan.json

purview-migrate relink-apply \
  --target-account new-purview \
  --input manifests/relink-plan.json \
  --apply \
  --report-format csv \
  --report-output manifests/report.csv

# 8. Grant managed identity permissions
bash scripts/permissions.sh

# 9. Link Key Vault
bash scripts/link-keyvault.sh

# 10. Manually recreate scan credentials in Purview Portal
# - Management Center → Credentials → Create new
# - Link to Key Vault secrets (secrets cannot be exported)
```

## CLI Reference

### `purview-migrate export`

Export artifacts from source Purview account.

**Required Arguments**:
- `--source-account` - Source Purview account name (without `.purview.azure.com`)
- `--output` - Output path for JSON manifest

**Optional Arguments**:
- `--max-entities` - Maximum entities to export via search (default: 2000)
- `--lakehouse-output-dir` - Optional directory for Lakehouse-ready outputs (JSON files, tables, semantic/report artifacts)
- `--no-table-exports` - Skip table CSV exports when writing Lakehouse outputs
- `--no-semantic-report` - Skip semantic model/report artifact generation when writing Lakehouse outputs

**Example**:
```bash
purview-migrate export \
  --source-account my-source-purview \
  --output manifests/source-export.json \
  --max-entities 5000

# Export + Lakehouse package (JSON + tables + semantic/report metadata)
purview-migrate export \
  --source-account my-source-purview \
  --output manifests/source-export.json \
  --lakehouse-output-dir manifests/lakehouse
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

### `purview-migrate validate`

Validate manifest completeness before account deletion.

**⚠️ Use Case**: Before deleting a Purview account, verify all critical artifacts have been captured.

**Required Arguments**:
- `--input` - Input manifest JSON path

**Optional Arguments**:
- `--output` - Output path for validation report JSON

**Example**:
```bash
purview-migrate validate \
  --input manifests/pre-deletion-backup.json \
  --output manifests/validation-report.json
```

**Output Structure**:
```json
{
  "validation_status": "PASS",
  "deletion_ready": true,
  "critical_checks": [
    {"name": "collections", "captured": 15, "status": "OK"}
  ],
  "warnings": ["⚠ 5 scan credentials captured as references only"],
  "manual_steps_required": [
    {
      "category": "Managed Identity Permissions",
      "action": "Grant new managed identity permissions to data sources",
      "automation": "Script generation available"
    }
  ],
  "summary": {
    "total_collections": 15,
    "total_data_sources": 28,
    "manual_steps_count": 4
  }
}
```

**Exit Codes**:
- `0` - Validation passed, safe to delete
- `1` - Validation failed, DO NOT delete

### `purview-migrate generate-scripts`

Generate permission and linkage scripts for account restoration.

**⚠️ Use Case**: After account recreation, automate permission grants, Key Vault linkage, and dependency configuration.

**Required Arguments**:
- `--input` - Input manifest JSON path
- `--new-account-name` - Name of the new Purview account
- `--subscription-id` - Azure subscription ID
- `--output-dir` - Directory to write generated scripts

**Example**:
```bash
purview-migrate generate-scripts \
  --input manifests/pre-deletion-backup.json \
  --new-account-name my-new-purview \
  --subscription-id 12345678-1234-1234-1234-123456789012 \
  --output-dir scripts/
```

**Generated Files**:
- `RESTORATION_GUIDE.md` - Step-by-step restoration instructions
- `permissions.sh` - Azure CLI script to grant managed identity permissions to data sources
- `permissions.ps1` - PowerShell version of permission grants
- `link-keyvault.sh` - Key Vault linkage script
- `private-endpoint.arm.json` - ARM template for private endpoint recreation

### `purview-migrate lakehouse-package`

Create a Lakehouse analytics package from an existing manifest JSON.

**Use Case**: Keep raw JSON configs while also producing table files and semantic/report definitions for Fabric/Power BI analytics.

**Required Arguments**:
- `--input` - Input manifest JSON path
- `--output-dir` - Directory to write Lakehouse package files

**Optional Arguments**:
- `--no-table-exports` - Skip table CSV exports
- `--no-semantic-report` - Skip semantic model/report artifact generation

**Example**:
```bash
purview-migrate lakehouse-package \
  --input manifests/source-export.json \
  --output-dir manifests/lakehouse
```

**Outputs**:
- `json/` - One JSON file per artifact type (`collections.json`, `dataSources.json`, `entities.json`, etc.)
- `tables/` - Table-ready CSVs (`collections.csv`, `dataSources.csv`, `scans.csv`, `entities.csv`, `artifact_summary.csv`)
- `semantic/semantic_model.json` - Relationship-aware semantic model definition
- `semantic/report_spec.json` - Suggested report layout (pages/visuals)
- `semantic/capture_summary.json` and `semantic/capture_summary.md` - Coverage summary for audit/review

---

## Using with Microsoft Fabric

For Fabric Lakehouse environments, use the included Jupyter notebook:

**Location**: `examples/purview_migration_fabric.ipynb`

**Features**:
- Complete workflow in single notebook
- Stores all artifacts in Lakehouse Files area (`/lakehouse/default/Files/purview_migration/`)
- Supports analytics-friendly table exports for assets, scans, collections, and related artifacts
- Produces semantic model and report metadata files for quick Power BI/Fabric model setup
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

## Recommended Workflow

### Command Line (Delete & Recreate)

**⚠️ Remember: Only ONE Purview account can exist at a time**

1. **Export** - Capture all metadata from current account
2. **Validate** - Verify backup completeness (exit code 0 = safe to delete)
3. **Generate Scripts** - Create permission grants and linkage automation
4. **Review** - Check validation report, warnings, manual steps required
5. **Backup** - Store manifest in multiple secure locations (Git, storage account)
6. **Delete** - Remove old Purview account (⚠️ POINT OF NO RETURN)
7. **Create** - Provision new Purview account (wait for "Succeeded" status)
8. **Import** - Restore all artifacts to new account
9. **Relink** - Reconnect relationships between artifacts
10. **Permissions** - Grant managed identity access to data sources (run generated scripts)
11. **Key Vault** - Link Key Vault for scan credentials
12. **Credentials** - Manually recreate scan credentials in Portal (secrets cannot be exported)
13. **Test** - Run test scans on representative data sources
14. **Verify** - Check data products, data quality rules, lineage
15. **Cutover** - Enable scheduled scans, update external references

### Fabric Notebook (Delete & Recreate)

**Note:** Fabric notebook handles the same delete-and-recreate workflow as CLI

1. Edit configuration cell with current and new Purview account names
2. Set execution flags (RUN_EXPORT, RUN_VALIDATE, etc.)
3. Run export and validation cells first
4. Review validation report - ensure deletion_ready = true
5. **Manually delete and recreate account via Azure Portal or CLI**
6. Run import and relink cells to restore metadata
7. Review reports in Lakehouse Files area (`/lakehouse/default/Files/purview_migration/`)
8. Use CSV reports for triage of unresolved/failed items
9. Complete manual steps (permissions, credentials, Key Vault linkage)

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

## Testing

Run unit tests from repository root:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

Current test coverage includes:
- script generation output and template content checks
- CLI manifest normalization helper behavior

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
