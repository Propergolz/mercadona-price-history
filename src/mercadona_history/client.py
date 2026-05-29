from __future__ import annotations

import time
import uuid
from typing import Any

import requests


class MercadonaClient:
    def __init__(
        self,
        base_url: str = "https://tienda.mercadona.es/api",
        lang: str = "es",
        delay_seconds: float = 0.4,
        timeout_seconds: int = 30,
        max_retries: int = 3,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.lang = lang
        self.delay_seconds = delay_seconds
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update(
            {
                "accept": "application/json",
                "content-type": "application/json",
                "user-agent": "mercadona-price-history/0.1",
                "x-customer-device-id": str(uuid.uuid4()),
            }
        )

    def change_postal_code(self, postal_code: str) -> dict[str, str | None]:
        response = self._request(
            "PUT",
            "/postal-codes/actions/change-pc/",
            json={"new_postal_code": postal_code},
        )
        return {
            "postal_code": response.headers.get("x-customer-pc", postal_code),
            "warehouse_code": response.headers.get("x-customer-wh"),
        }

    def get_categories(self, warehouse_code: str | None = None) -> dict[str, Any]:
        return self._get_json("/categories/", warehouse_code=warehouse_code)

    def get_category(self, category_id: int, warehouse_code: str | None = None) -> dict[str, Any]:
        return self._get_json(f"/categories/{category_id}/", warehouse_code=warehouse_code)

    def get_product(self, product_id: str, warehouse_code: str | None = None) -> dict[str, Any]:
        return self._get_json(f"/products/{product_id}/", warehouse_code=warehouse_code)

    def _get_json(self, path: str, warehouse_code: str | None = None) -> dict[str, Any]:
        params = {"lang": self.lang}
        if warehouse_code:
            params["wh"] = warehouse_code
        return self._request("GET", path, params=params).json()

    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        url = f"{self.base_url}{path}"
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            time.sleep(self.delay_seconds)
            try:
                response = self.session.request(
                    method,
                    url,
                    timeout=self.timeout_seconds,
                    **kwargs,
                )
                response.raise_for_status()
                return response
            except (
                requests.Timeout,
                requests.ConnectionError,
                requests.HTTPError,
            ) as error:
                last_error = error
                status_code = getattr(getattr(error, "response", None), "status_code", None)
                retryable_status = status_code in {429, 500, 502, 503, 504}
                retryable_network = isinstance(error, (requests.Timeout, requests.ConnectionError))
                if attempt == self.max_retries or not (retryable_status or retryable_network):
                    raise
                wait_seconds = min(30, 2**attempt)
                print(
                    f"Request failed ({method} {path}) attempt {attempt}/{self.max_retries}: "
                    f"{error}. Retrying in {wait_seconds}s..."
                )
                time.sleep(wait_seconds)

        raise RuntimeError(f"Request failed after retries: {method} {url}") from last_error

