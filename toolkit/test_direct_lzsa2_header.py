"""Verify header-entry AF liveness, exact T-states and default compatibility."""
import gzip
import json
from pathlib import Path
import unittest

from z80 import Z80Machine
import resumable_lzsa2


class DirectHeaderTests(unittest.TestCase):
    def test_default_decoder_bytes_are_unchanged(self):
        for directory,name in (
            ('streaming_bypass_evidence','window-ZX-video-front_part07.json.gz'),
            ('same_cost_compression_evidence','dictionary-budgeted-window-ZX-video-front_part07.json.gz')):
            archived=Path(__file__).with_name(directory)/name
            m=json.loads(gzip.decompress(archived.read_bytes()))
            regions,_,_=resumable_lzsa2.build(core=m['decoder_labels']['start'],core_limit=0x8e80,
                                            streaming=m['lzsa2'].get('streaming',False))
            self.assertEqual([(r['address'],bytes.fromhex(r['code_hex'])) for r in m['lzsa2']['regions']],regions)

    def test_available_header_cost_and_live_registers(self):
        for direct in (False,True):
            regions,z,_=resumable_lzsa2.build(core=0x8d74,core_limit=0x8e80,streaming=True,direct_header=direct)
            # Exhaust AF flags and both halves of the saved nibble reservoir.
            for flags in range(256):
                m=Z80Machine()
                for at,data in regions:m.set_memory_block(at,data)
                m.memory[z['header_frontier']]=0xe0
                m.af=0x6900|flags;m.alt_af=(flags<<8)|((flags*37)&255)
                m.hl=0xdf80;m.de=0xc321;m.bc=0x37a9;m.alt_hl=0x1234;m.alt_de=0x2345;m.alt_bc=0x3456
                saved={name:getattr(m,name) for name in ('hl','de','bc','alt_af','alt_hl','alt_de','alt_bc')}
                m.sp=0x9df0;m.pc=z['token_guard'];m.set_breakpoint(z['token_body']);m.ticks_to_stop=10000
                while m.pc!=z['token_body']:
                    self.assertFalse(m.run()&m._TICKS_LIMIT_HIT)
                self.assertEqual(10000-m.ticks_to_stop,46 if direct else 96)
                self.assertEqual(m.sp,0x9df0)
                self.assertEqual(saved,{name:getattr(m,name) for name in saved})
                # The first token instructions immediately replace AF. Both
                # variants therefore enter literal/offset parsing identically.
                m.memory[m.hl]=flags
                m.clear_breakpoint(z['token_body']);m.set_breakpoint(z['token_body']+3)
                while m.pc!=z['token_body']+3:
                    self.assertFalse(m.run()&m._TICKS_LIMIT_HIT)
                self.assertEqual(m.a,flags&24)
                self.assertEqual(m.alt_af,saved['alt_af'])

    def test_input_wait_entry_and_resume_costs(self):
        for direct in (False,True):
            regions,z,_=resumable_lzsa2.build(core=0x8d74,core_limit=0x8e80,streaming=True,direct_header=direct)
            for source,expected in ((0xdf80,63 if direct else 98),(0xfff0,51 if direct else 89)):
                m=Z80Machine()
                for at,data in regions:m.set_memory_block(at,data)
                m.hl=source;m.sp=0x9df0;m.memory[z['header_frontier']]=0xdf
                m.pc=z['token_guard'];m.set_breakpoint(z['input_wait']);m.ticks_to_stop=10000
                while m.pc!=z['input_wait']:
                    self.assertFalse(m.run()&m._TICKS_LIMIT_HIT)
                self.assertEqual(10000-m.ticks_to_stop,expected)
                resume=m.memory[m.sp]+256*m.memory[m.sp+1]
                for output,target,expected_resume in ((0xc000,0xc100,31),(0xc001,0xc002,59)):
                    # Restore precisely at input_wait's RET boundary with a
                    # still-partial frontier. The actual wait/IRQ body is
                    # covered by the streaming component tests.
                    m.clear_breakpoint(z['input_wait']);m.set_breakpoint(z['guard_header'])
                    m.pc=resume;m.sp=0x9df0 if direct else 0x9dee;m.de=output
                    m.memory[z['high_operand']]=target>>8;m.memory[z['low_operand']]=target&255
                    m.ticks_to_stop=10000
                    while m.pc!=z['guard_header']:
                        self.assertFalse(m.run()&m._TICKS_LIMIT_HIT)
                    self.assertEqual(10000-m.ticks_to_stop,expected_resume if direct else 12)


if __name__=='__main__':unittest.main()
