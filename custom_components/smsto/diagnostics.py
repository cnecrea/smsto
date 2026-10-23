"""Diagnostic pentru SMS.to — fără cheia API și cu numerele de telefon mascate."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import SmsToConfigEntry
from .const import CONF_API_KEY
from .coordinator import summarize_messages, summarize_usage
from .api import mask_phone


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: SmsToConfigEntry) -> dict[str, Any]:
    coordinator = entry.runtime_data.coordinator
    data = coordinator.data or {}
    last = data.get("last_message") or {}
    return {
        "entry": async_redact_data(dict(entry.data), {CONF_API_KEY}),
        "last_update_success": coordinator.last_update_success,
        "balance": data.get("balance"),
        "estimate": data.get("estimate"),
        "cost_number": mask_phone(data.get("cost_number")),
        "usage_current": summarize_usage(data.get("usage_current")),
        "usage_previous": summarize_usage(data.get("usage_previous")),
        "messages_30_days": summarize_messages(data.get("messages")),
        "last_message": {
            k: (mask_phone(v) if k == "to" else v)
            for k, v in last.items()
            if k not in ("message", "callback_url")
        },
        "last_campaign": {
            k: v for k, v in (data.get("last_campaign") or {}).items() if k not in ("message", "callback_url")
        },
        "campaigns_total": data.get("campaigns_total"),
        "inbound_count": len(data.get("inbound") or []),
        "optouts_count": len(data.get("optouts") or []),
    }
