"""Config flow pentru SMS.to.

- `user`: cheia API + expeditorul. Validarea citește soldul și estimează costul unui
  SMS — nu se trimite niciun mesaj (înainte: un SMS de test real, plătit).
- `cost_number`: doar când expeditorul e un nume (ex. „HomeAssist") — numărul pentru
  calculul costului; opțional.
- `reauth`: cheia API nouă, cerută automat când SMS.to o refuză.
- `reconfigure` (meniul ⋮ → Reconfigurare) și opțiunile (butonul „Configurează"):
  schimbarea cheii, a expeditorului sau a numărului pentru cost, cu reîncărcare.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SmsToAuthError, SmsToClient, SmsToError, mask_phone, sender_label
from .const import CONF_API_KEY, CONF_COST_NUMBER, CONF_SENDER_ID, DOMAIN, NAME
from .coordinator import is_phone_number

_LOGGER = logging.getLogger(__name__)

_PASSWORD = selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD))
# Expeditor alfanumeric: 1–11 caractere (limita SMS); altfel număr de telefon
_ALPHA_SENDER_RE = re.compile(r"^[A-Za-z0-9 .\-]{1,11}$")


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _valid_sender(sender: str) -> bool:
    return is_phone_number(sender) or bool(_ALPHA_SENDER_RE.match(sender))


async def async_validate(
    hass: HomeAssistant, api_key: str, number: str | None, label: str | None = None
) -> dict[str, str]:
    """Cheia (prin sold) și, dacă există, numărul pentru cost (prin estimare) — nu trimite nimic."""
    label = label or "configurare"
    client = SmsToClient(async_get_clientsession(hass), api_key, label)
    _LOGGER.debug("[%s] Validez cheia API (%d caractere)%s", label, len(api_key),
                  f" și numărul pentru cost {mask_phone(number)}" if number else "")
    try:
        await client.async_get_balance()
    except SmsToAuthError as err:
        _LOGGER.debug("[%s] Validare: cheia API a fost refuzată — %s", label, err)
        return {"base": "invalid_auth"}
    except SmsToError as err:
        _LOGGER.debug("[%s] Validare: SMS.to nu răspunde — %s", label, err)
        return {"base": "cannot_connect"}
    except Exception:  # noqa: BLE001
        _LOGGER.exception("Eroare neașteptată la validarea SMS.to")
        return {"base": "unknown"}
    if number:
        try:
            estimate = await client.async_estimate(number)
        except SmsToError as err:
            _LOGGER.debug("[%s] Validare: estimarea costului a eșuat — %s", label, err)
            return {"base": "invalid_number"}
        if estimate.get("invalid_count") or not estimate.get("estimated_cost"):
            _LOGGER.debug("[%s] Validare: SMS.to nu acceptă numărul %s (invalide: %s, cost: %s, erori: %s)", label,
                          mask_phone(number), estimate.get("invalid_count"), estimate.get("estimated_cost"),
                          estimate.get("errors"))
            return {"base": "invalid_number"}
    _LOGGER.debug("[%s] Validare reușită", label)
    return {}


async def async_check_settings(
    hass: HomeAssistant, entry: ConfigEntry, user_input: dict[str, Any]
) -> tuple[dict[str, str], dict[str, Any]]:
    """Cheie, expeditor și număr pentru cost noi (reconfigurare / opțiuni).

    Întoarce (erori, data nouă pentru intrare).
    """
    api_key = _clean(user_input[CONF_API_KEY])
    sender = _clean(user_input[CONF_SENDER_ID])
    number = _clean(user_input.get(CONF_COST_NUMBER)).replace(" ", "")
    label = sender_label(sender)
    if not _valid_sender(sender):
        _LOGGER.debug("[%s] Expeditor invalid (nici număr de telefon, nici nume de 1–11 caractere)", label)
        return {CONF_SENDER_ID: "invalid_sender_id"}, {}
    if number and not is_phone_number(number):
        _LOGGER.debug("[%s] Numărul pentru cost %s nu este un număr de telefon", label, mask_phone(number))
        return {CONF_COST_NUMBER: "invalid_number"}, {}
    if sender != entry.unique_id and any(
        e.unique_id == sender
        for e in hass.config_entries.async_entries(DOMAIN)
        if e.entry_id != entry.entry_id
    ):
        _LOGGER.debug("[%s] Expeditorul este deja folosit de alt cont SMS.to", label)
        return {CONF_SENDER_ID: "already_configured"}, {}
    check = number or (sender.replace(" ", "") if is_phone_number(sender) else None)
    errors = await async_validate(hass, api_key, check, label)
    if errors:
        return errors, {}
    data = {CONF_API_KEY: api_key, CONF_SENDER_ID: sender}
    if number:
        data[CONF_COST_NUMBER] = number
    # doar numele câmpurilor modificate, nu valorile
    changed = [k for k in (CONF_API_KEY, CONF_SENDER_ID, CONF_COST_NUMBER) if data.get(k) != entry.data.get(k)]
    _LOGGER.debug("[%s] Setări noi valide; modificate: %s", label, ", ".join(changed) or "nimic")
    return {}, data


def settings_schema(current: dict[str, Any]) -> vol.Schema:
    """Formularul cu setările curente (cheia rămâne mascată)."""
    return vol.Schema(
        {
            vol.Required(CONF_API_KEY, default=current.get(CONF_API_KEY, "")): _PASSWORD,
            vol.Required(CONF_SENDER_ID, default=current.get(CONF_SENDER_ID, "")): str,
            vol.Optional(
                CONF_COST_NUMBER,
                description={"suggested_value": current.get(CONF_COST_NUMBER, "")},
            ): str,
        }
    )


class SmsToConfigFlow(ConfigFlow, domain=DOMAIN):
    """Configurarea SMS.to din interfață."""

    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> SmsToOptionsFlow:
        return SmsToOptionsFlow()

    async def _async_validate(self, api_key: str, number: str | None, label: str | None) -> dict[str, str]:
        return await async_validate(self.hass, api_key, number, label)

    # ── Adăugarea contului ──

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            api_key = _clean(user_input[CONF_API_KEY])
            sender = _clean(user_input[CONF_SENDER_ID])
            label = sender_label(sender)
            if not _valid_sender(sender):
                _LOGGER.debug("[%s] Configurare: expeditor invalid", label)
                errors[CONF_SENDER_ID] = "invalid_sender_id"
            else:
                await self.async_set_unique_id(sender)
                self._abort_if_unique_id_configured()
                phone = is_phone_number(sender)
                _LOGGER.debug("[%s] Configurare: expeditor de tip %s", label, "număr" if phone else "nume")
                errors = await self._async_validate(api_key, sender.replace(" ", "") if phone else None, label)
                if not errors:
                    self._data = {CONF_API_KEY: api_key, CONF_SENDER_ID: sender}
                    if phone:
                        _LOGGER.debug("[%s] Configurare: cont creat", label)
                        return self.async_create_entry(title=f"{NAME} ({sender})", data=self._data)
                    return await self.async_step_cost_number()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_KEY): _PASSWORD,
                    vol.Required(CONF_SENDER_ID): str,
                }
            ),
            errors=errors,
        )

    async def async_step_cost_number(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Expeditor alfanumeric: numărul pentru calculul costului (opțional)."""
        errors: dict[str, str] = {}
        if user_input is not None:
            label = sender_label(self._data[CONF_SENDER_ID])
            number = _clean(user_input.get(CONF_COST_NUMBER)).replace(" ", "")
            if number and not is_phone_number(number):
                _LOGGER.debug("[%s] Configurare: %s nu este un număr de telefon", label, mask_phone(number))
                errors[CONF_COST_NUMBER] = "invalid_number"
            else:
                if number:
                    errors = await self._async_validate(self._data[CONF_API_KEY], number, label)
                if not errors:
                    data = {**self._data, **({CONF_COST_NUMBER: number} if number else {})}
                    _LOGGER.debug("[%s] Configurare: cont creat (%s)", label,
                                  f"cost calculat pentru {mask_phone(number)}" if number else "fără număr pentru cost")
                    return self.async_create_entry(title=f"{NAME} ({data[CONF_SENDER_ID]})", data=data)

        return self.async_show_form(
            step_id="cost_number",
            data_schema=vol.Schema({vol.Optional(CONF_COST_NUMBER): str}),
            errors=errors,
            description_placeholders={"sender_id": self._data.get(CONF_SENDER_ID, "")},
        )

    # ── Reautentificare ──

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        _LOGGER.debug("[%s] Reautentificare cerută: SMS.to a refuzat cheia API",
                      sender_label(entry_data.get(CONF_SENDER_ID)))
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            api_key = _clean(user_input[CONF_API_KEY])
            label = sender_label(entry.data.get(CONF_SENDER_ID))
            errors = await self._async_validate(api_key, None, label)
            if not errors:
                _LOGGER.debug("[%s] Reautentificare reușită — reîncarc contul", label)
                return self.async_update_reload_and_abort(entry, data_updates={CONF_API_KEY: api_key})
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_API_KEY): _PASSWORD}),
            errors=errors,
            description_placeholders={"sender_id": entry.data.get(CONF_SENDER_ID, "")},
        )

    # ── Reconfigurare ──

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Meniul ⋮ → Reconfigurare: cheie API, expeditor, număr pentru cost."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            _LOGGER.debug("[%s] Reconfigurare din meniul ⋮", sender_label(entry.data.get(CONF_SENDER_ID)))
            errors, data = await async_check_settings(self.hass, entry, user_input)
            if not errors:
                return self.async_update_reload_and_abort(
                    entry, unique_id=data[CONF_SENDER_ID], title=f"{NAME} ({data[CONF_SENDER_ID]})", data=data
                )
        return self.async_show_form(
            step_id="reconfigure", data_schema=settings_schema(user_input or entry.data), errors=errors
        )


class SmsToOptionsFlow(OptionsFlow):
    """Butonul „Configurează": aceleași setări ca reconfigurarea."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry = self.config_entry
        errors: dict[str, str] = {}
        if user_input is not None:
            _LOGGER.debug("[%s] Reconfigurare din „Configurează”", sender_label(entry.data.get(CONF_SENDER_ID)))
            errors, data = await async_check_settings(self.hass, entry, user_input)
            if not errors:
                sender = data[CONF_SENDER_ID]
                self.hass.config_entries.async_update_entry(
                    entry, data=data, unique_id=sender, title=f"{NAME} ({sender})"
                )
                # Un singur reload (nu există listener de opțiuni)
                self.hass.config_entries.async_schedule_reload(entry.entry_id)
                return self.async_create_entry(data=dict(entry.options))
        return self.async_show_form(
            step_id="init", data_schema=settings_schema(user_input or entry.data), errors=errors
        )
