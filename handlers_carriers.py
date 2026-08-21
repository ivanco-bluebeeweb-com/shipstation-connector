"""Carriers, carrier package types, warehouses, address validation, and the
account summary value-add report.
"""
from __future__ import annotations

from imperal_sdk import ActionResult

import shipstation_client as sc
from accounts import _get_key
from app import ext, chat
from schemas import (
    NoParams,
    Carrier, CarrierList, GetCarrierParams, GetCarrierOptionsParams,
    CarrierOptionList,
    PackageType, PackageTypeList, ListCarrierPackageTypesParams,
    CreatePackageTypeParams, UpdatePackageTypeParams, DeletePackageTypeParams,
    Warehouse, WarehouseList, GetWarehouseParams, CreateWarehouseParams,
    UpdateWarehouseParams, DeleteWarehouseParams,
    ValidateAddressParams, AddressValidationResult,
    GetAccountSummaryParams, AccountSummary,
    DeleteResult,
)


def _carrier_from(d: dict) -> Carrier:
    return Carrier(
        carrier_id=d.get("carrier_id", ""),
        carrier_code=d.get("carrier_code", ""),
        friendly_name=d.get("friendly_name", ""),
        account_number=d.get("account_number", ""),
        requires_funded_amount=bool(d.get("requires_funded_amount")),
        balance=float(d.get("balance") or 0.0),
        nickname=d.get("nickname", ""),
        disabled_by_billing_plan=bool(d.get("disabled_by_billing_plan")),
    )


@chat.function(name="list_carriers", data_model=CarrierList, description="List carrier accounts connected in ShipStation (e.g. UPS, FedEx, USPS) with balance and account info.")
async def list_carriers(ctx, params: NoParams) -> ActionResult:
    """List carrier accounts connected in ShipStation (e.g. UPS, FedEx, USPS) with balance and account info."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    data = await sc.request(ctx, key, "GET", "/carriers")
    items = [_carrier_from(c) for c in data.get("carriers", [])]
    return ActionResult.success(CarrierList(items=items))


@chat.function(name="get_carrier", data_model=Carrier, description="Read one carrier account in full by id.")
async def get_carrier(ctx, params: GetCarrierParams) -> ActionResult:
    """Read one carrier account in full by id."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    data = await sc.request(ctx, key, "GET", f"/carriers/{params.carrier_id}")
    return ActionResult.success(_carrier_from(data))


@chat.function(name="get_carrier_options", data_model=CarrierOptionList, description="Read the configurable shipping options a specific carrier supports (e.g. saturday delivery, signature confirmation).")
async def get_carrier_options(ctx, params: GetCarrierOptionsParams) -> ActionResult:
    """Read the configurable shipping options a specific carrier supports (e.g. saturday delivery, signature confirmation)."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    data = await sc.request(ctx, key, "GET", f"/carriers/{params.carrier_id}/options")
    from schemas import CarrierOption
    items = [CarrierOption(name=o.get("name", ""), default_value=str(o.get("default_value", "")), description=o.get("description", "")) for o in data.get("options", [])]
    return ActionResult.success(CarrierOptionList(items=items))


def _package_type_from(d: dict) -> PackageType:
    return PackageType(
        package_id=d.get("package_id", ""),
        carrier_id=d.get("carrier_id", ""),
        name=d.get("name", ""),
        code=d.get("code", ""),
        domestic=bool(d.get("domestic")),
        international=bool(d.get("international")),
    )


@chat.function(name="list_carrier_package_types", data_model=PackageTypeList, description="List package types a carrier supports (built-in and custom), e.g. flat rate envelope, box, thick envelope.")
async def list_carrier_package_types(ctx, params: ListCarrierPackageTypesParams) -> ActionResult:
    """List package types a carrier supports (built-in and custom), e.g. flat rate envelope, box, thick envelope."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    data = await sc.request(ctx, key, "GET", f"/carriers/{params.carrier_id}/packages")
    items = [_package_type_from(p) for p in data.get("packages", [])]
    return ActionResult.success(PackageTypeList(items=items))


@chat.function(name="create_package_type", data_model=PackageType, description="Create a custom package type with fixed dimensions for a carrier.")
async def create_package_type(ctx, params: CreatePackageTypeParams) -> ActionResult:
    """Create a custom package type with fixed dimensions for a carrier."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    body = {
        "carrier_id": params.carrier_id,
        "name": params.name,
        "dimensions": {"length": params.length, "width": params.width, "height": params.height, "unit": params.size_unit},
    }
    data = await sc.request(ctx, key, "POST", "/packages", json_body=body)
    return ActionResult.success(_package_type_from(data), message=f"Package type '{params.name}' created.")


@chat.function(name="update_package_type", data_model=PackageType, description="Update an existing custom package type's name or dimensions.")
async def update_package_type(ctx, params: UpdatePackageTypeParams) -> ActionResult:
    """Update an existing custom package type's name or dimensions."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    body: dict = {}
    if params.name:
        body["name"] = params.name
    if params.length or params.width or params.height:
        body["dimensions"] = {"length": params.length, "width": params.width, "height": params.height, "unit": params.size_unit}
    data = await sc.request(ctx, key, "PUT", f"/packages/{params.package_id}", json_body=body)
    return ActionResult.success(_package_type_from(data), message="Package type updated.")


@chat.function(name="delete_package_type", data_model=DeleteResult, description="Permanently delete a custom package type.")
async def delete_package_type(ctx, params: DeletePackageTypeParams) -> ActionResult:
    """Permanently delete a custom package type."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    await sc.request(ctx, key, "DELETE", f"/packages/{params.package_id}")
    return ActionResult.success(DeleteResult(deleted=True, id=params.package_id), message="Package type deleted.")


def _warehouse_from(d: dict) -> Warehouse:
    origin = d.get("origin_address") or {}
    return Warehouse(
        warehouse_id=str(d.get("warehouse_id", "")),
        name=d.get("name", ""),
        is_default=bool(d.get("is_default")),
        origin_line1=origin.get("address_line1", ""),
        origin_city=origin.get("city_locality", ""),
        origin_state=origin.get("state_province", ""),
        origin_postal_code=origin.get("postal_code", ""),
        origin_country=origin.get("country_code", ""),
    )


@chat.function(name="list_warehouses", data_model=WarehouseList, description="List warehouses/ship-from locations configured in ShipStation.")
async def list_warehouses(ctx, params: NoParams) -> ActionResult:
    """List warehouses/ship-from locations configured in ShipStation."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    data = await sc.request(ctx, key, "GET", "/warehouses")
    items = [_warehouse_from(w) for w in data.get("warehouses", [])]
    return ActionResult.success(WarehouseList(items=items))


@chat.function(name="get_warehouse", data_model=Warehouse, description="Read one warehouse in full by id.")
async def get_warehouse(ctx, params: GetWarehouseParams) -> ActionResult:
    """Read one warehouse in full by id."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    data = await sc.request(ctx, key, "GET", f"/warehouses/{params.warehouse_id}")
    return ActionResult.success(_warehouse_from(data))


def _address_body(a) -> dict:
    return {
        "address_line1": a.line1,
        "city_locality": a.city,
        "state_province": a.state,
        "postal_code": a.postal_code,
        "country_code": a.country,
        "name": a.name,
        "phone": a.phone,
        "company_name": a.company_name,
    }


@chat.function(name="create_warehouse", data_model=Warehouse, description="Create a new warehouse/ship-from location.")
async def create_warehouse(ctx, params: CreateWarehouseParams) -> ActionResult:
    """Create a new warehouse/ship-from location."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    body = {"name": params.name, "origin_address": _address_body(params.origin_address), "is_default": params.is_default}
    data = await sc.request(ctx, key, "POST", "/warehouses", json_body=body)
    return ActionResult.success(_warehouse_from(data), message=f"Warehouse '{params.name}' created.")


@chat.function(name="update_warehouse", data_model=Warehouse, description="Update an existing warehouse's name or default flag.")
async def update_warehouse(ctx, params: UpdateWarehouseParams) -> ActionResult:
    """Update an existing warehouse's name or default flag."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    body: dict = {}
    if params.name:
        body["name"] = params.name
    body["is_default"] = params.is_default
    data = await sc.request(ctx, key, "PUT", f"/warehouses/{params.warehouse_id}", json_body=body)
    return ActionResult.success(_warehouse_from(data), message="Warehouse updated.")


@chat.function(name="delete_warehouse", data_model=DeleteResult, description="Permanently delete a warehouse.")
async def delete_warehouse(ctx, params: DeleteWarehouseParams) -> ActionResult:
    """Permanently delete a warehouse."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    await sc.request(ctx, key, "DELETE", f"/warehouses/{params.warehouse_id}")
    return ActionResult.success(DeleteResult(deleted=True, id=params.warehouse_id), message="Warehouse deleted.")


@chat.function(name="validate_address", data_model=AddressValidationResult, description="Validate a shipping address against carrier address-verification data before creating a label with it.")
async def validate_address(ctx, params: ValidateAddressParams) -> ActionResult:
    """Validate a shipping address against carrier address-verification data before creating a label with it."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    body = [{
        "address_line1": params.line1, "city_locality": params.city,
        "state_province": params.state, "postal_code": params.postal_code,
        "country_code": params.country, "name": params.name,
    }]
    data = await sc.request(ctx, key, "POST", "/addresses/validate", json_body=body)
    first = (data[0] if isinstance(data, list) and data else data) or {}
    matched = first.get("matched_address") or {}
    return ActionResult.success(AddressValidationResult(
        status=first.get("status", ""),
        matched_line1=matched.get("address_line1", ""),
        matched_city=matched.get("city_locality", ""),
        matched_state=matched.get("state_province", ""),
        matched_postal_code=matched.get("postal_code", ""),
        matched_country=matched.get("country_code", ""),
        messages=first.get("messages", []),
    ))


@chat.function(name="get_account_summary", data_model=AccountSummary, description="Value-add report: one-glance ShipStation account health -- carrier/warehouse counts, open batches, recent label volume.")
async def get_account_summary(ctx, params: GetAccountSummaryParams) -> ActionResult:
    """Value-add report: one-glance ShipStation account health -- carrier/warehouse counts, open batches, recent label volume."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    carriers = await sc.request(ctx, key, "GET", "/carriers")
    warehouses = await sc.request(ctx, key, "GET", "/warehouses")
    batches = await sc.request(ctx, key, "GET", "/batches", params={"status": "open", **sc.page_params(1, 1)})
    labels_30 = await sc.request(ctx, key, "GET", "/labels", params=sc.page_params(1, 1))
    return ActionResult.success(AccountSummary(
        carrier_count=len(carriers.get("carriers", [])),
        warehouse_count=len(warehouses.get("warehouses", [])),
        open_batches=batches.get("total", 0) or 0,
        labels_last_7_days=0,
        labels_last_30_days=labels_30.get("total", 0) or 0,
        voided_last_30_days=0,
        detail="Voided/7-day counts require ShipStation's own reporting export; not available via a single V2 call.",
    ))
