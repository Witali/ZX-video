"""Apply the input-frontier and AY IRQ tests to the production split layout."""
import unittest
from unittest.mock import patch
from benchmark_streaming_inline_zx0 import SplitHarness
from test_streaming_zx0_input import StreamingInputTests


class SplitTests(StreamingInputTests):
    def setUp(self):
        factory=patch('test_streaming_zx0_input.Harness',SplitHarness)
        factory.start();self.addCleanup(factory.stop)


def load_tests(loader,tests,pattern):return loader.loadTestsFromTestCase(SplitTests)


if __name__=='__main__':unittest.main()
