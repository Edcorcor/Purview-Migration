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

## 8. Apply relink execution

```powershell
purview-migrate relink-apply --target-account <target-account> --input manifests/relink-plan.json --output manifests/relink-status.json --apply
```

Use `manifests/relink-status.json` to review unresolved entities and run additional scans or manual mapping updates.
