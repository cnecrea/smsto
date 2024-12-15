"""Initialize the SMS.to notify service."""
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
import voluptuous as vol
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN

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
        await _register_notify_service(hass, api_key, sender_id)
        _LOGGER.info("Successfully initialized SMS.to notify service with sender ID: %s", sender_id)
    except HomeAssistantError as err:
        _LOGGER.error("Failed to register SMS.to notify service: %s", err)
        return False

    # Register sensors
    try:
        _LOGGER.debug("Registering SMS.to sensors.")
        await hass.config_entries.async_forward_entry_setup(entry, "sensor")
        _LOGGER.info("Successfully registered SMS.to sensors.")
    except Exception as err:
        _LOGGER.error("Failed to register SMS.to sensors: %s", err)
        return False  # Stop setup if sensors fail to load

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


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an SMS.to config entry."""
    _LOGGER.debug("Unloading SMS.to integration.")

    # Unregister notify service manually
    if hass.services.has_service("notify", "smsto"):
        hass.services.async_remove("notify", "smsto")
        _LOGGER.debug("Successfully removed notify.smsto service.")

    # Unload sensors
    try:
        _LOGGER.debug("Unloading SMS.to sensors.")
        sensor_unloaded = await hass.config_entries.async_forward_entry_unload(entry, "sensor")
        _LOGGER.debug("Sensors unloaded: %s", sensor_unloaded)
    except Exception as err:
        _LOGGER.error("Failed to unload SMS.to sensors: %s", err)
        sensor_unloaded = False

    # Remove data
    hass.data[DOMAIN].pop(entry.entry_id, None)
    _LOGGER.debug("Removed SMS.to entry data from Home Assistant.")

    return sensor_unloaded
