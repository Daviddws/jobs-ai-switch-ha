"""Jobs AI Switch: turn the Jobs app's AI on for 15 minutes, and answer its asks from the phone."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import JobsAiClient, JobsAiError
from .const import ACTION_APPROVE, ACTION_DENY, CONF_NOTIFY, CONF_SECRET, CONF_URL, ON_MINUTES
from .coordinator import JobsAiCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BINARY_SENSOR, Platform.BUTTON, Platform.SENSOR, Platform.SWITCH]

type JobsAiConfigEntry = ConfigEntry[JobsAiCoordinator]


def _notify_service(entry: ConfigEntry) -> str | None:
    """The phone's notify service ("mobile_app_…"), from the options or the first setup."""
    return entry.options.get(CONF_NOTIFY, entry.data.get(CONF_NOTIFY)) or None


async def async_setup_entry(hass: HomeAssistant, entry: JobsAiConfigEntry) -> bool:
    """Set up the integration from a config entry."""
    client = JobsAiClient(async_get_clientsession(hass), entry.data[CONF_URL], entry.data[CONF_SECRET])
    coordinator = JobsAiCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    approve = f"{ACTION_APPROVE}_{entry.entry_id}"
    deny = f"{ACTION_DENY}_{entry.entry_id}"
    tag = f"jobs_ai_{entry.entry_id}"
    # the ask the phone was last told about (its time), so each ask is sent once
    sent: dict[str, str | None] = {"at": None}

    async def notify(data: dict) -> None:
        service = _notify_service(entry)
        if not service:
            return
        try:
            await hass.services.async_call("notify", service, data, blocking=True)
        except Exception as err:  # noqa: BLE001 - a missing phone must not break the switch
            _LOGGER.warning("Couldn't notify %s: %s", service, err)

    @callback
    def on_update() -> None:
        """A new ask from the app: send it to the phone. Answered or dropped: clear it there."""
        data = coordinator.data or {}
        asked = data.get("asked")
        if asked and asked.get("at") != sent["at"]:
            sent["at"] = asked.get("at")
            hass.async_create_task(
                notify(
                    {
                        "title": "Turn AI on in Jobs?",
                        "message": f"{asked.get('by') or 'The app'} asked to use AI for {ON_MINUTES} minutes.",
                        "data": {
                            "tag": tag,
                            "actions": [
                                {"action": approve, "title": "Approve"},
                                {"action": deny, "title": "Deny"},
                            ],
                        },
                    }
                )
            )
        elif not asked and sent["at"]:
            sent["at"] = None
            hass.async_create_task(notify({"message": "clear_notification", "data": {"tag": tag}}))

    entry.async_on_unload(coordinator.async_add_listener(on_update))
    # an ask already waiting when Home Assistant starts goes to the phone now, not on the next poll
    on_update()

    async def on_action(event: Event) -> None:
        """Approve or Deny tapped on the phone."""
        action = event.data.get("action")
        if action not in (approve, deny):
            return
        try:
            if action == approve:
                await client.async_turn_on(ON_MINUTES)
            else:
                await client.async_deny()
        except JobsAiError as err:
            _LOGGER.warning("Couldn't answer the ask: %s", err)
            await notify({"title": "Jobs AI", "message": f"Couldn't reach Jobs: {err}"})
        await coordinator.async_request_refresh()

    entry.async_on_unload(hass.bus.async_listen("mobile_app_notification_action", on_action))
    entry.async_on_unload(entry.add_update_listener(_reload_on_options))
    return True


async def _reload_on_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """A new phone picked in the options: start again with it."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: JobsAiConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
