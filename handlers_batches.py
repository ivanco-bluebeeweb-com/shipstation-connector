"""Batches (bulk label processing), customs manifests, and pickup scheduling."""
from __future__ import annotations

from imperal_sdk import ActionResult

import shipstation_client as sc
from accounts import _get_key
from app import ext, chat
from schemas import (
    CreateBatchParams, Batch, BatchList, ListBatchesParams, GetBatchParams,
    AddToBatchParams, RemoveFromBatchParams, ProcessBatchParams, DeleteBatchParams,
    CreateManifestParams, Manifest, ManifestList, ListManifestsParams, GetManifestParams,
    SchedulePickupParams, Pickup, PickupList, ListPickupsParams, GetPickupParams,
    CancelPickupParams, DeleteResult,
)


def _batch_from(d: dict) -> Batch:
    return Batch(
        batch_id=d.get("batch_id", ""),
        batch_number=d.get("batch_number", ""),
        status=d.get("status", ""),
        label_count=int(d.get("count", 0) or 0),
        errors_count=int(d.get("errors", 0) or 0),
        completed_at=d.get("completed_at", "") or "",
        created_at=d.get("created_at", ""),
    )


def _manifest_from(d: dict) -> Manifest:
    return Manifest(
        manifest_id=d.get("manifest_id", ""),
        carrier_id=d.get("carrier_id", ""),
        ship_date=d.get("ship_date", ""),
        warehouse_id=d.get("warehouse_id", ""),
        submitted_at=d.get("created_at", ""),
        manifest_download_url=(d.get("manifests") or [{}])[0].get("manifest_download", {}).get("href", "") if d.get("manifests") else "",
        shipments_count=int(d.get("shipments_count", 0) or 0),
    )


def _pickup_from(d: dict) -> Pickup:
    return Pickup(
        pickup_id=d.get("pickup_id", ""),
        carrier_id=d.get("carrier_id", ""),
        warehouse_id=d.get("warehouse_id", ""),
        pickup_date=d.get("pickup_date", ""),
        confirmation_number=d.get("carrier_pickup_id", "") or d.get("confirmation_number", ""),
        status=d.get("status", ""),
    )


# ── Batches ──────────────────────────────────────────────────────────────

@chat.function(name="create_batch", event="shipstation-connector.create_batch", effects=['create:batch'], action_type="write", data_model=Batch, description="Create a new batch (a group of shipments to process/label together) in ShipStation, optionally pre-populated with shipment ids.")
async def create_batch(ctx, params: CreateBatchParams) -> ActionResult:
    """Create a new batch (a group of shipments to process/label together) in ShipStation, optionally pre-populated with shipment ids."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    body = {}
    if params.batch_notes:
        body["batch_notes"] = params.batch_notes
    if params.shipment_ids:
        body["shipment_ids"] = params.shipment_ids
    data = await sc.request(ctx, key, "POST", "/batches", json=body)
    return ActionResult.success(_batch_from(data))


@chat.function(name="list_batches", event="shipstation-connector.list_batches", action_type="read", data_model=BatchList, description="List batches, optionally filtered by status ('open', 'completed', 'processing').")
async def list_batches(ctx, params: ListBatchesParams) -> ActionResult:
    """List batches, optionally filtered by status ('open', 'completed', 'processing')."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    q = sc.page_params(params.page, params.page_size)
    if params.status:
        q["status"] = params.status
    data = await sc.request(ctx, key, "GET", "/batches", params=q)
    items = [_batch_from(b) for b in data.get("batches", [])]
    return ActionResult.success(BatchList(items=items))


@chat.function(name="get_batch", event="shipstation-connector.get_batch", action_type="read", data_model=Batch, description="Read one batch in full -- status, label count, and any errors.")
async def get_batch(ctx, params: GetBatchParams) -> ActionResult:
    """Read one batch in full -- status, label count, and any errors."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    data = await sc.request(ctx, key, "GET", "/batches/" + params.batch_id)
    return ActionResult.success(_batch_from(data))


@chat.function(name="add_to_batch", event="shipstation-connector.add_to_batch", effects=['update:batch'], action_type="write", data_model=Batch, description="Add shipments to an existing open batch.")
async def add_to_batch(ctx, params: AddToBatchParams) -> ActionResult:
    """Add shipments to an existing open batch."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    data = await sc.request(ctx, key, "POST", "/batches/" + params.batch_id + "/add", json={"shipment_ids": params.shipment_ids})
    return ActionResult.success(_batch_from(data))


@chat.function(name="remove_from_batch", event="shipstation-connector.remove_from_batch", effects=['update:batch'], action_type="write", data_model=Batch, description="Remove shipments from an open batch.")
async def remove_from_batch(ctx, params: RemoveFromBatchParams) -> ActionResult:
    """Remove shipments from an open batch."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    data = await sc.request(ctx, key, "POST", "/batches/" + params.batch_id + "/remove", json={"shipment_ids": params.shipment_ids})
    return ActionResult.success(_batch_from(data))


@chat.function(
    name="process_batch", event="shipstation-connector.process_batch", effects=['create:label', 'charge:postage'], action_type="destructive", data_model=Batch,
    description=(
        "PROCESS a batch -- PURCHASES REAL SHIPPING LABELS for every shipment in "
        "it, SPENDING REAL CARRIER POSTAGE FUNDS. ShipStation V2 has no sandbox: "
        "this charges your live account for every shipment in the batch."
    ),
)
async def process_batch(ctx, params: ProcessBatchParams) -> ActionResult:
    """PROCESS a batch -- PURCHASES REAL SHIPPING LABELS for every shipment in it, SPENDING REAL CARRIER POSTAGE FUNDS. ShipStation V2 has no sandbox: this charges your live account for every shipment in the batch."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    body = {"label_format": params.label_format, "label_layout": params.label_layout}
    data = await sc.request(ctx, key, "POST", "/batches/" + params.batch_id + "/process/labels", json=body)
    return ActionResult.success(_batch_from(data))


@chat.function(name="delete_batch", event="shipstation-connector.delete_batch", effects=['delete:batch'], action_type="destructive", data_model=DeleteResult, description="Permanently delete a batch. Does not void any labels already purchased through it.")
async def delete_batch(ctx, params: DeleteBatchParams) -> ActionResult:
    """Permanently delete a batch. Does not void any labels already purchased through it."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    await sc.request(ctx, key, "DELETE", "/batches/" + params.batch_id)
    return ActionResult.success(DeleteResult(deleted=True, id=params.batch_id))


# ── Manifests ────────────────────────────────────────────────────────────

@chat.function(
    name="create_manifest", event="shipstation-connector.create_manifest", effects=['create:manifest'], action_type="write", data_model=Manifest,
    description=(
        "Create a customs/carrier manifest -- the end-of-day document some "
        "carriers (e.g. USPS SCAN form) require to accept a batch of shipments "
        "for pickup. Does not purchase labels; the shipments must already have "
        "labels."
    ),
)
async def create_manifest(ctx, params: CreateManifestParams) -> ActionResult:
    """Create a customs/carrier manifest -- the end-of-day document some carriers (e.g. USPS SCAN form) require to accept a batch of shipments for pickup. Does not purchase labels; the shipments must already have labels."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    body = {"carrier_id": params.carrier_id}
    if params.warehouse_id:
        body["warehouse_id"] = params.warehouse_id
    if params.ship_date:
        body["ship_date"] = params.ship_date
    if params.shipment_ids:
        body["shipment_ids"] = params.shipment_ids
    data = await sc.request(ctx, key, "POST", "/manifests", json=body)
    return ActionResult.success(_manifest_from(data))


@chat.function(name="list_manifests", event="shipstation-connector.list_manifests", action_type="read", data_model=ManifestList, description="List customs/carrier manifests, optionally filtered by warehouse.")
async def list_manifests(ctx, params: ListManifestsParams) -> ActionResult:
    """List customs/carrier manifests, optionally filtered by warehouse."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    q = sc.page_params(params.page, params.page_size)
    if params.warehouse_id:
        q["warehouse_id"] = params.warehouse_id
    data = await sc.request(ctx, key, "GET", "/manifests", params=q)
    items = [_manifest_from(m) for m in data.get("manifests", [])]
    return ActionResult.success(ManifestList(items=items))


@chat.function(name="get_manifest", event="shipstation-connector.get_manifest", action_type="read", data_model=Manifest, description="Read one manifest in full, including its download URL.")
async def get_manifest(ctx, params: GetManifestParams) -> ActionResult:
    """Read one manifest in full, including its download URL."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    data = await sc.request(ctx, key, "GET", "/manifests/" + params.manifest_id)
    return ActionResult.success(_manifest_from(data))


# ── Pickups ──────────────────────────────────────────────────────────────

@chat.function(
    name="schedule_pickup", event="shipstation-connector.schedule_pickup", effects=['create:pickup'], action_type="write", data_model=Pickup,
    description=(
        "Schedule a carrier pickup at a warehouse -- asks the carrier to send a "
        "driver to collect packages. Some carriers may charge a pickup fee; "
        "check the carrier's own terms."
    ),
)
async def schedule_pickup(ctx, params: SchedulePickupParams) -> ActionResult:
    """Schedule a carrier pickup at a warehouse -- asks the carrier to send a driver to collect packages. Some carriers may charge a pickup fee; check the carrier's own terms."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    body = {
        "carrier_id": params.carrier_id,
        "warehouse_id": params.warehouse_id,
        "pickup_date": params.pickup_date,
    }
    if params.ready_time:
        body["ready_time"] = params.ready_time
    if params.close_time:
        body["close_time"] = params.close_time
    data = await sc.request(ctx, key, "POST", "/pickups", json=body)
    return ActionResult.success(_pickup_from(data))


@chat.function(name="list_pickups", event="shipstation-connector.list_pickups", action_type="read", data_model=PickupList, description="List scheduled carrier pickups.")
async def list_pickups(ctx, params: ListPickupsParams) -> ActionResult:
    """List scheduled carrier pickups."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    q = sc.page_params(params.page, params.page_size)
    data = await sc.request(ctx, key, "GET", "/pickups", params=q)
    items = [_pickup_from(p) for p in data.get("pickups", [])]
    return ActionResult.success(PickupList(items=items))


@chat.function(name="get_pickup", event="shipstation-connector.get_pickup", action_type="read", data_model=Pickup, description="Read one scheduled pickup in full.")
async def get_pickup(ctx, params: GetPickupParams) -> ActionResult:
    """Read one scheduled pickup in full."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    data = await sc.request(ctx, key, "GET", "/pickups/" + params.pickup_id)
    return ActionResult.success(_pickup_from(data))


@chat.function(name="cancel_pickup", event="shipstation-connector.cancel_pickup", effects=['delete:pickup'], action_type="destructive", data_model=DeleteResult, description="Cancel a scheduled carrier pickup.")
async def cancel_pickup(ctx, params: CancelPickupParams) -> ActionResult:
    """Cancel a scheduled carrier pickup."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    await sc.request(ctx, key, "DELETE", "/pickups/" + params.pickup_id)
    return ActionResult.success(DeleteResult(deleted=True, id=params.pickup_id))
