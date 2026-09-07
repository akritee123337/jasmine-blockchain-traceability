"""HTTP client for the Hyperledger Fabric Gateway bridge."""

import json
import os
from urllib.error import URLError
from urllib.request import Request, urlopen
from typing import Any, Dict, List


class FabricGatewayError(RuntimeError):
    """Raised when the Fabric Gateway cannot complete a request."""


class FabricGatewayClient:
    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or os.getenv("FABRIC_GATEWAY_URL", "http://127.0.0.1:8081")).rstrip("/")

    def _request(self, method: str, path: str, payload: Dict[str, Any] | None = None) -> Any:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(
            f"{self.base_url}{path}",
            data=data,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urlopen(request, timeout=15) as response:
                return json.loads(response.read().decode("utf-8"))
        except URLError as error:
            raise FabricGatewayError(f"Fabric Gateway request failed: {error}") from error

    def record_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", "/events", event)

    def get_batch_events(self, batch_id: str) -> List[Dict[str, Any]]:
        return self._request("GET", f"/batches/{batch_id}/events")

    def verify_batch(self, batch_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/batches/{batch_id}/verify")
