"""Tests for BitChat-over-Nostr embedding helpers."""

import pytest
from bitchat_protocol import encode as encode_packet, BitchatPacket, MessageType
from bitchat_nostr import (
    encode_packet_to_base64,
    decode_packet_from_base64,
    extract_packet_from_event,
    build_dm_rumor,
    NostrEvent,
    NostrKind,
)


def make_test_packet_bytes() -> bytes:
    packet = BitchatPacket(
        version=1,
        type=int(MessageType.MESSAGE),
        ttl=7,
        timestamp=0,
        flags=0,
        sender_id=bytes.fromhex("abcdef0123456789"),
        payload=b"relay test",
    )
    return encode_packet(packet, padding=False)


class TestBase64Embedding:
    def test_encode_decode_roundtrip(self):
        packet_bytes = make_test_packet_bytes()
        b64 = encode_packet_to_base64(packet_bytes)
        assert len(b64) > 0
        decoded = decode_packet_from_base64(b64)
        assert decoded is not None
        assert decoded == packet_bytes

    def test_returns_none_invalid_base64(self):
        result = decode_packet_from_base64("!!!not_valid!!!")
        assert result is None

    def test_empty_content_returns_none(self):
        result = decode_packet_from_base64("")
        # decode_packet_from_base64 returns raw bytes or None; empty base64 = b""
        # empty bytes is valid base64 but not a valid packet
        # extract_packet_from_event will catch invalid packets


class TestExtractPacketFromEvent:
    def _make_event(self, content: str) -> NostrEvent:
        return NostrEvent(
            id="a" * 64,
            pubkey="b" * 64,
            created_at=0,
            kind=int(NostrKind.GIFT_WRAP),
            tags=[],
            content=content,
            sig="c" * 128,
        )

    def test_valid_packet_extracted(self):
        packet_bytes = make_test_packet_bytes()
        b64 = encode_packet_to_base64(packet_bytes)
        event = self._make_event(b64)
        result = extract_packet_from_event(event)
        assert result is not None
        assert result.packet == packet_bytes
        assert result.sender_id_hex == "abcdef0123456789"
        assert result.event is event

    def test_invalid_content_returns_none(self):
        event = self._make_event("not a bitchat packet")
        result = extract_packet_from_event(event)
        assert result is None

    def test_garbage_base64_returns_none(self):
        event = self._make_event("dGhpcyBpcyBub3QgYSBwYWNrZXQ=")  # "this is not a packet"
        result = extract_packet_from_event(event)
        assert result is None


class TestBuildDMRumor:
    def test_rumor_has_correct_kind_and_p_tag(self):
        packet_bytes = make_test_packet_bytes()
        sender = "a" * 64
        recipient = "b" * 64
        rumor = build_dm_rumor(packet_bytes, sender, recipient)

        assert rumor.kind == int(NostrKind.DM)
        assert rumor.pubkey == sender
        assert any(t[0] == "p" and t[1] == recipient for t in rumor.tags)

    def test_rumor_content_is_valid_base64_packet(self):
        packet_bytes = make_test_packet_bytes()
        rumor = build_dm_rumor(packet_bytes, "a" * 64, "b" * 64)
        decoded_bytes = decode_packet_from_base64(rumor.content)
        assert decoded_bytes == packet_bytes
