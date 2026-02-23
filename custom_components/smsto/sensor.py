"""Sensor platform for SMS.to."""
import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SMSToCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class SMSToSensorEntityDescription(SensorEntityDescription):
    """Describes an SMS.to sensor entity."""

    data_key: str


SENSOR_DESCRIPTIONS: tuple[SMSToSensorEntityDescription, ...] = (
    SMSToSensorEntityDescription(
        key="balance",
        data_key="balance",
        translation_key="balance",
        icon="mdi:cash",
        native_unit_of_measurement="EUR",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SMSToSensorEntityDescription(
        key="total_messages",
        data_key="total_messages",
        translation_key="total_messages",
        icon="mdi:message-text-outline",
        state_class=SensorStateClass.TOTAL,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SMS.to sensors from a config entry."""
    coordinator: SMSToCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities = [
        SMSToSensor(coordinator, description, entry)
        for description in SENSOR_DESCRIPTIONS
    ]

    async_add_entities(entities)
    _LOGGER.debug("SMS.to sensors added: %s", [e.entity_description.key for e in entities])


class SMSToSensor(CoordinatorEntity[SMSToCoordinator], SensorEntity):
    """Representation of an SMS.to sensor."""

    entity_description: SMSToSensorEntityDescription
    has_entity_name = True

    def __init__(
        self,
        coordinator: SMSToCoordinator,
        description: SMSToSensorEntityDescription,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

    @property
    def native_value(self) -> Any:
        """Return the sensor value from coordinator data."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self.entity_description.data_key)

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for grouping entities."""
        return DeviceInfo(
            identifiers={(DOMAIN, "smsto")},
            name="SMS Notifications via SMS.to",
            manufacturer="SMS.to",
            model="SMS Notifications via SMS.to",
            entry_type=DeviceEntryType.SERVICE,
        )
