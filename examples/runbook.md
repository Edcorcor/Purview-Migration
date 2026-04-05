# Migration Runbook

## 1. Authenticate

```powershell
az login
az account set --subscription <subscription-id>
```

## 2. Export source artifacts

```powershell
purview-migrate export --source-account <source-account> --output manifests/source-export.json
```

## 3. Review manifest

Open `manifests/source-export.json` and check:
- `warnings`
- object counts under `artifacts`

## 4. Dry-run target import

```powershell
purview-migrate import --target-account <target-account> --input manifests/source-export.json
```

## 5. Apply target import

```powershell
purview-migrate import --target-account <target-account> --input manifests/source-export.json --apply
```

## 6. Generate relink plan

```powershell
purview-migrate relink --input manifests/source-export.json --output manifests/relink-plan.json
```

## 7. Dry-run relink execution

```powershell
purview-migrate relink-apply --target-account <target-account> --input manifests/relink-plan.json --output manifests/relink-status.json
```

## 8. Apply relink execution with entity validation and reporting

```powershell
purview-migrate relink-apply --target-account <target-account> --input manifests/relink-plan.json --output manifests/relink-status.json --max-entity-validation 5000 --report-format csv --report-output manifests/relink-report.csv --apply
```

## 9. Review relink status report

Open the generated report:
- `manifests/relink-status.json` — updated plan with per-item status (dry-run or after apply)
- `manifests/relink-report.csv` — grouped by outcome for quick triage of unresolved/failed items

Use the report to hand off unresolved entities and failures to data engineering or governance teams.
