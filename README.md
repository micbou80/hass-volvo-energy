# Volvo Energy — Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

A [Home Assistant](https://www.home-assistant.io/) custom integration that exposes your Volvo electric vehicle's energy data as sensors, using the official [Volvo Energy API v2](https://developer.volvocars.com/apis/energy/v2/overview/).

## Sensors

| Sensor | Description | Unit |
|--------|-------------|------|
| Battery Charge Level | Current state of charge | % |
| Electric Range | Estimated remaining range | km |
| Estimated Charging Time | Minutes until fully charged | min |
| Target Battery Charge Level | Configured charge target | % |
| Charging Connection Status | e.g. `CONNECTED_AC`, `DISCONNECTED` | — |
| Charging System Status | e.g. `CHARGING`, `IDLE`, `DONE` | — |
| Charging Current Limit | e.g. `A_16`, `A_32` | — |

All sensors are grouped under a single device named **Volvo `<VIN>`** in Home Assistant.

Data is polled every **5 minutes** (within the API's rate limits of 10,000 calls/day).

---

## Prerequisites

Before installing, you need a **Volvo Cars Developer Portal** account and an application set up there:

1. Go to [developer.volvocars.com](https://developer.volvocars.com/) and sign in (or create an account).
2. Create a new application.
3. On the application page, subscribe to the **Energy API v2**.
4. Note down:
   - **VCC API Key** (shown on the application details page)
   - **Client ID**
   - **Client Secret**
5. Add the following as an **OAuth 2.0 Redirect URI** in your application settings:

   ```
   https://<your-home-assistant-url>/auth/external/callback
   ```

   Replace `<your-home-assistant-url>` with your HA instance's externally reachable URL (e.g. `https://homeassistant.local:8123` for local setups or your Nabu Casa URL).

   > **Tip:** If you are unsure of your HA URL, check **Settings → System → Network** in Home Assistant.

---

## Installation

### Via HACS (recommended)

1. Open HACS in your Home Assistant instance.
2. Go to **Integrations** → click the three-dot menu → **Custom repositories**.
3. Add `https://github.com/micbou80/hass-volvo-energy` as a repository of type **Integration**.
4. Search for **Volvo Energy** and click **Download**.
5. Restart Home Assistant.

### Manual installation

1. Copy the `custom_components/volvo_energy` folder into your Home Assistant `config/custom_components/` directory.
2. Restart Home Assistant.

---

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **Volvo Energy**.
3. Fill in the form:
   - **VCC API Key** — from the Volvo Developer Portal
   - **Client ID** — from the Volvo Developer Portal
   - **Client Secret** — from the Volvo Developer Portal
   - **Vehicle VIN** — the 17-character VIN of your vehicle
4. Click **Submit**. You will be redirected to the Volvo Cars login page.
5. Sign in with the **Volvo Cars account that owns the vehicle**.
6. After successful authentication, Home Assistant will create the integration and all sensors will appear within a few seconds.

### Adding multiple vehicles

Repeat the configuration steps above for each vehicle, using its own VIN. Each vehicle will appear as a separate device in Home Assistant.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| OAuth redirect fails / blank page | Ensure the redirect URI `https://<ha-url>/auth/external/callback` is registered exactly in the Volvo Developer Portal. |
| `Authentication failed` error | Double-check your Client ID, Client Secret, and VCC API Key. |
| Sensors show as unavailable | The vehicle may be offline or sleeping. The sensors will update when data is next available. |
| `Token refresh failed` | Your refresh token has expired (valid for 7 days without a refresh). Re-add the integration to re-authenticate. |
| Rate limit errors | The default 5-minute polling interval is well within the 10,000 calls/day limit. If you have multiple vehicles, this still applies comfortably. |

---

## API Reference

- [Volvo Energy API v2 Overview](https://developer.volvocars.com/apis/energy/v2/overview/)
- [Volvo Developer Portal](https://developer.volvocars.com/)
- [API Rate Limits](https://developer.volvocars.com/news/api-rate-limits/)

---

## Contributing

Pull requests are welcome. Please open an issue first to discuss significant changes.

## Licence

MIT
