"""Exact AYH1 records, constants, all register values and malformed input."""
import random
import unittest

from ay_huffman_stream import encode,decode


class ResidentAudioTests(unittest.TestCase):
    def test_empty_and_constant_ticks(self):
        for ticks in ([],[b'\0']*100,[bytes([1,10,15])]*100):
            coded,detail=encode(ticks,bytes(range(11)))
            self.assertEqual(decode(coded),(bytes(range(11)),ticks))
            self.assertEqual(detail['coded_bits'],0)
            self.assertEqual(len(coded),detail['total_bytes'])

    def test_full_register_alphabet_and_random_masks(self):
        ticks=[bytes([11])+b''.join(bytes([r,value]) for r in range(11)) for value in range(256)]
        rng=random.Random(4901)
        for _ in range(1500):
            pairs=b''.join(bytes([r,rng.randrange(256)]) for r in range(11) if rng.randrange(2))
            ticks.append(bytes([len(pairs)//2])+pairs)
        coded,_=encode(ticks)
        self.assertEqual(decode(coded),(bytes(11),ticks))

    def test_bounds_and_input_validation(self):
        coded,_=encode([b'\0',bytes([1,0,1]),bytes([2,0,4,6,31])])
        for cut in range(len(coded)):
            with self.assertRaises(ValueError): decode(coded[:cut])
        with self.assertRaises(ValueError): decode(coded+b'\0')
        for tick in (bytes([1,11,0]),bytes([2,1,3,1,5]),bytes([2,3,1,1,3]),bytes([1,0])):
            with self.assertRaises(ValueError): encode([tick])


if __name__=='__main__':unittest.main()
