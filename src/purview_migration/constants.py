from __future__ import annotations

# Canonical keys in manifest["artifacts"].
LIST_ARTIFACT_KEYS: tuple[str, ...] = (
    "collections",
    "dataSources",
    "glossaryCategories",
    "glossaryTerms",
    "classifications",
    "scanRulesets",
    "scanCredentials",
    "entities",
)

# Dict-backed artifact key where values are scan lists grouped by source.
SCANS_BY_SOURCE_KEY = "scansBySource"

# Common summary/check set used for validation and reporting.
VALIDATION_ARTIFACT_KEYS: tuple[str, ...] = (
    "collections",
    "dataSources",
    "glossaryTerms",
    "classifications",
    "scanRulesets",
)
