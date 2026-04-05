from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class MigrationManifest:
    source_account: str
    exported_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    collections: list[dict[str, Any]] = field(default_factory=list)
    data_sources: list[dict[str, Any]] = field(default_factory=list)
    scans_by_source: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    glossary_categories: list[dict[str, Any]] = field(default_factory=list)
    glossary_terms: list[dict[str, Any]] = field(default_factory=list)
    classifications: list[dict[str, Any]] = field(default_factory=list)
    scan_rulesets: list[dict[str, Any]] = field(default_factory=list)
    scan_credentials: list[dict[str, Any]] = field(default_factory=list)
    entities: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "metadata": {
                "sourceAccount": self.source_account,
                "exportedAtUtc": self.exported_at_utc,
            },
            "artifacts": {
                "collections": self.collections,
                "dataSources": self.data_sources,
                "scansBySource": self.scans_by_source,
                "glossaryCategories": self.glossary_categories,
                "glossaryTerms": self.glossary_terms,
                "classifications": self.classifications,
                "scanRulesets": self.scan_rulesets,
                "scanCredentials": self.scan_credentials,
                "entities": self.entities,
            },
            "warnings": self.warnings,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MigrationManifest":
        metadata = data.get("metadata", {})
        artifacts = data.get("artifacts", {})
        return cls(
            source_account=metadata.get("sourceAccount", ""),
            exported_at_utc=metadata.get("exportedAtUtc", ""),
            collections=artifacts.get("collections", []),
            data_sources=artifacts.get("dataSources", []),
            scans_by_source=artifacts.get("scansBySource", {}),
            glossary_categories=artifacts.get("glossaryCategories", []),
            glossary_terms=artifacts.get("glossaryTerms", []),
            classifications=artifacts.get("classifications", []),
            scan_rulesets=artifacts.get("scanRulesets", []),
            scan_credentials=artifacts.get("scanCredentials", []),
            entities=artifacts.get("entities", []),
            warnings=data.get("warnings", []),
        )


@dataclass
class ImportResult:
    created: int = 0
    updated: int = 0
    skipped: int = 0
    failed: int = 0
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "created": self.created,
            "updated": self.updated,
            "skipped": self.skipped,
            "failed": self.failed,
            "warnings": self.warnings,
        }


@dataclass
class RelinkResult:
    linked: int = 0
    created: int = 0
    skipped: int = 0
    failed: int = 0
    unresolved: int = 0
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "linked": self.linked,
            "created": self.created,
            "skipped": self.skipped,
            "failed": self.failed,
            "unresolved": self.unresolved,
            "warnings": self.warnings,
        }
