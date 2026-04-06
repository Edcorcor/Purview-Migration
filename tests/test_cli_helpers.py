from __future__ import annotations

import unittest
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from purview_migration.cli import _normalize_manifest_document


class CliHelperTests(unittest.TestCase):
    def test_normalize_manifest_document_passes_through_full_manifest(self) -> None:
        full_manifest = {
            "metadata": {"sourceAccount": "acct"},
            "artifacts": {"collections": []},
            "warnings": ["w1"],
        }

        normalized = _normalize_manifest_document(full_manifest)
        self.assertEqual(full_manifest, normalized)

    def test_normalize_manifest_document_wraps_artifacts_only(self) -> None:
        artifacts_only = {
            "collections": [{"name": "root"}],
            "dataSources": [],
        }

        normalized = _normalize_manifest_document(artifacts_only)
        self.assertEqual({}, normalized["metadata"])
        self.assertEqual([], normalized["warnings"])
        self.assertEqual(artifacts_only, normalized["artifacts"])


if __name__ == "__main__":
    unittest.main()
