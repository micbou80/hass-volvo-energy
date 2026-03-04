"""Sensor platform for the Volvo Energy integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfLength, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_VIN, DOMAIN
from .coordinator import VolvoEnergyCoordinator


@dataclass(frozen=True)
class VolvoSensorEntityDescription(SensorEntityDescription):
    """Extends SensorEntityDescription with Volvo-specific fields."""

    api_key: str = ""  # Key in the API 'data' response dict


SENSOR_DESCRIPTIONS: tuple[VolvoSensorEntityDescription, ...] = (
    VolvoSensorEntityDescription(
        key="battery_charge_level",
        api_key="batteryChargeLevel",
        name="Battery Charge Level",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:battery",
    ),
    VolvoSensorEntityDescription(
        key="electric_range",
        api_key="electricRange",
        name="Electric Range",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        icon="mdi:map-marker-distance",
    ),
    VolvoSensorEntityDescription(
        key="estimated_charging_time",
        api_key="estimatedChargingTime",
        name="Estimated Charging Time",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        icon="mdi:timer-outline",
    ),
    VolvoSensorEntityDescription(
        key="target_battery_charge_level",
        api_key="targetBatteryChargeLevel",
        name="Target Battery Charge Level",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:battery-arrow-up",
    ),
    VolvoSensorEntityDescription(
        key="charging_connection_status",
        api_key="chargingConnectionStatus",
        name="Charging Connection Status",
        device_class=SensorDeviceClass.ENUM,
        icon="mdi:ev-plug-type2",
        options=[
            "CONNECTED_AC",
            "CONNECTED_DC",
            "DISCONNECTED",
            "FAULT",
            "UNSPECIFIED",
        ],
    ),
    VolvoSensorEntityDescription(
        key="charging_system_status",
        api_key="chargingSystemStatus",
        name="Charging System Status",
        device_class=SensorDeviceClass.ENUM,
        icon="mdi:battery-charging",
        options=[
            "CHARGING",
            "IDLE",
            "DONE",
            "FAULT",
            "SCHEDULED",
            "UNSPECIFIED",
        ],
    ),
    VolvoSensorEntityDescription(
        key="charging_current_limit",
        api_key="chargingCurrentLimit",
        name="Charging Current Limit",
        device_class=SensorDeviceClass.ENUM,
        icon="mdi:current-ac",
        options=[
            "A_6",
            "A_8",
            "A_10",
            "A_16",
            "A_32",
            "UNLOCKED",
            "UNSPECIFIED",
        ],
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Volvo Energy sensors from a config entry."""
    coordinator: VolvoEnergyCoordinator = hass.data[DOMAIN][entry.entry_id]
    vin: str = entry.data[CONF_VIN]

    async_add_entities(
        VolvoEnergySensor(coordinator, description, vin)
        for description in SENSOR_DESCRIPTIONS
    )


class VolvoEnergySensor(CoordinatorEntity[VolvoEnergyCoordinator], SensorEntity):
    """Represents a single Volvo Energy sensor."""

    entity_description: VolvoSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: VolvoEnergyCoordinator,
        description: VolvoSensorEntityDescription,
        vin: str,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._vin = vin
        self._attr_unique_id = f"{vin}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, vin)},
            name=f"Volvo {vin}",
            manufacturer="Volvo Cars",
            model="Electric Vehicle",
        )

    @property
    def _api_data(self) -> dict[str, Any] | None:
        """Return the field dict for this sensor from the coordinator data."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self.entity_description.api_key)

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self._api_data is not None

    @property
    def native_value(self) -> Any:
        data = self._api_data
        if data is None:
            return None
        raw = data.get("value")
        # Numeric fields arrive as strings from the API; coerce where appropriate
        if self.entity_description.state_class == SensorStateClass.MEASUREMENT:
            try:
                return float(raw)
            except (TypeError, ValueError):
                return raw
        return raw

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self._api_data
        if data is None:
            return {}
        attrs: dict[str, Any] = {}
        if "timestamp" in data:
            attrs["last_updated"] = data["timestamp"]
        if "unit" in data:
            attrs["api_unit"] = data["unit"]
        return attrs
