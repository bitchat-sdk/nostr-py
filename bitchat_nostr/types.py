"""Nostr types for the BitChat-over-Nostr transport."""

from __future__ import annotations

import dataclasses
from enum import IntEnum
from typing import Any, Optional


@dataclasses.dataclass
class NostrEvent:
    """A raw Nostr event as sent over WebSocket (NIP-01)."""
    id: str            # 32-byte lowercase hex SHA-256 of the serialized event.
    pubkey: str        # 32-byte lowercase hex public key of the event creator.
    created_at: int    # Unix timestamp in seconds.
    kind: int          # Event kind.
    tags: list[list[str]]  # Array of tag arrays.
    content: str       # Event content.
    sig: str           # 64-byte hex Schnorr signature.

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "NostrEvent":
        return cls(
            id=d["id"],
            pubkey=d["pubkey"],
            created_at=d["created_at"],
            kind=d["kind"],
            tags=d["tags"],
            content=d["content"],
            sig=d["sig"],
        )


@dataclasses.dataclass
class NostrRumor:
    """Unsigned Nostr event (rumor) — no id or sig."""
    pubkey: str
    created_at: int
    kind: int
    tags: list[list[str]]
    content: str

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "NostrRumor":
        return cls(
            pubkey=d["pubkey"],
            created_at=d["created_at"],
            kind=d["kind"],
            tags=d["tags"],
            content=d["content"],
        )


class NostrKind(IntEnum):
    """NIP-17 event kinds."""
    DM = 14              # NIP-17 DM rumor (inner message, never published directly).
    SEAL = 13            # NIP-17 Seal (signed by sender).
    GIFT_WRAP = 1059     # NIP-17 Gift Wrap (ephemeral key, published to relay).
    EPHEMERAL_EVENT = 20000   # Ephemeral event for geohash-based presence.
    GEOHASH_PRESENCE = 20001  # Geohash presence broadcast.


@dataclasses.dataclass
class EmbeddedBitChatPayload:
    """A decoded BitChat-over-Nostr embedded payload."""
    packet: bytes               # The raw BitChat binary packet bytes.
    event: NostrEvent           # The Nostr event that carried this payload.
    sender_id_hex: Optional[str] = None  # The senderID from the inner packet (hex).


@dataclasses.dataclass
class RelayConfig:
    """Relay connection configuration."""
    url: str            # WebSocket URL of the relay.
    read: bool = True   # Read operations enabled.
    write: bool = True  # Write operations enabled.


@dataclasses.dataclass
class NostrFilter:
    """Subscription filter (NIP-01)."""
    ids: Optional[list[str]] = None
    authors: Optional[list[str]] = None
    kinds: Optional[list[int]] = None
    since: Optional[int] = None
    until: Optional[int] = None
    limit: Optional[int] = None
    e: Optional[list[str]] = None   # #e tag filter
    p: Optional[list[str]] = None   # #p tag filter

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        if self.ids is not None:
            d["ids"] = self.ids
        if self.authors is not None:
            d["authors"] = self.authors
        if self.kinds is not None:
            d["kinds"] = self.kinds
        if self.since is not None:
            d["since"] = self.since
        if self.until is not None:
            d["until"] = self.until
        if self.limit is not None:
            d["limit"] = self.limit
        if self.e is not None:
            d["#e"] = self.e
        if self.p is not None:
            d["#p"] = self.p
        return d
