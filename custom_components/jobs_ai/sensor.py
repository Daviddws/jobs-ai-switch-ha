"""When Jobs AI turns itself off."""

from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import JobsAiConfigEntry
from .coordinator import JobsAiCoordinator, jobs_ai_device_info


async def async_setup_entry(hass: HomeAssistant, entry: JobsAiConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Add the sensor."""
    async_add_entities([JobsAiOffAt(entry.runtime_data, entry.entry_id)])


class JobsAiOffAt(CoordinatorEntity[JobsAiCoordinator], SensorEntity):
    """The time AI turns off, while it's on (unknown while off)."""

    _attr_has_entity_name = True
    _attr_translation_key = "off_at"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: JobsAiCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_off_at"
        self._attr_device_info = jobs_ai_device_info(entry_id)

    @property
    def native_value(self) -> datetime | None:
        """The server's 'until', while on."""
        until = self.coordinator.data.get("until")
        return dt_util.parse_datetime(until) if until else None
