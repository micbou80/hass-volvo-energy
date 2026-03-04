"""Constants for the Volvo Energy integration."""

DOMAIN = "volvo_energy"

# Volvo API
API_BASE_URL = "https://api.volvocars.com/energy/v2"
TOKEN_URL = "https://volvoid.eu.volvocars.com/as/token.oauth2"
AUTH_URL = "https://volvoid.eu.volvocars.com/as/authorization.oauth2"

OAUTH_SCOPES = [
    "openid",
    "profile",
    "email",
    "conve:battery_charge_level",
    "conve:electric_range",
    "conve:charging_connection_status",
    "conve:charging_system_status",
    "conve:estimated_charging_time",
    "conve:charging_current_limit",
    "conve:target_battery_charge_level",
]

# Config entry keys
CONF_VCC_API_KEY = "vcc_api_key"
CONF_CLIENT_ID = "client_id"
CONF_CLIENT_SECRET = "client_secret"
CONF_VIN = "vin"
CONF_ACCESS_TOKEN = "access_token"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_TOKEN_EXPIRES_AT = "token_expires_at"

# Polling
DEFAULT_UPDATE_INTERVAL = 300  # seconds (5 minutes)

# Token refresh buffer — refresh if token expires within this many seconds
TOKEN_REFRESH_BUFFER = 60
