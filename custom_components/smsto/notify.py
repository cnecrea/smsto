"""SMS.to notification service and API client."""
import logging

import aiohttp

from homeassistant.exceptions import HomeAssistantError

from .const import (
    API_URL_BALANCE,
    API_URL_MESSAGES,
    API_URL_SEND,
    DEFAULT_ERROR_MESSAGE,
    DEFAULT_TIMEOUT,
    ERROR_MESSAGES,
)

_LOGGER = logging.getLogger(__name__)


class SMSToNotificationService:
    """SMS.to API client for sending SMS and fetching account data."""

    def __init__(
        self, api_key: str, sender_id: str, session: aiohttp.ClientSession
    ) -> None:
        """Initialize the service."""
        self._api_key = api_key
        self._sender_id = sender_id
        self._session = session
        _LOGGER.debug(
            "SMSToNotificationService initialized (API key: %s****, Sender ID: %s)",
            api_key[:4],
            sender_id,
        )

    @property
    def _headers(self) -> dict:
        """Return default headers for API requests."""
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _get_error_message(self, status: int) -> str:
        """Return a human-readable error message for the given HTTP status."""
        return ERROR_MESSAGES.get(status, DEFAULT_ERROR_MESSAGE)

    async def async_send_message(
        self,
        message: str = "",
        title: str = "",
        target: list[str] | None = None,
        data: dict | None = None,
    ) -> None:
        """Send an SMS to the specified targets."""
        if not target:
            _LOGGER.error("No target phone number provided.")
            raise HomeAssistantError("No target phone number provided.")

        if not isinstance(target, list) or not all(
            isinstance(t, str) for t in target
        ):
            _LOGGER.error("Invalid target format: expected a list of strings.")
            raise HomeAssistantError(
                "Invalid target format. Must be a list of phone numbers."
            )

        if data is not None and not isinstance(data, dict):
            _LOGGER.error("Invalid 'data' format: expected a dict, got %s.", type(data))
            raise HomeAssistantError("Invalid 'data' format. Must be a dictionary.")

        payload = {
            "to": target,
            "message": f"{title}\n\n{message}" if title else message,
            "sender_id": self._sender_id,
        }
        if data:
            payload.update(data)

        _LOGGER.debug("Sending SMS — target: %s, payload keys: %s", target, list(payload.keys()))

        try:
            async with self._session.post(
                API_URL_SEND,
                json=payload,
                headers=self._headers,
                timeout=aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT),
            ) as response:
                response_text = await response.text()

                if response.status != 200:
                    error_msg = self._get_error_message(response.status)
                    _LOGGER.error(
                        "SMS send failed — status: %s, error: %s, response: %s",
                        response.status,
                        error_msg,
                        response_text,
                    )
                    raise HomeAssistantError(
                        f"Error: {error_msg} (Response: {response_text})"
                    )

                _LOGGER.info("SMS sent successfully to: %s", target)

        except aiohttp.ClientError as err:
            _LOGGER.error("ClientError while sending SMS: %s", err)
            raise HomeAssistantError(f"ClientError while sending SMS: {err}") from err

    async def async_get_balance(self) -> float | None:
        """Fetch the account balance from SMS.to API."""
        _LOGGER.debug("Fetching balance from SMS.to API.")

        try:
            async with self._session.get(
                API_URL_BALANCE,
                headers=self._headers,
                timeout=aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT),
            ) as response:
                if response.status != 200:
                    error_msg = self._get_error_message(response.status)
                    _LOGGER.error(
                        "Balance fetch failed — status: %s, error: %s",
                        response.status,
                        error_msg,
                    )
                    raise HomeAssistantError(f"Error fetching balance: {error_msg}")

                data = await response.json()
                balance = data.get("balance")
                _LOGGER.debug("Balance fetched: %s", balance)
                return balance

        except aiohttp.ClientError as err:
            _LOGGER.error("ClientError fetching balance: %s", err)
            raise HomeAssistantError(f"Balance API error: {err}") from err

    async def async_get_total_messages(self) -> int | None:
        """Fetch the total number of SMS sent."""
        _LOGGER.debug("Fetching total messages from SMS.to API.")

        try:
            async with self._session.get(
                API_URL_MESSAGES,
                headers=self._headers,
                timeout=aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT),
            ) as response:
                if response.status != 200:
                    error_msg = self._get_error_message(response.status)
                    _LOGGER.error(
                        "Total messages fetch failed — status: %s, error: %s",
                        response.status,
                        error_msg,
                    )
                    raise HomeAssistantError(
                        f"Error fetching total messages: {error_msg}"
                    )

                data = await response.json()
                total = data.get("total", 0)
                _LOGGER.debug("Total messages fetched: %s", total)
                return total

        except aiohttp.ClientError as err:
            _LOGGER.error("ClientError fetching total messages: %s", err)
            raise HomeAssistantError(f"Total messages API error: {err}") from err
