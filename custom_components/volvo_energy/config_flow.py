"""Config flow for the Volvo Energy integration."""
from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import urlencode

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.network import get_url

from .api import VolvoAuthError, VolvoEnergyAPI
from .const import (
    AUTH_URL,
    CONF_ACCESS_TOKEN,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_REFRESH_TOKEN,
    CONF_TOKEN_EXPIRES_AT,
    CONF_VCC_API_KEY,
    CONF_VIN,
    DOMAIN,
    OAUTH_SCOPES,
)

_LOGGER = logging.getLogger(__name__)

_VIN_RE = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$", re.IGNORECASE)


class VolvoEnergyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Volvo Energy."""

    VERSION = 1

    def __init__(self) -> None:
        self._user_input: dict[str, Any] = {}
        self._code_verifier: str = ""
        self._redirect_uri: str = ""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the credentials form and validate input."""
        errors: dict[str, str] = {}

        if user_input is not None:
            vin = user_input[CONF_VIN].strip().upper()
            if not _VIN_RE.match(vin):
                errors[CONF_VIN] = "invalid_vin"
            else:
                user_input[CONF_VIN] = vin
                # Abort if this VIN is already configured
                await self.async_set_unique_id(vin)
                self._abort_if_unique_id_configured()

                self._user_input = user_input
                return await self.async_step_oauth()

        description_placeholders = {
            "volvo_dev_portal": "https://developer.volvocars.com/",
        }

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_VCC_API_KEY): str,
                    vol.Required(CONF_CLIENT_ID): str,
                    vol.Required(CONF_CLIENT_SECRET): str,
                    vol.Required(CONF_VIN): str,
                }
            ),
            errors=errors,
            description_placeholders=description_placeholders,
        )

    async def async_step_oauth(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Generate PKCE params and redirect the user to Volvo's auth page."""
        code_verifier, code_challenge = VolvoEnergyAPI.generate_pkce()
        self._code_verifier = code_verifier

        try:
            ha_url = get_url(self.hass, prefer_external=True)
        except Exception:
            ha_url = get_url(self.hass)

        self._redirect_uri = f"{ha_url}/auth/external/callback"

        params = {
            "response_type": "code",
            "client_id": self._user_input[CONF_CLIENT_ID],
            "redirect_uri": self._redirect_uri,
            "scope": " ".join(OAUTH_SCOPES),
            "state": self.flow_id,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        auth_url = f"{AUTH_URL}?{urlencode(params)}"

        return self.async_external_step(step_id="oauth", url=auth_url)

    async def async_step_oauth_callback(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the OAuth2 callback from Volvo's auth server."""
        # user_input contains the query params from the callback URL
        # HA passes these via external_data after async_external_step_done
        data = user_input or {}
        code = data.get("code")

        if not code:
            return self.async_abort(reason="oauth_error")

        session = async_get_clientsession(self.hass)
        try:
            tokens = await VolvoEnergyAPI.exchange_code(
                session=session,
                client_id=self._user_input[CONF_CLIENT_ID],
                client_secret=self._user_input[CONF_CLIENT_SECRET],
                code=code,
                redirect_uri=self._redirect_uri,
                code_verifier=self._code_verifier,
            )
        except VolvoAuthError as err:
            _LOGGER.error("OAuth token exchange failed: %s", err)
            return self.async_abort(reason="auth_failed")

        vin = self._user_input[CONF_VIN]
        entry_data = {
            CONF_VCC_API_KEY: self._user_input[CONF_VCC_API_KEY],
            CONF_CLIENT_ID: self._user_input[CONF_CLIENT_ID],
            CONF_CLIENT_SECRET: self._user_input[CONF_CLIENT_SECRET],
            CONF_VIN: vin,
            CONF_ACCESS_TOKEN: tokens["access_token"],
            CONF_REFRESH_TOKEN: tokens["refresh_token"],
            CONF_TOKEN_EXPIRES_AT: tokens["expires_at"],
        }

        return self.async_create_entry(title=f"Volvo {vin}", data=entry_data)
