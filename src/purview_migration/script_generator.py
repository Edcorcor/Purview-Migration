from __future__ import annotations

from typing import Any


def generate_permission_scripts(manifest: dict[str, Any], new_account_name: str, subscription_id: str) -> dict[str, str]:
    """
    Generate Azure CLI and PowerShell scripts to grant permissions after account recreation.
    """
    
    artifacts = manifest.get("artifacts", {})
    scripts = {}
    
    # Generate managed identity permission script
    data_sources = artifacts.get("dataSources", [])
    
    azure_cli_permissions = f"""#!/bin/bash
# Grant Purview Managed Identity permissions to data sources
# Run this after creating the new Purview account: {new_account_name}

set -e

PURVIEW_ACCOUNT="{new_account_name}"
SUBSCRIPTION_ID="{subscription_id}"

echo "Getting Purview managed identity..."
PURVIEW_PRINCIPAL_ID=$(az purview account show \\
  --name $PURVIEW_ACCOUNT \\
  --resource-group <resource-group-name> \\
  --query identity.principalId -o tsv)

echo "Purview Managed Identity: $PURVIEW_PRINCIPAL_ID"
echo ""

"""
    
    # Add permissions for each data source
    for idx, source in enumerate(data_sources, 1):
        source_name = source.get("name", f"source-{idx}")
        source_kind = source.get("kind", "Unknown")
        properties = source.get("properties", {})
        
        # Try to extract resource information
        resource_id = properties.get("resourceId") or properties.get("endpoint") or properties.get("serverEndpoint")
        
        if resource_id:
            azure_cli_permissions += f"""# Data Source {idx}: {source_name} ({source_kind})
echo "Granting permissions for {source_name}..."

"""
            if "storage" in source_kind.lower() or "adls" in source_kind.lower():
                azure_cli_permissions += f"""az role assignment create \\
  --role "Storage Blob Data Reader" \\
  --assignee $PURVIEW_PRINCIPAL_ID \\
  --scope "{resource_id}"

"""
            elif "sql" in source_kind.lower():
                azure_cli_permissions += f"""# For SQL: Grant db_datareader role via T-SQL:
# CREATE USER [{new_account_name}] FROM EXTERNAL PROVIDER;
# ALTER ROLE db_datareader ADD MEMBER [{new_account_name}];

"""
    
    azure_cli_permissions += """
echo "✓ Permission grants completed"
echo "⚠ Review and grant SQL Server permissions manually using T-SQL commands above"
"""
    
    scripts["permissions.sh"] = azure_cli_permissions
    
    # PowerShell version
    powershell_permissions = f"""# PowerShell script to grant Purview Managed Identity permissions
# Run this after creating the new Purview account: {new_account_name}

$ErrorActionPreference = "Stop"

$PurviewAccount = "{new_account_name}"
$SubscriptionId = "{subscription_id}"
$ResourceGroup = "<resource-group-name>"

Write-Host "Getting Purview managed identity..." -ForegroundColor Cyan
$purview = Get-AzPurviewAccount -Name $PurviewAccount -ResourceGroupName $ResourceGroup
$principalId = $purview.Identity.PrincipalId

Write-Host "Purview Managed Identity: $principalId" -ForegroundColor Green
Write-Host ""

"""
    
    for idx, source in enumerate(data_sources, 1):
        source_name = source.get("name", f"source-{idx}")
        source_kind = source.get("kind", "Unknown")
        properties = source.get("properties", {})
        resource_id = properties.get("resourceId") or properties.get("endpoint")
        
        if resource_id and ("storage" in source_kind.lower() or "adls" in source_kind.lower()):
            powershell_permissions += f"""# Data Source {idx}: {source_name}
Write-Host "Granting Storage Blob Data Reader for {source_name}..." -ForegroundColor Cyan
New-AzRoleAssignment -ObjectId $principalId `
  -RoleDefinitionName "Storage Blob Data Reader" `
  -Scope "{resource_id}"

"""
    
    powershell_permissions += """
Write-Host "✓ Permission grants completed" -ForegroundColor Green
Write-Host "⚠ Review and grant SQL Server permissions manually" -ForegroundColor Yellow
"""
    
    scripts["permissions.ps1"] = powershell_permissions
    
    # Generate Key Vault linkage script
    key_vault_script = f"""#!/bin/bash
# Link Key Vault to new Purview account
# Prerequisites: Key Vault must exist and contain scan credentials

PURVIEW_ACCOUNT="{new_account_name}"
KEY_VAULT_NAME="<your-key-vault-name>"
RESOURCE_GROUP="<resource-group-name>"

echo "Linking Key Vault to Purview account..."

# Get Purview managed identity
PURVIEW_PRINCIPAL_ID=$(az purview account show \\
  --name $PURVIEW_ACCOUNT \\
  --resource-group $RESOURCE_GROUP \\
  --query identity.principalId -o tsv)

# Grant Key Vault permissions
echo "Granting Key Vault permissions to Purview..."
az keyvault set-policy \\
  --name $KEY_VAULT_NAME \\
  --object-id $PURVIEW_PRINCIPAL_ID \\
  --secret-permissions get list

# Link Key Vault in Purview (via Az CLI or Portal)
echo "✓ Key Vault permissions granted"
echo "⚠ Complete Key Vault linkage in Purview Portal: Management > Credentials > Key Vault connections"
"""
    
    scripts["link-keyvault.sh"] = key_vault_script
    
    # Generate ARM template for private endpoints (if needed)
    arm_template = {
        "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
        "contentVersion": "1.0.0.0",
        "parameters": {
            "purviewAccountName": {
                "type": "string",
                "defaultValue": new_account_name
            },
            "privateEndpointName": {
                "type": "string",
                "defaultValue": f"{new_account_name}-pe"
            },
            "vnetName": {
                "type": "string",
                "metadata": {"description": "Virtual Network name"}
            },
            "subnetName": {
                "type": "string",
                "metadata": {"description": "Subnet name for private endpoint"}
            }
        },
        "resources": [
            {
                "type": "Microsoft.Network/privateEndpoints",
                "apiVersion": "2021-05-01",
                "name": "[parameters('privateEndpointName')]",
                "location": "[resourceGroup().location]",
                "properties": {
                    "subnet": {
                        "id": "[resourceId('Microsoft.Network/virtualNetworks/subnets', parameters('vnetName'), parameters('subnetName'))]"
                    },
                    "privateLinkServiceConnections": [
                        {
                            "name": "[parameters('privateEndpointName')]",
                            "properties": {
                                "privateLinkServiceId": "[resourceId('Microsoft.Purview/accounts', parameters('purviewAccountName'))]",
                                "groupIds": ["account"]
                            }
                        }
                    ]
                }
            }
        ]
    }
    
    import json
    scripts["private-endpoint.arm.json"] = json.dumps(arm_template, indent=2)
    
    # Generate restoration order checklist
    restoration_guide = f"""# Purview Account Recreation - Restoration Guide

## Prerequisites (Complete BEFORE creating new account)

1. ✅ Export completed successfully
2. ✅ Validation passed (all critical artifacts captured)
3. ✅ Backup manifest saved: manifests/source-export.json
4. ✅ Key Vault contains all scan credential secrets
5. ✅ Resource permissions documented

## Step 1: Delete Old Account

```bash
az purview account delete \\
  --name <old-account-name> \\
  --resource-group <resource-group> \\
  --yes
```

Wait for deletion to complete (~15 minutes).

## Step 2: Create New Purview Account

```bash
az purview account create \\
  --name {new_account_name} \\
  --resource-group <resource-group> \\
  --location <location> \\
  --managed-resource-group-name <mrg-name> \\
  --public-network-access Enabled
```

Wait for account creation (~20 minutes).

## Step 3: Run Automated Import

```bash
# Import all artifacts
purview-migrate import \\
  --target-account {new_account_name} \\
  --input manifests/source-export.json \\
  --apply

# Generate and execute relink plan
purview-migrate relink \\
  --input manifests/source-export.json \\
  --output manifests/relink-plan.json

purview-migrate relink-apply \\
  --target-account {new_account_name} \\
  --input manifests/relink-plan.json \\
  --apply
```

## Step 4: Grant Managed Identity Permissions

Run generated scripts:

```bash
# Azure CLI
bash scripts/permissions.sh

# Or PowerShell
pwsh scripts/permissions.ps1
```

## Step 5: Link Key Vault

```bash
bash scripts/link-keyvault.sh
```

Then complete in Purview Portal:
- Management → Credentials → Key Vault connections → Add
- Select your Key Vault
- Test connection

## Step 6: Configure Scan Credentials

In Purview Portal:
1. Go to Management → Credentials
2. For each credential, create new credential using Key Vault secret
3. Reference the secret name from old account

## Step 7: Verify and Test

1. ✅ All collections visible
2. ✅ All data sources registered
3. ✅ All scans configured
4. ✅ Scan credentials working
5. ✅ Test scan execution on one data source
6. ✅ Verify glossary terms
7. ✅ Check private endpoints (if applicable)

## Step 8: Resume Scanning

Re-enable and run scans:
1. Go to each data source
2. Verify scan configuration
3. Run new scan
4. Monitor for errors

## Manual Steps Required

- Reconfigure self-hosted integration runtimes (if used)
- Re-apply custom network rules
- Recreate private endpoints (use ARM templates in scripts/)
- Validate RBAC role assignments on Purview account itself
- Update any external references to Purview account (e.g., in Data Factory)

## Rollback Plan

If restoration fails:
1. Manifest backup is in: manifests/source-export.json
2. Old account configuration documented in validation report
3. Can recreate in different region if needed
"""
    
    scripts["RESTORATION_GUIDE.md"] = restoration_guide
    
    return scripts
