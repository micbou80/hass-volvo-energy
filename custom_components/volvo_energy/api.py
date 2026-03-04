"""API auth wrappers for the Volvo Energy integration."""

from __future__ import annotations

from aiohttp import ClientSession
from volvocarsapi.auth import AccessTokenManager

from homeassistant.helpers.config_entry_oauth2_flow import OAuth2Session


class VolvoEnergyAuth(AccessTokenManager):
    """Auth manager for runtime use — delegates token refresh to HA's OAuth2Session."""

    def __init__(self, websession: ClientSession, oauth_session: OAuth2Session) -> None:
        super().__init__(websession)
        self._oauth_session = oauth_session

    async def async_get_access_token(self) -> str:
        """Return a valid access token, refreshing if needed."""
        await self._oauth_session.async_ensure_token_valid()
        return str(self._oauth_session.token["access_token"])


class ConfigFlowVolvoEnergyAuth(AccessTokenManager):
    """Auth manager for config flow use — holds a single static token for validation."""

    def __init__(self, websession: ClientSession, token: str) -> None:
        super().__init__(websession)
        self._token = token

    async def async_get_access_token(self) -> str:
        """Return the static token (no refresh supported during config flow)."""
        return self._token
