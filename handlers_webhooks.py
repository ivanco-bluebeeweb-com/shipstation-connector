"""Webhook subscriptions -- ShipStation pushes events to a URL you provide."""
from __future__ import annotations

from imperal_sdk import ActionResult

import shipstation_client as sc
from accounts import _get_key
from app import ext, chat
from schemas import (
    NoParams,
    CreateWebhookParams, Webhook, WebhookList, GetWebhookParams, DeleteWebhookParams,
    DeleteResult,
)


def _webhook_from(d: dict) -> Webhook:
    return Webhook(
        webhook_id=str(d.get("webhook_id", "")),
        event_type=d.get("event", d.get("event_type", "")),
        url=d.get("url", ""),
        name=d.get("name", ""),
        created_at=d.get("created_at", ""),
    )


@chat.function(
    name="create_webhook", event="shipstation-connector.create_webhook", effects=['create:webhook'], action_type="write", data_model=Webhook,
    description=(
        "Subscribe to a ShipStation event (e.g. 'label_created', "
        "'track', 'batch') -- ShipStation will POST to your URL when it fires."
    ),
)
async def create_webhook(ctx, params: CreateWebhookParams) -> ActionResult:
    """Subscribe to a ShipStation event (e.g. 'label_created', 'track', 'batch') -- ShipStation will POST to your URL when it fires."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    body = {"event": params.event_type, "url": params.url}
    if params.name:
        body["name"] = params.name
    data = await sc.request(ctx, key, "POST", "/environment/webhooks", json=body)
    return ActionResult.success(_webhook_from(data))


@chat.function(name="list_webhooks", event="shipstation-connector.list_webhooks", action_type="read", data_model=WebhookList, description="List webhook subscriptions configured on this ShipStation account.")
async def list_webhooks(ctx, params: NoParams) -> ActionResult:
    """List webhook subscriptions configured on this ShipStation account."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    data = await sc.request(ctx, key, "GET", "/environment/webhooks")
    items = [_webhook_from(w) for w in data.get("webhooks", [])]
    return ActionResult.success(WebhookList(items=items))


@chat.function(name="get_webhook", event="shipstation-connector.get_webhook", action_type="read", data_model=Webhook, description="Read one webhook subscription in full.")
async def get_webhook(ctx, params: GetWebhookParams) -> ActionResult:
    """Read one webhook subscription in full."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    data = await sc.request(ctx, key, "GET", "/environment/webhooks/" + params.webhook_id)
    return ActionResult.success(_webhook_from(data))


@chat.function(name="delete_webhook", event="shipstation-connector.delete_webhook", effects=['delete:webhook'], action_type="destructive", data_model=DeleteResult, description="Permanently remove a webhook subscription. Cannot be undone.")
async def delete_webhook(ctx, params: DeleteWebhookParams) -> ActionResult:
    """Permanently remove a webhook subscription. Cannot be undone."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    await sc.request(ctx, key, "DELETE", "/environment/webhooks/" + params.webhook_id)
    return ActionResult.success(DeleteResult(deleted=True, id=params.webhook_id))
