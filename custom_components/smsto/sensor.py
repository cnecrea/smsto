"""Senzorii SMS.to: sold, SMS-uri disponibile, cost, mesaje și campanii."""

from __future__ import annotations

import logging
import math
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import SmsToConfigEntry
from .api import mask_phone, sender_label
from .const import CAMPAIGN_STATUSES, CONF_SENDER_ID, DOMAIN, MESSAGE_STATUSES, NAME
from .coordinator import (
    SmsToCoordinator,
    campaign_status,
    message_status,
    summarize_messages,
    summarize_usage,
)

_LOGGER = logging.getLogger(__name__)


# ───────────────────────────── Funcții ajutătoare ─────────────────────────────


def _clean(attrs: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in attrs.items() if v is not None}


def _currency(data: dict[str, Any]) -> str | None:
    balance = data.get("balance")
    return balance[1] if balance else None


def _balance(data: dict[str, Any]) -> float | None:
    balance = data.get("balance")
    return round(balance[0], 4) if balance else None


def _cost_per_sms(data: dict[str, Any]) -> float | None:
    estimate = data.get("estimate") or {}
    cost = estimate.get("estimated_cost")
    if not cost:
        return None
    return round(float(cost) / max(int(estimate.get("sms_count") or 1), 1), 4)


def _available_sms(data: dict[str, Any]) -> int | None:
    balance, cost = _balance(data), _cost_per_sms(data)
    if balance is None or not cost:
        return None
    return max(math.floor(balance / cost), 0)


def _start_of_month(data: dict[str, Any]) -> datetime:
    month = data.get("month") or dt_util.now().strftime("%Y-%m")
    year, mon = (int(x) for x in month.split("-"))
    return dt_util.start_of_local_day(datetime(year, mon, 1))


def _usage(data: dict[str, Any], key: str) -> dict[str, Any] | None:
    return summarize_usage(data.get(key))


def _last_message_attrs(data: dict[str, Any]) -> dict[str, Any]:
    msg = data.get("last_message") or {}
    if not msg:
        return {}
    status = message_status(msg.get("status"))
    return _clean(
        {
            "sent_at": msg.get("sent_at") or msg.get("created_at"),
            "recipient": mask_phone(msg.get("to")),
            "cost": msg.get("cost"),
            "channel": str(msg.get("type") or "sms").lower(),
            "parts": msg.get("sms_count"),
            "source": "api" if msg.get("is_api") else "web",
            "failed_reason": msg.get("failed_reason") or None,
            "raw_status": msg.get("status") if status == "unknown" else None,
        }
    )


def _available_attrs(data: dict[str, Any]) -> dict[str, Any]:
    estimate = data.get("estimate") or {}
    return _clean(
        {
            "cost_per_sms": _cost_per_sms(data),
            "parts_per_message": estimate.get("sms_count"),
            "calculated_for": mask_phone(data.get("cost_number")),
            "balance": _balance(data),
        }
    )


def _sent_month_attrs(data: dict[str, Any]) -> dict[str, Any]:
    current = _usage(data, "usage_current") or {}
    previous = _usage(data, "usage_previous") or {}
    return _clean(
        {
            "month": data.get("month"),
            "by_channel": current.get("by_channel") or None,
            "by_country": current.get("by_country") or None,
            "previous_month_count": previous.get("count"),
            "previous_month_cost": previous.get("cost"),
        }
    )


def _messages_attrs(data: dict[str, Any]) -> dict[str, Any]:
    summary = summarize_messages(data.get("messages")) or {}
    if not summary:
        return {}
    return _clean(
        {
            "delivered": summary["delivered"],
            "failed": summary["failed"],
            "pending": summary["pending"],
            "delivery_rate": summary["delivery_rate"],
            "cost": summary["cost"],
            "parts": summary["parts"],
            "via_api": summary["via_api"],
            "via_web": summary["via_web"],
            # API-ul nu documentează paginarea: lista poate fi incompletă
            "list_truncated": True if summary["limit_reached"] else None,
        }
    )


def _campaign_attrs(data: dict[str, Any]) -> dict[str, Any]:
    campaign = data.get("last_campaign") or {}
    attrs: dict[str, Any] = {"total_campaigns": data.get("campaigns_total")}
    if campaign:
        attrs.update(
            {
                "created_at": campaign.get("created_at"),
                "sent": campaign.get("sent_messages"),
                "delivered": campaign.get("delivered_messages"),
                "failed": campaign.get("failed_messages"),
                "pending": campaign.get("pending_messages"),
                "cost": campaign.get("client_total_cost"),
            }
        )
    return _clean(attrs)


def _inbound_attrs(data: dict[str, Any]) -> dict[str, Any]:
    inbound = data.get("inbound") or []
    if not inbound:
        return {}
    last = inbound[-1]
    return _clean({"last_from": mask_phone(last.get("from")), "last_received": last.get("receivedDate")})


def _count(key: str) -> Callable[[dict[str, Any]], int | None]:
    return lambda data: len(data[key]) if data.get(key) is not None else None


# ───────────────────────────── Descrieri ─────────────────────────────


@dataclass(frozen=True, kw_only=True)
class SmsToSensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], Any]
    attrs_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None
    unit_fn: Callable[[dict[str, Any]], str | None] | None = None
    monthly_reset: bool = False


SENSORS: tuple[SmsToSensorDescription, ...] = (
    SmsToSensorDescription(
        key="balance",  # aceeași cheie ca în versiunile vechi → același entity_id
        translation_key="balance",
        icon="mdi:wallet-outline",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=_balance,
        unit_fn=_currency,
    ),
    SmsToSensorDescription(
        key="available_sms",
        translation_key="available_sms",
        icon="mdi:message-plus-outline",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_available_sms,
        attrs_fn=_available_attrs,
    ),
    SmsToSensorDescription(
        key="cost_per_sms",
        translation_key="cost_per_sms",
        icon="mdi:receipt-text-outline",
        device_class=SensorDeviceClass.MONETARY,
        suggested_display_precision=3,
        value_fn=_cost_per_sms,
        unit_fn=_currency,
    ),
    SmsToSensorDescription(
        key="last_message",
        translation_key="last_message",
        icon="mdi:message-check-outline",
        device_class=SensorDeviceClass.ENUM,
        options=MESSAGE_STATUSES,
        value_fn=lambda d: message_status(d["last_message"].get("status")) if d.get("last_message") else None,
        attrs_fn=_last_message_attrs,
    ),
    SmsToSensorDescription(
        key="sent_this_month",
        translation_key="sent_this_month",
        icon="mdi:calendar-month-outline",
        state_class=SensorStateClass.TOTAL,
        monthly_reset=True,
        value_fn=lambda d: (_usage(d, "usage_current") or {}).get("count"),
        attrs_fn=_sent_month_attrs,
    ),
    SmsToSensorDescription(
        key="cost_this_month",
        translation_key="cost_this_month",
        icon="mdi:cash-multiple",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
        monthly_reset=True,
        value_fn=lambda d: (_usage(d, "usage_current") or {}).get("cost"),
        unit_fn=lambda d: (_usage(d, "usage_current") or {}).get("currency") or _currency(d),
        attrs_fn=lambda d: _clean({"previous_month_cost": (_usage(d, "usage_previous") or {}).get("cost")}),
    ),
    SmsToSensorDescription(
        key="messages_30_days",
        translation_key="messages_30_days",
        icon="mdi:chart-bar",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: (summarize_messages(d.get("messages")) or {}).get("count"),
        attrs_fn=_messages_attrs,
    ),
    SmsToSensorDescription(
        key="last_campaign",
        translation_key="last_campaign",
        icon="mdi:bullhorn-outline",
        device_class=SensorDeviceClass.ENUM,
        options=CAMPAIGN_STATUSES,
        value_fn=lambda d: campaign_status(d["last_campaign"]) if d.get("last_campaign") else None,
        attrs_fn=_campaign_attrs,
    ),
    SmsToSensorDescription(
        key="inbound_sms",
        translation_key="inbound_sms",
        icon="mdi:message-arrow-left-outline",
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,  # doar cu un număr închiriat
        value_fn=_count("inbound"),
        attrs_fn=_inbound_attrs,
    ),
    SmsToSensorDescription(
        key="optouts",
        translation_key="optouts",
        icon="mdi:account-cancel-outline",
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=_count("optouts"),
    ),
)


# ───────────────────────────── Platformă ─────────────────────────────


async def async_setup_entry(
    hass: HomeAssistant, entry: SmsToConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    _cleanup_legacy(hass, entry)
    coordinator = entry.runtime_data.coordinator
    async_add_entities(SmsToSensor(coordinator, entry, description) for description in SENSORS)
    _LOGGER.debug("[%s] %d senzori adăugați (%d dezactivați implicit)", sender_label(entry.data.get(CONF_SENDER_ID)),
                  len(SENSORS), sum(1 for d in SENSORS if not d.entity_registry_enabled_default))


def _cleanup_legacy(hass: HomeAssistant, entry: SmsToConfigEntry) -> None:
    """Versiunile ≤ 2.0 aveau senzorul „Total SMS" (mereu 0) — eliminat."""
    ent_reg = er.async_get(hass)
    old = ent_reg.async_get_entity_id("sensor", DOMAIN, f"{entry.entry_id}_total_messages")
    if old:
        _LOGGER.debug("Șterg senzorul vechi „Total SMS” (%s)", old)
        ent_reg.async_remove(old)


class SmsToSensor(CoordinatorEntity[SmsToCoordinator], SensorEntity):
    """Un senzor SMS.to (pe dispozitivul contului)."""

    _attr_has_entity_name = True
    entity_description: SmsToSensorDescription

    def __init__(
        self, coordinator: SmsToCoordinator, entry: SmsToConfigEntry, description: SmsToSensorDescription
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=NAME,
            manufacturer=NAME,
            model=f"Expeditor {entry.data.get(CONF_SENDER_ID)}",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://app.sms.to",
        )

    @property
    def _data(self) -> dict[str, Any]:
        return self.coordinator.data or {}

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self._data)

    @property
    def native_unit_of_measurement(self) -> str | None:
        if self.entity_description.unit_fn:
            return self.entity_description.unit_fn(self._data)
        return self.entity_description.native_unit_of_measurement

    @property
    def last_reset(self) -> datetime | None:
        return _start_of_month(self._data) if self.entity_description.monthly_reset else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.attrs_fn is None:
            return None
        return self.entity_description.attrs_fn(self._data) or None
