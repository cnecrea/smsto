"""The SMS.to integration."""
import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.service import async_set_service_schema

from .const import CONF_API_KEY, CONF_SENDER_ID, DOMAIN
from .coordinator import SMSToCoordinator
from .notify import SMSToNotificationService

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

PLATFORMS = ["sensor"]

NOTIFY_SMSTO_SCHEMA = vol.Schema(
    {
        vol.Required("message"): cv.string,
        vol.Optional("title"): cv.string,
        vol.Optional("target"): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional("data"): vol.Schema(
            {
                vol.Optional("callback_url"): cv.url,
                vol.Optional("priority"): cv.string,
            }
        ),
    }
)

# Schema for the Developer Tools UI (fields, descriptions, examples, selectors)
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
            "description": "Platform-specific additional data.",
            "example": {"callback_url": "https://example.com/callback"},
            "required": False,
            "selector": {"object": {}},
        },
    },
}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SMS.to from a config entry."""
    _LOGGER.debug("Setting up SMS.to integration (entry: %s).", entry.entry_id)

    api_key: str = entry.data[CONF_API_KEY]
    sender_id: str = entry.data[CONF_SENDER_ID]

    if not api_key or not api_key.strip():
        _LOGGER.error("Invalid API Key: must be a non-empty string.")
        return False

    if not sender_id or not sender_id.strip():
        _LOGGER.error("Invalid Sender ID: must be a non-empty string.")
        return False

    _LOGGER.debug("API Key: %s****, Sender ID: %s", api_key[:4], sender_id)

    # Shared aiohttp session
    session = async_get_clientsession(hass)

    # Create the API service
    service = SMSToNotificationService(api_key, sender_id, session)

    # Create and run the coordinator
    coordinator = SMSToCoordinator(hass, service)
    await coordinator.async_config_entry_first_refresh()

    # Store runtime data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "service": service,
    }

    # Register the notify.smsto service
    _register_notify_service(hass, service)

    # Forward platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.info("SMS.to integration setup complete.")
    return True


def _register_notify_service(
    hass: HomeAssistant, service: SMSToNotificationService
) -> None:
    """Register the notify.smsto service if not already registered."""
    if hass.services.has_service("notify", "smsto"):
        _LOGGER.debug("notify.smsto service already registered — skipping.")
        return

    async def async_handle_send(call: ServiceCall) -> None:
        """Handle notify.smsto service calls."""
        message: str = call.data.get("message", "")
        title: str = call.data.get("title", "")
        target = call.data.get("target")
        data: dict = call.data.get("data", {})

        if message == "TEST_MESSAGE":
            _LOGGER.info(
                "Test message detected — skipping API call. "
                "Title: %s, Target: %s, Data: %s",
                title,
                target,
                data,
            )
            return

        _LOGGER.debug(
            "notify.smsto called — message: %s, target: %s", message[:50], target
        )

        try:
            await service.async_send_message(
                message=message, title=title, target=target, data=data
            )
        except Exception as err:
            _LOGGER.error("Error sending SMS notification: %s", err)
            raise HomeAssistantError("Failed to send SMS notification.") from err

    hass.services.async_register(
        "notify", "smsto", async_handle_send, schema=NOTIFY_SMSTO_SCHEMA
    )

    # Set the UI schema so Developer Tools shows fields, descriptions, and examples
    async_set_service_schema(
        hass=hass, domain="notify", service="smsto", schema=SERVICE_SCHEMA_UI
    )

    _LOGGER.debug("notify.smsto service registered with UI schema.")


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an SMS.to config entry."""
    _LOGGER.debug("Unloading SMS.to integration (entry: %s).", entry.entry_id)

    # Unload platforms
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        _LOGGER.debug("Entry data removed for %s.", entry.entry_id)

        # Remove the notify service only if no other entries remain
        if not hass.data[DOMAIN]:
            if hass.services.has_service("notify", "smsto"):
                hass.services.async_remove("notify", "smsto")
                _LOGGER.debug("notify.smsto service removed.")

    _LOGGER.info("SMS.to integration unload %s.", "complete" if unloaded else "failed")
    return unloaded
