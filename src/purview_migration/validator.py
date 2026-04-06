from __future__ import annotations

from typing import Any

from purview_migration.constants import SCANS_BY_SOURCE_KEY


def validate_completeness(manifest: dict[str, Any]) -> dict[str, Any]:
    """
    Validate that all critical artifacts have been captured before account deletion.
    Returns a completeness report with warnings for missing or incomplete data.
    """
    
    report = {
        "validation_status": "PASS",
        "critical_checks": [],
        "warnings": [],
        "manual_steps_required": [],
        "deletion_ready": False,
    }

    artifacts = manifest.get("artifacts", {})
    
    # Critical checks
    checks = {
        "collections": {
            "artifact": artifacts.get("collections", []),
            "min_expected": 1,
            "critical": True,
            "message": "Collections define the organizational structure",
        },
        "dataSources": {
            "artifact": artifacts.get("dataSources", []),
            "min_expected": 0,
            "critical": False,
            "message": "Data sources to be re-registered",
        },
        "scans": {
            "artifact": artifacts.get(SCANS_BY_SOURCE_KEY, {}),
            "min_expected": 0,
            "critical": False,
            "message": "Scan configurations to be restored",
        },
        "glossaryTerms": {
            "artifact": artifacts.get("glossaryTerms", []),
            "min_expected": 0,
            "critical": False,
            "message": "Business glossary definitions",
        },
        "classifications": {
            "artifact": artifacts.get("classifications", []),
            "min_expected": 0,
            "critical": False,
            "message": "Custom classification schemas",
        },
        "scanRulesets": {
            "artifact": artifacts.get("scanRulesets", []),
            "min_expected": 0,
            "critical": False,
            "message": "Custom scan rule configurations",
        },
    }

    for check_name, check_config in checks.items():
        artifact_data = check_config["artifact"]
        count = len(artifact_data) if isinstance(artifact_data, list) else len(artifact_data.keys())

        check_result = {
            "name": check_name,
            "captured": count,
            "status": "OK" if count >= check_config["min_expected"] else "MISSING",
            "critical": check_config["critical"],
            "message": check_config["message"],
        }

        report["critical_checks"].append(check_result)

        if check_result["critical"] and check_result["status"] == "MISSING":
            report["validation_status"] = "FAIL"
            report["warnings"].append(
                f"CRITICAL: No {check_name} captured. {check_config['message']}"
            )

    # Check for credentials warning
    creds = artifacts.get("scanCredentials", [])
    if creds:
        report["warnings"].append(
            f"⚠ {len(creds)} scan credentials captured as references only. "
            "You must manually configure secrets in target Key Vault."
        )
        report["manual_steps_required"].append(
            _manual_step(
                category="Credentials",
                action="Recreate scan credentials in target account",
                details=f"{len(creds)} credentials need secrets configured in Key Vault",
                automation="Partially - credential names captured, secrets must be re-entered",
            )
        )

    # Check for integration runtime configurations
    if not artifacts.get("integrationRuntimes"):
        report["warnings"].append(
            "⚠ Integration Runtimes not captured. If you use self-hosted IR, you must reconfigure manually."
        )
        report["manual_steps_required"].append(
            _manual_step(
                category="Integration Runtime",
                action="Reconfigure self-hosted integration runtimes",
                details="IR configurations and credentials cannot be exported via API",
                automation="None - manual reconfiguration required",
            )
        )

    # Check for managed identity permissions
    report["manual_steps_required"].append(
        _manual_step(
            category="Managed Identity Permissions",
            action="Grant new managed identity permissions to data sources",
            details="Reader/Contributor permissions on ADLS, SQL, etc.",
            automation="Script generation available via generate-scripts command",
        )
    )

    # Check for private endpoints
    report["manual_steps_required"].append(
        _manual_step(
            category="Private Endpoints",
            action="Recreate private endpoint connections",
            details="Private endpoints to Purview account endpoints",
            automation="ARM template generation available",
        )
    )

    # Check for Key Vault linkage
    report["manual_steps_required"].append(
        _manual_step(
            category="Key Vault",
            action="Link Key Vault to new Purview account",
            details="Required for scan credentials",
            automation="Azure CLI script generation available",
        )
    )

    # Determine if ready for deletion
    report["deletion_ready"] = report["validation_status"] == "PASS"

    # Add summary
    report["summary"] = {
        "total_collections": len(artifacts.get("collections", [])),
        "total_data_sources": len(artifacts.get("dataSources", [])),
        "total_scans": sum(len(scans) for scans in artifacts.get(SCANS_BY_SOURCE_KEY, {}).values()),
        "total_glossary_terms": len(artifacts.get("glossaryTerms", [])),
        "total_entities_snapshot": len(artifacts.get("entities", [])),
        "manual_steps_count": len(report["manual_steps_required"]),
        "warnings_count": len(report["warnings"]),
    }

    return report


def _manual_step(*, category: str, action: str, details: str, automation: str) -> dict[str, str]:
    return {
        "category": category,
        "action": action,
        "details": details,
        "automation": automation,
    }
