"""Config flow for Harvst WaterMate integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.const import CONF_HOST
from homeassistant.exceptions import HomeAssistantError

from .api import WaterMateAPI
from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    api = WaterMateAPI(data[CONF_HOST])

    if not await api.test_connection():
        raise CannotConnectError

    # Return info that you want to store in the config entry.
    return {"title": f"WaterMate ({data[CONF_HOST]})"}


class ConfigFlow(ConfigFlow, domain=DOMAIN):  # type: ignore[misc]
    """Handle a config flow for Harvst WaterMate."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnectError:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnectError(HomeAssistantError):
    """Error to indicate we cannot connect."""
