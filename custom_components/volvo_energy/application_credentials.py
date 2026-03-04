"""Application credentials platform for the Volvo Energy integration."""

from __future__ import annotations

from volvocarsapi.auth import AUTHORIZE_URL, TOKEN_URL
from volvocarsapi.scopes import ALL_SCOPES

from homeassistant.components.application_credentials import ClientCredential
from homeassistant.core import HomeAssistant
from homeassistant.helpers.config_entry_oauth2_flow import (
    LocalOAuth2ImplementationWithPkce,
)


async def async_get_auth_implementation(
    hass: HomeAssistant, auth_domain: str, credential: ClientCredential
) -> VolvoEnergyOAuth2Implementation:
    """Return auth implementation for Volvo Energy."""
    return VolvoEnergyOAuth2Implementation(
        hass,
        auth_domain,
        credential.client_id,
        AUTHORIZE_URL,
        TOKEN_URL,
        credential.client_secret,
    )


class VolvoEnergyOAuth2Implementation(LocalOAuth2ImplementationWithPkce):
    """Volvo Energy OAuth2 implementation with PKCE."""

    @property
    def extra_authorize_data(self) -> dict:
        """Append all energy scopes to the authorize URL."""
        return super().extra_authorize_data | {
            "scope": " ".join(ALL_SCOPES),
        }
