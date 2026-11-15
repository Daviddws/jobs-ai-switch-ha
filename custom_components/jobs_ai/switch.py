"""The Jobs AI switch: on for 15 minutes (the Jobs server turns it off on time), or off now."""

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import JobsAiConfigEntry
from .api import JobsAiError
from .const import ON_MINUTES
from .coordinator import JobsAiCoordinator, jobs_ai_device_info


async def async_setup_entry(hass: HomeAssistant, entry: JobsAiConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Add the switch."""
    async_add_entities([JobsAiSwitch(entry.runtime_data, entry.entry_id)])


class JobsAiSwitch(CoordinatorEntity[JobsAiCoordinator], SwitchEntity):
    """AI in the Jobs app."""

    _attr_has_entity_name = True
    _attr_translation_key = "ai"

    def __init__(self, coordinator: JobsAiCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_ai"
        self._attr_device_info = jobs_ai_device_info(entry_id)

    @property
    def is_on(self) -> bool:
        """On while the Jobs server says so."""
        return bool(self.coordinator.data.get("on"))

    async def _send(self, call) -> None:
        try:
            self.coordinator.async_set_updated_data(await call)
        except JobsAiError as err:
            raise HomeAssistantError(f"Can't reach Jobs: {err}") from err

    async def async_turn_on(self, **kwargs: Any) -> None:
        """On for 15 minutes."""
        await self._send(self.coordinator.client.async_turn_on(ON_MINUTES))

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Off now."""
        await self._send(self.coordinator.client.async_turn_off())
