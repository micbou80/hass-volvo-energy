"""DataUpdateCoordinator for the Volvo Energy integration."""
from __future__ import annotations

import logging
import time
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import VolvoAPIError, VolvoAuthError, VolvoEnergyAPI
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_REFRESH_TOKEN,
    CONF_TOKEN_EXPIRES_AT,
    CONF_VCC_API_KEY,
    CONF_VIN,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    TOKEN_REFRESH_BUFFER,
)

_LOGGER = logging.getLogger(__name__)


class VolvoEnergyCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator that polls the Volvo Energy API and handles token refresh."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._entry = entry
        self._vin: str = entry.data[CONF_VIN]
        session = async_get_clientsession(hass)
        self._api = VolvoEnergyAPI(
            session=session,
            vcc_api_key=entry.data[CONF_VCC_API_KEY],
            access_token=entry.data[CONF_ACCESS_TOKEN],
        )
        self._session = session

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{self._vin}",
            update_interval=timedelta(seconds=DEFAULT_UPDATE_INTERVAL),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch latest energy state, refreshing the token if needed."""
        await self._async_ensure_token_valid()

        try:
            return await self._api.get_energy_state(self._vin)
        except VolvoAuthError as err:
            raise ConfigEntryAuthFailed(
                f"Authentication failed for VIN {self._vin}: {err}"
            ) from err
        except VolvoAPIError as err:
            raise UpdateFailed(f"Error fetching Volvo Energy data: {err}") from err

    async def _async_ensure_token_valid(self) -> None:
        """Refresh the access token if it is about to expire."""
        expires_at: float = self._entry.data.get(CONF_TOKEN_EXPIRES_AT, 0)
        if time.time() < expires_at - TOKEN_REFRESH_BUFFER:
            return

        _LOGGER.debug("Access token expiring soon, refreshing…")
        try:
            tokens = await VolvoEnergyAPI.refresh_access_token(
                session=self._session,
                client_id=self._entry.data[CONF_CLIENT_ID],
                client_secret=self._entry.data[CONF_CLIENT_SECRET],
                refresh_token=self._entry.data[CONF_REFRESH_TOKEN],
            )
        except VolvoAuthError as err:
            raise ConfigEntryAuthFailed(
                f"Token refresh failed for VIN {self._vin}: {err}"
            ) from err

        new_data = {
            **self._entry.data,
            CONF_ACCESS_TOKEN: tokens["access_token"],
            CONF_REFRESH_TOKEN: tokens.get("refresh_token", self._entry.data[CONF_REFRESH_TOKEN]),
            CONF_TOKEN_EXPIRES_AT: tokens["expires_at"],
        }
        self.hass.config_entries.async_update_entry(self._entry, data=new_data)
        self._api.update_access_token(tokens["access_token"])
        _LOGGER.debug("Access token refreshed successfully")
