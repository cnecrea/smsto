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

        # Handle test message
        if message == "TEST_MESSAGE":
            _LOGGER.info("Test message detected. Skipping API call.")
            _LOGGER.debug("Test Message Details: Title: %s, Target: %s, Data: %s", title, target, data)
            return  # Skip API call for test messages

        # Validate target
        if not target:
            _LOGGER.error("No target phone number provided.")
            raise HomeAssistantError("No target phone number provided.")

        if not isinstance(target, list) or not all(isinstance(t, str) for t in target):
            _LOGGER.error("Invalid target format. Must be a list of phone numbers.")
            raise HomeAssistantError("Invalid target format. Must be a list of phone numbers.")

        # Validate data
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

        _LOGGER.debug("Payload being sent: %s", payload)
        _LOGGER.debug("Headers being sent: %s", headers)

        # Send the request
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            try:
                url = "https://api.sms.to/sms/send"
                _LOGGER.debug("Sending POST request to URL: %s", url)
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

        _LOGGER.debug("Fetching balance with URL: %s", url)

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=headers) as response:
                    response_text = await response.text()
                    _LOGGER.debug("Response received for balance: %s", response_text)

                    if response.status == 200:
                        data = await response.json()
                        _LOGGER.debug("Balance fetched successfully: %s", data)
                        return data
                    else:
                        error_message = ERROR_MESSAGES.get(response.status, ERROR_MESSAGES["default"])
                        _LOGGER.error(
                            "Failed to fetch balance. Status: %s, Error: %s",
                            response.status,
                            error_message,
                        )
                        raise HomeAssistantError(f"Error fetching balance: {response.status}")
            except Exception as e:
                _LOGGER.error("Error during balance API call: %s", e)
                raise HomeAssistantError(f"Balance API error: {e}")

    async def get_total_messages(self):
        """Fetch the total number of SMS sent."""
        url = "https://api.sms.to/v2/messages"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        _LOGGER.debug("Fetching total messages with URL: %s", url)

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=headers) as response:
                    response_text = await response.text()
                    _LOGGER.debug("Response received for total messages: %s", response_text)

                    if response.status == 200:
                        data = await response.json()
                        if isinstance(data, dict) and "total" in data:
                            total = data["total"]
                            _LOGGER.debug("Total messages fetched successfully: %d", total)
                            return total
                        else:
                            _LOGGER.warning("Unexpected response format for total messages: %s", data)
                            return 0
                    else:
                        error_message = ERROR_MESSAGES.get(response.status, ERROR_MESSAGES["default"])
                        _LOGGER.error(
                            "Failed to fetch total messages. Status: %s, Error: %s",
                            response.status,
                            error_message,
                        )
                        raise HomeAssistantError(f"Error fetching total messages: {response.status}")
            except Exception as e:
                _LOGGER.error("Error during total messages API call: %s", e)
                raise HomeAssistantError(f"Total messages API error: {e}")
