#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from asysbus import AsbMeta, AsbPacket, encodeAsbPacket, decodeAsbPacket

class TestPlatformAsysbus(unittest.TestCase):
    """Test the Asysbus platform."""

    def test_encode_valid_multicast_packet(self):
        expectedAsbPacket = b"1BAFF2511"

        encodedPacket = encodeAsbPacket(AsbPacket(
            meta = AsbMeta(type = 0x01, port = 0xFF, source = 0x000A, target = 0x000B),
            length = 2,
            data = [0x51, 0x01]
        ))

        self.assertEqual(expectedAsbPacket, encodedPacket)

    def test_encode_valid_multicast_packet_with_zero_port_which_becomes_ff(self):
        expectedAsbPacket = b"156781234FF2AABB"

        encodedPacket = encodeAsbPacket(AsbPacket(
            meta = AsbMeta(type = 0x01, port = 0x00, source = 0x1234, target = 0x5678),
            length = 2,
            data = [0xAA, 0xBB]
        ))

        self.assertEqual(expectedAsbPacket, encodedPacket)

    def test_encode_valid_multicast_packet_without_data(self):
        expectedAsbPacket = b"1BBAAFF0"

        encodedPacket = encodeAsbPacket(AsbPacket(
            meta = AsbMeta(type = 0x01, port = 0xFF, source = 0x00AA, target = 0x00BB),
            length = 0,
            data = []
        ))

        self.assertEqual(expectedAsbPacket, encodedPacket)

    def test_encode_valid_multicast_packet_with_eight_byte_data(self):
        expectedAsbPacket = b"156781234FF8AABBCCDDEEFF12"

        encodedPacket = encodeAsbPacket(AsbPacket(
            meta = AsbMeta(type = 0x01, port = 0x00, source = 0x1234, target = 0x5678),
            length = 8,
            data = [0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF, 0x01, 0x02]
        ))

        self.assertEqual(expectedAsbPacket, encodedPacket)

    def test_decode_invalid_packet_string(self):
        self.assertIsNone(decodeAsbPacket("invalidpacketstring"))

    def test_decode_valid_broadcast_packet(self):
        expectedAsbPacket = AsbPacket(
            meta = AsbMeta(type = 0x00, port = 0xFF, source = 0x000A, target = 0x0000),
            length = 2,
            data = [0x51, 0x01]
        )

        decodedPacket = decodeAsbPacket("00AFF2511")
        self.assertEqual(expectedAsbPacket, decodedPacket)

    def test_decode_valid_multicast_packet(self):
        expectedAsbPacket = AsbPacket(
            meta = AsbMeta(type = 0x01, port = 0xFF, source = 0x00A1, target = 0x00B1),
            length = 2,
            data = [0xAA, 0x02]
        )

        decodedPacket = decodeAsbPacket("1B1A1FF2AA2")
        self.assertEqual(expectedAsbPacket, decodedPacket)

    def test_decode_valid_unicast_packet_with_singlebyte_source_and_address(self):
        expectedAsbPacket = AsbPacket(
            meta = AsbMeta(type = 0x02, port = 0x42, source = 0x0034, target = 0x0012),
            length = 2,
            data = [0xAA, 0xBB]
        )

        decodedPacket = decodeAsbPacket("21234422AABB")
        self.assertEqual(expectedAsbPacket, decodedPacket)

    def test_decode_valid_unicast_packet_with_multibyte_source_and_address(self):
        expectedAsbPacket = AsbPacket(
            meta = AsbMeta(type = 0x02, port = 0x42, source = 0x1234, target = 0x5678),
            length = 2,
            data = [0xAA, 0xBB]
        )

        decodedPacket = decodeAsbPacket("256781234422AABB")
        self.assertEqual(expectedAsbPacket, decodedPacket)

    def test_decode_valid_unicast_packet_without_data(self):
        expectedAsbPacket = AsbPacket(
            meta = AsbMeta(type = 0x02, port = 0x42, source = 0x0034, target = 0x0012),
            length = 0,
            data = []
        )

        decodedPacket = decodeAsbPacket("21234420")
        self.assertEqual(expectedAsbPacket, decodedPacket)

    def test_decode_valid_unicast_packet_with_one_byte_data(self):
        expectedAsbPacket = AsbPacket(
            meta = AsbMeta(type = 0x02, port = 0x42, source = 0x0034, target = 0x0012),
            length = 1,
            data = [0x44]
        )

        decodedPacket = decodeAsbPacket("2123442144")
        self.assertEqual(expectedAsbPacket, decodedPacket)

    def test_decode_valid_unicast_packet_with_eight_byte_data(self):
        expectedAsbPacket = AsbPacket(
            meta = AsbMeta(type = 0x02, port = 0x42, source = 0x00A1, target = 0x00B1),
            length = 8,
            data = [0xAA, 0x01, 0xBB, 0x02, 0xCC, 0x03, 0xDD, 0x04]
        )

        decodedPacket = decodeAsbPacket("2B1A1428AA1BB2CC3DD4")
        self.assertEqual(expectedAsbPacket, decodedPacket)

    def test_decode_valid_unicast_packet_with_lowercase_hex_data(self):
        expectedAsbPacket = AsbPacket(
            meta = AsbMeta(type = 0x02, port = 0x42, source = 0x00A1, target = 0x00B1),
            length = 4,
            data = [0xAA, 0x01, 0xBB, 0x02]
        )

        decodedPacket = decodeAsbPacket("2B1A1424aa1bb2")
        self.assertEqual(expectedAsbPacket, decodedPacket)

if __name__ == '__main__':
    unittest.main()
