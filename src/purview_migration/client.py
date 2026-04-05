from __future__ import annotations

import time
from typing import Any

import requests
from azure.identity import DefaultAzureCredential


class PurviewClient:
    """Thin REST wrapper for Purview data-plane operations."""

    TOKEN_SCOPE = "https://purview.azure.net/.default"

    def __init__(self, account_name: str, timeout_seconds: int = 60) -> None:
        self.account_name = account_name
        self.base_url = f"https://{account_name}.purview.azure.com"
        self.timeout_seconds = timeout_seconds
        self.credential = DefaultAzureCredential(exclude_interactive_browser_credential=False)

    def _headers(self) -> dict[str, str]:
        token = self.credential.get_token(self.TOKEN_SCOPE).token
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def request(
        self,
        method: str,
        path: str,
        *,
        api_version: str | None = None,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | list[dict[str, Any]] | None = None,
        retries: int = 3,
    ) -> Any:
        url = f"{self.base_url}{path}"
        query_params = dict(params or {})
        if api_version:
            query_params["api-version"] = api_version

        attempt = 0
        while True:
            attempt += 1
            response = requests.request(
                method=method,
                url=url,
                headers=self._headers(),
                params=query_params,
                json=body,
                timeout=self.timeout_seconds,
            )

            if response.status_code < 400:
                if not response.text:
                    return {}
                content_type = response.headers.get("content-type", "")
                if "application/json" in content_type:
                    return response.json()
                return {"raw": response.text}

            should_retry = response.status_code in {429, 500, 502, 503, 504}
            if should_retry and attempt <= retries:
                backoff_seconds = 2 ** (attempt - 1)
                time.sleep(backoff_seconds)
                continue

            raise RuntimeError(
                f"Purview API call failed: {method} {url} status={response.status_code} body={response.text}"
            )

    @staticmethod
    def _as_items(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            if isinstance(payload.get("value"), list):
                return payload["value"]
            if isinstance(payload.get("items"), list):
                return payload["items"]
        return []

    def list_collections(self) -> list[dict[str, Any]]:
        payload = self.request("GET", "/account/collections", api_version="2019-11-01-preview")
        return self._as_items(payload)

    def create_or_update_collection(self, collection: dict[str, Any]) -> dict[str, Any]:
        name = collection.get("name") or collection.get("friendlyName")
        if not name:
            raise ValueError("Collection has no name/friendlyName")
        body = {
            "name": collection.get("name", name),
            "friendlyName": collection.get("friendlyName", name),
            "parentCollection": collection.get("parentCollection"),
        }
        return self.request(
            "PUT",
            f"/account/collections/{name}",
            api_version="2019-11-01-preview",
            body=body,
        )

    def list_data_sources(self) -> list[dict[str, Any]]:
        payload = self.request("GET", "/scan/datasources", api_version="2023-09-01-preview")
        return self._as_items(payload)

    def create_or_update_data_source(self, data_source: dict[str, Any]) -> dict[str, Any]:
        name = data_source.get("name")
        kind = data_source.get("kind")
        properties = data_source.get("properties", {})
        if not name or not kind:
            raise ValueError("Data source requires both name and kind")
        return self.request(
            "PUT",
            f"/scan/datasources/{name}",
            api_version="2023-09-01-preview",
            body={"name": name, "kind": kind, "properties": properties},
        )

    def list_scans(self, data_source_name: str) -> list[dict[str, Any]]:
        payload = self.request(
            "GET",
            f"/scan/datasources/{data_source_name}/scans",
            api_version="2023-09-01-preview",
        )
        return self._as_items(payload)

    def create_or_update_scan(self, data_source_name: str, scan: dict[str, Any]) -> dict[str, Any]:
        name = scan.get("name")
        kind = scan.get("kind")
        properties = scan.get("properties", {})
        if not name or not kind:
            raise ValueError("Scan requires both name and kind")
        return self.request(
            "PUT",
            f"/scan/datasources/{data_source_name}/scans/{name}",
            api_version="2023-09-01-preview",
            body={"name": name, "kind": kind, "properties": properties},
        )

    def list_glossary_categories(self) -> list[dict[str, Any]]:
        payload = self.request("GET", "/datamap/api/atlas/v2/glossary/categories")
        return self._as_items(payload)

    def list_glossary_terms(self) -> list[dict[str, Any]]:
        payload = self.request("GET", "/datamap/api/atlas/v2/glossary/terms")
        return self._as_items(payload)

    def create_glossary_category(self, category: dict[str, Any]) -> dict[str, Any]:
        return self.request("POST", "/datamap/api/atlas/v2/glossary/category", body=category)

    def create_glossary_term(self, term: dict[str, Any]) -> dict[str, Any]:
        return self.request("POST", "/datamap/api/atlas/v2/glossary/term", body=term)

    def list_classifications(self) -> list[dict[str, Any]]:
        payload = self.request(
            "GET",
            "/datamap/api/atlas/v2/types/typedefs",
            params={"type": "CLASSIFICATION"},
        )
        if isinstance(payload, dict) and isinstance(payload.get("classificationDefs"), list):
            return payload["classificationDefs"]
        return []

    def upsert_classification(self, classification_def: dict[str, Any]) -> dict[str, Any]:
        return self.request(
            "POST",
            "/datamap/api/atlas/v2/types/typedefs",
            body={"classificationDefs": [classification_def]},
        )

    def list_scan_rulesets(self) -> list[dict[str, Any]]:
        payload = self.request("GET", "/scan/rulesets", api_version="2023-09-01-preview")
        return self._as_items(payload)

    def create_or_update_scan_ruleset(self, ruleset: dict[str, Any]) -> dict[str, Any]:
        name = ruleset.get("name")
        kind = ruleset.get("kind")
        properties = ruleset.get("properties", {})
        if not name or not kind:
            raise ValueError("Ruleset requires both name and kind")
        return self.request(
            "PUT",
            f"/scan/rulesets/{name}",
            api_version="2023-09-01-preview",
            body={"name": name, "kind": kind, "properties": properties},
        )

    def list_scan_credentials(self) -> list[dict[str, Any]]:
        payload = self.request("GET", "/scan/credentials", api_version="2023-09-01-preview")
        return self._as_items(payload)

    def create_or_update_scan_credential(self, credential: dict[str, Any]) -> dict[str, Any]:
        name = credential.get("name")
        kind = credential.get("kind")
        properties = credential.get("properties", {})
        if not name or not kind:
            raise ValueError("Credential requires both name and kind")
        return self.request(
            "PUT",
            f"/scan/credentials/{name}",
            api_version="2023-09-01-preview",
            body={"name": name, "kind": kind, "properties": properties},
        )

    def search_entities(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        payload = self.request(
            "POST",
            "/datamap/api/search/query",
            body={"keywords": "*", "limit": limit, "offset": offset},
        )
        if isinstance(payload, dict):
            if isinstance(payload.get("value"), list):
                return payload["value"]
            if isinstance(payload.get("@search.count"), int) and isinstance(payload.get("value"), list):
                return payload["value"]
        return []
