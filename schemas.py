"""Pydantic params models + SDL entity contracts for ShipStation Connector.

All params models are module-scope (V17 federal invariant, same rule as
Shopify Connector / Klaviyo Connector's schemas.py).
"""
from __future__ import annotations

from pydantic import BaseModel, Field
from imperal_sdk import sdl


class NoParams(BaseModel):
    """Explicit empty params model -- V17 disallows untyped handlers."""
    pass


# ──────────────────────────────────────────────────────────────────────────
# Connection
# ──────────────────────────────────────────────────────────────────────────


class ConnectShipStationParams(BaseModel):
    api_key: str = Field(
        "",
        description="Your ShipStation API V2 key from Account Settings > API Settings.",
    )
    label: str = Field("", description="Optional friendly name for this connection.")


class ProviderConnection(sdl.Entity):
    id: str = ""
    title: str = ""
    connected: bool = False
    detail: str = ""


class ProviderConnectionList(sdl.Entity):
    items: list[ProviderConnection] = []


class DisconnectShipStationParams(BaseModel):
    connection_id: str = Field(..., description="Connection id from list_connections.")


class DeleteResult(sdl.Entity):
    deleted: bool = False
    id: str = ""


class ConnParams(BaseModel):
    connection_id: str = Field("", description="Connection id from list_connections. Omit to use the only connected account.")


# ──────────────────────────────────────────────────────────────────────────
# Carriers / Warehouses / Package types
# ──────────────────────────────────────────────────────────────────────────


class Carrier(sdl.Entity):
    carrier_id: str = ""
    carrier_code: str = ""
    friendly_name: str = ""
    account_number: str = ""
    requires_funded_amount: bool = False
    balance: float = 0.0
    nickname: str = ""


class CarrierList(sdl.Entity):
    items: list[Carrier] = []


class GetCarrierParams(ConnParams):
    carrier_id: str = Field(..., description="Carrier id from list_carriers.")


class GetCarrierOptionsParams(ConnParams):
    carrier_id: str = Field(..., description="Carrier id from list_carriers.")


class CarrierOption(sdl.Entity):
    name: str = ""
    default_value: str = ""
    description: str = ""
    values: list[str] = []


class CarrierOptionList(sdl.Entity):
    items: list[CarrierOption] = []


class PackageType(sdl.Entity):
    package_id: str = ""
    package_code: str = ""
    name: str = ""
    carrier_id: str = ""
    domestic: bool = True
    international: bool = True
    description: str = ""


class PackageTypeList(sdl.Entity):
    items: list[PackageType] = []


class ListCarrierPackageTypesParams(ConnParams):
    carrier_id: str = Field(..., description="Carrier id from list_carriers.")


class CreatePackageTypeParams(ConnParams):
    name: str = Field(..., description="Name for this custom package type, e.g. 'Small padded mailer'.")
    description: str = Field("", description="Optional description.")
    length: float = Field(0.0, description="Length in the given unit.")
    width: float = Field(0.0, description="Width in the given unit.")
    height: float = Field(0.0, description="Height in the given unit.")
    unit: str = Field("inch", description="Dimension unit: 'inch' or 'centimeter'.")


class UpdatePackageTypeParams(ConnParams):
    package_id: str = Field(..., description="Package type id to update.")
    name: str = Field("", description="New name, omit to leave unchanged.")
    description: str = Field("", description="New description, omit to leave unchanged.")
    length: float = Field(0.0, description="New length, omit (0) to leave unchanged.")
    width: float = Field(0.0, description="New width, omit (0) to leave unchanged.")
    height: float = Field(0.0, description="New height, omit (0) to leave unchanged.")
    unit: str = Field("", description="New dimension unit, omit to leave unchanged.")


class DeletePackageTypeParams(ConnParams):
    package_id: str = Field(..., description="Package type id to permanently delete.")


class Warehouse(sdl.Entity):
    warehouse_id: str = ""
    name: str = ""
    origin_address_city: str = ""
    origin_address_country: str = ""
    is_default: bool = False
    created_at: str = ""


class WarehouseList(sdl.Entity):
    items: list[Warehouse] = []


class GetWarehouseParams(ConnParams):
    warehouse_id: str = Field(..., description="Warehouse id from list_warehouses.")


class AddressInput(BaseModel):
    name: str = Field("", description="Recipient/contact name.")
    company_name: str = Field("", description="Company name, if any.")
    address_line1: str = Field(..., description="Street address line 1.")
    address_line2: str = Field("", description="Street address line 2.")
    city_locality: str = Field(..., description="City.")
    state_province: str = Field(..., description="State or province code.")
    postal_code: str = Field(..., description="Postal/ZIP code.")
    country_code: str = Field(..., description="ISO 3166-1 alpha-2 country code, e.g. 'US'.")
    phone: str = Field("", description="Phone number.")
    address_residential_indicator: str = Field("unknown", description="'yes', 'no', or 'unknown'.")


class CreateWarehouseParams(BaseModel):
    connection_id: str = Field("", description="Connection id from list_connections. Omit to use the only connected account.")
    name: str = Field(..., description="Warehouse display name.")
    origin_name: str = Field("", description="Origin contact name.")
    origin_company_name: str = Field("", description="Origin company name.")
    origin_address_line1: str = Field(..., description="Origin street address line 1.")
    origin_address_line2: str = Field("", description="Origin street address line 2.")
    origin_city_locality: str = Field(..., description="Origin city.")
    origin_state_province: str = Field(..., description="Origin state/province code.")
    origin_postal_code: str = Field(..., description="Origin postal/ZIP code.")
    origin_country_code: str = Field(..., description="Origin ISO 3166-1 alpha-2 country code.")
    origin_phone: str = Field("", description="Origin phone number.")


class UpdateWarehouseParams(ConnParams):
    warehouse_id: str = Field(..., description="Warehouse id to update.")
    name: str = Field("", description="New display name, omit to leave unchanged.")
    origin_address_line1: str = Field("", description="New origin address line 1, omit to leave unchanged.")
    origin_city_locality: str = Field("", description="New origin city, omit to leave unchanged.")
    origin_state_province: str = Field("", description="New origin state/province, omit to leave unchanged.")
    origin_postal_code: str = Field("", description="New origin postal code, omit to leave unchanged.")
    origin_country_code: str = Field("", description="New origin country code, omit to leave unchanged.")


class DeleteWarehouseParams(ConnParams):
    warehouse_id: str = Field(..., description="Warehouse id to permanently delete.")


# ──────────────────────────────────────────────────────────────────────────
# Rates
# ──────────────────────────────────────────────────────────────────────────


class PackageInput(BaseModel):
    weight_value: float = Field(..., description="Package weight value.")
    weight_unit: str = Field("pound", description="Weight unit: 'pound', 'ounce', or 'gram'.")
    length: float = Field(0.0, description="Package length, omit (0) if unknown.")
    width: float = Field(0.0, description="Package width, omit (0) if unknown.")
    height: float = Field(0.0, description="Package height, omit (0) if unknown.")
    size_unit: str = Field("inch", description="Dimension unit: 'inch' or 'centimeter'.")


class CalculateRatesParams(BaseModel):
    connection_id: str = Field("", description="Connection id from list_connections. Omit to use the only connected account.")
    carrier_ids: list[str] = Field(default_factory=list, description="Carrier ids to compare rates from; omit to compare all connected carriers.")
    ship_from_line1: str = Field(..., description="Ship-from street address line 1.")
    ship_from_city: str = Field(..., description="Ship-from city.")
    ship_from_state: str = Field(..., description="Ship-from state/province code.")
    ship_from_postal_code: str = Field(..., description="Ship-from postal/ZIP code.")
    ship_from_country: str = Field(..., description="Ship-from ISO 3166-1 alpha-2 country code.")
    ship_to_line1: str = Field(..., description="Ship-to street address line 1.")
    ship_to_city: str = Field(..., description="Ship-to city.")
    ship_to_state: str = Field(..., description="Ship-to state/province code.")
    ship_to_postal_code: str = Field(..., description="Ship-to postal/ZIP code.")
    ship_to_country: str = Field(..., description="Ship-to ISO 3166-1 alpha-2 country code.")
    ship_to_residential: str = Field("unknown", description="'yes', 'no', or 'unknown'.")
    weight_value: float = Field(..., description="Package weight value.")
    weight_unit: str = Field("pound", description="Weight unit: 'pound', 'ounce', or 'gram'.")
    length: float = Field(0.0, description="Package length, omit (0) if unknown.")
    width: float = Field(0.0, description="Package width, omit (0) if unknown.")
    height: float = Field(0.0, description="Package height, omit (0) if unknown.")
    size_unit: str = Field("inch", description="Dimension unit: 'inch' or 'centimeter'.")
    confirmation: str = Field("none", description="Delivery confirmation: 'none', 'delivery', 'signature', 'adult_signature', 'direct_signature'.")


class Rate(sdl.Entity):
    rate_id: str = ""
    carrier_id: str = ""
    carrier_friendly_name: str = ""
    service_type: str = ""
    service_code: str = ""
    shipping_amount: float = 0.0
    currency: str = "usd"
    delivery_days: int = 0
    estimated_delivery_date: str = ""
    trackable: bool = True


class RateList(sdl.Entity):
    items: list[Rate] = []


class GetShipmentRatesParams(ConnParams):
    shipment_id: str = Field(..., description="Shipment id from list_shipments or create_shipment.")


# ──────────────────────────────────────────────────────────────────────────
# Shipments
# ──────────────────────────────────────────────────────────────────────────


class CreateShipmentParams(BaseModel):
    connection_id: str = Field("", description="Connection id from list_connections. Omit to use the only connected account.")
    carrier_id: str = Field(..., description="Carrier id from list_carriers.")
    service_code: str = Field(..., description="Carrier service code, e.g. 'usps_priority_mail'.")
    ship_from_line1: str = Field(..., description="Ship-from street address line 1.")
    ship_from_city: str = Field(..., description="Ship-from city.")
    ship_from_state: str = Field(..., description="Ship-from state/province code.")
    ship_from_postal_code: str = Field(..., description="Ship-from postal/ZIP code.")
    ship_from_country: str = Field(..., description="Ship-from ISO 3166-1 alpha-2 country code.")
    ship_from_name: str = Field("", description="Ship-from contact name.")
    ship_to_name: str = Field(..., description="Ship-to recipient name.")
    ship_to_line1: str = Field(..., description="Ship-to street address line 1.")
    ship_to_city: str = Field(..., description="Ship-to city.")
    ship_to_state: str = Field(..., description="Ship-to state/province code.")
    ship_to_postal_code: str = Field(..., description="Ship-to postal/ZIP code.")
    ship_to_country: str = Field(..., description="Ship-to ISO 3166-1 alpha-2 country code.")
    ship_to_phone: str = Field("", description="Ship-to phone number.")
    weight_value: float = Field(..., description="Package weight value.")
    weight_unit: str = Field("pound", description="Weight unit: 'pound', 'ounce', or 'gram'.")
    ship_date: str = Field("", description="Ship date, ISO 8601 (YYYY-MM-DD); omit to use today.")
    warehouse_id: str = Field("", description="Warehouse id to ship from, omit to use the default warehouse.")


class UpdateShipmentParams(ConnParams):
    shipment_id: str = Field(..., description="Shipment id to update.")
    carrier_id: str = Field("", description="New carrier id, omit to leave unchanged.")
    service_code: str = Field("", description="New service code, omit to leave unchanged.")
    ship_date: str = Field("", description="New ship date, omit to leave unchanged.")
    weight_value: float = Field(0.0, description="New weight value, omit (0) to leave unchanged.")
    weight_unit: str = Field("", description="New weight unit, omit to leave unchanged.")


class CancelShipmentParams(ConnParams):
    shipment_id: str = Field(..., description="Shipment id to cancel.")


class ListShipmentsParams(ConnParams):
    page: int = Field(1, ge=1)
    page_size: int = Field(25, ge=1, le=500)
    shipment_status: str = Field("", description="Filter: 'pending', 'processing', 'label_purchased', 'cancelled', omit for all.")
    carrier_id: str = Field("", description="Filter by carrier id, omit for all.")
    tag: str = Field("", description="Filter by tag name, omit for all.")


class GetShipmentParams(ConnParams):
    shipment_id: str = Field(..., description="Shipment id from list_shipments.")


class Shipment(sdl.Entity):
    shipment_id: str = ""
    carrier_id: str = ""
    service_code: str = ""
    ship_date: str = ""
    shipment_status: str = ""
    ship_to_name: str = ""
    ship_to_city: str = ""
    ship_to_country: str = ""
    tracking_number: str = ""
    tags: list[str] = []


class ShipmentList(sdl.Entity):
    items: list[Shipment] = []


class TagShipmentParams(ConnParams):
    shipment_id: str = Field(..., description="Shipment id to tag.")
    tag_name: str = Field(..., description="Tag name to attach, from list_tags or a new one.")


class UntagShipmentParams(ConnParams):
    shipment_id: str = Field(..., description="Shipment id to untag.")
    tag_name: str = Field(..., description="Tag name to remove.")


# ──────────────────────────────────────────────────────────────────────────
# Tags
# ──────────────────────────────────────────────────────────────────────────


class Tag(sdl.Entity):
    name: str = ""
    color: str = ""


class TagList(sdl.Entity):
    items: list[Tag] = []


class CreateTagParams(ConnParams):
    name: str = Field(..., description="Tag name to create.")
    color: str = Field("", description="Optional hex color for the tag, e.g. '#FF0000'.")


# ──────────────────────────────────────────────────────────────────────────
# Labels
# ──────────────────────────────────────────────────────────────────────────


class CreateLabelFromShipmentParams(ConnParams):
    shipment_id: str = Field(..., description="Shipment id to purchase a label for.")
    label_format: str = Field("pdf", description="'pdf', 'png', or 'zpl'.")
    label_layout: str = Field("4x6", description="Label size, e.g. '4x6' or 'letter'.")
    label_download_type: str = Field("url", description="'url' or 'inline' (base64).")


class CreateLabelFromRateParams(ConnParams):
    rate_id: str = Field(..., description="Rate id from calculate_rates.")
    label_format: str = Field("pdf", description="'pdf', 'png', or 'zpl'.")
    label_layout: str = Field("4x6", description="Label size, e.g. '4x6' or 'letter'.")
    label_download_type: str = Field("url", description="'url' or 'inline' (base64).")


class CreateReturnLabelParams(ConnParams):
    outbound_label_id: str = Field(..., description="The original outbound label id this return label is for.")
    label_format: str = Field("pdf", description="'pdf', 'png', or 'zpl'.")
    label_layout: str = Field("4x6", description="Label size, e.g. '4x6' or 'letter'.")


class Label(sdl.Entity):
    label_id: str = ""
    status: str = ""
    shipment_id: str = ""
    carrier_id: str = ""
    tracking_number: str = ""
    label_download_url: str = ""
    label_format: str = ""
    voided: bool = False
    is_return_label: bool = False
    shipment_cost: float = 0.0
    created_at: str = ""


class LabelList(sdl.Entity):
    items: list[Label] = []


class ListLabelsParams(ConnParams):
    page: int = Field(1, ge=1)
    page_size: int = Field(25, ge=1, le=500)
    shipment_id: str = Field("", description="Filter by shipment id, omit for all.")
    carrier_id: str = Field("", description="Filter by carrier id, omit for all.")
    batch_id: str = Field("", description="Filter by batch id, omit for all.")


class GetLabelParams(ConnParams):
    label_id: str = Field(..., description="Label id from list_labels.")


class VoidLabelParams(ConnParams):
    label_id: str = Field(..., description="Label id to void. Only unshipped/unused labels can be voided.")


class GetLabelDownloadParams(ConnParams):
    label_id: str = Field(..., description="Label id from list_labels.")


# ──────────────────────────────────────────────────────────────────────────
# Batches
# ──────────────────────────────────────────────────────────────────────────


class CreateBatchParams(BaseModel):
    connection_id: str = Field("", description="Connection id from list_connections. Omit to use the only connected account.")
    shipment_ids: list[str] = Field(default_factory=list, description="Shipment ids to include in this batch.")
    rate_ids: list[str] = Field(default_factory=list, description="Rate ids to include instead of shipment ids, if purchasing from pre-fetched rates.")


class Batch(sdl.Entity):
    batch_id: str = ""
    status: str = ""
    count: int = 0
    completed_count: int = 0
    errors_count: int = 0
    created_at: str = ""


class BatchList(sdl.Entity):
    items: list[Batch] = []


class GetBatchParams(ConnParams):
    batch_id: str = Field(..., description="Batch id from list_batches.")


class ListBatchesParams(ConnParams):
    page: int = Field(1, ge=1)
    page_size: int = Field(25, ge=1, le=500)
    status: str = Field("", description="Filter by status, omit for all.")


class AddToBatchParams(ConnParams):
    batch_id: str = Field(..., description="Batch id to add to.")
    shipment_ids: list[str] = Field(default_factory=list, description="Shipment ids to add.")


class RemoveFromBatchParams(ConnParams):
    batch_id: str = Field(..., description="Batch id to remove from.")
    shipment_ids: list[str] = Field(default_factory=list, description="Shipment ids to remove.")


class ProcessBatchParams(ConnParams):
    batch_id: str = Field(..., description="Batch id to process (purchase all labels in the batch).")


class DeleteBatchParams(ConnParams):
    batch_id: str = Field(..., description="Batch id to permanently delete.")


# ──────────────────────────────────────────────────────────────────────────
# Manifests
# ──────────────────────────────────────────────────────────────────────────


class CreateManifestParams(ConnParams):
    warehouse_id: str = Field("", description="Warehouse id to manifest shipments from; omit if using ship_date+carrier_id filtering instead.")
    carrier_id: str = Field(..., description="Carrier id to create the manifest for.")
    ship_date: str = Field("", description="ISO date (YYYY-MM-DD) of shipments to include; omit for today.")
    shipment_ids: list[str] = Field(default_factory=list, description="Explicit shipment ids to manifest; omit to manifest by ship_date/warehouse instead.")


class Manifest(sdl.Entity):
    manifest_id: str = ""
    carrier_id: str = ""
    ship_date: str = ""
    warehouse_id: str = ""
    submitted_at: str = ""
    manifest_download_url: str = ""
    shipments_count: int = 0


class ManifestList(sdl.Entity):
    items: list[Manifest] = []


class ListManifestsParams(ConnParams):
    page: int = Field(1, ge=1)
    page_size: int = Field(25, ge=1, le=500)
    warehouse_id: str = Field("", description="Filter by warehouse id, omit for all.")


class GetManifestParams(ConnParams):
    manifest_id: str = Field(..., description="Manifest id to read.")


# ──────────────────────────────────────────────────────────────────────────
# Pickups
# ──────────────────────────────────────────────────────────────────────────


class SchedulePickupParams(ConnParams):
    carrier_id: str = Field(..., description="Carrier id to schedule the pickup with.")
    warehouse_id: str = Field(..., description="Warehouse id the pickup happens at.")
    pickup_date: str = Field(..., description="ISO date (YYYY-MM-DD) for the pickup.")
    ready_time: str = Field(..., description="Time of day the shipment(s) will be ready, HH:MM (24h).")
    close_time: str = Field(..., description="Time of day the location closes, HH:MM (24h).")
    shipment_ids: list[str] = Field(default_factory=list, description="Shipment ids to include in this pickup; omit to let the carrier pick up everything manifested for that date.")


class Pickup(sdl.Entity):
    pickup_id: str = ""
    carrier_id: str = ""
    warehouse_id: str = ""
    pickup_date: str = ""
    confirmation_number: str = ""
    status: str = ""


class PickupList(sdl.Entity):
    items: list[Pickup] = []


class ListPickupsParams(ConnParams):
    page: int = Field(1, ge=1)
    page_size: int = Field(25, ge=1, le=500)


class GetPickupParams(ConnParams):
    pickup_id: str = Field(..., description="Pickup id to read.")


class CancelPickupParams(ConnParams):
    pickup_id: str = Field(..., description="Pickup id to cancel.")


# ──────────────────────────────────────────────────────────────────────────
# Products
# ──────────────────────────────────────────────────────────────────────────


class Product(sdl.Entity):
    product_id: str = ""
    sku: str = ""
    name: str = ""
    weight_value: float = 0.0
    weight_unit: str = ""
    active: bool = True
    created_at: str = ""


class ProductList(sdl.Entity):
    items: list[Product] = []


class ListProductsParams(ConnParams):
    page: int = Field(1, ge=1)
    page_size: int = Field(25, ge=1, le=500)
    sku: str = Field("", description="Filter by exact SKU, omit for all.")


class GetProductParams(ConnParams):
    product_id: str = Field(..., description="Product id to read.")


class CreateProductParams(ConnParams):
    sku: str = Field(..., description="Product SKU.")
    name: str = Field(..., description="Product name.")
    weight_value: float = Field(0.0, description="Default package weight for this product, omit (0) if unknown.")
    weight_unit: str = Field("pound", description="Weight unit: 'pound', 'ounce', or 'gram'.")


class UpdateProductParams(ConnParams):
    product_id: str = Field(..., description="Product id to update.")
    name: str = Field("", description="New name, omit to leave unchanged.")
    weight_value: float = Field(0.0, description="New default weight, omit (0) to leave unchanged.")
    weight_unit: str = Field("", description="New weight unit, omit to leave unchanged.")
    active: bool = Field(True, description="Whether the product is active.")


# ──────────────────────────────────────────────────────────────────────────
# Users
# ──────────────────────────────────────────────────────────────────────────


class ShipStationUser(sdl.Entity):
    user_id: str = ""
    username: str = ""
    email: str = ""
    created_at: str = ""


class ShipStationUserList(sdl.Entity):
    items: list[ShipStationUser] = []


# ──────────────────────────────────────────────────────────────────────────
# Address validation
# ──────────────────────────────────────────────────────────────────────────


class ValidateAddressParams(ConnParams):
    line1: str = Field(..., description="Street address line 1.")
    city: str = Field(..., description="City.")
    state: str = Field("", description="State/province code, required for US/CA addresses.")
    postal_code: str = Field(..., description="Postal/ZIP code.")
    country: str = Field(..., description="ISO 3166-1 alpha-2 country code.")
    name: str = Field("", description="Recipient/contact name, optional but improves match quality.")


class AddressValidationResult(sdl.Entity):
    status: str = ""
    matched_line1: str = ""
    matched_city: str = ""
    matched_state: str = ""
    matched_postal_code: str = ""
    matched_country: str = ""
    messages: list[str] = []


# ──────────────────────────────────────────────────────────────────────────
# Tracking
# ──────────────────────────────────────────────────────────────────────────


class TrackShipmentParams(ConnParams):
    carrier_id: str = Field(..., description="Carrier id the tracking number belongs to.")
    tracking_number: str = Field(..., description="Tracking number to look up.")


class TrackingEvent(sdl.Entity):
    occurred_at: str = ""
    description: str = ""
    city: str = ""
    state: str = ""
    country: str = ""


class TrackingResult(sdl.Entity):
    status_code: str = ""
    status_description: str = ""
    carrier_id: str = ""
    tracking_number: str = ""
    estimated_delivery: str = ""
    events: list[TrackingEvent] = []


class StopTrackingParams(ConnParams):
    carrier_id: str = Field(..., description="Carrier id the tracking number belongs to.")
    tracking_number: str = Field(..., description="Tracking number to stop tracking.")


# ──────────────────────────────────────────────────────────────────────────
# Webhooks
# ──────────────────────────────────────────────────────────────────────────


class CreateWebhookParams(ConnParams):
    event_type: str = Field(
        ...,
        description="Event to subscribe to, e.g. 'track', 'batch', 'manifest', 'sales_order', 'fulfillment_shipped', 'fulfillment_rejected'.",
    )
    url: str = Field(..., description="HTTPS URL ShipStation will POST the event payload to.")


class Webhook(sdl.Entity):
    webhook_id: str = ""
    event_type: str = ""
    url: str = ""
    is_active: bool = True
    created_at: str = ""


class WebhookList(sdl.Entity):
    items: list[Webhook] = []


class GetWebhookParams(ConnParams):
    webhook_id: str = Field(..., description="Webhook id from list_webhooks.")


class DeleteWebhookParams(ConnParams):
    webhook_id: str = Field(..., description="Webhook id to permanently remove.")


# ──────────────────────────────────────────────────────────────────────────
# Store summary (value-add report, same shape as Shopify's get_store_summary)
# ──────────────────────────────────────────────────────────────────────────


class GetAccountSummaryParams(ConnParams):
    pass


class AccountSummary(sdl.Entity):
    carrier_count: int = 0
    warehouse_count: int = 0
    open_batches: int = 0
    labels_last_7_days: int = 0
    labels_last_30_days: int = 0
    voided_last_30_days: int = 0
    detail: str = ""
