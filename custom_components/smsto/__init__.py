"""Initialize the SMS.to notify service."""
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.service import async_set_service_schema
import voluptuous as vol
from homeassistant.exceptions import HomeAssistantError
from .const import DOMAIN

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_LOGGER = logging.getLogger(__name__)

NOTIFY_SMSTO_SCHEMA = vol.Schema(
    {
        vol.Required("message"): cv.string,
        vol.Optional("title"): cv.string,
        vol.Optional("target"): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional("data"): vol.Schema({
            vol.Optional("callback_url"): cv.url,
            vol.Optional("priority"): cv.string,
        }),
    }
)

SERVICE_SCHEMA = {
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
    _LOGGER.debug("Starting setup for SMS.to integration.")

    # Retrieve configuration data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data
    api_key = entry.data.get("api_key")
    sender_id = entry.data.get("sender_id")

    # Validate API Key and Sender ID
    if not isinstance(api_key, str) or not api_key.strip():
        _LOGGER.error("Invalid API Key: Must be a non-empty string.")
        return False
    if not isinstance(sender_id, str) or not sender_id.strip():
        _LOGGER.error("Invalid Sender ID: Must be a non-empty string.")
        return False

    _LOGGER.debug("API Key: %s, Sender ID: %s", api_key[:4] + "****", sender_id)

    # Register notify service
    try:
        _LOGGER.debug("Registering SMS.to notify service.")
        await _register_notify_service(hass, api_key, sender_id)
        _LOGGER.info("Successfully initialized SMS.to notify service.")
    except HomeAssistantError as err:
        _LOGGER.error("Failed to register SMS.to notify service: %s", err)
        return False

    # Forward notify and sensor platforms
    try:
        _LOGGER.debug("Registering SMS.to notify and sensor platforms.")
        await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
        _LOGGER.info("Successfully registered SMS.to platforms.")
    except Exception as err:
        _LOGGER.error("Failed to register SMS.to platforms: %s", err)
        return False

    return True


async def _register_notify_service(hass: HomeAssistant, api_key: str, sender_id: str):
    """Register the notify.smsto service."""
    from .notify import SMSToNotificationService

    notify_service = SMSToNotificationService(api_key, sender_id)

    async def async_send_message_service(call):
        """Handle the notify service call."""
        try:
            _LOGGER.debug("Handling notify.smsto service call.")
            message = call.data.get("message", "")
            title = call.data.get("title", "")
            target = call.data.get("target")
            data = call.data.get("data", {})

            if message == "TEST_MESSAGE":
                _LOGGER.info("Test message detected. Skipping API call.")
                _LOGGER.debug("Test Message Details: Title: %s, Target: %s, Data: %s", title, target, data)
                return  # Skip API call for test messages

            _LOGGER.debug("Message Details: %s", call.data)
            await notify_service.async_send_message(
                message=message,
                title=title,
                target=target,
                data=data,
            )
            _LOGGER.info("SMS notification sent successfully.")
        except Exception as err:
            _LOGGER.error("Error sending SMS notification: %s", err)
            raise HomeAssistantError("Failed to send SMS notification.")

    hass.services.async_register(
        "notify", "smsto", async_send_message_service, schema=NOTIFY_SMSTO_SCHEMA
    )

    # Set the service schema for UI
    async_set_service_schema(
        hass=hass, domain="notify", service="smsto", schema=SERVICE_SCHEMA
    )

    _LOGGER.debug("Service schema for notify.smsto has been set.")


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an SMS.to config entry."""
    _LOGGER.debug("Unloading SMS.to integration.")

    # Unregister notify service manually
    if hass.services.has_service("notify", "smsto"):
        hass.services.async_remove("notify", "smsto")
        _LOGGER.debug("Successfully removed notify.smsto service.")

    # Unload sensor platform
    try:
        _LOGGER.debug("Unloading SMS.to sensor platform.")
        unloaded = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
        _LOGGER.debug("Platforms unloaded: %s", unloaded)
    except Exception as err:
        _LOGGER.error("Failed to unload SMS.to platforms: %s", err)
        unloaded = False

    # Remove data
    hass.data[DOMAIN].pop(entry.entry_id, None)
    _LOGGER.debug("Removed SMS.to entry data from Home Assistant.")

    return unloaded
