"""Client for interacting with the Harvst WaterMate device."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

import async_timeout
from aiohttp import ClientError, ClientResponse, ClientSession

_LOGGER = logging.getLogger(__name__)

EVENT_HEADERS = {
    "Accept": "text/event-stream",
    "User-Agent": "Mozilla/5.0 (Home Assistant Integration)",
}

CONTROL_HEADERS = {
    "Accept": "*/*",
    "User-Agent": "Mozilla/5.0 (Home Assistant Integration)",
}

_TIMEOUT = 15
_CONNECTION_TEST_TIMEOUT = 30
_MAX_LOG_CHARS = 200
_REDACTED = "***REDACTED***"
_SENSITIVE_KEYS = {"token", "password", "secret", "auth", "key", "session"}


def _shorten(value: Any) -> str:
    """Return a compact representation suitable for logging."""
    string_value = json.dumps(value, default=str) if not isinstance(value, str) else value
    if len(string_value) <= _MAX_LOG_CHARS:
        return string_value
    return f"{string_value[: _MAX_LOG_CHARS - 3]}..."


def _redact(value: Any) -> Any:
    """Redact sensitive values from payloads destined for logs."""
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if any(sensitive in key.lower() for sensitive in _SENSITIVE_KEYS):
                redacted[key] = _REDACTED
            else:
                redacted[key] = _redact(item)
        return redacted
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def _format_payload_for_log(value: Any) -> str:
    """Return a sanitized, truncated representation for logging."""
    try:
        sanitized = _redact(value)
    except TypeError:
        sanitized = value
    return _shorten(sanitized)


@dataclass(slots=True)
class _RawSSEMessage:
    """Internal container for raw SSE messages."""

    data: str
    event: str | None = None
    id: str | None = None
    retry: int | None = None


@dataclass(slots=True)
class SSEMessage:
    """Structured SSE message yielded to consumers."""

    payload: dict[str, Any] | None
    event: str | None = None
    id: str | None = None
    retry: int | None = None


class _SSEParser:
    """Parse raw SSE streams into discrete messages."""

    def __init__(self) -> None:
        self._buffer = ""
        self._reset_message()

    def feed(self, chunk: bytes) -> list[_RawSSEMessage]:
        """Consume a chunk of bytes and return completed messages."""
        text = chunk.decode("utf-8", errors="ignore")
        self._buffer += text
        messages: list[_RawSSEMessage] = []

        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            line = line.rstrip("\r")
            message = self._process_line(line)
            if message:
                messages.append(message)

        return messages

    def flush(self) -> list[_RawSSEMessage]:
        """Flush any buffered message when the stream closes."""
        tail = self._process_line("")
        return [tail] if tail else []

    def _process_line(self, line: str) -> _RawSSEMessage | None:
        if line == "":
            if not self._data and self._event is None and self._id is None and self._retry is None:
                self._reset_message()
                return None
            message = _RawSSEMessage(
                data="\n".join(self._data),
                event=self._event or None,
                id=self._id or None,
                retry=self._retry,
            )
            self._reset_message()
            return message

        if line.startswith(":"):
            return None

        if ":" in line:
            field, value = line.split(":", 1)
            value = value.lstrip()
        else:
            field, value = line, ""

        if field == "data":
            self._data.append(value)
        elif field == "event":
            self._event = value
        elif field == "id":
            self._id = value
        elif field == "retry":
            try:
                self._retry = int(value)
            except ValueError:
                self._retry = None

        return None

    def _reset_message(self) -> None:
        self._data: list[str] = []
        self._event: str | None = None
        self._id: str | None = None
        self._retry: int | None = None



class HarvstWatermateApiClientError(Exception):
    """Base error for WaterMate API issues."""


class HarvstWatermateApiClientCommunicationError(HarvstWatermateApiClientError):
    """Raised when communication with the WaterMate device fails."""


class HarvstWatermateApiClientAuthenticationError(HarvstWatermateApiClientError):
    """Raised when the WaterMate device rejects our credentials."""


class HarvstWatermateApiClient:
    """Simple API client to interact with the WaterMate controller."""

    def __init__(self, host: str, session: ClientSession) -> None:
        """Initialize the client."""
        # Strip any scheme prefix the user may have included
        normalized = host
        for prefix in ("http://", "https://"):
            if normalized.lower().startswith(prefix):
                normalized = normalized[len(prefix):]
                break
        # Also strip any trailing slashes
        self._host = normalized.rstrip("/")
        self._session = session

    @property
    def _events_url(self) -> str:
        return f"http://{self._host}/events"

    @property
    def _control_url(self) -> str:
        return f"http://{self._host}/control"

    async def async_set_output(self, output_id: str, turn_on: bool) -> None:
        """Control one of the WaterMate outputs."""
        command = f"{output_id}{'On' if turn_on else 'Off'}"
        params = {"do": command}

        async with self._request(
            description=f"sending control command '{command}'",
            url=self._control_url,
            headers=CONTROL_HEADERS,
            params=params,
        ):
            _LOGGER.debug("Sent WaterMate command '%s'", command)

    async def async_test_connection(self) -> None:
        """Validate we can reach the device."""
        try:
            async with async_timeout.timeout(_CONNECTION_TEST_TIMEOUT):
                async for message in self.async_iter_events():
                    _LOGGER.debug(
                        "Connection test received payload from WaterMate: %s",
                        _format_payload_for_log(message.payload),
                    )
                    return
        except asyncio.TimeoutError as err:
            raise HarvstWatermateApiClientCommunicationError(
                "Timed out waiting for data from WaterMate events stream"
            ) from err
        raise HarvstWatermateApiClientCommunicationError(
            "No data received from WaterMate events stream"
        )

    async def _raise_for_status(self, response: ClientResponse) -> None:
        """Validate the response status code."""
        if response.status == 401:
            _LOGGER.error("WaterMate rejected credentials for host %s", self._host)
            raise HarvstWatermateApiClientAuthenticationError("Invalid credentials")

        if response.status >= 400:
            text = await response.text()
            _LOGGER.warning(
                "WaterMate responded with %s to %s: %s",
                response.status,
                response.real_url,
                _format_payload_for_log(text),
            )
            raise HarvstWatermateApiClientCommunicationError(
                f"WaterMate responded with {response.status}: {text}"
            )

    @asynccontextmanager
    async def _request(
        self,
        *,
        description: str,
        url: str,
        headers: dict[str, str],
        params: dict[str, Any] | None = None,
    ) -> AsyncIterator[ClientResponse]:
        response: ClientResponse | None = None
        try:
            _LOGGER.debug("Opening session for %s", description)
            async with async_timeout.timeout(_TIMEOUT):
                response = await self._session.get(
                    url,
                    headers=headers,
                    params=params,
                    ssl=False,
                )
            await self._raise_for_status(response)
            yield response
        except HarvstWatermateApiClientError:
            raise
        except ClientError as err:
            _LOGGER.warning("Communication error while %s: %s", description, err)
            raise HarvstWatermateApiClientCommunicationError(
                f"Communication error while {description}: {err}"
            ) from err
        except asyncio.TimeoutError as err:
            _LOGGER.warning("Timed out while %s", description)
            raise HarvstWatermateApiClientCommunicationError(
                f"Timed out while {description}"
            ) from err
        finally:
            if response is not None and not response.closed:
                response.release()

    async def async_iter_events(self) -> AsyncIterator[SSEMessage]:
        """Iterate over the live SSE event stream."""
        async with self._request(
            description="opening events stream",
            url=self._events_url,
            headers=EVENT_HEADERS,
        ) as response:
            parser = _SSEParser()
            async for chunk in response.content.iter_chunked(1024):
                for raw_message in parser.feed(chunk):
                    parsed = self._convert_message(raw_message)
                    if parsed:
                        yield parsed
            for raw_message in parser.flush():
                parsed = self._convert_message(raw_message)
                if parsed:
                    yield parsed

    async def async_listen_events(
        self,
        callback: Callable[[SSEMessage], Awaitable[None] | None],
        *,
        stop_event: asyncio.Event,
    ) -> None:
        """Listen to events until the stop event is set."""
        async for message in self.async_iter_events():
            if stop_event.is_set():
                return
            result = callback(message)
            if asyncio.iscoroutine(result):
                await result
        # Connection terminated without stop_event; allow caller to decide on retries.

    def _convert_message(self, message: _RawSSEMessage) -> SSEMessage | None:
        if not message.data:
            if message.retry is not None:
                _LOGGER.debug("Received retry hint from WaterMate: %sms", message.retry)
                return SSEMessage(
                    payload=None,
                    event=message.event,
                    id=message.id,
                    retry=message.retry,
                )
            return None

        loggable_payload = message.data
        handshake = message.data.strip().lower()
        if handshake in {"hello!", "ping", ""}:
            _LOGGER.debug("Ignoring handshake message from WaterMate: %s", handshake)
            return None
        try:
            payload = json.loads(message.data)
        except json.JSONDecodeError:
            _LOGGER.warning(
                "Received malformed JSON from WaterMate: %s",
                _format_payload_for_log(loggable_payload),
            )
            return None

        _LOGGER.debug(
            "Received update from WaterMate: %s",
            _format_payload_for_log(payload),
        )

        return SSEMessage(
            payload=payload,
            event=message.event,
            id=message.id,
            retry=message.retry,
        )