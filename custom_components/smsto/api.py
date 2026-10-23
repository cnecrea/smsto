"""Client API pentru SMS.to (autentificare cu cheia API, ca Bearer)."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import aiohttp
from yarl import URL

from .const import (
    CAMPAIGNS_LIMIT,
    TIMEOUT,
    URL_BALANCE,
    URL_CAMPAIGNS,
    URL_ESTIMATE,
    URL_INBOUND,
    URL_LAST_CAMPAIGN,
    URL_LAST_MESSAGE,
    URL_MESSAGES,
    URL_MONTHLY_USAGE,
    URL_OPTOUTS,
    URL_SEND,
)

_LOGGER = logging.getLogger(__name__)


class SmsToError(Exception):
    """Eroare la comunicarea cu SMS.to."""


class SmsToAuthError(SmsToError):
    """Cheia API a fost refuzată (HTTP 401)."""


def mask_phone(number: Any) -> str | None:
    """„+40742524070" → „+40742•••070" — pentru atribute și jurnal."""
    text = str(number or "").replace(" ", "")
    if len(text) < 8:
        return text or None
    return f"{text[:6]}•••{text[-3:]}"


def sender_label(sender: Any) -> str:
    """Expeditorul în jurnal: numărul mascat, numele (ex. „HomeAssist") întreg."""
    text = str(sender or "").replace(" ", "")
    return (mask_phone(text) or "") if text.lstrip("+").isdigit() else str(sender or "")


def _api_message(body: Any) -> str:
    if isinstance(body, dict):
        return str(body.get("message") or body.get("error") or "")
    return str(body or "")[:200]


class SmsToClient:
    """Cereri către API-ul SMS.to. Doar `async_send` trimite mesaje."""

    def __init__(self, session: aiohttp.ClientSession, api_key: str, label: str | None = None) -> None:
        self._session = session
        self._api_key = api_key
        # Expeditorul (mascat dacă e număr): cu mai multe conturi, jurnalul arată care cont a cerut
        self._label = label or "configurare"

    def _debug(self, msg: str, *args: Any) -> None:
        _LOGGER.debug("[%s] " + msg, self._label, *args)

    async def _request(self, method: str, url: str, body: dict | None = None, *, allow_404: bool = False) -> Any:
        """Cerere HTTP. Jurnalul conține metoda, adresa, statusul și durata — niciodată cheia API."""
        headers = {"Authorization": f"Bearer {self._api_key}", "Accept": "application/json"}
        endpoint = URL(url).with_query(None).human_repr()
        started = time.monotonic()
        try:
            async with self._session.request(
                method, url, json=body, headers=headers, timeout=aiohttp.ClientTimeout(total=TIMEOUT)
            ) as resp:
                status = resp.status
                text = await resp.text()
        except (aiohttp.ClientError, TimeoutError) as err:
            self._debug("%s %s → eroare de rețea după %.0f ms: %r", method, endpoint,
                        (time.monotonic() - started) * 1000, err)
            raise SmsToError(f"SMS.to nu răspunde: {err}") from err

        elapsed_ms = (time.monotonic() - started) * 1000
        try:
            data = json.loads(text) if text.strip() else None
        except ValueError:
            data = text
        if status >= 400:
            self._debug("%s %s → HTTP %s în %.0f ms: %s", method, endpoint, status, elapsed_ms,
                        _api_message(data) or "fără detalii")
        else:
            self._debug("%s %s → HTTP %s în %.0f ms (%d octeți)", method, endpoint, status, elapsed_ms, len(text))
        if status == 401:
            raise SmsToAuthError(_api_message(data) or "Cheie API invalidă")
        if status == 404 and allow_404:
            return None
        if status >= 400:
            raise SmsToError(f"HTTP {status}: {_api_message(data)}".strip())
        return data

    # ── Cont ──

    async def async_get_balance(self) -> tuple[float, str]:
        """Soldul și moneda contului."""
        data = await self._request("GET", URL_BALANCE)
        if not isinstance(data, dict) or data.get("balance") is None:
            raise SmsToError("Răspuns neașteptat la sold")
        self._debug("Sold: %s %s", data["balance"], data.get("currency"))
        return float(data["balance"]), str(data.get("currency") or "EUR")

    async def async_estimate(self, to: str, message: str = "Test") -> dict[str, Any]:
        """Costul trimiterii unui mesaj — NU trimite nimic."""
        data = await self._request("POST", URL_ESTIMATE, {"message": message, "to": to})
        if not isinstance(data, dict):
            raise SmsToError("Răspuns neașteptat la estimarea costului")
        self._debug("Estimare cost pentru %s: %s (%s părți, %s numere invalide)", mask_phone(to),
                    data.get("estimated_cost"), data.get("sms_count"), data.get("invalid_count"))
        return data

    async def async_monthly_usage(self, month: str) -> dict[str, Any]:
        """Raportul de utilizare pentru luna `YYYY-MM` (toate canalele)."""
        data = await self._request("POST", URL_MONTHLY_USAGE, {"billing_month": month})
        if not isinstance(data, dict):
            raise SmsToError("Răspuns neașteptat la raportul lunar")
        results = data.get("results") or []
        self._debug("Raport %s: %d rânduri, %d mesaje, %.4f %s", month, len(results),
                    sum(int(r.get("quantity") or 0) for r in results),
                    sum(float(r.get("charged_price") or 0) for r in results), data.get("billing_currency"))
        return data

    # ── Mesaje și campanii ──

    async def async_last_message(self) -> dict[str, Any] | None:
        data = await self._request("GET", URL_LAST_MESSAGE, allow_404=True)
        if not (isinstance(data, dict) and data.get("id")):
            self._debug("Ultimul mesaj: niciunul")
            return None
        self._debug("Ultimul mesaj: %s către %s la %s (%s, cost %s)", data.get("status"), mask_phone(data.get("to")),
                    data.get("sent_at") or data.get("created_at"), data.get("type"), data.get("cost"))
        return data

    async def async_messages(self, since: str, limit: int) -> list[dict[str, Any]]:
        """Mesajele trimise de la `since` (format `Y-m-d H:i:s`, cel mult 31 de zile)."""
        url = str(URL(URL_MESSAGES).with_query({"limit": str(limit), "created_at_from": since}))
        items = _items(await self._request("GET", url))
        self._debug("Mesaje de la %s: %d%s", since, len(items), " (limita atinsă)" if len(items) >= limit else "")
        return items

    async def async_last_campaign(self) -> dict[str, Any] | None:
        data = await self._request("GET", URL_LAST_CAMPAIGN, allow_404=True)
        if not (isinstance(data, dict) and data.get("id")):
            self._debug("Ultima campanie: niciuna")
            return None
        self._debug("Ultima campanie: %s din %s (trimise %s, livrate %s, eșuate %s)", data.get("status"),
                    data.get("created_at"), data.get("sent_messages"), data.get("delivered_messages"),
                    data.get("failed_messages"))
        return data

    async def async_campaigns_total(self) -> int | str:
        """Numărul campaniilor; „100+" dacă API-ul nu dă totalul și lista e plină."""
        url = f"{URL_CAMPAIGNS}?limit={CAMPAIGNS_LIMIT}&page=1"
        data = await self._request("GET", url)
        if isinstance(data, dict):
            for source in (data, data.get("meta") or {}):
                if isinstance(source.get("total"), int):
                    self._debug("Campanii: %d (câmpul total din răspuns)", source["total"])
                    return source["total"]
        count = len(_items(data))
        self._debug("Campanii: %d în prima pagină (fără câmp total)", count)
        return f"{CAMPAIGNS_LIMIT}+" if count >= CAMPAIGNS_LIMIT else count

    async def async_inbound(self) -> list[dict[str, Any]]:
        """SMS-urile primite în ultima oră (doar pe un număr închiriat)."""
        items = _items(await self._request("GET", URL_INBOUND))
        self._debug("SMS-uri primite recent: %d", len(items))
        return items

    async def async_optouts(self) -> list[dict[str, Any]]:
        items = _items(await self._request("GET", URL_OPTOUTS))
        self._debug("Dezabonări recente: %d", len(items))
        return items

    # ── Trimitere ──

    async def async_send(
        self, to: list[str], message: str, sender_id: str, extra: dict[str, Any] | None = None
    ) -> Any:
        """Trimite un SMS către unul sau mai multe numere."""
        payload: dict[str, Any] = {"to": to, "message": message, "sender_id": sender_id}
        if extra:
            payload.update(extra)
        # textul mesajului nu ajunge în jurnal, doar lungimea
        self._debug("Trimit SMS de la %s către %s: %d caractere%s", sender_label(sender_id),
                    ", ".join(mask_phone(t) or "?" for t in to), len(message),
                    f", câmpuri extra: {sorted(extra)}" if extra else "")
        result = await self._request("POST", URL_SEND, payload)
        if isinstance(result, dict):
            self._debug("SMS.to a acceptat trimiterea: %s (message_id %s, campaign_id %s)",
                        _api_message(result) or "fără mesaj", result.get("message_id"), result.get("campaign_id"))
        return result


def _items(data: Any) -> list[dict[str, Any]]:
    """Lista dintr-un răspuns: fie direct o listă, fie `{"data": [...]}`."""
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict) and isinstance(data.get("data"), list):
        return [x for x in data["data"] if isinstance(x, dict)]
    return []
