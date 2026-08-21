"""Rate shopping, shipment CRUD, tagging, and tracking."""
from __future__ import annotations

from imperal_sdk import ActionResult

import shipstation_client as sc
from accounts import _get_key
from app import ext, chat
from schemas import (
    NoParams,
    CalculateRatesParams, Rate, RateList, GetShipmentRatesParams,
    CreateShipmentParams, UpdateShipmentParams, CancelShipmentParams,
    ListShipmentsParams, GetShipmentParams, Shipment, ShipmentList,
    TagShipmentParams, UntagShipmentParams,
    Tag, TagList, CreateTagParams,
    TrackShipmentParams, TrackingResult, TrackingEvent, StopTrackingParams,
    DeleteResult,
)


def _addr_body(prefix_line1, city, state, postal, country, name=""):
    return {
        "name": name, "address_line1": prefix_line1, "city_locality": city,
        "state_province": state, "postal_code": postal, "country_code": country,
    }


def _shipment_from(d: dict) -> Shipment:
    return Shipment(
        shipment_id=d.get("shipment_id", ""),
        status=d.get("shipment_status", d.get("status", "")),
        carrier_id=d.get("carrier_id", ""),
        service_code=d.get("service_code", ""),
        ship_to_name=(d.get("ship_to") or {}).get("name", ""),
        ship_to_city=(d.get("ship_to") or {}).get("city_locality", ""),
        ship_date=d.get("ship_date", ""),
        tags=[t.get("name", "") for t in d.get("tags", []) if isinstance(t, dict)],
        created_at=d.get("created_at", ""),
    )


@chat.function(name="calculate_rates", data_model=RateList, description="Compare shipping rates across connected carriers for a shipment (rate shopping). Does not create anything or spend money.")
async def calculate_rates(ctx, params: CalculateRatesParams) -> ActionResult:
    """Compare shipping rates across connected carriers for a shipment (rate shopping). Does not create anything or spend money."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    body = {
        "rate_options": {"carrier_ids": params.carrier_ids} if params.carrier_ids else {},
        "shipment": {
            "ship_from": _addr_body(params.ship_from_line1, params.ship_from_city, params.ship_from_state, params.ship_from_postal_code, params.ship_from_country),
            "ship_to": _addr_body(params.ship_to_line1, params.ship_to_city, params.ship_to_state, params.ship_to_postal_code, params.ship_to_country),
            "packages": [{
                "weight": {"value": p.weight_value, "unit": p.weight_unit},
                **({"dimensions": {"length": p.length, "width": p.width, "height": p.height, "unit": p.size_unit}} if p.length else {}),
            } for p in params.packages],
        },
    }
    data = await sc.request(ctx, key, "POST", "/rates", json_body=body)
    items = []
    for r in data.get("rate_response", {}).get("rates", []) or data.get("rates", []):
        items.append(Rate(
            rate_id=r.get("rate_id", ""), carrier_id=r.get("carrier_id", ""),
            service_code=r.get("service_code", ""), service_type=r.get("service_type", ""),
            shipping_amount=float((r.get("shipping_amount") or {}).get("amount", 0.0)),
            currency=(r.get("shipping_amount") or {}).get("currency", "usd"),
            delivery_days=r.get("delivery_days") or 0,
            estimated_delivery_date=r.get("estimated_delivery_date", "") or "",
            trackable=bool(r.get("trackable")),
        ))
    return ActionResult.success(RateList(items=items))


@chat.function(name="get_shipment_rates", data_model=RateList, description="Re-fetch rates for an existing shipment (already has addresses/packages saved).")
async def get_shipment_rates(ctx, params: GetShipmentRatesParams) -> ActionResult:
    """Re-fetch rates for an existing shipment (already has addresses/packages saved)."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    data = await sc.request(ctx, key, "GET", f"/shipments/{params.shipment_id}/rates")
    items = [Rate(
        rate_id=r.get("rate_id", ""), carrier_id=r.get("carrier_id", ""),
        service_code=r.get("service_code", ""), service_type=r.get("service_type", ""),
        shipping_amount=float((r.get("shipping_amount") or {}).get("amount", 0.0)),
        currency=(r.get("shipping_amount") or {}).get("currency", "usd"),
        delivery_days=r.get("delivery_days") or 0,
        estimated_delivery_date=r.get("estimated_delivery_date", "") or "",
        trackable=bool(r.get("trackable")),
    ) for r in data.get("rates", [])]
    return ActionResult.success(RateList(items=items))


@chat.function(name="create_shipment", data_model=Shipment, description="Create a new shipment (addresses + package details). Does not purchase a label yet -- use create_label_from_shipment after.")
async def create_shipment(ctx, params: CreateShipmentParams) -> ActionResult:
    """Create a new shipment (addresses + package details). Does not purchase a label yet -- use create_label_from_shipment after."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    body = {
        "ship_from": _addr_body(params.ship_from_line1, params.ship_from_city, params.ship_from_state, params.ship_from_postal_code, params.ship_from_country),
        "ship_to": _addr_body(params.ship_to_line1, params.ship_to_city, params.ship_to_state, params.ship_to_postal_code, params.ship_to_country, params.ship_to_name),
        "packages": [{"weight": {"value": p.weight_value, "unit": p.weight_unit}} for p in params.packages],
    }
    if params.carrier_id:
        body["carrier_id"] = params.carrier_id
    if params.service_code:
        body["service_code"] = params.service_code
    data = await sc.request(ctx, key, "POST", "/shipments", json_body=body)
    return ActionResult.success(_shipment_from(data), message="Shipment created.", refresh_panels=["ss_results"])


@chat.function(name="update_shipment", data_model=Shipment, description="Update an existing (not-yet-labeled) shipment's carrier/service.")
async def update_shipment(ctx, params: UpdateShipmentParams) -> ActionResult:
    """Update an existing (not-yet-labeled) shipment's carrier/service."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    body = {}
    if params.carrier_id:
        body["carrier_id"] = params.carrier_id
    if params.service_code:
        body["service_code"] = params.service_code
    data = await sc.request(ctx, key, "PUT", f"/shipments/{params.shipment_id}", json_body=body)
    return ActionResult.success(_shipment_from(data), message="Shipment updated.", refresh_panels=["ss_results"])


@chat.function(name="cancel_shipment", data_model=DeleteResult, description="Cancel a shipment that has not been labeled yet.")
async def cancel_shipment(ctx, params: CancelShipmentParams) -> ActionResult:
    """Cancel a shipment that has not been labeled yet."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    await sc.request(ctx, key, "PUT", f"/shipments/{params.shipment_id}/cancel")
    return ActionResult.success(DeleteResult(deleted=True, id=params.shipment_id), message="Shipment canceled.", refresh_panels=["ss_results"])


@chat.function(name="list_shipments", data_model=ShipmentList, description="List shipments in the connected ShipStation account, with status/carrier/ship-to.")
async def list_shipments(ctx, params: ListShipmentsParams) -> ActionResult:
    """List shipments in the connected ShipStation account, with status/carrier/ship-to."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    qp = sc.page_params(params.page, params.page_size)
    if params.shipment_status:
        qp["shipment_status"] = params.shipment_status
    data = await sc.request(ctx, key, "GET", "/shipments", params=qp)
    items = [_shipment_from(s) for s in data.get("shipments", [])]
    return ActionResult.success(ShipmentList(items=items))


@chat.function(name="get_shipment", data_model=Shipment, description="Read one shipment in full by id.")
async def get_shipment(ctx, params: GetShipmentParams) -> ActionResult:
    """Read one shipment in full by id."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    data = await sc.request(ctx, key, "GET", f"/shipments/{params.shipment_id}")
    return ActionResult.success(_shipment_from(data))


@chat.function(name="create_tag", data_model=Tag, description="Create a new shipment tag (a label you can attach to shipments for organizing/filtering).")
async def create_tag(ctx, params: CreateTagParams) -> ActionResult:
    """Create a new shipment tag (a label you can attach to shipments for organizing/filtering)."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    data = await sc.request(ctx, key, "POST", "/tags", json_body={"name": params.name})
    return ActionResult.success(Tag(tag_id=str(data.get("tag_id", "")), name=data.get("name", params.name)), message="Tag created.")


@chat.function(name="list_tags", data_model=TagList, description="List shipment tags defined on this ShipStation account.")
async def list_tags(ctx, params: NoParams) -> ActionResult:
    """List shipment tags defined on this ShipStation account."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    data = await sc.request(ctx, key, "GET", "/tags")
    items = [Tag(tag_id=str(t.get("tag_id", "")), name=t.get("name", "")) for t in data if isinstance(data, list)] if isinstance(data, list) else []
    return ActionResult.success(TagList(items=items))


@chat.function(name="tag_shipment", data_model=Shipment, description="Attach a tag to a shipment.")
async def tag_shipment(ctx, params: TagShipmentParams) -> ActionResult:
    """Attach a tag to a shipment."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    data = await sc.request(ctx, key, "POST", f"/shipments/{params.shipment_id}/tags/{params.tag_name}")
    return ActionResult.success(_shipment_from(data), message="Tag attached.", refresh_panels=["ss_results"])


@chat.function(name="untag_shipment", data_model=Shipment, description="Remove a tag from a shipment.")
async def untag_shipment(ctx, params: UntagShipmentParams) -> ActionResult:
    """Remove a tag from a shipment."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    data = await sc.request(ctx, key, "DELETE", f"/shipments/{params.shipment_id}/tags/{params.tag_name}")
    return ActionResult.success(_shipment_from(data), message="Tag removed.", refresh_panels=["ss_results"])


@chat.function(name="track_shipment", data_model=TrackingResult, description="Look up live tracking status/events for a carrier + tracking number.")
async def track_shipment(ctx, params: TrackShipmentParams) -> ActionResult:
    """Look up live tracking status/events for a carrier + tracking number."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    data = await sc.request(ctx, key, "GET", "/tracking", params={"carrier_id": params.carrier_id, "tracking_number": params.tracking_number})
    events = [TrackingEvent(
        occurred_at=e.get("occurred_at", ""), description=e.get("description", ""),
        city=e.get("city_locality", ""), state=e.get("state_province", ""), country=e.get("country_code", ""),
    ) for e in data.get("events", [])]
    return ActionResult.success(TrackingResult(
        status_code=data.get("status_code", ""), status_description=data.get("status_description", ""),
        carrier_id=params.carrier_id, tracking_number=params.tracking_number,
        estimated_delivery=data.get("estimated_delivery_date", "") or "",
        events=events,
    ))


@chat.function(name="stop_tracking_shipment", data_model=DeleteResult, description="Stop tracking a carrier + tracking number pair (unsubscribes from further tracking webhook updates for it).")
async def stop_tracking_shipment(ctx, params: StopTrackingParams) -> ActionResult:
    """Stop tracking a carrier + tracking number pair (unsubscribes from further tracking webhook updates for it)."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    await sc.request(ctx, key, "DELETE", "/tracking/stop", params={"carrier_id": params.carrier_id, "tracking_number": params.tracking_number})
    return ActionResult.success(DeleteResult(deleted=True, id=params.tracking_number), message="Stopped tracking.")
