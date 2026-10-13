"""Exact phrase reconstruction, varied repeats and malformed stream handling."""
import random
import unittest
from phrase_probe import encode, decode


class PhraseTests(unittest.TestCase):
    def test_static_and_repeating_varied_phrases(self):
        phrase=b''.join(bytes([i])*9 for i in range(16))
        for raw in (b'',bytes(9)*300,phrase*100,bytes(9)*100+phrase*12+bytes([255])*9*270):
            coded,_=encode(raw)
            self.assertEqual(decode(coded),raw)
        coded,info=encode(phrase*100)
        self.assertGreater(info['dictionary_references'],0)
        self.assertLess(len(coded),len(phrase*100)//5)

    def test_random_data_and_truncation(self):
        raw=random.Random(13).randbytes(9*1000)
        coded,_=encode(raw)
        self.assertEqual(decode(coded),raw)
        for damaged in (coded[:-1],coded+b'\0',b'AYP1',b'bad header'):
            with self.assertRaises(ValueError):decode(damaged)
        with self.assertRaises(ValueError):encode(raw+b'\0')


if __name__=='__main__':unittest.main()
