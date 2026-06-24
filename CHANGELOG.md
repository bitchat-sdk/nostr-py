# Changelog — bitchat_nostr (Python)

All notable changes follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.2] — 2026-06-12

### Changed
- Constrained the `bitchat-protocol` dependency from `>=0.1.0` to `>=0.2.0,<0.3.0`.
  This guarantees the `RequestSyncPacket` TLV codec (added in protocol-core 0.2.0)
  is present and pins below the next major to avoid silently resolving a future
  breaking release.
- Version is now single-sourced from `bitchat_nostr/__init__.py` via hatch, so
  `pyproject.toml` and `__version__` can no longer drift.

> Version bumped to 0.1.2 to align all four BitChat `nostr` SDKs (Swift, Kotlin,
> TypeScript, Python) on a common version. 0.1.1 was not released for Python.

## [0.1.0] — 2026-03-22

Initial GA release.

### Added
- `RelayClient` — async WebSocket Nostr relay client (NIP-01) built on `websockets`
  - `connect()` / `close()` / async context manager
  - `publish(event)` → `bool` with configurable timeout and `OK` acknowledgement
  - `subscribe(id, filters, on_event, on_eose?)` / `unsubscribe(id)`
  - Exponential back-off reconnect with configurable max attempts
- Observability hooks on `RelayClient`:
  - `on_connect`, `on_disconnect`, `on_notice`, `on_publish_ok`, `on_event`, `on_eose`, `on_reconnect`, `on_error`
  - `events_received` and `events_published` counters
- Handler type aliases: `EventHandler`, `EoseHandler`, `PublishOkHandler`, `ReconnectHandler`, `ErrorHandler`
- `connect_to_relay(url, **kwargs)` — convenience coroutine factory
- NIP-17 Gift Wrap helpers: `seal_rumor()`, `gift_wrap()`, `unwrap_gift()`, `unseal_rumor()`
- `wrap_and_send()` / `receive_and_unwrap()` — end-to-end send/receive with full NIP-17 flow
- `build_dm_rumor()` — construct a kind-14 DM rumor embedding a BitChat packet
- `build_geohash_presence_event()` — construct a geo-tagged presence event
- `encode_packet_to_base64()` / `decode_packet_from_base64()` — Base64 transport encoding
- `extract_packet_from_event(event)` → `EmbeddedBitChatPayload | None`; returns `.packet` (raw bytes), `.event`, `.sender_id_hex`
- `serialize_event()` — canonical NIP-01 JSON serialisation for signing
- `CryptoProvider` abstract base / protocol — inject secp256k1 / Schnorr implementation
- `NostrEvent`, `NostrRumor`, `NostrFilter`, `NostrKind`, `RelayConfig`, `EmbeddedBitChatPayload` dataclasses

### Protocol Compatibility
Compatible with NIP-01, NIP-17. Wire events are interoperable with any standard Nostr relay.

[0.1.0]: https://github.com/bitchat-sdk/nostr-py/releases/tag/v0.1.0

[Unreleased]: https://github.com/bitchat-sdk/nostr-py/compare/v0.1.0...HEAD