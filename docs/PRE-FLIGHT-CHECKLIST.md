# Purview Account Delete & Recreate - Pre-Flight Checklist
# Print this checklist and verify each item before proceeding

## Prerequisites Verification

### Environment Setup
- [ ] Python 3.10+ installed and accessible
  ```bash
  python --version  # Should show 3.10 or higher
  ```

- [ ] Purview Migration Toolkit installed
  ```bash
  pip install -e .
  purview-migrate --help  # Should display command help
  ```

- [ ] Azure CLI installed and logged in
  ```bash
  az --version
  az login
  az account show  # Verify correct subscription
  ```

### Permissions Verification
- [ ] Contributor or Owner role on source Purview account
  ```bash
  az purview account show --name <account> --resource-group <rg>
  ```

- [ ] Contributor or Owner role on target resource group
  ```bash
  az group show --name <resource-group>
  ```

- [ ] Can create Purview accounts (check subscription quota)
  ```bash
  az purview account check-name-availability \
    --name <new-account-name> --location <location>
  ```

- [ ] Access to Key Vault containing scan credentials
  ```bash
  az keyvault secret list --vault-name <key-vault-name>
  ```

### Information Gathering
```
Source Account Name:     _________________________________
Target Account Name:     _________________________________
Resource Group:          _________________________________
Location/Region:         _________________________________
Subscription ID:         _________________________________
Key Vault Name(s):       _________________________________
                        _________________________________
```

### Data Sources Documentation
List all data sources currently scanned (for permission grants after recreation):

```
1. ___________________________________  Type: ____________  Resource ID: _________________________
2. ___________________________________  Type: ____________  Resource ID: _________________________
3. ___________________________________  Type: ____________  Resource ID: _________________________
4. ___________________________________  Type: ____________  Resource ID: _________________________
5. ___________________________________  Type: ____________  Resource ID: _________________________
(Add more as needed)
```

### Integration Runtimes (if applicable)
- [ ] Self-hosted IR installation files backed up
- [ ] IR authentication keys documented
- [ ] IR host machine details recorded:
  ```
  IR Name:               _________________________________
  Host Machine:          _________________________________
  Installation Path:     _________________________________
  ```

### Scan Credentials Documentation
List all scan credentials (you'll need to recreate these):

```
1. Credential Name: ___________________________  Type: ____________  Key Vault Secret: _____________
2. Credential Name: ___________________________  Type: ____________  Key Vault Secret: _____________
3. Credential Name: ___________________________  Type: ____________  Key Vault Secret: _____________
4. Credential Name: ___________________________  Type: ____________  Key Vault Secret: _____________
(Add more as needed)
```

### Network Configuration
- [ ] Private endpoints documented (if applicable)
  ```
  VNet Name:             _________________________________
  Subnet Name:           _________________________________
  Private DNS Zone:      _________________________________
  ```

- [ ] Firewall rules documented
  ```
  Rule 1: ____________________________________________________________
  Rule 2: ____________________________________________________________
  ```

### Stakeholder Communication
- [ ] All Purview users notified of maintenance window
- [ ] Maintenance window scheduled:
  ```
  Start Time:  _____________ (Date/Time)
  End Time:    _____________ (Date/Time)
  Duration:    _____________ (Expected: 2-4 hours)
  ```

- [ ] Rollback plan documented
- [ ] Support contacts identified:
  ```
  Azure Support:         _________________________________
  Team Lead:             _________________________________
  Backup Contact:        _________________________________
  ```

---

## Phase 1: Backup & Validation
**DO NOT PROCEED TO PHASE 2 UNTIL ALL PHASE 1 ITEMS ARE CHECKED**

### Export
- [ ] Export command executed successfully
  ```bash
  purview-migrate export \
    --source-account <account> \
    --output backups/full-backup.json \
    --max-entities 10000
  ```

- [ ] Export JSON file created and readable
  ```bash
  ls -lh backups/full-backup.json
  cat backups/full-backup.json | jq '.collections | length'
  ```

- [ ] Export artifact counts match expectations:
  ```
  Collections:           _______ (Expected: ~_____)
  Data Sources:          _______ (Expected: ~_____)
  Scans:                 _______ (Expected: ~_____)
  Glossary Terms:        _______ (Expected: ~_____)
  Classifications:       _______ (Expected: ~_____)
  Entities Captured:     _______ (Expected: ~_____)
  ```

### Validation
- [ ] Validation command executed successfully
  ```bash
  purview-migrate validate \
    --input backups/full-backup.json \
    --output backups/validation-report.json
  ```

- [ ] Validation status is **PASS**
  ```bash
  cat backups/validation-report.json | jq '.validation_status'
  # Must show: "PASS"
  ```

- [ ] `deletion_ready` flag is **true**
  ```bash
  cat backups/validation-report.json | jq '.deletion_ready'
  # Must show: true
  ```

- [ ] All critical checks show status **OK**
  ```bash
  cat backups/validation-report.json | jq '.critical_checks[] | select(.critical == true)'
  # All critical items must show "status": "OK"
  ```

- [ ] Warnings reviewed and acceptable
  ```
  Number of Warnings:  _______
  
  Review each warning:
  1. ___________________________________________________________  Acceptable? [ ]
  2. ___________________________________________________________  Acceptable? [ ]
  3. ___________________________________________________________  Acceptable? [ ]
  ```

- [ ] Manual steps documented and understood
  ```
  Number of Manual Steps:  _______
  
  Each manual step assigned to team member:
  1. ________________________________________  Owner: _____________  ETA: ________
  2. ________________________________________  Owner: _____________  ETA: ________
  3. ________________________________________  Owner: _____________  ETA: ________
  ```

### Script Generation
- [ ] Scripts generated successfully
  ```bash
  purview-migrate generate-scripts \
    --input backups/full-backup.json \
    --new-account-name <new-account> \
    --subscription-id <sub-id> \
    --output-dir scripts/
  ```

- [ ] Scripts reviewed and customized:
  ```
  scripts/RESTORATION_GUIDE.md       [ ] Reviewed  [ ] Understood
  scripts/permissions.sh             [ ] Reviewed  [ ] Customized as needed
  scripts/permissions.ps1            [ ] Reviewed  [ ] Customized as needed
  scripts/link-keyvault.sh           [ ] Reviewed  [ ] Customized as needed
  scripts/private-endpoint.arm.json  [ ] Reviewed  [ ] Customized as needed
  ```

### Backup Security
- [ ] Backup files copied to secure location
  ```
  Primary Backup:    backups/full-backup.json  [ ] Copied to: __________________
  Offsite Copy:      [ ] Copied to: __________________
  ```

- [ ] Backup files committed to version control
  ```bash
  git add backups/ scripts/
  git commit -m "Pre-deletion backup for <account> - $(date)"
  git push
  ```

- [ ] Backup integrity verified
  ```bash
  md5sum backups/full-backup.json  # Record hash: __________________________
  ```

---

## Phase 2: Deletion - POINT OF NO RETURN
**⚠️ DO NOT PROCEED UNLESS ALL PHASE 1 ITEMS ARE CHECKED AND VERIFIED ⚠️**

### Final Confirmation
- [ ] All Phase 1 items verified and checked
- [ ] Backup validated and secured in multiple locations
- [ ] Stakeholders notified of imminent deletion
- [ ] Rollback plan ready (if deletion succeeds but restoration fails)
- [ ] Team available for support during restoration

### Delete Old Account
- [ ] Deletion command executed
  ```bash
  az purview account delete \
    --name <old-account> \
    --resource-group <rg> \
    --yes
  
  Deletion Started At: _____________ (Time)
  ```

- [ ] Deletion confirmed
  ```bash
  az purview account show --name <old-account> --resource-group <rg>
  # Should eventually return: ResourceNotFound
  
  Deletion Completed At: _____________ (Time)
  Deletion Duration: _____________ minutes
  ```

### Create New Account
- [ ] Creation command executed
  ```bash
  az purview account create \
    --name <new-account> \
    --resource-group <rg> \
    --location <location> \
    --managed-resource-group-name <mrg-name> \
    --public-network-access Enabled
  
  Creation Started At: _____________ (Time)
  ```

- [ ] Creation succeeded
  ```bash
  az purview account show \
    --name <new-account> \
    --resource-group <rg> \
    --query provisioningState
  # Should show: "Succeeded"
  
  Creation Completed At: _____________ (Time)
  Creation Duration: _____________ minutes
  ```

- [ ] Managed identity recorded
  ```bash
  az purview account show \
    --name <new-account> \
    --resource-group <rg> \
    --query identity.principalId -o tsv
  
  New Managed Identity Principal ID: _________________________________
  ```

---

## Phase 3: Restoration

### Import Artifacts
- [ ] Import dry-run executed successfully
  ```bash
  purview-migrate import \
    --target-account <new-account> \
    --input backups/full-backup.json
  # (no --apply flag)
  
  Dry-Run Result: _____________
  ```

- [ ] Import applied successfully
  ```bash
  purview-migrate import \
    --target-account <new-account> \
    --input backups/full-backup.json \
    --apply
  
  Result Counts:
  Collections Created:  _______
  Data Sources Created: _______
  Scans Created:        _______
  Glossary Items:       _______
  ```

### Relink Execution
- [ ] Relink plan generated
  ```bash
  purview-migrate relink \
    --input backups/full-backup.json \
    --output backups/relink-plan.json
  ```

- [ ] Relink applied successfully
  ```bash
  purview-migrate relink-apply \
    --target-account <new-account> \
    --input backups/relink-plan.json \
    --apply \
    --max-entity-validation 10000 \
    --report-format json \
    --report-output backups/relink-report.json
  
  Result:
  Linked:    _______
  Created:   _______
  Missing:   _______
  Failed:    _______
  ```

### Permission Grants
- [ ] Managed identity permissions granted
  ```bash
  bash scripts/permissions.sh
  
  Data Sources Granted:
  1. ___________________________________  [ ] Success  [ ] Failed: _____________
  2. ___________________________________  [ ] Success  [ ] Failed: _____________
  3. ___________________________________  [ ] Success  [ ] Failed: _____________
  ```

- [ ] SQL Server T-SQL permissions executed
  ```sql
  -- For each SQL database:
  Database 1: ___________________  [ ] CREATE USER executed  [ ] db_datareader granted
  Database 2: ___________________  [ ] CREATE USER executed  [ ] db_datareader granted
  Database 3: ___________________  [ ] CREATE USER executed  [ ] db_datareader granted
  ```

### Key Vault & Credentials
- [ ] Key Vault linked
  ```bash
  bash scripts/link-keyvault.sh
  ```

- [ ] Key Vault connection tested in Portal
  ```
  Portal: Management Center → Credentials → Key Vault connections
  Status: [ ] Connected  [ ] Test Successful
  ```

- [ ] Scan credentials recreated
  ```
  Credential 1: ___________________  [ ] Created  [ ] Tested  [ ] Linked to scans
  Credential 2: ___________________  [ ] Created  [ ] Tested  [ ] Linked to scans
  Credential 3: ___________________  [ ] Created  [ ] Tested  [ ] Linked to scans
  ```

### Network & Integration
- [ ] Private endpoints recreated (if applicable)
  ```bash
  az deployment group create \
    --resource-group <rg> \
    --template-file scripts/private-endpoint.arm.json
  
  Status: [ ] Deployed  [ ] Connection Approved  [ ] DNS Updated
  ```

- [ ] Integration runtimes reconfigured (if applicable)
  ```
  IR 1: ___________________  [ ] Created  [ ] Key Generated  [ ] Registered  [ ] Online
  IR 2: ___________________  [ ] Created  [ ] Key Generated  [ ] Registered  [ ] Online
  ```

---

## Phase 4: Verification & Testing

### Component Verification
- [ ] All collections visible in Data Map
  ```
  Expected Collections: _______
  Actual Collections:   _______
  Match: [ ] Yes  [ ] No - Discrepancy: _______________
  ```

- [ ] All data sources registered
  ```
  Expected Sources: _______
  Actual Sources:   _______
  Match: [ ] Yes  [ ] No - Discrepancy: _______________
  ```

- [ ] All scans configured
  ```
  Expected Scans: _______
  Actual Scans:   _______
  Match: [ ] Yes  [ ] No - Discrepancy: _______________
  ```

- [ ] Glossary terms intact
  ```
  Expected Terms: _______
  Actual Terms:   _______
  Match: [ ] Yes  [ ] No - Discrepancy: _______________
  ```

### Test Scan Execution
- [ ] Test scan on representative data source #1
  ```
  Data Source: ___________________
  Scan Name:   ___________________
  Status:      [ ] Success  [ ] Failed: _______________
  Assets Found: _______
  ```

- [ ] Test scan on representative data source #2
  ```
  Data Source: ___________________
  Scan Name:   ___________________
  Status:      [ ] Success  [ ] Failed: _______________
  Assets Found: _______
  ```

- [ ] Test scan on representative data source #3
  ```
  Data Source: ___________________
  Scan Name:   ___________________
  Status:      [ ] Success  [ ] Failed: _______________
  Assets Found: _______
  ```

### End-to-End Validation
- [ ] Sample asset searchable in Data Catalog
  ```
  Asset Name: ___________________  [ ] Found  [ ] Schema Correct  [ ] Lineage Present
  ```

- [ ] Glossary term assignment working
  ```
  Test Term: ___________________  [ ] Assigned to asset  [ ] Visible in UI
  ```

- [ ] Classification applied correctly
  ```
  Test Classification: ___________________  [ ] Detected  [ ] Applied
  ```

---

## Phase 5: Production Cutover

### Scan Schedule Activation
- [ ] All scan schedules reviewed
  ```
  Scheduled Scans: _______
  Reviewed:        _______
  ```

- [ ] Scan schedules enabled
  ```
  Enabled: _______  
  Verified: [ ] First scheduled run upcoming at: _____________
  ```

### External Service Updates
- [ ] Azure Data Factory linked service updated
  ```
  ADF Instance 1: ___________________  [ ] Updated  [ ] Tested
  ADF Instance 2: ___________________  [ ] Updated  [ ] Tested
  ```

- [ ] Azure Synapse workspace updated
  ```
  Synapse Workspace: ___________________  [ ] Updated  [ ] Tested
  ```

- [ ] Custom applications updated
  ```
  App 1: ___________________  [ ] Endpoint Updated  [ ] Auth Tested
  App 2: ___________________  [ ] Endpoint Updated  [ ] Auth Tested
  ```

### RBAC & User Access
- [ ] User roles assigned
  ```
  Purview Data Curators:   _______ users  [ ] Assigned  [ ] Verified
  Purview Data Readers:    _______ users  [ ] Assigned  [ ] Verified
  Purview Data Source Admins: _______ users  [ ] Assigned  [ ] Verified
  ```

- [ ] Sample user login tested
  ```
  Test User 1: ___________________  [ ] Can login  [ ] Can view data  [ ] Can curate
  Test User 2: ___________________  [ ] Can login  [ ] Can view data  [ ] Can curate
  ```

### Documentation Updates
- [ ] Internal documentation updated with new account name
- [ ] Runbooks updated with new endpoints
- [ ] Architecture diagrams updated
- [ ] Support tickets/FAQs updated

### Stakeholder Sign-Off
- [ ] Migration validated by Data Governance team
  ```
  Signed Off By: ___________________  Date: _______  Time: _______
  ```

- [ ] Migration validated by Data Engineering team
  ```
  Signed Off By: ___________________  Date: _______  Time: _______
  ```

- [ ] Production cutover approved
  ```
  Approved By: ___________________  Date: _______  Time: _______
  ```

---

## Post-Migration Monitoring (First 48 Hours)

### Hour 1-4
- [ ] Monitor scan executions
  ```
  Successful Scans:  _______
  Failed Scans:      _______
  ```

- [ ] Check Azure Monitor for errors
  ```
  Errors Detected:   _______  [ ] Resolved
  ```

- [ ] Verify asset ingestion
  ```
  Assets Discovered: _______  
  Expected Rate:     [ ] Normal  [ ] Below Normal
  ```

### Hour 4-24
- [ ] All scheduled scans executed
  ```
  Total Scheduled:  _______
  Executed:         _______
  Success Rate:     _______ %
  ```

- [ ] User feedback collected
  ```
  Users Contacted:  _______
  Issues Reported:  _______  [ ] Resolved
  ```

### Hour 24-48
- [ ] Lineage relationships rebuilding
  ```
  Lineage Edges:    _______
  Status:           [ ] Complete  [ ] In Progress
  ```

- [ ] Search index healthy
  ```
  Search Latency:   _______ ms
  Status:           [ ] Normal  [ ] Degraded
  ```

- [ ] All critical workflows operational
  ```
  Workflow 1: ___________________  [ ] Operational
  Workflow 2: ___________________  [ ] Operational
  Workflow 3: ___________________  [ ] Operational
  ```

---

## Sign-Off

### Migration Team
```
Migration Lead:          _________________  Signature: __________  Date: _______
Technical Lead:          _________________  Signature: __________  Date: _______
Operations Lead:         _________________  Signature: __________  Date: _______
```

### Business Stakeholders
```
Data Governance Owner:   _________________  Signature: __________  Date: _______
Data Engineering Owner:  _________________  Signature: __________  Date: _______
Security Officer:        _________________  Signature: __________  Date: _______
```

---

## Notes & Issues
```
Issue 1: ___________________________________________________________________________
Resolution: ________________________________________________________________________
Owner: _________________  Status: _______________  Resolved: [ ] Yes  [ ] No

Issue 2: ___________________________________________________________________________
Resolution: ________________________________________________________________________
Owner: _________________  Status: _______________  Resolved: [ ] Yes  [ ] No

Issue 3: ___________________________________________________________________________
Resolution: ________________________________________________________________________
Owner: _________________  Status: _______________  Resolved: [ ] Yes  [ ] No
```

---

**Checklist Version:** 1.0  
**Last Updated:** 2026-04-05  
**Migration ID:** ___________________  
**Completion Date:** ___________________  
**Total Duration:** ___________________ (hours)
