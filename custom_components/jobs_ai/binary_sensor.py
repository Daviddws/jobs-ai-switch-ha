"""An ask from the Jobs app waiting for an answer."""

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import JobsAiConfigEntry
from .coordinator import JobsAiCoordinator, jobs_ai_device_info


async def async_setup_entry(hass: HomeAssistant, entry: JobsAiConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Add the binary sensor."""
    async_add_entities([JobsAiAsked(entry.runtime_data, entry.entry_id)])


class JobsAiAsked(CoordinatorEntity[JobsAiCoordinator], BinarySensorEntity):
    """On while "Ask to turn on" waits (5 minutes at most)."""

    _attr_has_entity_name = True
    _attr_translation_key = "asked"

    def __init__(self, coordinator: JobsAiCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_asked"
        self._attr_device_info = jobs_ai_device_info(entry_id)

    @property
    def is_on(self) -> bool:
        """An ask is waiting."""
        return bool(self.coordinator.data.get("asked"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Who asked, and when."""
        asked = self.coordinator.data.get("asked") or {}
        return {"asked_by": asked.get("by"), "asked_at": asked.get("at")}
