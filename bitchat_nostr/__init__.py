"""
bitchat_nostr — BitChat-over-Nostr transport for Python.

Quickstart:

    from bitchat_nostr import RelayClient, build_dm_rumor, extract_packet_from_event
    from bitchat_nostr import RelayConfig, NostrFilter, NostrKind
"""

from .types import (
    NostrEvent,
    NostrRumor,
    NostrKind,
    EmbeddedBitChatPayload,
    RelayConfig,
    NostrFilter,
)
from .embed import (
    encode_packet_to_base64,
    decode_packet_from_base64,
    extract_packet_from_event,
    build_dm_rumor,
    build_geohash_presence_event,
)
from .wrap import (
    CryptoProvider,
    serialize_event,
    seal_rumor,
    gift_wrap,
    unwrap_gift,
    unseal_rumor,
    wrap_and_send,
    receive_and_unwrap,
)
from .relay import (
    RelayClient,
    connect_to_relay,
    EventHandler,
    EoseHandler,
    PublishOkHandler,
    ReconnectHandler,
    ErrorHandler,
)

__version__ = "0.1.0"

__all__ = [
    # Types
    "NostrEvent",
    "NostrRumor",
    "NostrKind",
    "EmbeddedBitChatPayload",
    "RelayConfig",
    "NostrFilter",
    # Embed
    "encode_packet_to_base64",
    "decode_packet_from_base64",
    "extract_packet_from_event",
    "build_dm_rumor",
    "build_geohash_presence_event",
    # Wrap
    "CryptoProvider",
    "serialize_event",
    "seal_rumor",
    "gift_wrap",
    "unwrap_gift",
    "unseal_rumor",
    "wrap_and_send",
    "receive_and_unwrap",
    # Relay
    "RelayClient",
    "connect_to_relay",
    # Relay handler types
    "EventHandler",
    "EoseHandler",
    "PublishOkHandler",
    "ReconnectHandler",
    "ErrorHandler",
]
