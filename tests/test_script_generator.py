from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from purview_migration.script_generator import generate_permission_scripts


class ScriptGeneratorTests(unittest.TestCase):
    def test_generate_permission_scripts_includes_all_expected_files(self) -> None:
        manifest = {
            "artifacts": {
                "dataSources": [
                    {
                        "name": "adls-prod",
                        "kind": "AdlsGen2",
                        "properties": {"resourceId": "/subscriptions/abc/resourceGroups/rg/providers/Microsoft.Storage/storageAccounts/stg1"},
                    },
                    {
                        "name": "sql-prod",
                        "kind": "AzureSqlDatabase",
                        "properties": {"serverEndpoint": "sqlserver.database.windows.net"},
                    },
                ]
            }
        }

        scripts = generate_permission_scripts(
            manifest=manifest,
            new_account_name="new-purview",
            subscription_id="00000000-0000-0000-0000-000000000000",
        )

        expected = {
            "permissions.sh",
            "permissions.ps1",
            "link-keyvault.sh",
            "private-endpoint.arm.json",
            "RESTORATION_GUIDE.md",
        }
        self.assertEqual(expected, set(scripts.keys()))

    def test_permissions_scripts_contain_source_specific_entries(self) -> None:
        manifest = {
            "artifacts": {
                "dataSources": [
                    {
                        "name": "adls-prod",
                        "kind": "AdlsGen2",
                        "properties": {"resourceId": "/subscriptions/abc/resourceGroups/rg/providers/Microsoft.Storage/storageAccounts/stg1"},
                    },
                    {
                        "name": "sql-prod",
                        "kind": "AzureSqlDatabase",
                        "properties": {"endpoint": "sqlserver.database.windows.net"},
                    },
                ]
            }
        }

        scripts = generate_permission_scripts(
            manifest=manifest,
            new_account_name="new-purview",
            subscription_id="00000000-0000-0000-0000-000000000000",
        )

        permissions_sh = scripts["permissions.sh"]
        self.assertIn("Granting permissions for adls-prod", permissions_sh)
        self.assertIn("Storage Blob Data Reader", permissions_sh)
        self.assertIn("CREATE USER [new-purview] FROM EXTERNAL PROVIDER;", permissions_sh)

        permissions_ps1 = scripts["permissions.ps1"]
        self.assertIn("Granting Storage Blob Data Reader for adls-prod", permissions_ps1)
        self.assertNotIn("Granting Storage Blob Data Reader for sql-prod", permissions_ps1)

    def test_private_endpoint_template_has_new_account_defaults(self) -> None:
        scripts = generate_permission_scripts(
            manifest={"artifacts": {"dataSources": []}},
            new_account_name="new-purview",
            subscription_id="00000000-0000-0000-0000-000000000000",
        )

        arm = json.loads(scripts["private-endpoint.arm.json"])
        self.assertEqual(
            "new-purview",
            arm["parameters"]["purviewAccountName"]["defaultValue"],
        )
        self.assertEqual(
            "new-purview-pe",
            arm["parameters"]["privateEndpointName"]["defaultValue"],
        )


if __name__ == "__main__":
    unittest.main()
