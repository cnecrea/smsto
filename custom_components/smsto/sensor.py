"""Sensor platform for SMS.to."""
import logging
from datetime import timedelta
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle
from .notify import SMSToNotificationService

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=5)  # Interval de actualizare pentru senzori


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up SMS.to sensors."""
    api_key = entry.data["api_key"]
    sender_id = entry.data["sender_id"]
    smsto_service = SMSToNotificationService(api_key, sender_id)

    # Crearea senzorilor
    sensors = [
        SMSToBalanceSensor(smsto_service, entry.entry_id),
        SMSToTotalMessagesSensor(smsto_service, entry.entry_id),
    ]

    # Apelează manual update pentru prima dată înainte de a adăuga senzorii
    for sensor in sensors:
        await sensor.async_update(no_throttle=True)

    async_add_entities(sensors)


class SMSToBalanceSensor(Entity):
    """Sensor for SMS.to balance."""

    def __init__(self, api_service, entry_id):
        self._api_service = api_service
        self._state = None
        self._name = "Balance"
        self._unit = "EUR"
        self._unique_id = f"{entry_id}_balance"

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return self._unit

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def icon(self):
        """Return the icon based on the state."""
        return "mdi:cash"  # Icon for balance

    @property
    def extra_state_attributes(self):
        """Add friendly name and other attributes."""
        return {
            "friendly_name": "Balance",
            "unit_of_measurement": self._unit,
        }

    @Throttle(SCAN_INTERVAL)
    async def async_update(self, no_throttle=False):
        """Fetch balance data from SMS.to API."""
        if no_throttle:
            _LOGGER.debug("Initial update for %s without throttle.", self._unique_id)
        else:
            _LOGGER.debug("Fetching balance data for %s with throttle.", self._unique_id)

        try:
            balance_data = await self._api_service.get_balance()
            raw_balance = balance_data.get("balance")
            if raw_balance is not None:
                self._state = round(raw_balance, 2)  # Format balance to 2 decimal places
                _LOGGER.debug(
                    "Balance updated for %s: %.2f EUR", self._unique_id, self._state
                )
            else:
                _LOGGER.warning("Balance data is missing or invalid for %s.", self._unique_id)
                self._state = "Unavailable"
        except Exception as e:
            _LOGGER.error("Error updating balance for %s: %s", self._unique_id, e)
            self._state = "Error"


class SMSToTotalMessagesSensor(Entity):
    """Sensor for total SMS.to messages sent."""

    def __init__(self, api_service, entry_id):
        self._api_service = api_service
        self._state = 0
        self._name = "Total SMS Sent"
        self._unique_id = f"{entry_id}_total_messages"

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._state

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def icon(self):
        """Return the icon for total SMS sent."""
        return "mdi:message-text-outline"  # Icon for total SMS

    @property
    def extra_state_attributes(self):
        """Add friendly name and other attributes."""
        return {
            "friendly_name": "Total SMS Sent",
        }

    @Throttle(SCAN_INTERVAL)
    async def async_update(self, no_throttle=False):
        """Fetch total messages data from SMS.to API."""
        if no_throttle:
            _LOGGER.debug("Initial update for %s without throttle.", self._unique_id)
        else:
            _LOGGER.debug("Fetching total messages data for %s with throttle.", self._unique_id)

        try:
            response = await self._api_service.get_total_messages()

            if isinstance(response, dict) and response.get("total"):
                total_messages = response["total"]
                self._state = total_messages
                _LOGGER.debug("Total messages updated for %s: %d", self._unique_id, self._state)
            elif isinstance(response, int):
                self._state = response
                _LOGGER.debug("Total messages updated (from int) for %s: %d", self._unique_id, self._state)
            else:
                _LOGGER.warning(
                    "Unexpected response format for total messages on %s: %s", self._unique_id, response
                )
                self._state = "Unavailable"

        except Exception as e:
            _LOGGER.error("Error updating total messages for %s: %s", self._unique_id, e)
            self._state = "Error"
