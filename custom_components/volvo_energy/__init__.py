"""The Volvo Energy integration."""

from __future__ import annotations

from volvocarsapi.api import VolvoCarsApi
from volvocarsapi.models import VolvoApiException, VolvoAuthException

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryNotReady,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.config_entry_oauth2_flow import (
    ImplementationUnavailableError,
    OAuth2Session,
    async_get_config_entry_implementation,
)

from .api import VolvoEnergyAuth
from .const import CONF_VIN, DOMAIN
from .coordinator import VolvoEnergyCoordinator

PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Volvo Energy from a config entry."""
    try:
        implementation = await async_get_config_entry_implementation(hass, entry)
    except ImplementationUnavailableError as err:
        raise ConfigEntryNotReady("OAuth2 implementation unavailable") from err

    web_session = async_get_clientsession(hass)
    oauth_session = OAuth2Session(hass, entry, implementation)
    auth = VolvoEnergyAuth(web_session, oauth_session)
    api = VolvoCarsApi(
        web_session,
        auth,
        entry.data[CONF_API_KEY],
        entry.data[CONF_VIN],
    )

    try:
        await api.async_get_access_token()
    except VolvoAuthException as err:
        raise ConfigEntryAuthFailed from err
    except VolvoApiException as err:
        raise ConfigEntryNotReady from err

    coordinator = VolvoEnergyCoordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Volvo Energy config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded
