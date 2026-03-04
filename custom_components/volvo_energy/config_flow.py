"""Config flow for the Volvo Energy integration."""
from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import urlencode

import voluptuous as vol
from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.network import NoURLAvailableError, get_url

from .api import VolvoAuthError, VolvoEnergyAPI
from .const import (
    AUTH_URL,
    CALLBACK_REGISTERED_KEY,
    CONF_ACCESS_TOKEN,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_REFRESH_TOKEN,
    CONF_TOKEN_EXPIRES_AT,
    CONF_VCC_API_KEY,
    CONF_VIN,
    DOMAIN,
    OAUTH_CALLBACK_PATH,
    OAUTH_SCOPES,
)

_LOGGER = logging.getLogger(__name__)

_VIN_RE = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$", re.IGNORECASE)


class VolvoEnergyOAuthCallbackView(HomeAssistantView):
    """Receives the OAuth2 authorization code redirect from Volvo Cars."""

    url = OAUTH_CALLBACK_PATH
    name = "api:volvo_energy:oauth2callback"
    requires_auth = False

    async def get(self, request: web.Request) -> web.Response:
        """Handle the OAuth2 callback GET request."""
        hass = request.app["hass"]
        state = request.query.get("state")  # equals the config flow_id
        code = request.query.get("code")
        error = request.query.get("error")

        if not state:
            return web.Response(text="Missing state parameter", status=400)

        user_input: dict[str, Any] = {"state": state}
        if code:
            user_input["code"] = code
        elif error:
            user_input["error"] = error
        else:
            return web.Response(text="Missing code or error parameter", status=400)

        try:
            await hass.config_entries.flow.async_configure(
                flow_id=state, user_input=user_input
            )
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Could not resume flow %s (may have expired)", state)

        return web.Response(
            headers={"content-type": "text/html"},
            text="<script>window.close()</script><p>Authentication complete. You can close this window.</p>",
        )


class VolvoEnergyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Volvo Energy."""

    VERSION = 1

    def __init__(self) -> None:
        self._user_input: dict[str, Any] = {}
        self._code_verifier: str = ""
        self._redirect_uri: str = ""
        self._oauth_code: str = ""

    # ------------------------------------------------------------------
    # Step 1: credentials form
    # ------------------------------------------------------------------

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the credentials form and validate input."""
        errors: dict[str, str] = {}

        # Register the OAuth callback view once per HA lifetime
        if not self.hass.data.get(CALLBACK_REGISTERED_KEY):
            self.hass.http.register_view(VolvoEnergyOAuthCallbackView())
            self.hass.data[CALLBACK_REGISTERED_KEY] = True

        # Determine HA URL for the description placeholder
        try:
            ha_url = get_url(self.hass, prefer_external=True)
        except NoURLAvailableError:
            ha_url = get_url(self.hass, allow_internal=True)

        if user_input is not None:
            vin = user_input[CONF_VIN].strip().upper()
            if not _VIN_RE.match(vin):
                errors[CONF_VIN] = "invalid_vin"
            else:
                user_input[CONF_VIN] = vin
                await self.async_set_unique_id(vin)
                self._abort_if_unique_id_configured()
                self._user_input = user_input
                return await self.async_step_oauth()

        callback_url = f"{ha_url}{OAUTH_CALLBACK_PATH}"
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
            description_placeholders={
                "volvo_dev_portal": "https://developer.volvocars.com/",
                "ha_url": callback_url,
            },
        )

    # ------------------------------------------------------------------
    # Step 2: OAuth2 redirect + callback (same method, called twice by HA)
    # ------------------------------------------------------------------

    async def async_step_oauth(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Redirect user to Volvo auth (first call) or handle the code (second call)."""
        if user_input is not None:
            # Second call: our callback view resumed the flow with the code
            if "error" in user_input:
                _LOGGER.error("Volvo OAuth error: %s", user_input["error"])
                return self.async_abort(reason="oauth_error")
            self._oauth_code = user_input.get("code", "")
            if not self._oauth_code:
                return self.async_abort(reason="oauth_error")
            # Must return EXTERNAL_STEP_DONE before we can call async_create_entry
            return self.async_external_step_done(next_step_id="create_entry")

        # First call: generate PKCE and build the auth URL
        code_verifier, code_challenge = VolvoEnergyAPI.generate_pkce()
        self._code_verifier = code_verifier

        try:
            ha_url = get_url(self.hass, prefer_external=True)
        except NoURLAvailableError:
            ha_url = get_url(self.hass, allow_internal=True)

        self._redirect_uri = f"{ha_url}{OAUTH_CALLBACK_PATH}"

        params = {
            "response_type": "code",
            "client_id": self._user_input[CONF_CLIENT_ID],
            "redirect_uri": self._redirect_uri,
            "scope": " ".join(OAUTH_SCOPES),
            "state": self.flow_id,  # plain flow_id — matched by our own callback view
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        return self.async_external_step(
            step_id="oauth", url=f"{AUTH_URL}?{urlencode(params)}"
        )

    # ------------------------------------------------------------------
    # Step 3: exchange code → tokens → create entry
    # ------------------------------------------------------------------

    async def async_step_create_entry(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Exchange the authorization code for tokens and create the config entry."""
        session = async_get_clientsession(self.hass)
        try:
            tokens = await VolvoEnergyAPI.exchange_code(
                session=session,
                client_id=self._user_input[CONF_CLIENT_ID],
                client_secret=self._user_input[CONF_CLIENT_SECRET],
                code=self._oauth_code,
                redirect_uri=self._redirect_uri,
                code_verifier=self._code_verifier,
            )
        except VolvoAuthError as err:
            _LOGGER.error("OAuth token exchange failed: %s", err)
            return self.async_abort(reason="auth_failed")

        vin = self._user_input[CONF_VIN]
        return self.async_create_entry(
            title=f"Volvo {vin}",
            data={
                CONF_VCC_API_KEY: self._user_input[CONF_VCC_API_KEY],
                CONF_CLIENT_ID: self._user_input[CONF_CLIENT_ID],
                CONF_CLIENT_SECRET: self._user_input[CONF_CLIENT_SECRET],
                CONF_VIN: vin,
                CONF_ACCESS_TOKEN: tokens["access_token"],
                CONF_REFRESH_TOKEN: tokens["refresh_token"],
                CONF_TOKEN_EXPIRES_AT: tokens["expires_at"],
            },
        )
