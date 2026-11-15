"""Deny a waiting ask (Approve is turning the switch on)."""

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import JobsAiConfigEntry
from .api import JobsAiError
from .coordinator import JobsAiCoordinator, jobs_ai_device_info


async def async_setup_entry(hass: HomeAssistant, entry: JobsAiConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Add the button."""
    async_add_entities([JobsAiDeny(entry.runtime_data, entry.entry_id)])


class JobsAiDeny(CoordinatorEntity[JobsAiCoordinator], ButtonEntity):
    """Answer the app's ask with no."""

    _attr_has_entity_name = True
    _attr_translation_key = "deny"

    def __init__(self, coordinator: JobsAiCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_deny"
        self._attr_device_info = jobs_ai_device_info(entry_id)

    async def async_press(self) -> None:
        """Deny."""
        try:
            self.coordinator.async_set_updated_data(await self.coordinator.client.async_deny())
        except JobsAiError as err:
            raise HomeAssistantError(f"Can't reach Jobs: {err}") from err
