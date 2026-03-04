"""Config flow for the Volvo Energy integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from volvocarsapi.api import VolvoCarsApi
from volvocarsapi.models import VolvoApiException, VolvoCarsVehicle

from homeassistant.config_entries import (
    SOURCE_REAUTH,
    SOURCE_RECONFIGURE,
    ConfigFlowResult,
)
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_API_KEY, CONF_NAME, CONF_TOKEN
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers.config_entry_oauth2_flow import AbstractOAuth2FlowHandler
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import ConfigFlowVolvoEnergyAuth
from .const import CONF_VIN, DOMAIN, MANUFACTURER

_LOGGER = logging.getLogger(__name__)


def _create_api(hass, access_token: str, api_key: str) -> VolvoCarsApi:
    session = aiohttp_client.async_get_clientsession(hass)
    auth = ConfigFlowVolvoEnergyAuth(session, access_token)
    return VolvoCarsApi(session, auth, api_key)


class VolvoEnergyConfigFlow(AbstractOAuth2FlowHandler, domain=DOMAIN):
    """Config flow for Volvo Energy using HA's OAuth2 framework."""

    DOMAIN = DOMAIN

    def __init__(self) -> None:
        super().__init__()
        self._vehicles: list[VolvoCarsVehicle] = []
        self._config_data: dict = {}

    @property
    def extra_authorize_data(self) -> dict:
        """Scopes are set in application_credentials.py — nothing extra needed here."""
        return {}

    @property
    def logger(self) -> logging.Logger:
        return _LOGGER

    async def async_oauth_create_entry(self, data: dict) -> ConfigFlowResult:
        """OAuth done — proceed to API key step."""
        self._config_data |= (self.init_data or {}) | data
        return await self.async_step_api_key()

    # ------------------------------------------------------------------
    # Re-auth / reconfigure
    # ------------------------------------------------------------------

    async def async_step_reauth(self, _: Any) -> ConfigFlowResult:
        """Trigger re-auth when tokens become invalid."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is None:
            return self.async_show_form(
                step_id="reauth_confirm",
                description_placeholders={CONF_NAME: self._get_reauth_entry().title},
            )
        return await self.async_step_user()

    async def async_step_reconfigure(
        self, data: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return await self.async_step_api_key()

    # ------------------------------------------------------------------
    # Step: API key
    # ------------------------------------------------------------------

    async def async_step_api_key(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect and validate the VCC API Key."""
        errors: dict[str, str] = {}

        if user_input is not None:
            api = _create_api(
                self.hass,
                self._config_data[CONF_TOKEN][CONF_ACCESS_TOKEN],
                user_input[CONF_API_KEY],
            )
            try:
                await self._async_load_vehicles(api)
            except VolvoApiException:
                _LOGGER.exception("Unable to retrieve vehicles")
                errors["base"] = "cannot_load_vehicles"

            if not errors:
                self._config_data |= user_input
                return await self.async_step_vin()

        if user_input is None:
            if self.source == SOURCE_REAUTH:
                # Try existing API key — skip form if still valid
                user_input = self._config_data
                api = _create_api(
                    self.hass,
                    self._config_data[CONF_TOKEN][CONF_ACCESS_TOKEN],
                    self._config_data.get(CONF_API_KEY, ""),
                )
                try:
                    await self._async_load_vehicles(api)
                    return await self.async_step_vin()
                except VolvoApiException:
                    pass
            elif self.source == SOURCE_RECONFIGURE:
                user_input = self._config_data = dict(
                    self._get_reconfigure_entry().data
                )
            else:
                user_input = {}

        schema = self.add_suggested_values_to_schema(
            vol.Schema(
                {
                    vol.Required(CONF_API_KEY): TextSelector(
                        TextSelectorConfig(
                            type=TextSelectorType.TEXT, autocomplete="password"
                        )
                    ),
                }
            ),
            {CONF_API_KEY: user_input.get(CONF_API_KEY, "")},
        )

        return self.async_show_form(
            step_id="api_key",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "volvo_dev_portal": "https://developer.volvocars.com/account/#your-api-applications"
            },
        )

    # ------------------------------------------------------------------
    # Step: VIN selection
    # ------------------------------------------------------------------

    async def async_step_vin(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let user select a VIN (or auto-select if only one vehicle)."""
        errors: dict[str, str] = {}

        if len(self._vehicles) == 1:
            self._config_data[CONF_VIN] = self._vehicles[0].vin
            return await self._async_create_or_update()

        if self.source in (SOURCE_REAUTH, SOURCE_RECONFIGURE):
            return await self._async_create_or_update()

        if user_input is not None:
            self._config_data |= user_input
            return await self._async_create_or_update()

        if len(self._vehicles) == 0:
            errors[CONF_VIN] = "no_vehicles"

        schema = vol.Schema(
            {
                vol.Required(CONF_VIN): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            SelectOptionDict(
                                value=v.vin,
                                label=f"{v.description.model} ({v.vin})",
                            )
                            for v in self._vehicles
                        ],
                        multiple=False,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="vin", data_schema=schema, errors=errors
        )

    # ------------------------------------------------------------------
    # Entry creation / update
    # ------------------------------------------------------------------

    async def _async_create_or_update(self) -> ConfigFlowResult:
        vin = self._config_data[CONF_VIN]
        await self.async_set_unique_id(vin)

        if self.source == SOURCE_REAUTH:
            self._abort_if_unique_id_mismatch()
            return self.async_update_reload_and_abort(
                self._get_reauth_entry(),
                data_updates=self._config_data,
            )

        if self.source == SOURCE_RECONFIGURE:
            self._abort_if_unique_id_mismatch()
            return self.async_update_reload_and_abort(
                self._get_reconfigure_entry(),
                data_updates=self._config_data,
                reload_even_if_entry_is_unchanged=False,
            )

        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=f"{MANUFACTURER} {vin}",
            data=self._config_data,
        )

    async def _async_load_vehicles(self, api: VolvoCarsApi) -> None:
        self._vehicles = []
        vins = await api.async_get_vehicles()
        for vin in vins:
            vehicle = await api.async_get_vehicle_details(vin)
            if vehicle:
                self._vehicles.append(vehicle)
