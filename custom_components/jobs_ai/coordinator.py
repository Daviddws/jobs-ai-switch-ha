"""Polling coordinator for Jobs AI Switch."""

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import JobsAiAuthError, JobsAiClient, JobsAiError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


def jobs_ai_device_info(entry_id: str) -> DeviceInfo:
    """Return the device that the switch's entities share."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry_id)},
        name="Jobs AI",
        manufacturer="Jobs app",
        model="AI switch",
    )


class JobsAiCoordinator(DataUpdateCoordinator[dict]):
    """Polls the switch, often enough that an ask from the app reaches the phone within seconds."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: JobsAiClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=10),
        )
        self.client = client

    async def _async_update_data(self) -> dict:
        try:
            return await self.client.async_get_state()
        except JobsAiAuthError as err:
            raise ConfigEntryAuthFailed("The Jobs server refused the secret") from err
        except JobsAiError as err:
            raise UpdateFailed(f"Can't reach the Jobs server: {err}") from err
