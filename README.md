# bitchat-nostr

[![PyPI](https://img.shields.io/pypi/v/bitchat-nostr)](https://pypi.org/project/bitchat-nostr/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://python.org)
[![License: Unlicense](https://img.shields.io/badge/license-Unlicense-blue.svg)](https://unlicense.org)

BitChat-over-Nostr transport for Python.

Implements the relay transport layer for BitChat: NIP-17 gift-wrap private messages,
async relay client (NIP-01), and helpers for embedding BitChat binary packets inside
Nostr events.

## Installation

```bash
pip install bitchat-nostr
# Optional: NIP-44 encryption requires a secp256k1 library
pip install nostr-sdk  # or pynostr, etc.
```

## Quick Start

### Listen for BitChat packets via Nostr relay

```python
import asyncio
from bitchat_nostr import RelayClient, RelayConfig, NostrFilter, NostrKind, extract_packet_from_event

async def main():
    async with RelayClient(RelayConfig(url='wss://relay.example.com')) as relay:
        async def on_event(event, sub_id):
            # After decrypting the gift wrap, extract the BitChat packet:
            embedded = extract_packet_from_event(event)
            if embedded:
                print('Received BitChat packet from', embedded.sender_id_hex)

        await relay.subscribe(
            'bitchat-dm',
            [NostrFilter(kinds=[int(NostrKind.GIFT_WRAP)])],
            on_event,
        )
        await asyncio.sleep(60)  # listen for 60 seconds

asyncio.run(main())
```

### Send a BitChat packet via NIP-17

```python
from bitchat_protocol import encode as encode_packet, BitchatPacket, MessageType
from bitchat_nostr import build_dm_rumor, wrap_and_send, RelayClient, RelayConfig

async def send():
    # 1. Encode your BitChat packet
    packet = BitchatPacket(version=1, type=int(MessageType.NOISE_ENCRYPTED), ...)
    wire = encode_packet(packet, padding=False)

    # 2. Build a NIP-17 DM rumor carrying the packet
    rumor = build_dm_rumor(wire, sender_nostr_pubkey, recipient_nostr_pubkey)

    # 3. Wrap and publish (requires your CryptoProvider implementation)
    gift_wrap_event = wrap_and_send(rumor, sender_privkey, recipient_pubkey, crypto)

    async with RelayClient(RelayConfig(url='wss://relay.example.com')) as relay:
        ok = await relay.publish(gift_wrap_event)
        print('Published:', ok)
```

## API

### RelayClient

```python
RelayClient(config: RelayConfig, *, connect_timeout=5.0, publish_timeout=3.0, ...)
async with client:
    await client.subscribe(id, filters, on_event, on_eose=None)
    await client.unsubscribe(id)
    await client.publish(event) -> bool
    await client.close()
```

### Embedding Helpers

```python
encode_packet_to_base64(packet_bytes: bytes) -> str
decode_packet_from_base64(content: str) -> bytes | None
extract_packet_from_event(event: NostrEvent) -> EmbeddedBitChatPayload | None
build_dm_rumor(packet_bytes, sender_pubkey, recipient_pubkey) -> NostrRumor
build_geohash_presence_event(packet_bytes, sender_pubkey, geohash) -> NostrRumor
```

### NIP-17 Gift Wrap

```python
wrap_and_send(rumor, sender_privkey, recipient_pubkey, crypto) -> NostrEvent
receive_and_unwrap(gift_wrap_event, recipient_privkey, crypto) -> NostrRumor | None
# Individual steps:
seal_rumor(rumor, sender_privkey, recipient_pubkey, crypto) -> NostrEvent
gift_wrap(seal, recipient_pubkey, crypto) -> NostrEvent
unwrap_gift(gift_wrap_event, recipient_privkey, crypto) -> NostrEvent | None
unseal_rumor(seal_event, recipient_privkey, crypto) -> NostrRumor | None
```

### CryptoProvider Protocol

```python
class MyCrypto:
    def nip44_encrypt(self, plaintext, sender_privkey, recipient_pubkey) -> str: ...
    def nip44_decrypt(self, ciphertext, recipient_privkey, sender_pubkey) -> str | None: ...
    def get_public_key(self, private_key) -> str: ...
    def sign_event(self, event, private_key) -> NostrEvent: ...
    def generate_ephemeral_key(self) -> bytes: ...
```

## Running Tests

```bash
pip install -e ".[dev]"
pytest
```

## License

Unlicense — public domain.
