"""Integrarea SMS.to: notificări SMS și datele contului."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.service import async_set_service_schema

from .api import SmsToClient, SmsToError, mask_phone, sender_label
from .const import CONF_API_KEY, CONF_COST_NUMBER, CONF_SENDER_ID, DOMAIN, TEST_MESSAGE
from .coordinator import SmsToCoordinator

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

PLATFORMS = ["sensor"]


@dataclass
class SmsToRuntime:
    client: SmsToClient
    coordinator: SmsToCoordinator


type SmsToConfigEntry = ConfigEntry[SmsToRuntime]

NOTIFY_SMSTO_SCHEMA = vol.Schema(
    {
        vol.Required("message"): cv.string,
        vol.Optional("title"): cv.string,
        vol.Optional("target"): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional("data"): vol.Schema(
            {
                vol.Optional("callback_url"): cv.url,
                vol.Optional("priority"): cv.string,
                vol.Optional("sender_id"): cv.string,
            },
            extra=vol.ALLOW_EXTRA,
        ),
    }
)

# Descrierea serviciului în Instrumente pentru dezvoltatori (câmpuri, exemple)
SERVICE_SCHEMA_UI = {
    "name": "SMS.to Notification",
    "description": "Send an SMS notification through SMS.to",
    "fields": {
        "message": {
            "description": "The text of the notification to send.",
            "example": "The garage door is open!",
            "required": True,
            "selector": {"text": {}},
        },
        "title": {
            "description": "The title of the notification (optional).",
            "example": "Garage Door Alert",
            "required": False,
            "selector": {"text": {}},
        },
        "target": {
            "description": "Phone numbers to send the notification to (comma-separated).",
            "example": "+40730040302, +40740040303",
            "required": True,
            "selector": {"text": {}},
        },
        "data": {
            "description": "Platform-specific additional data. With several SMS.to accounts, "
            "sender_id selects the account to send from.",
            "example": {"callback_url": "https://example.com/callback"},
            "required": False,
            "selector": {"object": {}},
        },
    },
}


def _loaded_entries(hass: HomeAssistant) -> list[SmsToConfigEntry]:
    return [
        e
        for e in hass.config_entries.async_entries(DOMAIN)
        if e.state is ConfigEntryState.LOADED and isinstance(getattr(e, "runtime_data", None), SmsToRuntime)
    ]


async def async_setup_entry(hass: HomeAssistant, entry: SmsToConfigEntry) -> bool:
    """Configurează un cont SMS.to."""
    label = sender_label(entry.data.get(CONF_SENDER_ID))
    _LOGGER.debug("[%s] Pornesc contul (intrarea %s, număr pentru cost: %s)", label, entry.entry_id,
                  mask_phone(entry.data.get(CONF_COST_NUMBER)) or "expeditorul / niciunul")
    client = SmsToClient(async_get_clientsession(hass), entry.data[CONF_API_KEY], label)
    coordinator = SmsToCoordinator(hass, entry, client)
    # SMS.to indisponibil → ConfigEntryNotReady (reîncercare automată);
    # cheie refuzată → ConfigEntryAuthFailed (HA cere reautentificarea)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = SmsToRuntime(client=client, coordinator=coordinator)
    _register_notify_service(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _remove_legacy_device(hass, entry)
    _LOGGER.debug("[%s] Cont pornit, actualizare la fiecare %s", label, coordinator.update_interval)
    return True


def _remove_legacy_device(hass: HomeAssistant, entry: SmsToConfigEntry) -> None:
    """Versiunile ≤ 2.0 foloseau un dispozitiv comun („smsto") pentru toate conturile.

    Se șterge abia după ce senzorii s-au mutat pe dispozitivul contului și doar dacă
    nu mai are entități: ștergerea unui dispozitiv șterge și entitățile lui.
    """
    dev_reg = dr.async_get(hass)
    ent_reg = er.async_get(hass)
    for device in dr.async_entries_for_config_entry(dev_reg, entry.entry_id):
        if (DOMAIN, "smsto") not in device.identifiers:
            continue
        if er.async_entries_for_device(ent_reg, device.id, include_disabled_entities=True):
            _LOGGER.debug("Dispozitivul vechi comun „smsto” mai are entități — îl păstrez")
        else:
            _LOGGER.debug("Șterg dispozitivul vechi comun „smsto” (fără entități)")
            dev_reg.async_remove_device(device.id)


def _register_notify_service(hass: HomeAssistant) -> None:
    """Serviciul notify.smsto — păstrat pentru automatizările existente."""
    if hass.services.has_service("notify", DOMAIN):
        return

    async def async_handle_send(call: ServiceCall) -> None:
        message: str = call.data.get("message", "")
        title: str = call.data.get("title", "")
        target: list[str] | None = call.data.get("target")
        data: dict = dict(call.data.get("data") or {})

        if message == TEST_MESSAGE:
            _LOGGER.info("Mesaj de test — nu se trimite nimic (destinatari: %s)",
                         ", ".join(mask_phone(t) or "?" for t in target or []) or "niciunul")
            return
        if not target:
            raise HomeAssistantError("Lipsește numărul de telefon al destinatarului (target).")

        # Contul se alege la fiecare apel (înainte: rămânea legat de primul cont
        # configurat, chiar și după ștergerea lui). Cu mai multe conturi,
        # data.sender_id alege contul cu acel expeditor.
        entries = _loaded_entries(hass)
        if not entries:
            raise HomeAssistantError("Integrarea SMS.to nu este încărcată.")
        wanted = data.get("sender_id")
        entry = next((e for e in entries if e.data.get(CONF_SENDER_ID) == wanted), entries[0])
        sender = data.pop("sender_id", None) or entry.data[CONF_SENDER_ID]
        label = sender_label(entry.data.get(CONF_SENDER_ID))
        if wanted and wanted != entry.data.get(CONF_SENDER_ID):
            _LOGGER.debug("[%s] notify.smsto: niciun cont cu expeditorul %s — folosesc primul cont, "
                          "cu expeditorul cerut", label, sender_label(wanted))
        _LOGGER.debug("[%s] notify.smsto: %d destinatar(i), %d caractere%s, din %d cont(uri) încărcate",
                      label, len(target), len(message), " + titlu" if title else "", len(entries))

        text = f"{title}\n\n{message}" if title else message
        try:
            await entry.runtime_data.client.async_send(target, text, sender, data)
        except SmsToError as err:
            _LOGGER.debug("[%s] notify.smsto: trimiterea a eșuat — %s", label, err)
            raise HomeAssistantError(f"SMS-ul nu a putut fi trimis: {err}") from err
        _LOGGER.debug("[%s] SMS trimis către %d destinatar(i); reîmprospătez soldul", label, len(target))
        # Soldul și „Ultimul SMS" se actualizează imediat
        await entry.runtime_data.coordinator.async_request_refresh()

    hass.services.async_register("notify", DOMAIN, async_handle_send, schema=NOTIFY_SMSTO_SCHEMA)
    async_set_service_schema(hass, "notify", DOMAIN, SERVICE_SCHEMA_UI)
    _LOGGER.debug("Serviciul notify.%s a fost înregistrat", DOMAIN)


async def async_unload_entry(hass: HomeAssistant, entry: SmsToConfigEntry) -> bool:
    """Descarcă un cont SMS.to."""
    _LOGGER.debug("[%s] Descarc contul", sender_label(entry.data.get(CONF_SENDER_ID)))
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded and not [e for e in _loaded_entries(hass) if e.entry_id != entry.entry_id]:
        if hass.services.has_service("notify", DOMAIN):
            hass.services.async_remove("notify", DOMAIN)
            _LOGGER.debug("Niciun alt cont încărcat — serviciul notify.%s a fost eliminat", DOMAIN)
    return unloaded
