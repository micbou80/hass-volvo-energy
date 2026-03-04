"""Volvo Energy API v2 client."""
from __future__ import annotations

import base64
import hashlib
import logging
import secrets
import time
from typing import Any

import aiohttp

from .const import API_BASE_URL, TOKEN_URL

_LOGGER = logging.getLogger(__name__)


class VolvoAuthError(Exception):
    """Raised when authentication fails (401/403)."""


class VolvoAPIError(Exception):
    """Raised when the API returns an unexpected error."""


class VolvoEnergyAPI:
    """Client for the Volvo Energy API v2."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        vcc_api_key: str,
        access_token: str,
    ) -> None:
        self._session = session
        self._vcc_api_key = vcc_api_key
        self._access_token = access_token

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._access_token}",
            "vcc-api-key": self._vcc_api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def update_access_token(self, access_token: str) -> None:
        """Update the access token (called after a refresh)."""
        self._access_token = access_token

    async def get_energy_state(self, vin: str) -> dict[str, Any]:
        """Fetch the full energy state for a vehicle.

        Returns the contents of the 'data' key from the API response.
        Raises VolvoAuthError on 401/403, VolvoAPIError on other failures.
        """
        url = f"{API_BASE_URL}/vehicles/{vin}/state"
        try:
            async with self._session.get(url, headers=self._headers) as resp:
                if resp.status in (401, 403):
                    raise VolvoAuthError(f"Authentication error: HTTP {resp.status}")
                if resp.status != 200:
                    body = await resp.text()
                    raise VolvoAPIError(
                        f"API returned HTTP {resp.status}: {body[:200]}"
                    )
                payload = await resp.json()
                return payload.get("data", payload)
        except aiohttp.ClientError as err:
            raise VolvoAPIError(f"Network error: {err}") from err

    # ------------------------------------------------------------------
    # Static OAuth2 helpers
    # ------------------------------------------------------------------

    @staticmethod
    def generate_pkce() -> tuple[str, str]:
        """Generate a PKCE code_verifier and code_challenge pair.

        Returns:
            (code_verifier, code_challenge)
        """
        code_verifier = secrets.token_urlsafe(64)
        digest = hashlib.sha256(code_verifier.encode()).digest()
        code_challenge = (
            base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
        )
        return code_verifier, code_challenge

    @staticmethod
    async def exchange_code(
        session: aiohttp.ClientSession,
        client_id: str,
        client_secret: str,
        code: str,
        redirect_uri: str,
        code_verifier: str,
    ) -> dict[str, Any]:
        """Exchange an authorization code for access + refresh tokens.

        Returns dict with keys: access_token, refresh_token, expires_in.
        Raises VolvoAuthError on failure.
        """
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret,
            "code_verifier": code_verifier,
        }
        try:
            async with session.post(
                TOKEN_URL,
                data=data,
                headers={"Accept": "application/json"},
            ) as resp:
                payload = await resp.json()
                if resp.status != 200:
                    error = payload.get("error_description", payload.get("error", "unknown"))
                    raise VolvoAuthError(f"Token exchange failed: {error}")
                payload["expires_at"] = time.time() + payload.get("expires_in", 3600)
                return payload
        except aiohttp.ClientError as err:
            raise VolvoAuthError(f"Network error during token exchange: {err}") from err

    @staticmethod
    async def refresh_access_token(
        session: aiohttp.ClientSession,
        client_id: str,
        client_secret: str,
        refresh_token: str,
    ) -> dict[str, Any]:
        """Use a refresh token to obtain a new access token.

        Returns dict with keys: access_token, refresh_token, expires_in, expires_at.
        Raises VolvoAuthError on failure.
        """
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
        }
        try:
            async with session.post(
                TOKEN_URL,
                data=data,
                headers={"Accept": "application/json"},
            ) as resp:
                payload = await resp.json()
                if resp.status != 200:
                    error = payload.get("error_description", payload.get("error", "unknown"))
                    raise VolvoAuthError(f"Token refresh failed: {error}")
                payload["expires_at"] = time.time() + payload.get("expires_in", 3600)
                return payload
        except aiohttp.ClientError as err:
            raise VolvoAuthError(f"Network error during token refresh: {err}") from err
