"""
Async Nostr relay client for BitChat-over-Nostr transport.

Implements NIP-01 WebSocket protocol using `websockets`.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable, Coroutine
from typing import Any, Optional

import websockets
from websockets.asyncio.client import ClientConnection

from .types import NostrEvent, NostrFilter, RelayConfig

log = logging.getLogger(__name__)

EventHandler = Callable[[NostrEvent, str], Coroutine[Any, Any, None]]
EoseHandler = Callable[[str], Coroutine[Any, Any, None]]
PublishOkHandler = Callable[[str, bool, str], None]       # (event_id, ok, message)
ReconnectHandler = Callable[[int, float], None]           # (attempt, delay_seconds)
ErrorHandler = Callable[[Exception], None]


class RelayClient:
    """Async Nostr relay client.

    Usage::

        async with RelayClient(RelayConfig(url='wss://relay.example.com')) as relay:
            await relay.subscribe('sub-1', [NostrFilter(kinds=[1059])], on_event)
            # ... relay.publish(event)
    """

    def __init__(
        self,
        config: RelayConfig,
        *,
        connect_timeout: float = 5.0,
        publish_timeout: float = 3.0,
        max_reconnect_attempts: int = 3,
        reconnect_base_delay: float = 1.0,
    ) -> None:
        self.config = config
        self.connect_timeout = connect_timeout
        self.publish_timeout = publish_timeout
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_base_delay = reconnect_base_delay

        self._ws: Optional[ClientConnection] = None
        self._subscriptions: dict[str, EventHandler] = {}
        self._eose_handlers: dict[str, EoseHandler] = {}
        self._pending_ok: dict[str, asyncio.Future[bool]] = {}
        self._recv_task: Optional[asyncio.Task[None]] = None
        self._reconnect_attempts = 0
        self._closed = False

        # --- Observability hooks ---
        # Set any of these before connecting to receive lifecycle events.

        #: Called when the WebSocket connection opens.
        self.on_connect: Optional[Callable[[], None]] = None
        #: Called when the connection closes. Argument is the WS close code (int).
        self.on_disconnect: Optional[Callable[[int], None]] = None
        #: Called when the relay sends a NOTICE message.
        self.on_notice: Optional[Callable[[str], None]] = None
        #: Called when the relay acknowledges a published event (OK verb).
        #: Signature: on_publish_ok(event_id: str, ok: bool, message: str)
        self.on_publish_ok: Optional[PublishOkHandler] = None
        #: Called for every inbound EVENT *before* routing to subscription handlers.
        #: Signature: on_event(event: NostrEvent, subscription_id: str)
        self.on_event: Optional[Callable[[NostrEvent, str], None]] = None
        #: Called for every EOSE *before* invoking the per-subscription handler.
        #: Signature: on_eose(subscription_id: str)
        self.on_eose: Optional[Callable[[str], None]] = None
        #: Called when a reconnect is scheduled. Args: (attempt: int, delay_seconds: float)
        self.on_reconnect: Optional[ReconnectHandler] = None
        #: Called on unhandled recv-loop errors.
        self.on_error: Optional[ErrorHandler] = None

        # --- Metrics counters ---
        #: Total events received across all subscriptions since construction.
        self.events_received: int = 0
        #: Total events published since construction.
        self.events_published: int = 0

    async def connect(self) -> None:
        """Connect to the relay WebSocket."""
        self._ws = await asyncio.wait_for(
            websockets.connect(self.config.url),
            timeout=self.connect_timeout,
        )
        self._reconnect_attempts = 0
        if self.on_connect:
            self.on_connect()
        self._recv_task = asyncio.create_task(self._recv_loop())

    async def close(self) -> None:
        """Close the connection. No automatic reconnect after this."""
        self._closed = True
        if self._recv_task:
            self._recv_task.cancel()
        if self._ws:
            await self._ws.close()
            self._ws = None

    async def __aenter__(self) -> "RelayClient":
        await self.connect()
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    async def publish(self, event: NostrEvent) -> bool:
        """Publish an event to the relay.

        Returns True if the relay acknowledges with OK=true, False if rejected.
        Raises TimeoutError on timeout.
        """
        if not (self.config.write):
            raise PermissionError("This relay connection is read-only")

        loop = asyncio.get_event_loop()
        future: asyncio.Future[bool] = loop.create_future()
        self._pending_ok[event.id] = future

        await self._send(["EVENT", event.to_dict()])
        self.events_published += 1
        try:
            return await asyncio.wait_for(future, timeout=self.publish_timeout)
        except asyncio.TimeoutError:
            self._pending_ok.pop(event.id, None)
            raise TimeoutError(f"Publish timed out for event {event.id}")

    async def subscribe(
        self,
        subscription_id: str,
        filters: list[NostrFilter],
        on_event: EventHandler,
        on_eose: Optional[EoseHandler] = None,
    ) -> None:
        """Subscribe to events matching the given filters."""
        if not self.config.read:
            raise PermissionError("This relay connection is write-only")
        self._subscriptions[subscription_id] = on_event
        if on_eose:
            self._eose_handlers[subscription_id] = on_eose
        await self._send(["REQ", subscription_id, *[f.to_dict() for f in filters]])

    async def unsubscribe(self, subscription_id: str) -> None:
        """Unsubscribe from a subscription."""
        self._subscriptions.pop(subscription_id, None)
        self._eose_handlers.pop(subscription_id, None)
        await self._send(["CLOSE", subscription_id])

    async def _send(self, message: list[Any]) -> None:
        if self._ws is not None:
            await self._ws.send(json.dumps(message, separators=(",", ":")))

    async def _recv_loop(self) -> None:
        assert self._ws is not None
        try:
            async for raw in self._ws:
                await self._handle_message(str(raw))
        except (websockets.ConnectionClosed, asyncio.CancelledError):
            pass
        except Exception as e:
            log.error("relay recv error: %s", e)
            if self.on_error:
                self.on_error(e)
        finally:
            if not self._closed:
                await self._schedule_reconnect()

    async def _handle_message(self, raw: str) -> None:
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            return
        if not isinstance(msg, list) or len(msg) < 2:
            return

        verb = msg[0]

        if verb == "EVENT" and len(msg) >= 3:
            sub_id, event_dict = msg[1], msg[2]
            if isinstance(event_dict, dict):
                event = NostrEvent.from_dict(event_dict)
                self.events_received += 1
                if self.on_event:
                    self.on_event(event, sub_id)
                handler = self._subscriptions.get(sub_id)
                if handler:
                    await handler(event, sub_id)

        elif verb == "EOSE" and len(msg) >= 2:
            sub_id = msg[1]
            if self.on_eose:
                self.on_eose(str(sub_id))
            eose_handler = self._eose_handlers.get(sub_id)
            if eose_handler:
                await eose_handler(sub_id)

        elif verb == "OK" and len(msg) >= 3:
            event_id, ok = msg[1], msg[2]
            ok_message = str(msg[3]) if len(msg) >= 4 else ""
            if self.on_publish_ok:
                self.on_publish_ok(str(event_id), bool(ok), ok_message)
            future = self._pending_ok.pop(event_id, None)
            if future and not future.done():
                future.set_result(bool(ok))

        elif verb == "NOTICE" and len(msg) >= 2:
            if self.on_notice:
                self.on_notice(str(msg[1]))

    async def _schedule_reconnect(self) -> None:
        if self._closed or self._reconnect_attempts >= self.max_reconnect_attempts:
            return
        self._reconnect_attempts += 1
        delay = self.reconnect_base_delay * (2 ** (self._reconnect_attempts - 1))
        if self.on_reconnect:
            self.on_reconnect(self._reconnect_attempts, delay)
        await asyncio.sleep(delay)
        try:
            await self.connect()
        except Exception as e:
            log.warning("reconnect failed: %s", e)
            if self.on_error:
                self.on_error(e)


async def connect_to_relay(url: str, **kwargs: Any) -> RelayClient:
    """Create and connect a relay client. Returns a connected client."""
    client = RelayClient(RelayConfig(url=url), **kwargs)
    await client.connect()
    return client
