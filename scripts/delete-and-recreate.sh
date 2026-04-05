#!/bin/bash
#
# Purview Account Delete & Recreate Automation Script
# 
# ⚠️ WARNING: This script will DELETE your Purview account and recreate it.
# Use with extreme caution. Review all steps before executing.
#
# Prerequisites:
# 1. Azure CLI logged in: az login
# 2. Purview migration toolkit installed: pip install -e .
# 3. Appropriate RBAC permissions
# 4. All configurations reviewed and validated
#

set -e  # Exit on any error

# =============================================================================
# CONFIGURATION - EDIT THESE VALUES
# =============================================================================

SOURCE_ACCOUNT="current-purview-account"
TARGET_ACCOUNT="new-purview-account"  # Can be same name as source
RESOURCE_GROUP="rg-purview"
LOCATION="eastus"
SUBSCRIPTION_ID="00000000-0000-0000-0000-000000000000"
MANAGED_RG_NAME="mrg-purview-${TARGET_ACCOUNT}"
KEY_VAULT_NAME="kv-purview-credentials"

# Directories
BACKUP_DIR="./backups/$(date +%Y%m%d-%H%M%S)"
SCRIPTS_DIR="${BACKUP_DIR}/scripts"

# =============================================================================
# SAFETY CHECKS
# =============================================================================

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  Purview Account Delete & Recreate                          ║"
echo "║  ⚠️  DESTRUCTIVE OPERATION - REVIEW CAREFULLY               ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Configuration:"
echo "  Source Account:  ${SOURCE_ACCOUNT}"
echo "  Target Account:  ${TARGET_ACCOUNT}"
echo "  Resource Group:  ${RESOURCE_GROUP}"
echo "  Location:        ${LOCATION}"
echo "  Backup Directory: ${BACKUP_DIR}"
echo ""

read -p "Have you reviewed the configuration above? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "❌ Aborted by user"
    exit 1
fi

read -p "⚠️  This will DELETE the ${SOURCE_ACCOUNT} account. Type 'DELETE' to confirm: " delete_confirm
if [ "$delete_confirm" != "DELETE" ]; then
    echo "❌ Deletion not confirmed. Aborted."
    exit 1
fi

# =============================================================================
# PHASE 1: BACKUP & VALIDATION
# =============================================================================

echo ""
echo "========================================="
echo "PHASE 1: Backup & Validation"
echo "========================================="

# Create backup directory
mkdir -p "${BACKUP_DIR}"
mkdir -p "${SCRIPTS_DIR}"

echo ""
echo "📦 Step 1/3: Exporting all artifacts..."
purview-migrate export \
  --source-account "${SOURCE_ACCOUNT}" \
  --output "${BACKUP_DIR}/full-backup.json" \
  --max-entities 10000

if [ $? -ne 0 ]; then
    echo "❌ Export failed. Aborting."
    exit 1
fi
echo "✅ Export completed"

echo ""
echo "✔️  Step 2/3: Validating backup completeness..."
purview-migrate validate \
  --input "${BACKUP_DIR}/full-backup.json" \
  --output "${BACKUP_DIR}/validation-report.json"

if [ $? -ne 0 ]; then
    echo "❌ Validation failed. Review ${BACKUP_DIR}/validation-report.json"
    echo "DO NOT DELETE the account until validation passes."
    exit 1
fi
echo "✅ Validation passed - backup is complete"

echo ""
echo "📝 Step 3/3: Generating restoration scripts..."
purview-migrate generate-scripts \
  --input "${BACKUP_DIR}/full-backup.json" \
  --new-account-name "${TARGET_ACCOUNT}" \
  --subscription-id "${SUBSCRIPTION_ID}" \
  --output-dir "${SCRIPTS_DIR}"

if [ $? -ne 0 ]; then
    echo "❌ Script generation failed. Aborting."
    exit 1
fi
echo "✅ Restoration scripts generated in ${SCRIPTS_DIR}"

# =============================================================================
# FINAL CONFIRMATION
# =============================================================================

echo ""
echo "========================================="
echo "Backup Complete - Review Before Proceeding"
echo "========================================="
echo ""
echo "Backup location: ${BACKUP_DIR}"
echo "Validation report: ${BACKUP_DIR}/validation-report.json"
echo "Restoration guide: ${SCRIPTS_DIR}/RESTORATION_GUIDE.md"
echo ""
echo "⚠️  POINT OF NO RETURN AHEAD"
echo ""
read -p "Proceed with account deletion? Type 'PROCEED' to continue: " proceed_confirm
if [ "$proceed_confirm" != "PROCEED" ]; then
    echo "❌ Deletion cancelled. Backup preserved in ${BACKUP_DIR}"
    exit 0
fi

# =============================================================================
# PHASE 2: DELETE & RECREATE
# =============================================================================

echo ""
echo "========================================="
echo "PHASE 2: Delete & Recreate Account"
echo "========================================="

echo ""
echo "🗑️  Step 1/2: Deleting account ${SOURCE_ACCOUNT}..."
az purview account delete \
  --name "${SOURCE_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --yes

if [ $? -ne 0 ]; then
    echo "❌ Account deletion failed"
    exit 1
fi

echo "⏳ Waiting for deletion to complete (this may take 10-20 minutes)..."
sleep 30

# Poll until account is fully deleted
while az purview account show --name "${SOURCE_ACCOUNT}" --resource-group "${RESOURCE_GROUP}" &>/dev/null; do
    echo "   Still deleting... waiting 30 more seconds"
    sleep 30
done

echo "✅ Account deleted successfully"

echo ""
echo "🏗️  Step 2/2: Creating new account ${TARGET_ACCOUNT}..."
az purview account create \
  --name "${TARGET_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --managed-resource-group-name "${MANAGED_RG_NAME}" \
  --public-network-access Enabled

if [ $? -ne 0 ]; then
    echo "❌ Account creation failed"
    echo "⚠️  Backup is safe in ${BACKUP_DIR}"
    echo "   You can retry account creation manually"
    exit 1
fi

echo "⏳ Waiting for account provisioning (this may take 15-30 minutes)..."
while true; do
    status=$(az purview account show \
      --name "${TARGET_ACCOUNT}" \
      --resource-group "${RESOURCE_GROUP}" \
      --query provisioningState -o tsv 2>/dev/null || echo "NotFound")
    
    if [ "$status" == "Succeeded" ]; then
        break
    elif [ "$status" == "Failed" ]; then
        echo "❌ Account provisioning failed"
        exit 1
    fi
    
    echo "   Provisioning status: ${status}... waiting"
    sleep 30
done

echo "✅ New account created successfully"

# Get managed identity for later use
PRINCIPAL_ID=$(az purview account show \
  --name "${TARGET_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query identity.principalId -o tsv)

echo "📌 New Purview Managed Identity: ${PRINCIPAL_ID}"
echo "   (You'll need this for permission grants)"

# =============================================================================
# PHASE 3: RESTORE
# =============================================================================

echo ""
echo "========================================="
echo "PHASE 3: Restore Artifacts"
echo "========================================="

echo ""
echo "📥 Step 1/4: Importing artifacts..."
purview-migrate import \
  --target-account "${TARGET_ACCOUNT}" \
  --input "${BACKUP_DIR}/full-backup.json" \
  --apply

if [ $? -ne 0 ]; then
    echo "⚠️  Import encountered errors, but may have partially succeeded"
    echo "   Review logs and retry if needed"
fi

echo ""
echo "🔗 Step 2/4: Generating relink plan..."
purview-migrate relink \
  --input "${BACKUP_DIR}/full-backup.json" \
  --output "${BACKUP_DIR}/relink-plan.json"

echo ""
echo "🔗 Step 3/4: Applying relink plan..."
purview-migrate relink-apply \
  --target-account "${TARGET_ACCOUNT}" \
  --input "${BACKUP_DIR}/relink-plan.json" \
  --apply \
  --max-entity-validation 10000 \
  --report-format json \
  --report-output "${BACKUP_DIR}/relink-report.json"

echo ""
echo "🔑 Step 4/4: Running permission scripts..."
echo "   Review and customize before executing automatically"
echo ""
echo "   To grant managed identity permissions:"
echo "   bash ${SCRIPTS_DIR}/permissions.sh"
echo ""
echo "   To link Key Vault:"
echo "   bash ${SCRIPTS_DIR}/link-keyvault.sh"
echo ""

# =============================================================================
# COMPLETION
# =============================================================================

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  Restoration Complete                                        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "✅ New account created: ${TARGET_ACCOUNT}"
echo "✅ Artifacts imported and relinked"
echo "✅ Managed Identity: ${PRINCIPAL_ID}"
echo ""
echo "📋 Next Steps (Manual):"
echo ""
echo "1. Grant Managed Identity Permissions:"
echo "   cd ${SCRIPTS_DIR}"
echo "   bash permissions.sh"
echo ""
echo "2. Link Key Vault:"
echo "   bash link-keyvault.sh"
echo ""
echo "3. Recreate Scan Credentials in Purview Portal:"
echo "   - Management Center → Credentials → Create new"
echo "   - Reference Key Vault secrets from old account"
echo ""
echo "4. Configure Private Endpoints (if needed):"
echo "   az deployment group create \\"
echo "     --resource-group ${RESOURCE_GROUP} \\"
echo "     --template-file ${SCRIPTS_DIR}/private-endpoint.arm.json"
echo ""
echo "5. Test Scan Execution:"
echo "   - Select one data source"
echo "   - Run manual scan"
echo "   - Verify credentials and permissions work"
echo ""
echo "6. Review Detailed Guide:"
echo "   ${SCRIPTS_DIR}/RESTORATION_GUIDE.md"
echo ""
echo "7. Review Reports:"
echo "   - Validation: ${BACKUP_DIR}/validation-report.json"
echo "   - Relink Status: ${BACKUP_DIR}/relink-report.json"
echo ""
echo "========================================="
echo "All backups preserved in: ${BACKUP_DIR}"
echo "========================================="
