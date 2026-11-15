"""Client for the Jobs app's AI switch (POST/GET /api/ai-switch on the Jobs server)."""

import asyncio

import aiohttp

TIMEOUT = aiohttp.ClientTimeout(total=15)


class JobsAiError(Exception):
    """The Jobs server could not be reached or answered with an error."""


class JobsAiAuthError(JobsAiError):
    """The secret was refused (it must match AI_SWITCH_SECRET on the server)."""


class JobsAiNoSwitchError(JobsAiError):
    """The server has no AI switch (AI_SWITCH_SECRET isn't set there)."""


class JobsAiClient:
    """Reads and sets the Jobs AI switch."""

    def __init__(self, session: aiohttp.ClientSession, url: str, secret: str) -> None:
        self._session = session
        self._url = url.rstrip("/") + "/api/ai-switch"
        self._headers = {"X-Ai-Switch-Secret": secret}

    async def _request(self, method: str, body: dict | None = None) -> dict:
        try:
            async with self._session.request(
                method,
                self._url,
                json=body,
                headers=self._headers,
                timeout=TIMEOUT,
                allow_redirects=False,
            ) as response:
                if response.status == 401:
                    raise JobsAiAuthError("The secret was refused")
                if response.status == 404:
                    raise JobsAiNoSwitchError("The Jobs server has no AI switch")
                if response.status >= 300:
                    raise JobsAiError(f"The Jobs server answered {response.status}")
                return await response.json()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise JobsAiError(str(err) or type(err).__name__) from err

    async def async_get_state(self) -> dict:
        """on, until, secondsLeft, asked ({at, by} or None), denied."""
        return await self._request("GET")

    async def async_turn_on(self, minutes: int) -> dict:
        """Turn AI on for `minutes` (the server allows 15 at most)."""
        return await self._request("POST", {"on": True, "minutes": minutes})

    async def async_turn_off(self) -> dict:
        """Turn AI off now."""
        return await self._request("POST", {"on": False})

    async def async_deny(self) -> dict:
        """Answer a waiting ask with no."""
        return await self._request("POST", {"deny": True})
