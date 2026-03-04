"""Sensor platform for the Volvo Energy integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from volvocarsapi.models import VolvoCarsApiBaseModel

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfLength,
    UnitOfPower,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_VIN, DOMAIN, MANUFACTURER
from .coordinator import VolvoEnergyCoordinator


@dataclass(frozen=True)
class VolvoEnergySensorDescription(SensorEntityDescription):
    """SensorEntityDescription extended with the API field key."""

    api_field: str = ""


# API field names taken from energy-api-specification.json and the official integration.
# ENUM options use lowercase to match the volvocarsapi library value convention.
SENSOR_DESCRIPTIONS: tuple[VolvoEnergySensorDescription, ...] = (
    VolvoEnergySensorDescription(
        key="battery_charge_level",
        api_field="batteryChargeLevel",
        name="Battery Charge Level",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=0,
    ),
    VolvoEnergySensorDescription(
        key="electric_range",
        api_field="electricRange",
        name="Electric Range",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        suggested_display_precision=0,
    ),
    VolvoEnergySensorDescription(
        key="estimated_charging_time",
        api_field="estimatedChargingTimeToTargetBatteryChargeLevel",
        name="Estimated Charging Time",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.MINUTES,
    ),
    VolvoEnergySensorDescription(
        key="target_battery_charge_level",
        api_field="targetBatteryChargeLevel",
        name="Target Battery Charge Level",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=0,
    ),
    VolvoEnergySensorDescription(
        key="charging_current_limit",
        api_field="chargingCurrentLimit",
        name="Charging Current Limit",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
    ),
    VolvoEnergySensorDescription(
        key="charging_power",
        api_field="chargingPower",
        name="Charging Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
    ),
    VolvoEnergySensorDescription(
        key="charger_connection_status",
        api_field="chargerConnectionStatus",
        name="Charger Connection Status",
        device_class=SensorDeviceClass.ENUM,
        options=["connected", "disconnected", "fault"],
    ),
    VolvoEnergySensorDescription(
        key="charging_status",
        api_field="chargingStatus",
        name="Charging Status",
        device_class=SensorDeviceClass.ENUM,
        options=["charging", "discharging", "done", "error", "idle", "scheduled"],
    ),
    VolvoEnergySensorDescription(
        key="charging_type",
        api_field="chargingType",
        name="Charging Type",
        device_class=SensorDeviceClass.ENUM,
        options=["ac", "dc", "none"],
    ),
    VolvoEnergySensorDescription(
        key="charger_power_status",
        api_field="chargerPowerStatus",
        name="Charger Power Status",
        device_class=SensorDeviceClass.ENUM,
        options=[
            "fault",
            "power_available_but_not_activated",
            "providing_power",
            "no_power_available",
        ],
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Volvo Energy sensors."""
    coordinator: VolvoEnergyCoordinator = hass.data[DOMAIN][entry.entry_id]
    vin: str = entry.data[CONF_VIN]
    async_add_entities(
        VolvoEnergySensor(coordinator, description, vin)
        for description in SENSOR_DESCRIPTIONS
    )


class VolvoEnergySensor(CoordinatorEntity[VolvoEnergyCoordinator], SensorEntity):
    """A single Volvo Energy sensor backed by a coordinator."""

    entity_description: VolvoEnergySensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: VolvoEnergyCoordinator,
        description: VolvoEnergySensorDescription,
        vin: str,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{vin}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, vin)},
            name=f"{MANUFACTURER} {vin}",
            manufacturer=MANUFACTURER,
        )

    @property
    def _field(self) -> VolvoCarsApiBaseModel | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self.entity_description.api_field)

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self._field is not None

    @property
    def native_value(self) -> Any:
        field = self._field
        if field is None:
            return None
        value = field.value  # type: ignore[attr-defined]
        if self.device_class == SensorDeviceClass.ENUM and value:
            v = str(value).lower()
            return v if v != "unspecified" else None
        if self.state_class == SensorStateClass.MEASUREMENT:
            try:
                return float(value)
            except (TypeError, ValueError):
                return value
        return value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        field = self._field
        if field is None:
            return {}
        updated_at = getattr(field, "updated_at", None)
        if updated_at:
            return {"last_updated": str(updated_at)}
        return {}
