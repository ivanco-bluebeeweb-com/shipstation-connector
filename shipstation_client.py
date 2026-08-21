"""ShipStation API V2 HTTP client -- auth, pagination helpers, and a thin
request wrapper shared by every handler module.

WHY ONE GLOBAL RETRY-ON-429 LOOP HERE, NOT PER HANDLER.

Per docs.shipstation.com/rate-limits (confirmed 2026-08-21), ShipStation
allows 200 requests/minute by default, applied ACCOUNT-WIDE (not per
endpoint). A 429 response carries a `Retry-After` header telling us
exactly how long to wait. The docs explicitly warn that retry logic
implemented per-caller (rather than centrally) causes many requests to
all retry at the same instant and get rate-limited again -- so exactly
like Klaviyo Connector's klaviyo_client.py, this is centralized once here.

WHY `error_source` IS SURFACED IN THE RAISED EXCEPTION.

ShipStation's own error envelope carries an `error_source` field
distinguishing a ShipStation-side rate limit from a THIRD-PARTY one (a
carrier, insurance provider, or marketplace enforcing its own limit) --
retrying blindly on a carrier-side error would be pointless and could
even worsen things. This client passes that field through unmodified so
handlers/users can tell the difference.

WHY `API-Key` HEADER, NOT Bearer/Basic.

ShipStation V2's own docs are explicit this is a bespoke header name
(docs.shipstation.com/authentication) -- built here rather than assumed,
same reasoning n8n Connector documents for its own bespoke auth header.

WHY `page` / `page_size` CURSOR-LESS PAGINATION HELPERS.

ShipStation V2 list endpoints use simple 1-based `page` + `page_size`
query params (not opaque cursors like Klaviyo/Shopify) -- confirmed
across list_shipments / list_carriers / list_webhooks docs. A tiny helper
keeps every handler's list_* tool consistent instead of hand-building
query dicts everywhere.
"""
from __future__ import annotations

import asyncio
from typing import Any

BASE_URL = "https://api.shipstation.com/v2"

_MAX_RETRIES_ON_429 = 1
_DEFAULT_RETRY_AFTER = 3.0


class ShipStationError(Exception):
    """Raised for any non-2xx ShipStation response, with parsed detail."""

    def __init__(self, status_code: int, detail: str, error_source: str = "", raw: Any = None):
        self.status_code = status_code
        self.detail = detail
        self.error_source = error_source
        self.raw = raw
        super().__init__(f"ShipStation API error {status_code}: {detail}")


def _headers(api_key: str) -> dict:
    return {
        "API-Key": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _extract_error(payload: Any) -> tuple[str, str]:
    """ShipStation V2 error bodies are typically:
    {"request_id": "...", "errors": [{"error_source": "...",
      "error_type": "...", "error_code": "...", "message": "..."}]}
    Returns (detail, error_source) for the FIRST reported error.
    """
    if isinstance(payload, dict):
        errors = payload.get("errors")
        if isinstance(errors, list) and errors:
            first = errors[0] if isinstance(errors[0], dict) else {}
            msg = first.get("message") or str(first)
            src = first.get("error_source", "")
            return msg, src
        if payload.get("message"):
            return str(payload["message"]), ""
    return str(payload), ""


async def request(
    ctx,
    api_key: str,
    method: str,
    path: str,
    *,
    params: dict | None = None,
    json_body: dict | None = None,
) -> dict:
    """Single ShipStation API V2 call with auth and one respectful retry
    on 429 honoring Retry-After. Raises ShipStationError on any non-2xx
    after that retry. Returns parsed JSON body (or {} for 204/empty).

    WHY `ctx.http`, NOT A DIRECT `httpx.AsyncClient` HERE -- same reasoning
    Klaviyo Connector's klaviyo_client.py documents: `ctx.http` is the
    platform's own egress client, swappable for
    imperal_sdk.testing.MockContext's MockHTTP in tests.
    """
    url = f"{BASE_URL}{path}"
    headers = _headers(api_key)
    method_fn = getattr(ctx.http, method.lower())
    attempts = 0
    while True:
        try:
            resp = await method_fn(url, headers=headers, params=params, json=json_body)
        except Exception as exc:  # pragma: no cover -- network/transport failure
            raise ShipStationError(0, f"Network error calling ShipStation: {exc}") from exc

        if resp.status_code == 429 and attempts < _MAX_RETRIES_ON_429:
            retry_after = (resp.headers or {}).get("Retry-After")
            try:
                wait_s = float(retry_after) if retry_after else _DEFAULT_RETRY_AFTER
            except ValueError:
                wait_s = _DEFAULT_RETRY_AFTER
            await asyncio.sleep(min(wait_s, 10.0))
            attempts += 1
            continue

        if resp.status_code == 204:
            return {}

        try:
            payload = resp.json() if resp.body else {}
        except ValueError:
            payload = {"raw_text": resp.text() if hasattr(resp, "text") else ""}

        if resp.status_code >= 400:
            detail, src = _extract_error(payload)
            raise ShipStationError(resp.status_code, detail, src, payload)

        return payload


def page_params(page: int = 1, page_size: int = 25) -> dict:
    """ShipStation V2 list endpoints: 1-based `page` + `page_size`
    (max varies per endpoint, 500 is the common ceiling; we cap
    conservatively at 100 to keep responses reasonably sized for chat)."""
    return {"page": max(1, page), "page_size": max(1, min(page_size, 100))}
