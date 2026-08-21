"""Extension declaration, secrets, lifecycle hooks.

WHY BYOK (bring-your-own-key), SAME REASONING AS Shopify Connector /
Klaviyo Connector. The user's ShipStation account is THEIR OWN account,
with their own carrier connections and their own billing for label
postage -- Imperal cannot and should not broker access to someone else's
shipping account centrally.

WHY A SINGLE SECRET (api_key), NOT client_id/client_secret, NOT OAUTH.

ShipStation API V2 authenticates every request with a static `API-Key`
header (docs.shipstation.com/authentication, confirmed during Discovery
2026-08-21) -- there is no OAuth authorization-code flow for V2 at all.
The key is generated once in the user's own account (Account Settings >
API Settings) and is shown only at generation time. This is the simplest
BYOK shape in the whole portfolio: one static key, no rotation dance, no
redirect flow to build.

WHY THIS CONNECTOR TARGETS API V2, NOT V1, NOT ShipEngine -- see
`CONNECTOR_DISCOVERY.md` \u00a72 for the full three-surface disambiguation.
V2 is the actively developed surface and the one that exposes batches,
manifests, pickups and return labels that V1 never had.

WHY `write_mode="both"`, SAME REASONING AS Shopify/Klaviyo/MuleSoft.

Declaring `write_mode="user"` would mean only the platform's generic
Secrets screen could write this -- leaving a first-time user with no
in-app screen explaining what a ShipStation V2 API key even is, where to
get one, or whether what they pasted actually works. `write_mode="both"`
keeps the platform Secrets screen working AND lets this extension's own
`connect_shipstation` validate the key against ShipStation's API *before*
writing it.

WHY NO SANDBOX MODE.

ShipStation V2 has no official sandbox/test environment (confirmed
2026-08-21) -- every call runs against the user's live account. Carrier
label purchases have a REAL POSTAGE COST. This connector therefore treats
every label-purchasing tool (`create_label_from_shipment`,
`create_label_from_rate`, `create_return_label`, batch label processing)
as a destructive-adjacent write with an explicit cost warning in its own
description, and the settings panel surfaces the same warning up front --
same posture as billing/payment tools elsewhere in this portfolio.
"""

from imperal_sdk import Extension, ChatExtension

ext = Extension(
    "shipstation-connector",
    version="0.1.0",
    display_name="ShipStation",
    description=(
        "Multi-carrier shipping and fulfillment via your own ShipStation "
        "account (API V2) -- compare rates across carriers, create and "
        "manage shipments, purchase/void/download labels (including "
        "multi-package and return labels), batch-process labels, generate "
        "customs manifests, schedule carrier pickups, manage warehouses, "
        "custom package types, products, tags, and webhooks. "
        "Bring-your-own-account (BYOK): connect your own ShipStation V2 "
        "API key, every call runs against your own account, your own "
        "carriers, and your own postage balance."
    ),
    icon="icon.svg",
    actions_explicit=True,
    capabilities=["shipstation:read", "shipstation:write"],
)

chat = ChatExtension(
    ext,
    tool_name="shipstation-connector",
    description=(
        "Rates, shipments, labels, batches, manifests, pickups, carriers, "
        "warehouses, package types, products, tags and webhooks via your "
        "own ShipStation account"
    ),
)

ext.secret(
    name="shipstation_api_key",
    description=(
        "Your ShipStation API V2 key, from Account Settings > API Settings "
        "> API Keys (generate a V2 key -- shown only once at creation, so "
        "save it immediately). Requires a ShipStation plan with API/"
        "shipping access."
    ),
    write_mode="both",
)


@ext.health_check
async def health_check(ctx) -> bool:
    """Basic liveness check -- confirms the secrets surface is reachable.

    Deliberately does NOT call out to ShipStation itself: a health check
    should verify OUR OWN plumbing works, not spend the user's rate-limit
    budget (200 req/min account-wide, shared with real shipping activity)
    on every kernel liveness probe. Whether the saved key is still valid is
    what connect_shipstation / list_connections are for.
    """
    await ctx.secrets.get("shipstation_api_key")


@ext.on_install
async def on_install(ctx):
    """Make the first step traceable -- and knowable.

    A ShipStation API key cannot be provisioned for the user, so a fresh
    install is inert by design until one is pasted via
    connect_shipstation. Recording that at install time means "nothing
    works yet" shows up as an expected state in the audit log rather than
    looking like a broken deployment -- same reasoning as Klaviyo
    Connector's on_install.
    """
    await ctx.log(
        "ShipStation Connector installed -- awaiting an API V2 key; "
        "call connect_shipstation to activate. No sandbox exists for this "
        "API -- label purchases carry a real postage cost from the first "
        "call."
    )
