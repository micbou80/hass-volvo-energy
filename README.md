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

## Step 1 — Set up the Volvo Cars Developer Portal

Before installing the integration, you need to create and **publish** an application on the Volvo Cars Developer Portal. This is a one-time setup that gives you the credentials the integration needs.

### 1.1 Create an account and application

1. Go to [developer.volvocars.com](https://developer.volvocars.com/) and sign in (or create an account). Use a regular browser — avoid private/incognito mode as it can cause "Invalid Session" errors.
2. Create a new application.
3. Subscribe the application to the **Energy API v2**.

### 1.2 Note your VCC API Key

On the application details page (before publishing), you will see:

- **Primary key** — also labelled "VSS API key" or "VCC API key Primary"
- **Secondary key** — the backup/rotation copy

These are identical in function. **Copy the Primary key** — this is your **VCC API Key** for the integration.

> The Primary and Secondary keys are just two copies of the same credential for rotation purposes. You can use either one, but Primary is recommended.

### 1.3 Add the OAuth Redirect URI

Before publishing, add your Home Assistant URL as an OAuth Redirect URI:

```
https://<your-home-assistant-url>/api/volvo_energy/oauth2callback
```

Replace `<your-home-assistant-url>` with your HA instance's externally reachable URL. Examples:
- `https://homeassistant.local:8123/api/volvo_energy/oauth2callback` (local LAN access)
- `https://abcdef.ui.nabu.casa/api/volvo_energy/oauth2callback` (Nabu Casa / Home Assistant Cloud)

> **Tip:** Check your exact URL in Home Assistant under **Settings → System → Network → Home Assistant URL**.

### 1.4 Publish the application to get Client ID and Client Secret

> **This step is required.** Client ID and Client Secret are only generated when you publish.

1. Make sure all **Scopes** are selected — expand every section to see them all.
2. Click **Publish**.
3. Fill in the required fields in the form that appears.
4. On the confirmation screen, you will see your **Client ID** and **Client Secret**.
5. **Copy both immediately** — the Client Secret may only be shown once.

> If you see an "Invalid Session" error during this step, log out of the portal and log back in using a normal browser window (not private/incognito), then try again. This is a known portal issue.

---

## Step 2 — Install the Integration

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

## Step 3 — Configure in Home Assistant

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **Volvo Energy**.
3. Fill in the form:

   | Field | Where to find it |
   |-------|-----------------|
   | **VCC API Key** | Primary key on the app details page (Step 1.2) |
   | **Client ID** | From the Publish confirmation screen (Step 1.4) |
   | **Client Secret** | From the Publish confirmation screen (Step 1.4) |
   | **Vehicle VIN** | Your car's 17-character VIN (see door frame, dashboard, or your Volvo app) |

4. Click **Submit**. You will be redirected to the Volvo Cars login page.
5. Sign in with the **Volvo Cars account that owns the vehicle**.
6. After successful authentication, Home Assistant will create the integration and all 7 sensors will appear.

### Adding multiple vehicles

Repeat Step 3 for each vehicle using its own VIN. Each vehicle appears as a separate device in Home Assistant.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Invalid Session" on the Developer Portal | Log out, close all portal tabs, re-open in a normal (non-incognito) browser window, and log back in. |
| "I can't find Client ID/Secret" | They only appear on the **Publish confirmation screen** (Step 1.4). If you already published without saving them, you may need to create a new application. |
| OAuth redirect fails / blank page | Ensure the redirect URI is registered **exactly** as `https://<ha-url>/api/volvo_energy/oauth2callback` in your app settings. |
| `Authentication failed` error | Double-check your Client ID, Client Secret, and VCC API Key. |
| Sensors show as unavailable | The vehicle may be offline or sleeping. Sensors will update when data is next available. |
| `Token refresh failed` | Your refresh token has expired (valid for 7 days without use). Re-add the integration to re-authenticate. |
| Rate limit errors | The 5-minute polling interval uses ~288 calls/day, well within the 10,000/day limit. |

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
