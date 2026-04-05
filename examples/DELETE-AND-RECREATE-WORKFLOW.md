# Purview Account Delete & Recreate Workflow

This guide covers the scenario where you need to **delete your existing Purview account** and **recreate it** while preserving all metadata, configurations, and relationships.

## ⚠️ Critical Considerations

- **This is a destructive operation** - the old account will be permanently deleted
- **Complete backup first** - ensure validation passes before deletion
- **Downtime expected** - plan for 1-2 hours minimum
- **Secrets don't migrate** - scan credentials require manual reconfiguration
- **Test thoroughly** - verify all functionality after restoration

## Prerequisites

1. **Permissions Required**
   - Owner or Contributor on source Purview account
   - Owner or Contributor on target resource group
   - Ability to create Purview accounts in subscription
   - Access to Key Vault containing scan credentials

2. **Tools Required**
   ```bash
   # Install the toolkit
   pip install -e .
   
   # Install Azure CLI
   az login
   az account set --subscription <subscription-id>
   ```

3. **Information Gathering**
   - Source account name
   - Target account name (can be same as source)
   - Resource group
   - Location/region
   - Key Vault name(s) used for credentials
   - List of all data sources being scanned

## Phase 1: Capture & Validate

### Step 1: Export Everything

Export all metadata from the existing account:

```bash
purview-migrate export \
  --source-account <current-account-name> \
  --output manifests/pre-deletion-backup.json \
  --max-entities 5000
```

**Expected Output:**
```json
{
  "status": "ok",
  "output": "manifests/pre-deletion-backup.json",
  "counts": {
    "collections": 15,
    "dataSources": 28,
    "scans": 45,
    "glossaryTerms": 150,
    "entities": 5000
  },
  "warnings": [...]
}
```

### Step 2: Validate Completeness

Verify that all critical artifacts have been captured:

```bash
purview-migrate validate \
  --input manifests/pre-deletion-backup.json \
  --output manifests/validation-report.json
```

**Review the validation report carefully:**

```json
{
  "validation_status": "PASS",
  "deletion_ready": true,
  "critical_checks": [
    {"name": "collections", "captured": 15, "status": "OK"},
    {"name": "dataSources", "captured": 28, "status": "OK"}
  ],
  "warnings": [
    "⚠ 5 scan credentials captured as references only",
    "⚠ Integration Runtimes not captured"
  ],
  "manual_steps_required": [
    {
      "category": "Credentials",
      "action": "Recreate scan credentials in target account",
      "automation": "Partially"
    },
    {
      "category": "Managed Identity Permissions",
      "action": "Grant new managed identity permissions to data sources",
      "automation": "Script generation available"
    }
  ],
  "summary": {
    "total_collections": 15,
    "total_data_sources": 28,
    "total_scans": 45,
    "manual_steps_count": 4,
    "warnings_count": 2
  }
}
```

**❌ If validation_status is "FAIL":**
- Review the critical_checks array
- Address any missing artifacts
- Re-run export with corrected parameters
- Do NOT proceed to deletion

**✅ If validation_status is "PASS":**
- Review manual_steps_required
- Document any custom configurations
- Proceed to script generation

### Step 3: Generate Restoration Scripts

Generate all helper scripts for post-creation setup:

```bash
purview-migrate generate-scripts \
  --input manifests/pre-deletion-backup.json \
  --new-account-name <new-account-name> \
  --subscription-id <your-subscription-id> \
  --output-dir scripts/
```

**Generated Files:**
- `scripts/RESTORATION_GUIDE.md` - Step-by-step restoration instructions
- `scripts/permissions.sh` - Azure CLI script to grant managed identity permissions
- `scripts/permissions.ps1` - PowerShell version of permission grants
- `scripts/link-keyvault.sh` - Key Vault linkage script
- `scripts/private-endpoint.arm.json` - ARM template for private endpoints

### Step 4: Final Checklist

**Before deletion, verify:**

- [ ] Export completed successfully
- [ ] Validation report shows `"deletion_ready": true`
- [ ] Backup manifest saved in secure location
- [ ] Restoration scripts generated and reviewed
- [ ] Key Vault accessible and contains all credential secrets
- [ ] Documented all custom network rules or private endpoints
- [ ] Notified stakeholders of planned downtime
- [ ] Confirmed subscription quota for Purview accounts

## Phase 2: Delete & Recreate

### Step 5: Delete Old Account

**⚠️ POINT OF NO RETURN - Backup confirmed? Yes? Proceed:**

```bash
# Delete the account
az purview account delete \
  --name <old-account-name> \
  --resource-group <resource-group> \
  --yes

# Wait for deletion to complete
az purview account show \
  --name <old-account-name> \
  --resource-group <resource-group>
# Should return: ResourceNotFound
```

**Deletion typically takes 10-20 minutes.**

### Step 6: Create New Account

```bash
# Create new Purview account
az purview account create \
  --name <new-account-name> \
  --resource-group <resource-group> \
  --location <location> \
  --managed-resource-group-name <managed-rg-name> \
  --public-network-access Enabled

# Wait for creation to complete
az purview account show \
  --name <new-account-name> \
  --resource-group <resource-group> \
  --query provisioningState
# Should return: "Succeeded"
```

**Creation typically takes 15-30 minutes.**

**Get the new managed identity:**

```bash
az purview account show \
  --name <new-account-name> \
  --resource-group <resource-group> \
  --query identity.principalId -o tsv
```

Save this Principal ID - you'll need it for permissions.

## Phase 3: Restore & Relink

### Step 7: Import Artifacts

Restore all artifacts to the new account:

```bash
# Start with dry-run to validate
purview-migrate import \
  --target-account <new-account-name> \
  --input manifests/pre-deletion-backup.json

# If dry-run succeeds, apply for real
purview-migrate import \
  --target-account <new-account-name> \
  --input manifests/pre-deletion-backup.json \
  --apply
```

**Monitor the output for:**
- Collections created count
- Data sources registered count
- Scans configured count
- Any import errors

### Step 8: Generate & Apply Relink Plan

Create name-based mappings and link artifacts:

```bash
# Generate the relink plan
purview-migrate relink \
  --input manifests/pre-deletion-backup.json \
  --output manifests/relink-plan.json

# Validate relink plan (dry-run)
purview-migrate relink-apply \
  --target-account <new-account-name> \
  --input manifests/relink-plan.json \
  --max-entity-validation 5000

# Apply the relink plan
purview-migrate relink-apply \
  --target-account <new-account-name> \
  --input manifests/relink-plan.json \
  --apply \
  --max-entity-validation 5000 \
  --report-format csv \
  --report-output manifests/relink-report.csv
```

**Review relink report for:**
- Linked vs Created vs Missing artifacts
- Failed operations requiring manual intervention

### Step 9: Grant Managed Identity Permissions

Run the generated permission scripts:

**Azure CLI:**
```bash
bash scripts/permissions.sh
```

**Or PowerShell:**
```powershell
pwsh scripts/permissions.ps1
```

**For SQL Server data sources, run T-SQL manually:**

```sql
-- Connect to each SQL database
USE YourDatabase;
GO

-- Create user for Purview managed identity
CREATE USER [<new-account-name>] FROM EXTERNAL PROVIDER;

-- Grant reader permissions
ALTER ROLE db_datareader ADD MEMBER [<new-account-name>];
GO
```

### Step 10: Link Key Vault

```bash
bash scripts/link-keyvault.sh
```

**Then complete in Azure Portal:**
1. Navigate to Purview account → Management Center → Credentials
2. Click "Manage Key Vault connections"
3. Add your Key Vault
4. Test the connection

### Step 11: Recreate Scan Credentials

For each scan credential in the old account:

1. Go to Management Center → Credentials
2. Create new credential
3. Select same authentication method (e.g., Service Principal, Account Key)
4. Reference the Key Vault secret name from old account
5. Test the credential

**Credential secret names from backup:**
```bash
# Extract credential names from manifest
cat manifests/pre-deletion-backup.json | \
  jq -r '.scanCredentials[].name'
```

### Step 12: Configure Private Endpoints (if needed)

If you used private endpoints:

```bash
# Deploy ARM template
az deployment group create \
  --resource-group <resource-group> \
  --template-file scripts/private-endpoint.arm.json \
  --parameters purviewAccountName=<new-account-name> \
                vnetName=<vnet-name> \
                subnetName=<subnet-name>
```

### Step 13: Reconfigure Integration Runtimes (if needed)

For self-hosted integration runtimes:

1. Navigate to Management Center → Integration runtimes
2. Create new self-hosted IR
3. Copy authentication key
4. Install/reconfigure IR on VM:
   ```powershell
   # On IR host machine
   .\RegisterIntegrationRuntime.exe <authentication-key>
   ```

## Phase 4: Verification

### Step 14: Verify All Components

**Collections:**
```bash
# Via API
curl -H "Authorization: Bearer $(az account get-access-token --resource https://purview.azure.com --query accessToken -o tsv)" \
  https://<new-account-name>.purview.azure.com/account/collections?api-version=2019-11-01-preview
```

**Data Sources:**
- Navigate to Data Map → Sources
- Verify all sources appear
- Check registration details

**Scans:**
- For each data source, verify scan rules
- Check scan schedules
- Validate scan credentials linked correctly

**Glossary:**
- Navigate to Data Catalog → Glossary
- Verify terms and categories
- Check term hierarchies

**Classifications:**
- Data Map → Classifications
- Verify custom classifications

### Step 15: Test Scan Execution

Run a test scan on one data source:

1. Select a representative data source (e.g., small ADLS container)
2. Trigger manual scan
3. Monitor scan progress
4. Verify assets discovered

**Troubleshoot common scan failures:**
- **Authentication error**: Check credential configuration
- **Permission denied**: Verify managed identity RBAC roles
- **Network error**: Check private endpoints and firewall rules
- **Integration runtime error**: Verify IR connectivity

### Step 16: Resume Production Scanning

Once test scan succeeds:

1. Enable scan schedules on all data sources
2. Monitor initial scan runs
3. Review discovered assets in Data Catalog
4. Verify lineage relationships

## Phase 5: Post-Migration Tasks

### Update External References

If other services reference the Purview account:

**Azure Data Factory:**
```json
// Update linked service
{
  "name": "PurviewLinkedService",
  "properties": {
    "type": "AzurePurview",
    "typeProperties": {
      "endpoint": "https://<new-account-name>.purview.azure.com"
    }
  }
}
```

**Azure Synapse:**
- Update Purview connection in workspace settings
- Re-link to new account endpoint

**Custom Applications:**
- Update Purview endpoint URLs
- Verify API authentication still works

### Update RBAC Assignments

Grant roles on the new Purview account:

```bash
# Purview Data Curator
az role assignment create \
  --role "Purview Data Curator" \
  --assignee <user-or-group-object-id> \
  --scope /subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.Purview/accounts/<new-account-name>

# Purview Data Reader
az role assignment create \
  --role "Purview Data Reader" \
  --assignee <user-or-group-object-id> \
  --scope /subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.Purview/accounts/<new-account-name>
```

### Final Verification Checklist

- [ ] All collections visible in Data Map
- [ ] All data sources registered correctly
- [ ] All scans configured with proper credentials
- [ ] Test scan executed successfully on each source type
- [ ] Glossary terms and relationships intact
- [ ] Custom classifications available
- [ ] Scan rulesets configured
- [ ] Integration runtimes connected (if applicable)
- [ ] Private endpoints working (if applicable)
- [ ] External services updated with new endpoint
- [ ] RBAC roles assigned to users
- [ ] Documentation updated with new account details

## Rollback Procedures

If restoration fails or issues are discovered:

### Option 1: Retry Restoration

If the new account exists but import failed:

```bash
# Re-run import
purview-migrate import \
  --target-account <new-account-name> \
  --input manifests/pre-deletion-backup.json \
  --apply

# Re-run relink
purview-migrate relink-apply \
  --target-account <new-account-name> \
  --input manifests/relink-plan.json \
  --apply
```

### Option 2: Create in Different Region

If regional issues or quota limits:

```bash
# Delete failed account
az purview account delete \
  --name <new-account-name> \
  --resource-group <resource-group> \
  --yes

# Create in different region
az purview account create \
  --name <new-account-name> \
  --resource-group <resource-group> \
  --location <different-location> \
  ...
```

### Option 3: Partial Restoration

If only specific artifacts fail:

1. Review error messages in import/relink output
2. Manually create failed artifacts in Portal
3. Re-run relink for remaining items

## Troubleshooting

### Import Failures

**Error:** `Collection parent not found`
- **Cause:** Parent collection wasn't created first
- **Fix:** Import uses dependency ordering, but verify parent exists
- **Manual:** Create parent collection in Portal manually

**Error:** `Data source registration failed`
- **Cause:** Resource ID invalid or permissions missing
- **Fix:** Verify resource still exists and is accessible
- **Manual:** Register data source through Portal

### Relink Failures

**Error:** `Scan credential not found`
- **Cause:** Credential not recreated yet
- **Fix:** Complete Step 11 (Recreate Scan Credentials) first
- **Manual:** Create credential, then re-run relink

**Error:** `Entity validation limit reached`
- **Cause:** More entities than --max-entity-validation
- **Fix:** Increase limit: `--max-entity-validation 10000`
- **Note:** Entity validation is informational only

### Scan Failures

**Error:** `Authentication failed`
- **Cause:** Credential misconfigured or Key Vault secret missing
- **Fix:** Verify secret exists in Key Vault, recreate credential

**Error:** `403 Forbidden`
- **Cause:** Managed identity lacks RBAC permissions
- **Fix:** Re-run permission scripts or grant manually:
  ```bash
  az role assignment create \
    --role "Storage Blob Data Reader" \
    --assignee <purview-managed-identity-id> \
    --scope <storage-account-resource-id>
  ```

**Error:** `Integration runtime not available`
- **Cause:** Self-hosted IR not reconfigured
- **Fix:** Complete Step 13 (Reconfigure Integration Runtimes)

### Performance Issues

**Slow import:**
- Reduce parallelism by processing collections sequentially
- Check API throttling limits

**Slow entity validation:**
- Reduce `--max-entity-validation` parameter
- Entity validation is optional, can be skipped

## Best Practices

1. **Timing:**
   - Schedule during maintenance window
   - Avoid month-end or critical reporting periods
   - Allow 2-4 hours for complete process

2. **Communication:**
   - Notify all Purview users in advance
   - Provide new account details before go-live
   - Document any configuration changes

3. **Testing:**
   - Test import in dry-run mode first
   - Validate one scan before enabling all
   - Verify critical business glossary terms

4. **Backup:**
   - Store manifest in source control (Git)
   - Keep validation report for compliance
   - Document manual configuration steps

5. **Monitoring:**
   - Monitor first scans closely
   - Check Azure Monitor for account health
   - Review scan history for errors

## Support

If you encounter issues:

1. Check validation report for warnings
2. Review generated restoration guide
3. Consult Purview API documentation
4. Open GitHub issue with:
   - Manifest summary (counts only, no sensitive data)
   - Validation report
   - Error messages from CLI output

## Related Documentation

- [Main README](../README.md)
- [Command Reference](../README.md#cli-reference)
- [Runbook Examples](./runbook.md)
- [Manifest Schema](./manifest-shape.json)
