"""Products (catalog), account users, and the store-summary value-add report."""
from __future__ import annotations

from imperal_sdk import ActionResult

import shipstation_client as sc
from accounts import _get_key
from app import ext, chat
from schemas import (
    NoParams,
    Product, ProductList, ListProductsParams, GetProductParams,
    CreateProductParams, UpdateProductParams,
    ShipStationUser, ShipStationUserList,
    GetAccountSummaryParams, AccountSummary,
)


def _product_from(d: dict) -> Product:
    w = d.get("weight") or {}
    return Product(
        product_id=str(d.get("product_id", "")),
        sku=d.get("sku", ""),
        name=d.get("product_name", d.get("name", "")),
        weight_value=float(w.get("value", 0.0) or 0.0),
        weight_unit=w.get("unit", ""),
        active=d.get("active", True),
        created_at=d.get("created_at", ""),
    )


@chat.function(name="list_products", event="shipstation-connector.list_products", action_type="read", data_model=ProductList, description="List products in ShipStation's catalog, optionally filtered by SKU.")
async def list_products(ctx, params: ListProductsParams) -> ActionResult:
    """List products in ShipStation's catalog, optionally filtered by SKU."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    q = sc.page_params(params.page, params.page_size)
    if params.sku:
        q["sku"] = params.sku
    data = await sc.request(ctx, key, "GET", "/products", params=q)
    items = [_product_from(p) for p in data.get("products", [])]
    return ActionResult.success(ProductList(items=items))


@chat.function(name="get_product", event="shipstation-connector.get_product", action_type="read", data_model=Product, description="Read one catalog product in full.")
async def get_product(ctx, params: GetProductParams) -> ActionResult:
    """Read one catalog product in full."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    data = await sc.request(ctx, key, "GET", "/products/" + params.product_id)
    return ActionResult.success(_product_from(data))


@chat.function(name="create_product", event="shipstation-connector.create_product", effects=['create:product'], action_type="write", data_model=Product, description="Create a new product in ShipStation's catalog with a default weight.")
async def create_product(ctx, params: CreateProductParams) -> ActionResult:
    """Create a new product in ShipStation's catalog with a default weight."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    body = {"sku": params.sku, "product_name": params.name}
    if params.weight_value:
        body["weight"] = {"value": params.weight_value, "unit": params.weight_unit}
    data = await sc.request(ctx, key, "POST", "/products", json=body)
    return ActionResult.success(_product_from(data))


@chat.function(name="update_product", event="shipstation-connector.update_product", effects=['update:product'], action_type="write", data_model=Product, description="Update selected fields of an existing catalog product. Only given fields change.")
async def update_product(ctx, params: UpdateProductParams) -> ActionResult:
    """Update selected fields of an existing catalog product. Only given fields change."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    body: dict = {}
    if params.name:
        body["product_name"] = params.name
    if params.weight_value:
        body["weight"] = {"value": params.weight_value, "unit": params.weight_unit or "pound"}
    body["active"] = params.active
    data = await sc.request(ctx, key, "PUT", "/products/" + params.product_id, json=body)
    return ActionResult.success(_product_from(data))


@chat.function(name="list_shipstation_users", event="shipstation-connector.list_shipstation_users", action_type="read", data_model=ShipStationUserList, description="List the users registered on this ShipStation account.")
async def list_shipstation_users(ctx, params: NoParams) -> ActionResult:
    """List the users registered on this ShipStation account."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    data = await sc.request(ctx, key, "GET", "/users")
    items = [
        ShipStationUser(
            user_id=u.get("user_id", ""),
            username=u.get("username", ""),
            email=u.get("email", ""),
            created_at=u.get("created_at", ""),
        )
        for u in data.get("users", [])
    ]
    return ActionResult.success(ShipStationUserList(items=items))


@chat.function(
    name="get_account_summary", event="shipstation-connector.get_account_summary", action_type="read", data_model=AccountSummary,
    description=(
        "Value-add report: one-glance ShipStation account health snapshot -- "
        "carrier count and combined balance, open shipments, pending "
        "batches, and recent label activity."
    ),
)
async def get_account_summary(ctx, params: GetAccountSummaryParams) -> ActionResult:
    """Value-add report: one-glance ShipStation account health snapshot -- carrier count and combined balance, open shipments, pending batches, and recent label activity."""
    key = await _get_key(ctx)
    if not key:
        return ActionResult.error("Connect ShipStation first.")
    carriers = (await sc.request(ctx, key, "GET", "/carriers")).get("carriers", [])
    shipments = await sc.request(ctx, key, "GET", "/shipments", params={"page": 1, "page_size": 1, "shipment_status": "pending"})
    batches = await sc.request(ctx, key, "GET", "/batches", params={"page": 1, "page_size": 1, "status": "open"})
    labels = await sc.request(ctx, key, "GET", "/labels", params={"page": 1, "page_size": 1})
    total_balance = sum(float(c.get("balance") or 0.0) for c in carriers)
    return ActionResult.success(AccountSummary(
        carrier_count=len(carriers),
        total_carrier_balance=total_balance,
        pending_shipments=int(shipments.get("total", 0) or 0),
        open_batches=int(batches.get("total", 0) or 0),
        labels_total=int(labels.get("total", 0) or 0),
    ))
