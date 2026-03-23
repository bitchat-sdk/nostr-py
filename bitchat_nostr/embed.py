"""
BitChat-over-Nostr embedding helpers.

BitChat binary packets are embedded in Nostr events as base64-encoded content.
"""

from __future__ import annotations

import base64
import time
from typing import Optional

from bitchat_protocol import decode as decode_packet, bytes_to_hex

from .types import EmbeddedBitChatPayload, NostrEvent, NostrKind, NostrRumor


def encode_packet_to_base64(packet_bytes: bytes) -> str:
    """Encode a BitChat binary packet to base64 for embedding in a Nostr event."""
    return base64.b64encode(packet_bytes).decode("ascii")


def decode_packet_from_base64(content: str) -> Optional[bytes]:
    """Decode base64 content to raw packet bytes.

    Returns None if the content is not valid base64.
    Does NOT validate that the bytes form a valid BitChat packet — call
    bitchat_protocol.decode() on the returned bytes for that.
    """
    try:
        return base64.b64decode(content, validate=True)
    except Exception:
        return None


def extract_packet_from_event(event: NostrEvent) -> Optional[EmbeddedBitChatPayload]:
    """Decode a BitChat packet from the content of a received Nostr event.

    Returns None if the event content does not contain a valid BitChat packet.
    """
    raw = decode_packet_from_base64(event.content)
    if raw is None:
        return None
    packet = decode_packet(raw)
    if packet is None:
        return None

    sender_id_hex: Optional[str] = None
    if packet.sender_id and len(packet.sender_id) >= 8:
        sender_id_hex = bytes_to_hex(packet.sender_id)

    return EmbeddedBitChatPayload(
        packet=raw,
        event=event,
        sender_id_hex=sender_id_hex,
    )


def build_dm_rumor(
    packet_bytes: bytes,
    sender_pubkey: str,
    recipient_pubkey: str,
) -> NostrRumor:
    """Build an unsigned NIP-17 DM rumor (kind 14) containing a BitChat packet.

    The caller must seal (kind 13) and gift-wrap (kind 1059) before publishing.
    See wrap.py for those operations.
    """
    return NostrRumor(
        pubkey=sender_pubkey,
        created_at=int(time.time()),
        kind=int(NostrKind.DM),
        tags=[["p", recipient_pubkey]],
        content=encode_packet_to_base64(packet_bytes),
    )


def build_geohash_presence_event(
    packet_bytes: bytes,
    sender_pubkey: str,
    geohash: str,
) -> NostrRumor:
    """Build an unsigned kind 20001 GeohashPresence event embedding a BitChat announce packet."""
    return NostrRumor(
        pubkey=sender_pubkey,
        created_at=int(time.time()),
        kind=int(NostrKind.GEOHASH_PRESENCE),
        tags=[["g", geohash]],
        content=encode_packet_to_base64(packet_bytes),
    )
