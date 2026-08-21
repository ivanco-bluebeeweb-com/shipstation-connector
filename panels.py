"""Panel UI -- connections list/connect form + a live carrier balance
snapshot.

SIDEBAR CONTENT -- NO CARDS ANYWHERE, per ~/UI_INTERFACE_STANDARD.md's
"left sidebar, no decorated cards" rule (same convention as Shopify
Connector's / MuleSoft Connector's panels.py). Every section is a plain
ui.Stack, stretched full-width, sections separated by ui.Divider() -- no
Card border/background/shadow anywhere in this slot. Disconnect lives
only in the "App settings" screen (panels_settings.py). The one secondary
"App settings" button is always the LAST element at the bottom of the
sidebar.

WHY A SINGLE PASSWORD FIELD, NOT A FULL FORM LIKE Shopify's shop+token.

ShipStation V2's API key is self-sufficient -- it identifies the account
by itself (no separate "shop domain" concept to pair it with), so the
connect form only ever needs the one field plus an optional label.
"""
from __future__ import annotations

from imperal_sdk import ui

from app import ext
from accounts import _get_key, _load_connections
import shipstation_client as sc


def _settings_button() -> ui.UINode:
    """The one required secondary entry point into the settings screen --
    always the last element at the bottom of the sidebar."""
    return ui.Button(
        "App settings", variant="secondary", size="sm", full_width=True,
        on_click=ui.Call("__panel__shipstation_settings"),
    )


def _connection_row(c: dict) -> ui.UINode:
    label = c.get("title") or c.get("detail", "")
    return ui.Stack(direction="v", gap=1, children=[
        ui.Text(label, variant="body"),
        ui.Text(c.get("detail", ""), variant="caption"),
    ])


def _connections_section(connections: list[dict]) -> ui.UINode:
    if not connections:
        return ui.Text("No ShipStation account connected yet.", variant="caption")
    children: list[ui.UINode] = []
    for i, c in enumerate(connections):
        if i > 0:
            children.append(ui.Divider())
        children.append(_connection_row(c))
    return ui.Stack(direction="v", gap=2, children=children)


def _connect_section() -> ui.UINode:
    """Plain content, no Card wrapper, stretched full-width per
    UI_INTERFACE_STANDARD.md. No intro walkthrough text here -- the API
    key location/setup steps live ONLY in shipstation_connect_help's
    modal (button below opens it); repeating them here would duplicate
    that instruction."""
    return ui.Stack(direction="v", gap=3, align="stretch", children=[
        ui.Button("How do I set this up?", variant="ghost", size="sm",
                  icon="HelpCircle",
                  on_click=ui.Call("__panel__shipstation_connect_help")),
        ui.Form(
            action="connect_shipstation",
            submit_label="Verify and connect",
            children=[
                ui.Stack(direction="v", gap=1, align="stretch", children=[
                    ui.Text("API key", variant="caption"),
                    ui.Password(param_name="api_key",
                                placeholder="Paste your ShipStation API V2 key"),
                ]),
                ui.Stack(direction="v", gap=1, align="stretch", children=[
                    ui.Text("Label (optional)", variant="caption"),
                    ui.Input(param_name="label", placeholder="e.g. Main warehouse account"),
                ]),
            ],
        ),
    ])


@ext.panel("shipstation_connect", slot="left", title="ShipStation", icon="📦",
           default_width=320, min_width=260, max_width=420)
async def shipstation_connect_panel(ctx, **kwargs) -> object:
    connections = await _load_connections(ctx)
    connected = bool(connections)

    header = ui.Header(text="ShipStation", level=2,
                        subtitle="Compare carrier rates, buy labels, and manage shipments from Imperal")

    if not connected:
        return ui.Stack(direction="v", gap=4, align="stretch", children=[
            header,
            _connect_section(),
            ui.Divider(),
            _settings_button(),
        ])

    summary_rows: list[ui.UINode] = []
    try:
        key = await _get_key(ctx)
        if key:
            data = await sc.request(ctx, key, "GET", "/carriers")
            carriers = data.get("carriers", [])
            summary_rows.append(ui.Text(f"{len(carriers)} carrier account(s) connected", variant="caption"))
    except Exception:
        pass

    return ui.Stack(direction="v", gap=4, align="stretch", children=[
        header,
        ui.Text("Connection", variant="subtitle"),
        _connections_section(connections),
        *summary_rows,
        ui.Divider(),
        _settings_button(),
    ])


@ext.panel("shipstation_connect_help", slot="center",
           title="How to connect ShipStation", center_overlay=True)
async def shipstation_connect_help(ctx, **kwargs) -> object:
    content = ui.Stack(direction="v", gap=3, children=[
        ui.Text("1. Log into your ShipStation account at ship.shipstation.com."),
        ui.Text("2. Go to Account Settings > API Settings."),
        ui.Text("3. Under \"API Keys\", generate a new API V2 key (or copy an existing one)."),
        ui.Text("4. Copy the key immediately -- ShipStation only shows the full value once."),
        ui.Text("5. Paste it into the form on the left."),
        ui.Divider(),
        ui.Alert(
            title="No sandbox -- every action is real",
            message=(
                "ShipStation API V2 has no test/sandbox mode. Rate lookups "
                "are free, but creating a label spends real carrier postage "
                "funds from your ShipStation balance immediately."
            ),
            type="warning",
        ),
        ui.Divider(),
        ui.Alert(
            title="Your own account, your own key",
            message=(
                "Imperal never sees or stores your ShipStation login. The "
                "API key you paste here talks directly to your account, "
                "scoped to your own carriers and shipments."
            ),
            type="info",
        ),
        ui.Divider(),
        ui.Link(
            label="Open ShipStation's official API authentication guide",
            href="https://docs.shipstation.com/authentication",
        ),
    ])
    return ui.Dialog(
        title="How to connect ShipStation",
        content=content,
        confirm_label="",
        cancel_label="Close",
    )


@ext.panel("shipstation_center", slot="center", title="ShipStation", icon="📦", center_overlay=True)
async def shipstation_center_panel(ctx, **kwargs) -> object:
    """Base center panel -- per UI_INTERFACE_STANDARD.md. This app has no
    list/detail content of its own to show in the center by default
    (everything lives in the sidebar). MUST carry center_overlay=True: a
    plain slot="center" panel is registered but never fetched at session
    init without it. Text is the shared canonical wording -- must stay
    identical across every app in this situation."""
    return ui.Empty(
        message="Nothing to show here -- this app is managed entirely from the sidebar.",
        icon="👈",
    )
