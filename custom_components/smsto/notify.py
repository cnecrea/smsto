"""SMS.to notification service."""
import logging
import aiohttp
from homeassistant.components.notify import BaseNotificationService
from homeassistant.exceptions import HomeAssistantError

_LOGGER = logging.getLogger(__name__)

ERROR_MESSAGES = {
    400: "Bad request. Please check your payload.",
    401: "Unauthorized. Verify your API key.",
    403: "Forbidden. You may not have permission to send SMS.",
    404: "Resource not found. Check the API endpoint.",
    429: "Rate limit exceeded. Please try again later.",
    500: "Internal server error. Try again later.",
    "default": "An unknown error occurred. Please check the logs.",
}


async def async_get_service(hass, config, discovery_info=None):
    """Set up the SMS.to notification service."""
    api_key = config["api_key"]
    sender_id = config["sender_id"]

    # Log pentru debug
    _LOGGER.debug("Setting up SMS.to notify service with API key: %s and sender ID: %s", api_key[:4] + "****", sender_id)

    # Înregistrăm serviciul direct din fișierul services.yaml
    await hass.helpers.service.async_set_service_schema(
        "notify", "smsto", {
            "name": "SMS.to Notification",
            "description": "Send an SMS notification through SMS.to",
            "fields": {
                "message": {"description": "The text to send", "required": True},
                "title": {"description": "The title of the message", "required": False},
                "target": {"description": "Phone numbers to notify", "required": True},
                "data": {"description": "Additional options for the message", "required": False},
            },
        }
    )

    return SMSToNotificationService(api_key, sender_id)


class SMSToNotificationService(BaseNotificationService):
    """Implementation of the SMS.to notification service."""

    def __init__(self, api_key, sender_id):
        """Initialize the service."""
        self._api_key = api_key
        self._sender_id = sender_id
        _LOGGER.debug(
            "Initializing SMS.to Notification Service with API key: %s and sender ID: %s",
            api_key[:4] + "****",
            sender_id,
        )

    async def async_send_message(self, message="", **kwargs):
        """Send a message to the target."""
        _LOGGER.debug("Preparing to send message: '%s' with kwargs: %s", message, kwargs)

        # Extract parameters
        target = kwargs.get("target")
        title = kwargs.get("title", "")
        data = kwargs.get("data", {})

        # Validate target
        if not target:
            _LOGGER.error("No target phone number provided.")
            raise HomeAssistantError("No target phone number provided.")

        if not isinstance(target, list) or not all(isinstance(t, str) for t in target):
            _LOGGER.error("Invalid target format. Must be a list of phone numbers.")
            raise HomeAssistantError("Invalid target format. Must be a list of phone numbers.")

        if not isinstance(data, dict):
            _LOGGER.error("Invalid 'data' format. Must be a dictionary.")
            raise HomeAssistantError("Invalid 'data' format. Must be a dictionary.")

        # Construct the payload
        payload = {
            "to": target,
            "message": f"{title}\n\n{message}" if title else message,
            "sender_id": self._sender_id,
        }
        payload.update(data)

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            try:
                url = "https://api.sms.to/sms/send"
                async with session.post(url, json=payload, headers=headers) as response:
                    response_text = await response.text()

                    if response.status != 200:
                        error_message = ERROR_MESSAGES.get(
                            response.status, ERROR_MESSAGES["default"]
                        )
                        _LOGGER.error(
                            "Failed to send SMS. Status: %s, Response: %s, Error: %s",
                            response.status,
                            response_text,
                            error_message,
                        )
                        raise HomeAssistantError(f"Error: {error_message} (Response: {response_text})")

                    _LOGGER.info("SMS successfully sent to: %s", target)

            except aiohttp.ClientError as e:
                _LOGGER.error("ClientError while sending SMS: %s", e)
                raise HomeAssistantError(f"ClientError while sending SMS: {e}")

            except Exception as e:
                _LOGGER.error("Unexpected error while sending SMS: %s", e)
                raise HomeAssistantError(f"Unexpected error while sending SMS: {e}")

    async def get_balance(self):
        """Fetch the balance from SMS.to API."""
        url = "https://auth.sms.to/api/balance"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=headers) as response:
                    response_text = await response.text()
                    if response.status == 200:
                        data = await response.json()
                        return {"balance": data.get("balance")}
                    else:
                        error_message = ERROR_MESSAGES.get(response.status, ERROR_MESSAGES["default"])
                        raise HomeAssistantError(f"Error fetching balance: {error_message}")
            except Exception as e:
                raise HomeAssistantError(f"Balance API error: {e}")

    async def get_total_messages(self):
        """Fetch the total number of SMS sent."""
        url = "https://api.sms.to/v2/messages"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=headers) as response:
                    response_text = await response.text()
                    if response.status == 200:
                        data = await response.json()
                        return data.get("total", 0)
                    else:
                        error_message = ERROR_MESSAGES.get(response.status, ERROR_MESSAGES["default"])
                        raise HomeAssistantError(f"Error fetching total messages: {error_message}")
            except Exception as e:
                raise HomeAssistantError(f"Total messages API error: {e}")
