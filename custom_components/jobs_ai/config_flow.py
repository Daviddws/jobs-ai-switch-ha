"""Config flow for Jobs AI Switch: the Jobs address, its switch secret, and the phone to ask."""

from collections.abc import Mapping
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
import voluptuous as vol

from .api import JobsAiAuthError, JobsAiClient, JobsAiError, JobsAiNoSwitchError
from .const import CONF_NOTIFY, CONF_SECRET, CONF_URL, DEFAULT_URL, DOMAIN

NO_PHONE = ""

PASSWORD = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))


def _phones(hass: HomeAssistant) -> SelectSelector:
    """The phones with the Home Assistant app (notify.mobile_app_…), or none."""
    services = sorted(s for s in hass.services.async_services().get("notify", {}) if s.startswith("mobile_app_"))
    options = [SelectOptionDict(value=NO_PHONE, label="No phone (no alerts)")] + [
        SelectOptionDict(value=s, label=s.removeprefix("mobile_app_").replace("_", " ").title()) for s in services
    ]
    return SelectSelector(SelectSelectorConfig(options=options, mode=SelectSelectorMode.DROPDOWN))


async def _check(hass: HomeAssistant, url: str, secret: str) -> str | None:
    """None when the server accepts the secret, else the error key."""
    try:
        await JobsAiClient(async_get_clientsession(hass), url, secret).async_get_state()
    except JobsAiAuthError:
        return "invalid_auth"
    except JobsAiNoSwitchError:
        return "no_switch"
    except JobsAiError:
        return "cannot_connect"
    return None


class JobsAiConfigFlow(ConfigFlow, domain=DOMAIN):
    """Asks for the Jobs address, the secret, and the phone."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the setup form."""
        errors: dict[str, str] = {}
        if user_input is not None:
            url = user_input[CONF_URL].strip().rstrip("/")
            await self.async_set_unique_id(url.lower())
            self._abort_if_unique_id_configured()
            error = await _check(self.hass, url, user_input[CONF_SECRET])
            if error:
                errors["base"] = error
            else:
                return self.async_create_entry(
                    title="Jobs AI",
                    data={CONF_URL: url, CONF_SECRET: user_input[CONF_SECRET], CONF_NOTIFY: user_input.get(CONF_NOTIFY, NO_PHONE)},
                )
        schema = vol.Schema(
            {
                vol.Required(CONF_URL, default=DEFAULT_URL): str,
                vol.Required(CONF_SECRET): PASSWORD,
                vol.Optional(CONF_NOTIFY, default=NO_PHONE): _phones(self.hass),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        """The server refused the secret (it was changed there)."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ask for the new secret."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            error = await _check(self.hass, entry.data[CONF_URL], user_input[CONF_SECRET])
            if error:
                errors["base"] = error
            else:
                return self.async_update_reload_and_abort(entry, data_updates={CONF_SECRET: user_input[CONF_SECRET]})
        return self.async_show_form(
            step_id="reauth_confirm", data_schema=vol.Schema({vol.Required(CONF_SECRET): PASSWORD}), errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Change the phone later."""
        return JobsAiOptionsFlow()


class JobsAiOptionsFlow(OptionsFlow):
    """Pick another phone for the asks."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the options form."""
        if user_input is not None:
            return self.async_create_entry(data={CONF_NOTIFY: user_input.get(CONF_NOTIFY, NO_PHONE)})
        current = self.config_entry.options.get(CONF_NOTIFY, self.config_entry.data.get(CONF_NOTIFY, NO_PHONE))
        schema = vol.Schema({vol.Optional(CONF_NOTIFY, default=current or NO_PHONE): _phones(self.hass)})
        return self.async_show_form(step_id="init", data_schema=schema)
