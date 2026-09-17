import random
import unittest

from zx0_speed import Token, encode, parse, rewrite
from zx0_codec import decompress


class ZX0SpeedTests(unittest.TestCase):
    def test_offset_state_backtracking_and_literals(self):
        for tokens, raw in (
            ([Token(0, 1), Token(1, 1, 1), Token(2, 3)], b'aabcd'),
            ([Token(0, 3), Token(3, 3, 3), Token(6, 2, 3)], b'abcabcab'),
            ([Token(0, 260), Token(260, 260, 260)], bytes(range(256)) + b'abcd' + bytes(range(256)) + b'abcd'),
        ):
            packed = encode(raw, tokens)
            self.assertEqual(parse(packed), (raw, tokens))
            for minimum in (2, 3, 4, 8, 300):
                self.assertEqual(decompress(rewrite(packed, minimum)), raw)

    def test_random_valid_sequences(self):
        rng = random.Random(979)
        for _ in range(100):
            raw = bytearray(rng.randbytes(rng.randrange(1, 50)))
            tokens = [Token(0, len(raw))]
            for index in range(40):
                length = rng.randrange(2, 40); offset = rng.randrange(1, len(raw) + 1)
                tokens.append(Token(len(raw), length, offset))
                for _ in range(length): raw.append(raw[-offset])
                if rng.randrange(2):
                    length = rng.randrange(1, 25); tokens.append(Token(len(raw), length))
                    raw.extend(rng.randbytes(length))
            packed = encode(bytes(raw), tokens)
            for minimum in (2, 4, 8):
                self.assertEqual(decompress(rewrite(packed, minimum)), raw)
