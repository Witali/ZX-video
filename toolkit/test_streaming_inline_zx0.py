"""Run the complete input-frontier/IRQ suite on the inline-literal core."""
import unittest
from unittest.mock import patch

import benchmark_streaming_zx0_input as bench
import streaming_inline_zx0 as machine
from test_streaming_zx0_input import StreamingInputTests


class InlineHarness(bench.Harness):
    def __init__(self):
        super().__init__()
        self.code,self.labels=machine.build()
        c=self.cpu;c.labels=self.labels
        c.patched={self.labels[n] for n in ('slice_high_operand','slice_low_operand',
            'slice_equal_branch','match_high_operand','match_low_operand','match_equal_branch')}
        c.patched.update((self.labels['dzx0t_last_offset']+1,self.labels['dzx0t_last_offset']+2))
        for i,value in enumerate(self.code):c.write8(machine.CODE+i,value)


class InlineTests(StreamingInputTests):
    def setUp(self):
        self.factory=patch('test_streaming_zx0_input.Harness',InlineHarness);self.factory.start()
        self.addCleanup(self.factory.stop)


def load_tests(loader,tests,pattern):return loader.loadTestsFromTestCase(InlineTests)


if __name__=='__main__':unittest.main()
