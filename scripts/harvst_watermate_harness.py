#!/usr/bin/env python3
"""Standalone harness for exercising the Harvst WaterMate API client."""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import logging
import os
import sys
import time
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aiohttp import ClientSession


def _load_api_module() -> ModuleType:
    module_path = ROOT / "custom_components" / "harvst_watermate" / "api.py"
    spec = importlib.util.spec_from_file_location("harvst_watermate_api", module_path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Unable to load API module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


api_module = _load_api_module()

HarvstWatermateApiClient = api_module.HarvstWatermateApiClient
HarvstWatermateApiClientAuthenticationError = (
    api_module.HarvstWatermateApiClientAuthenticationError
)
HarvstWatermateApiClientCommunicationError = (
    api_module.HarvstWatermateApiClientCommunicationError
)
HarvstWatermateApiClientError = api_module.HarvstWatermateApiClientError
SSEMessage = api_module.SSEMessage

_LOGGER = logging.getLogger(__name__)
_DEFAULT_LOG_LEVEL = "INFO"
_ENV_HOST = "HARVST_WATERMATE_HOST"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Interact with a Harvst WaterMate controller without running the Home Assistant integration."
        )
    )
    parser.add_argument(
        "--host",
        dest="host",
        help=(
            "WaterMate host or IP address. Falls back to the HARVST_WATERMATE_HOST environment variable if omitted."
        ),
    )
    parser.add_argument(
        "--log-level",
        dest="log_level",
        default=_DEFAULT_LOG_LEVEL,
        help="Python logging level (default: %(default)s).",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    events_parser = subparsers.add_parser(
        "events",
        help="Stream events from the controller and print them to stdout.",
    )
    events_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Stop after receiving N events (default: run until interrupted).",
    )
    events_parser.add_argument(
        "--duration",
        type=float,
        default=None,
        help="Stop after approximately N seconds (default: no time limit).",
    )
    events_parser.add_argument(
        "--compact",
        action="store_true",
        help="Render payload JSON on a single line instead of pretty-printing.",
    )
    events_parser.add_argument(
        "--include-meta",
        action="store_true",
        help="Include SSE metadata (event/id/retry) alongside payload output.",
    )

    test_parser = subparsers.add_parser(
        "test",
        help="Check connectivity by requesting the events stream once.",
    )
    test_parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress the payload dump; rely on exit code/logs only.",
    )

    set_output_parser = subparsers.add_parser(
        "set-output",
        help="Toggle a WaterMate output (e.g., pump or valve).",
    )
    set_output_parser.add_argument(
        "output_id",
        help="Identifier of the WaterMate output (for example, 'pump1').",
    )
    set_output_parser.add_argument(
        "state",
        choices=("on", "off"),
        help="Desired state for the output.",
    )

    return parser


class _ClientContext:
    def __init__(self, host: str) -> None:
        self._host = host
        self._session: ClientSession | None = None

    async def __aenter__(self) -> HarvstWatermateApiClient:
        self._session = ClientSession()
        return HarvstWatermateApiClient(self._host, self._session)

    async def __aexit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        if self._session is not None:
            await self._session.close()


def _resolve_host(host_arg: str | None) -> str:
    host = host_arg or os.getenv(_ENV_HOST)
    if not host:
        raise SystemExit(
            "No host provided. Supply --host or set the HARVST_WATERMATE_HOST environment variable."
        )
    return host


def _configure_logging(level: str) -> None:
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO))


def _format_message(message: SSEMessage, *, compact: bool, include_meta: bool) -> str:
    payload_fragment: str
    if message.payload is None:
        payload_fragment = "<no payload>"
    else:
        payload_fragment = json.dumps(
            message.payload,
            indent=None if compact else 2,
            separators=(",", ":") if compact else None,
            sort_keys=not compact,
        )

    if not include_meta:
        return payload_fragment

    meta: dict[str, Any] = {
        "event": message.event,
        "id": message.id,
        "retry": message.retry,
    }
    meta_fragment = json.dumps({k: v for k, v in meta.items() if v is not None})
    return f"meta={meta_fragment} payload={payload_fragment}"


async def _stream_events(
    client: HarvstWatermateApiClient,
    *,
    limit: int | None,
    duration: float | None,
    compact: bool,
    include_meta: bool,
) -> None:
    received = 0
    started = time.monotonic()
    try:
        async for message in client.async_iter_events():
            received += 1
            print(_format_message(message, compact=compact, include_meta=include_meta))
            if limit is not None and received >= limit:
                break
            if duration is not None and (time.monotonic() - started) >= duration:
                break
    except HarvstWatermateApiClientCommunicationError as err:
        _LOGGER.error("Event stream ended due to communication problem: %s", err)
        raise SystemExit(2) from err


async def _test_connection(
    client: HarvstWatermateApiClient,
    *,
    quiet: bool,
) -> None:
    try:
        async for message in client.async_iter_events():
            if not quiet:
                print(_format_message(message, compact=False, include_meta=True))
            break
    except HarvstWatermateApiClientCommunicationError as err:
        _LOGGER.error("Failed to read from events stream: %s", err)
        raise SystemExit(2) from err
    else:
        _LOGGER.info("Successfully received data from WaterMate events stream.")


async def _set_output(
    client: HarvstWatermateApiClient,
    *,
    output_id: str,
    state: str,
) -> None:
    turn_on = state.lower() == "on"
    try:
        await client.async_set_output(output_id, turn_on)
    except HarvstWatermateApiClientError as err:
        _LOGGER.error("Output command failed: %s", err)
        raise SystemExit(2) from err
    else:
        _LOGGER.info("Successfully set %s to %s", output_id, state.lower())


async def _run_with_client(args: argparse.Namespace) -> None:
    host = _resolve_host(args.host)
    try:
        async with _ClientContext(host) as client:
            if args.command == "events":
                await _stream_events(
                    client,
                    limit=args.limit,
                    duration=args.duration,
                    compact=args.compact,
                    include_meta=args.include_meta,
                )
            elif args.command == "test":
                await _test_connection(client, quiet=args.quiet)
            elif args.command == "set-output":
                await _set_output(client, output_id=args.output_id, state=args.state)
            else:
                raise SystemExit(f"Unknown command: {args.command}")
    except HarvstWatermateApiClientAuthenticationError as err:
        _LOGGER.error("Authentication failure: %s", err)
        raise SystemExit(3) from err


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    _configure_logging(args.log_level)

    try:
        asyncio.run(_run_with_client(args))
    except KeyboardInterrupt:
        _LOGGER.info("Interrupted by user")
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
