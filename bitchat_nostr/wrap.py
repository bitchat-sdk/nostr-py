"""
NIP-17 Gift Wrap helpers.

NIP-17 provides private direct messages via a double-encryption scheme:

  DM rumor (kind 14, unsigned) — the actual message
    └── Sealed (kind 13, signed by sender) — rumor encrypted to recipient
          └── Gift Wrap (kind 1059, ephemeral key) — seal encrypted to recipient
                └── Published to relay

Encryption primitives are injected via the CryptoProvider protocol
so this package does not hard-depend on a specific crypto library.
"""

from __future__ import annotations

import json
import time
from typing import Optional, Protocol

from .types import NostrEvent, NostrKind, NostrRumor


class CryptoProvider(Protocol):
    """Protocol for NIP-44 encryption operations.

    Implement using a secp256k1 library (e.g. pynostr, nostr-sdk-python).
    """

    def nip44_encrypt(
        self, plaintext: str, sender_privkey: bytes, recipient_pubkey: str
    ) -> str:
        """NIP-44 encrypt plaintext. Returns base64-encoded ciphertext."""
        ...

    def nip44_decrypt(
        self, ciphertext: str, recipient_privkey: bytes, sender_pubkey: str
    ) -> Optional[str]:
        """NIP-44 decrypt ciphertext. Returns plaintext or None on failure."""
        ...

    def get_public_key(self, private_key: bytes) -> str:
        """Derive a Nostr public key (64-char hex) from a 32-byte private key."""
        ...

    def sign_event(self, event: NostrRumor, private_key: bytes) -> NostrEvent:
        """Sign a Nostr event. Returns completed event with id and sig set."""
        ...

    def generate_ephemeral_key(self) -> bytes:
        """Generate a random 32-byte private key for ephemeral use."""
        ...


def serialize_event(event: NostrRumor) -> str:
    """Serialize a Nostr event for ID computation (NIP-01).
    Format: [0, pubkey, created_at, kind, tags, content]
    """
    return json.dumps(
        [0, event.pubkey, event.created_at, event.kind, event.tags, event.content],
        separators=(",", ":"),
        ensure_ascii=False,
    )


def seal_rumor(
    rumor: NostrRumor,
    sender_privkey: bytes,
    recipient_pubkey: str,
    crypto: CryptoProvider,
) -> NostrEvent:
    """Seal a DM rumor (kind 14) into a Seal (kind 13) signed by the sender."""
    sender_pubkey = crypto.get_public_key(sender_privkey)
    content = crypto.nip44_encrypt(
        json.dumps(rumor.to_dict(), separators=(",", ":"), ensure_ascii=False),
        sender_privkey,
        recipient_pubkey,
    )
    seal = NostrRumor(
        pubkey=sender_pubkey,
        created_at=int(time.time()),
        kind=int(NostrKind.SEAL),
        tags=[],
        content=content,
    )
    return crypto.sign_event(seal, sender_privkey)


def gift_wrap(
    seal: NostrEvent,
    recipient_pubkey: str,
    crypto: CryptoProvider,
) -> NostrEvent:
    """Wrap a Seal (kind 13) into a Gift Wrap (kind 1059) using an ephemeral key."""
    ephemeral_key = crypto.generate_ephemeral_key()
    ephemeral_pubkey = crypto.get_public_key(ephemeral_key)
    content = crypto.nip44_encrypt(
        json.dumps(seal.to_dict(), separators=(",", ":"), ensure_ascii=False),
        ephemeral_key,
        recipient_pubkey,
    )
    wrap = NostrRumor(
        pubkey=ephemeral_pubkey,
        created_at=int(time.time()),
        kind=int(NostrKind.GIFT_WRAP),
        tags=[["p", recipient_pubkey]],
        content=content,
    )
    return crypto.sign_event(wrap, ephemeral_key)


def unwrap_gift(
    gift_wrap_event: NostrEvent,
    recipient_privkey: bytes,
    crypto: CryptoProvider,
) -> Optional[NostrEvent]:
    """Unwrap a Gift Wrap (kind 1059) to recover the inner Seal."""
    if gift_wrap_event.kind != int(NostrKind.GIFT_WRAP):
        return None
    plaintext = crypto.nip44_decrypt(
        gift_wrap_event.content, recipient_privkey, gift_wrap_event.pubkey
    )
    if plaintext is None:
        return None
    try:
        d = json.loads(plaintext)
        return NostrEvent.from_dict(d)
    except Exception:
        return None


def unseal_rumor(
    seal_event: NostrEvent,
    recipient_privkey: bytes,
    crypto: CryptoProvider,
) -> Optional[NostrRumor]:
    """Unseal a Seal (kind 13) to recover the inner DM rumor."""
    if seal_event.kind != int(NostrKind.SEAL):
        return None
    plaintext = crypto.nip44_decrypt(
        seal_event.content, recipient_privkey, seal_event.pubkey
    )
    if plaintext is None:
        return None
    try:
        d = json.loads(plaintext)
        return NostrRumor.from_dict(d)
    except Exception:
        return None


def wrap_and_send(
    rumor: NostrRumor,
    sender_privkey: bytes,
    recipient_pubkey: str,
    crypto: CryptoProvider,
) -> NostrEvent:
    """Full NIP-17 send flow: rumor → seal → gift wrap.

    Returns a gift-wrap event ready for publication to a relay.
    """
    seal = seal_rumor(rumor, sender_privkey, recipient_pubkey, crypto)
    return gift_wrap(seal, recipient_pubkey, crypto)


def receive_and_unwrap(
    gift_wrap_event: NostrEvent,
    recipient_privkey: bytes,
    crypto: CryptoProvider,
) -> Optional[NostrRumor]:
    """Full NIP-17 receive flow: gift wrap → seal → rumor.

    Returns the inner DM rumor, or None on failure.
    """
    seal = unwrap_gift(gift_wrap_event, recipient_privkey, crypto)
    if seal is None:
        return None
    return unseal_rumor(seal, recipient_privkey, crypto)
