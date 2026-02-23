"""DataUpdateCoordinator for the SMS.to integration."""
import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, UPDATE_INTERVAL_MINUTES
from .notify import SMSToNotificationService

_LOGGER = logging.getLogger(__name__)


class SMSToCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to fetch SMS.to account data (balance + total messages)."""

    def __init__(
        self, hass: HomeAssistant, service: SMSToNotificationService
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=UPDATE_INTERVAL_MINUTES),
        )
        self._service = service

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch balance and total messages from SMS.to API."""
        _LOGGER.debug("Coordinator: fetching SMS.to account data.")

        data: dict[str, Any] = {
            "balance": None,
            "total_messages": None,
        }

        # Fetch balance
        try:
            balance = await self._service.async_get_balance()
            data["balance"] = round(balance, 2) if balance is not None else None
            _LOGGER.debug("Coordinator: balance = %s", data["balance"])
        except Exception as err:
            _LOGGER.error("Coordinator: failed to fetch balance — %s", err)
            raise UpdateFailed(f"Failed to fetch balance: {err}") from err

        # Fetch total messages
        try:
            total = await self._service.async_get_total_messages()
            data["total_messages"] = total
            _LOGGER.debug("Coordinator: total_messages = %s", data["total_messages"])
        except Exception as err:
            _LOGGER.error("Coordinator: failed to fetch total messages — %s", err)
            # Don't raise here — we already have balance data.
            # Just log the error; total_messages stays None.

        _LOGGER.debug("Coordinator: update complete — %s", data)
        return data
