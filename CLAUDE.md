# CLAUDE.md — Developer Notes for AI Assistants

This file provides context for AI coding assistants (Claude, Copilot, etc.) working on this repository.

## Project overview

This is a **Home Assistant custom integration** for the [Volvo Energy API v2](https://developer.volvocars.com/apis/energy/v2/overview/).
It is distributed via **HACS** (Home Assistant Community Store).

The integration polls Volvo's cloud API every 5 minutes and exposes 7 sensors per vehicle.

---

## File structure

```
hacs.json                          # HACS metadata (required at repo root)
README.md                          # User-facing documentation
CLAUDE.md                          # This file

custom_components/volvo_energy/
├── __init__.py                    # Entry point: async_setup_entry / async_unload_entry
├── manifest.json                  # HA integration metadata (domain, version, requirements)
├── const.py                       # All constants: URLs, config entry keys, defaults
├── api.py                         # VolvoEnergyAPI — HTTP client, PKCE helpers, token exchange
├── coordinator.py                 # VolvoEnergyCoordinator — DataUpdateCoordinator, token refresh
├── config_flow.py                 # Multi-step UI config flow (credentials → OAuth2 → entry creation)
├── sensor.py                      # 7 SensorEntity subclasses via CoordinatorEntity
├── strings.json                   # Config flow UI strings (source of truth)
└── translations/
    └── en.json                    # English translations (must mirror strings.json)
```

---

## Key design decisions

### No external pip dependencies
The integration uses Home Assistant's built-in `aiohttp` session (`async_get_clientsession`).
Do **not** add pip requirements to `manifest.json` unless absolutely necessary, as they create version-conflict risks in HA.

### OAuth2 via `async_external_step`
Volvo's auth requires PKCE + a `vcc-api-key` header on every request, which doesn't fit HA's `AbstractOAuth2FlowHandler`.
Instead, the config flow manually:
1. Generates PKCE (`secrets` + `hashlib` — stdlib only).
2. Returns `self.async_external_step(step_id="oauth", url=auth_url)` to redirect the user.
3. Handles the callback in `async_step_oauth_callback`.

### Token storage
Tokens are stored directly in the `ConfigEntry.data` dict.
After a refresh, `hass.config_entries.async_update_entry(entry, data={...})` persists the new tokens.

### Re-auth
`ConfigEntryAuthFailed` is raised on 401/403 or failed refresh — this triggers HA's built-in re-authentication UI (no extra re-auth flow needed).

### One config entry per VIN
`unique_id` is set to the VIN. `_abort_if_unique_id_configured()` prevents duplicates.

---

## Adding a new sensor

1. Open `sensor.py`.
2. Add a new `VolvoSensorEntityDescription` to the `SENSOR_DESCRIPTIONS` tuple:
   ```python
   VolvoSensorEntityDescription(
       key="my_new_sensor",          # unique snake_case key
       api_key="myNewSensorKey",     # key inside the API 'data' response
       name="My New Sensor",
       device_class=SensorDeviceClass.XXX,
       state_class=SensorStateClass.MEASUREMENT,
       native_unit_of_measurement=SOME_UNIT,
       icon="mdi:some-icon",
   )
   ```
3. That's it — `async_setup_entry` iterates `SENSOR_DESCRIPTIONS` automatically.

---

## Volvo Energy API v2

- **Base URL**: `https://api.volvocars.com/energy/v2`
- **Main endpoint**: `GET /vehicles/{vin}/state`
- **Auth**: OAuth2 Authorization Code + PKCE
  - Token URL: `https://volvoid.eu.volvocars.com/as/token.oauth2`
  - Auth URL: `https://volvoid.eu.volvocars.com/as/authorization.oauth2`
- **Extra header on every API call**: `vcc-api-key: <VCC_API_KEY>`
- **Rate limits**: 100 req/min, 10,000/day
- **Refresh token validity**: 7 days (if not refreshed) / 6 months (rolling)

### Response shape

```json
{
  "data": {
    "batteryChargeLevel":        { "value": "87.3", "unit": "%",       "timestamp": "..." },
    "electricRange":             { "value": 200,    "unit": "km",      "timestamp": "..." },
    "estimatedChargingTime":     { "value": 120,    "unit": "minutes", "timestamp": "..." },
    "targetBatteryChargeLevel":  { "value": 80,     "unit": "%",       "timestamp": "..." },
    "chargingConnectionStatus":  { "value": "CONNECTED_AC",            "timestamp": "..." },
    "chargingSystemStatus":      { "value": "CHARGING",                "timestamp": "..." },
    "chargingCurrentLimit":      { "value": "A_32",                    "timestamp": "..." }
  }
}
```

---

## Development tips

- **HA version**: Targets HA ≥ 2024.1.0. Use `SensorDeviceClass`, `UnitOfLength`, `UnitOfTime` from `homeassistant.const` / `homeassistant.components.sensor`.
- **Testing locally**: Copy `custom_components/volvo_energy/` into your HA `config/custom_components/` and restart.
- **Logging**: Set `logger: volvo_energy: debug` in `configuration.yaml` to see detailed logs.
- **Translations**: `strings.json` is the source; `translations/en.json` must be kept in sync.
- **Version bumps**: Update `version` in `manifest.json` for every release.

---

## Common gotchas

- The Volvo Developer Portal requires the redirect URI to be registered **exactly** — including the scheme and port. HA uses `/auth/external/callback` as the callback path.
- Numeric values from the API arrive as **strings** (e.g. `"87.3"` not `87.3`). The `native_value` property in `sensor.py` coerces them to `float` for measurement sensors.
- If `data` is missing a key (e.g. vehicle offline), `available` returns `False` and HA shows the sensor as unavailable — this is intentional.
