"""DataUpdateCoordinator for the Volvo Energy integration."""

from __future__ import annotations

import logging
from datetime import timedelta

from volvocarsapi.api import VolvoCarsApi
from volvocarsapi.models import VolvoCarsApiBaseModel, VolvoApiException, VolvoAuthException

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_UPDATE_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class VolvoEnergyCoordinator(DataUpdateCoordinator[dict[str, VolvoCarsApiBaseModel]]):
    """Polls the Volvo Energy API every 5 minutes. Token refresh is handled by HA."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, api: VolvoCarsApi
    ) -> None:
        self._api = api
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(seconds=DEFAULT_UPDATE_INTERVAL),
        )

    async def _async_update_data(self) -> dict[str, VolvoCarsApiBaseModel]:
        """Fetch the latest energy state, filtering out unsupported/errored fields."""
        try:
            raw = await self._api.async_get_energy_state()
        except VolvoAuthException as err:
            raise ConfigEntryAuthFailed from err
        except VolvoApiException as err:
            raise UpdateFailed(str(err)) from err

        return {
            key: field
            for key, field in raw.items()
            if field is not None
            and getattr(field, "status", "OK") != "ERROR"
        }
