"""Connect/disconnect ShipStation, list_connections -- same validate-before-
save pattern as Klaviyo Connector's accounts.py / Shopify Connector's own
connection handlers: a bad key is rejected immediately (one cheap GET
against ShipStation's own /carriers endpoint) instead of failing silently
on first real use later.
"""
from __future__ import annotations

from imperal_sdk import ActionResult, sdl

import shipstation_client as sc
from app import ext, chat
from schemas import (
    NoParams,
    ConnectShipStationParams, DisconnectShipStationParams,
    ProviderConnection, ProviderConnectionList,
    DeleteResult,
)

_SECRET_NAME = "shipstation_api_key"


async def _get_key(ctx) -> str:
    """Async because ctx.secrets.get() is a coroutine on the real SDK --
    a sync wrapper here would always return a truthy coroutine object
    instead of the actual stored value (or its absence), silently
    breaking every connection check in this connector."""
    return (await ctx.secrets.get(_SECRET_NAME)) or ""


@chat.function(
    name="connect_shipstation", event="shipstation-connector.connect_shipstation", effects=['create:connection'], action_type="write", data_model=ProviderConnection,
    description=(
        "Connect ShipStation by saving your own API V2 key, after checking "
        "it actually works. Get it from ShipStation: Account Settings > "
        "API Settings > API Keys (V2)."
    ),
)
async def connect_shipstation(ctx, params: ConnectShipStationParams) -> ActionResult:
    """Validate the key against ShipStation before saving it."""
    key = (params.api_key or "").strip()
    if not key:
        return ActionResult.error("API key is required.")
    try:
        await sc.request(ctx, key, "GET", "/carriers")
    except sc.ShipStationError as exc:
        if exc.status_code == 401:
            return ActionResult.error("That API key was rejected by ShipStation (401 Unauthorized). Double-check it was copied in full.")
        return ActionResult.error(f"Could not verify the key against ShipStation: {exc.detail}")

    await ctx.secrets.set(_SECRET_NAME, key)
    label = params.label.strip() or "ShipStation"
    return ActionResult.success(
        ProviderConnection(id="default", title=label, connected=True, detail="API key verified and saved."),
        message=f"Connected to ShipStation ({label}).",
        refresh_panels=["shipstation_connect", "shipstation_settings"],
    )


@chat.function(
    name="disconnect_shipstation", event="shipstation-connector.disconnect_shipstation", effects=['delete:connection'], action_type="destructive", data_model=DeleteResult,
    description="Disconnect ShipStation: deletes the saved API key. Nothing in your ShipStation account is changed.",
)
async def disconnect_shipstation(ctx, params: DisconnectShipStationParams) -> ActionResult:
    """Disconnect ShipStation: deletes the saved API key. Nothing in your ShipStation account is changed."""
    await ctx.secrets.delete(_SECRET_NAME)
    return ActionResult.success(
        DeleteResult(deleted=True, id=params.connection_id or "default"),
        message="Disconnected from ShipStation.",
        refresh_panels=["shipstation_connect", "shipstation_settings"],
    )


@chat.function(
    name="list_connections", event="shipstation-connector.list_connections", action_type="read", data_model=ProviderConnectionList,
    description="List the connected ShipStation account(s) and whether the saved key still works.",
)
async def list_connections(ctx, params: NoParams) -> ActionResult:
    """List the connected ShipStation account(s) and whether the saved key still works."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.success(ProviderConnectionList(items=[]), message="No ShipStation account connected.")
    detail = "Connected."
    connected = True
    try:
        await sc.request(ctx, key, "GET", "/carriers")
    except sc.ShipStationError as exc:
        connected = False
        detail = f"Saved key currently fails: {exc.detail}"
    return ActionResult.success(
        ProviderConnectionList(items=[ProviderConnection(id="default", title="ShipStation", connected=connected, detail=detail)]),
    )


async def get_connection_status(ctx) -> tuple[bool, str]:
    """Shared helper for panels: (connected, detail)."""
    key = await _get_key(ctx)
    if not key:
        return False, ""
    try:
        await sc.request(ctx, key, "GET", "/carriers")
        return True, "API key verified and saved."
    except sc.ShipStationError as exc:
        return False, f"Saved key currently fails: {exc.detail}"


async def _load_connections(ctx) -> list[dict]:
    """Shared helper for panels.py/panels_settings.py -- there is exactly
    one possible connection (a single BYOK secret, no multi-account
    concept), so this always returns 0 or 1 entries, dict-shaped like
    ProviderConnection so panels can render them without importing the
    Pydantic model."""
    connected, detail = await get_connection_status(ctx)
    if not connected and not detail:
        return []
    return [{"id": "default", "title": "ShipStation", "connected": connected, "detail": detail}]
