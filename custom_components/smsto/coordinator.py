"""DataUpdateCoordinator pentru SMS.to — datele contului, doar citire."""

from __future__ import annotations

import logging
import re
from collections import Counter
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import SmsToAuthError, SmsToClient, SmsToError, mask_phone, sender_label
from .const import (
    CAMPAIGN_STATUS_ALIASES,
    CONF_COST_NUMBER,
    CONF_SENDER_ID,
    DOMAIN,
    FAILED_STATUSES,
    MESSAGE_STATUSES,
    MESSAGES_DAYS,
    MESSAGES_LIMIT,
    PENDING_STATUSES,
    SLOW_REFRESH,
    UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

_PHONE_RE = re.compile(r"^\+?\d{6,15}$")


def is_phone_number(value: str | None) -> bool:
    """Expeditorul poate fi un număr de telefon sau un nume (ex. „HomeAssist")."""
    return bool(value and _PHONE_RE.match(value.replace(" ", "")))


def cost_number(entry: ConfigEntry) -> str | None:
    """Numărul pentru estimarea costului: cel configurat, altfel expeditorul (dacă e număr)."""
    number = (entry.data.get(CONF_COST_NUMBER) or "").replace(" ", "")
    if number:
        return number
    sender = (entry.data.get(CONF_SENDER_ID) or "").replace(" ", "")
    return sender if is_phone_number(sender) else None


def message_status(value: Any) -> str:
    status = str(value or "").strip().lower()
    return status if status in MESSAGE_STATUSES else "unknown"


def campaign_status(campaign: dict[str, Any]) -> str:
    if campaign.get("canceled_at"):
        return "canceled"
    return CAMPAIGN_STATUS_ALIASES.get(str(campaign.get("status") or "").strip().lower(), "unknown")


def summarize_usage(report: dict[str, Any] | None) -> dict[str, Any] | None:
    """Totalurile raportului lunar: mesaje și cost, pe canal și pe țară."""
    if report is None:
        return None
    results = report.get("results") or []
    by_channel: Counter[str] = Counter()
    by_country: Counter[str] = Counter()
    cost = 0.0
    for row in results:
        qty = int(row.get("quantity") or 0)
        by_channel[str(row.get("channel") or "?").upper()] += qty
        by_country[str(row.get("country") or "?").upper()] += qty
        cost += float(row.get("charged_price") or 0)
    return {
        "count": sum(by_channel.values()),
        "cost": round(cost, 4),
        "currency": report.get("billing_currency"),
        "by_channel": dict(by_channel),
        "by_country": dict(by_country),
    }


def summarize_messages(messages: list[dict[str, Any]] | None) -> dict[str, Any] | None:
    """Mesajele din ultimele 30 de zile, pe status, canal și sursă (API / web)."""
    if messages is None:
        return None
    statuses = Counter(message_status(m.get("status")) for m in messages)
    total = len(messages)
    delivered = statuses.get("delivered", 0)
    finished = delivered + sum(statuses.get(s, 0) for s in FAILED_STATUSES)
    return {
        "count": total,
        "parts": sum(int(m.get("sms_count") or 0) for m in messages),
        "cost": round(sum(float(m.get("cost") or 0) for m in messages), 4),
        "delivered": delivered,
        "failed": sum(statuses.get(s, 0) for s in FAILED_STATUSES),
        "pending": sum(statuses.get(s, 0) for s in PENDING_STATUSES),
        # rata de livrare din mesajele cu status final
        "delivery_rate": round(100 * delivered / finished, 1) if finished else None,
        "by_status": dict(statuses),
        "by_channel": dict(Counter(str(m.get("type") or "sms").lower() for m in messages)),
        "via_api": sum(1 for m in messages if m.get("is_api")),
        "via_web": sum(1 for m in messages if not m.get("is_api")),
        "limit_reached": total >= MESSAGES_LIMIT,
    }


class SmsToCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Citește periodic datele contului SMS.to."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: SmsToClient) -> None:
        self.label = sender_label(entry.data.get(CONF_SENDER_ID))
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            # numele apare în jurnalul HA („Finished fetching …") — numărul rămâne mascat
            name=f"{DOMAIN} ({self.label})",
            update_interval=UPDATE_INTERVAL,
        )
        self.client = client
        self._slow_refreshed_at: datetime | None = None
        self._partial_reported = False

    def _debug(self, msg: str, *args: Any) -> None:
        _LOGGER.debug("[%s] " + msg, self.label, *args)

    async def _async_update_data(self) -> dict[str, Any]:
        previous = dict(self.data or {})
        now = dt_util.now()
        slow_due = self._slow_refreshed_at is None or now - self._slow_refreshed_at >= SLOW_REFRESH
        data: dict[str, Any] = {}
        failed: list[str] = []
        self._debug(
            "Actualizare pornită (estimare cost și luna trecută: %s)",
            "se reîmprospătează" if slow_due
            else f"din memorie până la {(self._slow_refreshed_at + SLOW_REFRESH).strftime('%H:%M')}",
        )

        async def fetch(key: str, call, *, keep_previous: bool = True) -> None:
            """Un endpoint: la eroare temporară păstrează valoarea anterioară."""
            try:
                data[key] = await call()
            except SmsToAuthError:
                raise
            except SmsToError as err:
                failed.append(key)
                if keep_previous and key in previous:
                    data[key] = previous[key]
                self._debug("%s indisponibil — %s (%s)", key, err,
                            "păstrez valoarea anterioară" if key in data else "fără valoare anterioară")

        try:
            await fetch("balance", self.client.async_get_balance)

            number = cost_number(self.config_entry)
            if not number:
                self._debug("Fără număr pentru cost: costul per SMS și SMS-urile disponibile rămân necunoscute")
            elif slow_due or "estimate" not in previous:
                await fetch("estimate", lambda: self.client.async_estimate(number))
            else:
                data["estimate"] = previous["estimate"]

            this_month = now.strftime("%Y-%m")
            last_month = (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
            await fetch("usage_current", lambda: self.client.async_monthly_usage(this_month))
            if slow_due or "usage_previous" not in previous:
                await fetch("usage_previous", lambda: self.client.async_monthly_usage(last_month))
            else:
                data["usage_previous"] = previous["usage_previous"]

            since = (now - timedelta(days=MESSAGES_DAYS)).strftime("%Y-%m-%d 00:00:00")
            await fetch("last_message", self.client.async_last_message)
            await fetch("messages", lambda: self.client.async_messages(since, MESSAGES_LIMIT))
            await fetch("last_campaign", self.client.async_last_campaign)
            await fetch("campaigns_total", self.client.async_campaigns_total)
            await fetch("inbound", self.client.async_inbound)
            await fetch("optouts", self.client.async_optouts)
        except SmsToAuthError as err:
            self._debug("Cheia API a fost refuzată (%s) — Home Assistant va cere reautentificarea", err)
            raise ConfigEntryAuthFailed(f"SMS.to a refuzat cheia API: {err}") from err

        if "balance" not in data:
            # Fără sold (nici măcar unul anterior) nu avem date utile
            self._debug("Soldul nu a putut fi citit și nu există unul anterior — actualizare eșuată")
            raise UpdateFailed("SMS.to nu răspunde")
        if slow_due and "estimate" not in failed and "usage_previous" not in failed:
            self._slow_refreshed_at = now

        if failed and not self._partial_reported:
            _LOGGER.warning("[%s] SMS.to: nu au răspuns %s — păstrez valorile anterioare", self.label, ", ".join(failed))
            self._partial_reported = True
        elif not failed and self._partial_reported:
            _LOGGER.info("[%s] SMS.to: toate datele s-au actualizat din nou", self.label)
            self._partial_reported = False

        data["month"] = this_month
        data["previous_month"] = last_month
        data["cost_number"] = number
        if _LOGGER.isEnabledFor(logging.DEBUG):
            self._log_summary(data, failed)
        return data

    def _log_summary(self, data: dict[str, Any], failed: list[str]) -> None:
        """Un rând cu valorile pe care le vor arăta senzorii."""
        balance = data.get("balance")
        estimate = data.get("estimate") or {}
        usage = summarize_usage(data.get("usage_current")) or {}
        messages = summarize_messages(data.get("messages")) or {}
        self._debug(
            "Actualizare terminată: sold %s %s, cost/SMS %s (pentru %s), luna %s: %s SMS / %s %s, "
            "30 de zile: %s mesaje (%s livrate, %s eșuate), campanii %s, primite %s, dezabonări %s%s",
            balance[0] if balance else "?",
            balance[1] if balance else "",
            estimate.get("estimated_cost", "?"),
            mask_phone(data.get("cost_number")) or "—",
            data["month"],
            usage.get("count", "?"),
            usage.get("cost", "?"),
            usage.get("currency") or "",
            messages.get("count", "?"),
            messages.get("delivered", "?"),
            messages.get("failed", "?"),
            data.get("campaigns_total", "?"),
            len(data["inbound"]) if data.get("inbound") is not None else "?",
            len(data["optouts"]) if data.get("optouts") is not None else "?",
            f" — eșuate: {', '.join(failed)}" if failed else "",
        )
