"""The Volvo Energy integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .config_flow import VolvoEnergyOAuthCallbackView
from .const import CALLBACK_REGISTERED_KEY, DOMAIN
from .coordinator import VolvoEnergyCoordinator

PLATFORMS = ["sensor"]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the OAuth2 callback view on domain setup."""
    if not hass.data.get(CALLBACK_REGISTERED_KEY):
        hass.http.register_view(VolvoEnergyOAuthCallbackView())
        hass.data[CALLBACK_REGISTERED_KEY] = True
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Volvo Energy from a config entry."""
    coordinator = VolvoEnergyCoordinator(hass, entry)
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
