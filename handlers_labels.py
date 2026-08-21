"""Label purchase/download/void, including multi-package and return labels.

WHY EVERY LABEL-PURCHASING TOOL'S DESCRIPTION CARRIES A COST WARNING EVEN
THOUGH IT IS A "create" -- see app.py module docstring: ShipStation V2 has
no sandbox, so purchasing a label spends real carrier postage funds. This
is surfaced in the description text itself so the model/user sees the
cost warning before calling it, not buried in a doc.
"""
from __future__ import annotations

from imperal_sdk import ActionResult

import shipstation_client as sc
from accounts import _get_key
from app import ext, chat
from schemas import (
    CreateLabelFromShipmentParams, CreateLabelFromRateParams,
    CreateReturnLabelParams, Label, LabelList, ListLabelsParams,
    GetLabelParams, VoidLabelParams, DeleteResult,
)


def _label_from(d: dict) -> Label:
    dl = d.get("label_download") or {}
    return Label(
        label_id=d.get("label_id", ""),
        status=d.get("status", ""),
        shipment_id=d.get("shipment_id", ""),
        carrier_id=d.get("carrier_id", ""),
        tracking_number=d.get("tracking_number", ""),
        label_download_url=dl.get("pdf", "") or dl.get("href", ""),
        label_format=d.get("label_format", ""),
        voided=bool(d.get("voided")),
        is_return_label=bool(d.get("is_return_label")),
        shipment_cost=float((d.get("shipment_cost") or {}).get("amount", 0.0)),
        created_at=d.get("created_at", ""),
    )


@chat.function(
    name="create_label_from_shipment", data_model=Label,
    description=(
        "PURCHASE a shipping label for an existing shipment -- SPENDS REAL "
        "CARRIER POSTAGE FUNDS from your ShipStation account balance. "
        "ShipStation V2 has no sandbox/test mode: this charges your real "
        "account. Void the label immediately after if it was only a test."
    ),
)
async def create_label_from_shipment(ctx, params: CreateLabelFromShipmentParams) -> ActionResult:
    """PURCHASE a shipping label for an existing shipment -- SPENDS REAL CARRIER POSTAGE FUNDS from your ShipStation account balance. ShipStation V2 has no sandbox/test mode: this charges your real account. Void the label immediately after if it was only a test."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    body = {
        "shipment_id": params.shipment_id,
        "label_format": params.label_format,
        "label_layout": params.label_layout,
        "label_download_type": params.label_download_type,
    }
    try:
        data = await sc.request(ctx, key, "POST", "/labels/shipment/" + params.shipment_id, json=body)
    except sc.ShipStationError as exc:
        return ActionResult.error(f"Could not purchase label: {exc}")
    return ActionResult.success(_label_from(data))


@chat.function(
    name="create_label_from_rate", data_model=Label,
    description=(
        "PURCHASE a shipping label from a previously fetched rate (calculate_rates) -- "
        "SPENDS REAL CARRIER POSTAGE FUNDS. ShipStation V2 has no sandbox/test mode."
    ),
)
async def create_label_from_rate(ctx, params: CreateLabelFromRateParams) -> ActionResult:
    """PURCHASE a shipping label from a previously fetched rate (calculate_rates) -- SPENDS REAL CARRIER POSTAGE FUNDS. ShipStation V2 has no sandbox/test mode."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    body = {
        "rate_id": params.rate_id,
        "label_format": params.label_format,
        "label_layout": params.label_layout,
        "label_download_type": params.label_download_type,
    }
    try:
        data = await sc.request(ctx, key, "POST", "/labels/rates/" + params.rate_id, json=body)
    except sc.ShipStationError as exc:
        return ActionResult.error(f"Could not purchase label: {exc}")
    return ActionResult.success(_label_from(data))


@chat.function(
    name="create_return_label", data_model=Label,
    description=(
        "PURCHASE a return shipping label linked to a previous outbound label -- "
        "SPENDS REAL CARRIER POSTAGE FUNDS. ShipStation V2 has no sandbox/test mode."
    ),
)
async def create_return_label(ctx, params: CreateReturnLabelParams) -> ActionResult:
    """PURCHASE a return shipping label linked to a previous outbound label -- SPENDS REAL CARRIER POSTAGE FUNDS. ShipStation V2 has no sandbox/test mode."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    body = {
        "label_format": params.label_format,
        "label_layout": params.label_layout,
    }
    try:
        data = await sc.request(ctx, key, "POST", "/labels/" + params.outbound_label_id + "/return", json=body)
    except sc.ShipStationError as exc:
        return ActionResult.error(f"Could not purchase return label: {exc}")
    return ActionResult.success(_label_from(data))


@chat.function(name="list_labels", data_model=LabelList, description="List purchased shipping labels, optionally filtered by shipment.")
async def list_labels(ctx, params: ListLabelsParams) -> ActionResult:
    """List purchased shipping labels, optionally filtered by shipment."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    q = sc.page_params(params.page, params.page_size)
    if params.shipment_id:
        q["shipment_id"] = params.shipment_id
    data = await sc.request(ctx, key, "GET", "/labels", params=q)
    items = [_label_from(l) for l in data.get("labels", [])]
    return ActionResult.success(LabelList(items=items))


@chat.function(name="get_label", data_model=Label, description="Read one purchased label in full, including its download URL.")
async def get_label(ctx, params: GetLabelParams) -> ActionResult:
    """Read one purchased label in full, including its download URL."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    data = await sc.request(ctx, key, "GET", "/labels/" + params.label_id)
    return ActionResult.success(_label_from(data))


@chat.function(
    name="void_label", data_model=DeleteResult,
    description=(
        "Void a purchased label and request a refund of its postage cost from the "
        "carrier. Must be done promptly -- most carriers only refund labels voided "
        "within a short window (often 24-48h) of purchase."
    ),
)
async def void_label(ctx, params: VoidLabelParams) -> ActionResult:
    """Void a purchased label and request a refund of its postage cost from the carrier. Must be done promptly -- most carriers only refund labels voided within a short window (often 24-48h) of purchase."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    try:
        await sc.request(ctx, key, "PUT", "/labels/" + params.label_id + "/void")
    except sc.ShipStationError as exc:
        return ActionResult.error(f"Could not void label: {exc}")
    return ActionResult.success(DeleteResult(deleted=True, id=params.label_id))
