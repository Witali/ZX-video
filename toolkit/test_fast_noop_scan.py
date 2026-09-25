"""Paired opcode execution, including zero-copy vector page crossings."""
import unittest
from hashlib import sha256

from benchmark_context_huffman import word
from frame_output_pipeline import Harness
from probe_fast_noop_scan import frame_runs, scanner_tstates


class FastNoopScanTests(unittest.TestCase):
    def test_run_cycles_and_pointers_at_every_vector_alignment(self):
        variants = [Harness([bytes([8]*256)]*2,bytes(256),raw_attributes=True,
            fast_mask_dispatch=True,selective_cache=True,skip_noop_runs=True,
            fast_noop_scan=v) for v in (False,True)]
        for offset in range(256):
            for length in range(1,17):
                for following in ('end','vector','patch'):
                    if length == 16 and following != 'end': continue
                    results = []
                    # The two mask positions exercise a 16-bit page advance.
                    mask_base = 0xa4fe if offset % 2 else 0xa5e0
                    vector_base = 0xa700+offset
                    for fast,h in enumerate(variants):
                        cpu = h.cpu; cpu.guarding = False
                        for i in range(17): cpu.write8(vector_base+i,0)
                        for i in range(34): cpu.write8(mask_base+i,0)
                        if following == 'vector': cpu.write8(vector_base+length,81)
                        if following == 'patch': cpu.write8(mask_base+2*length+offset%2,128)
                        word(cpu,h.recon['vectors'],vector_base)
                        word(cpu,h.recon['bitmap_masks'],mask_base)
                        word(cpu,h.recon['target'],0x6600)
                        cpu.write8(h.recon['tiles_left'],length if following == 'end' else 16)
                        cpu.pc = h.recon['tile']; started = cpu.tstates
                        while True:
                            row = h.instructions[cpu.pc]; before = cpu.tstates; cpu.step()
                            allowed = row['tstates']
                            self.assertIn(cpu.tstates-before,allowed if isinstance(allowed,list) else [allowed])
                            if cpu.pc in (h.recon['tile'],h.recon['stripe_done']): break
                        self.assertEqual(cpu.tstates-started,scanner_tstates(length,following,bool(fast)))
                        state = (word(cpu,h.recon['vectors']),word(cpu,h.recon['bitmap_masks']),
                            word(cpu,h.recon['target']),cpu.read8(h.recon['tiles_left']))
                        self.assertEqual(state,(vector_base+length,mask_base+2*length,0x6600+2*length,
                            0 if following == 'end' else 16-length))
                        results.append(state)
                    self.assertEqual(*results)

    def test_full_frame_patch_halves_and_stripe_edges(self):
        for length in range(1,17):
            for following in ('low_patch','high_patch','clear'):
                vectors,masks = bytearray(192),bytearray(384)
                encoded = bytearray(); expected = bytearray(3840)
                selected = {16,31,175}
                if length < 16: selected.add(32+length)
                for tile in sorted(selected):
                    if following == 'clear': vectors[tile] = 81
                    else:
                        half = int(following == 'high_patch')
                        masks[tile*2+half] = 128; encoded.append(1)
                        row,column = divmod(tile,16)
                        expected[row*256+column*2+128*half] = 1
                group = (1,0,len(encoded)*8,bytes(vectors),bytes(masks),bytes(96),bytes(encoded),b'')
                totals = []
                for fast in (False,True):
                    h = Harness([bytes([8]*256)]*2,bytes(256),raw_attributes=True,
                        fast_mask_dispatch=True,selective_cache=True,skip_noop_runs=True,
                        skip_static_stripes=True,fast_noop_scan=fast)
                    totals.append(h.run(group,b'\xff'*80,bytes(expected),0,cache_map=bytes(3))['total_tstates'])
                runs,patches = frame_runs(vectors,masks)
                delta = -6*patches+sum(scanner_tstates(k,t,True)-scanner_tstates(k,t) for k,t in runs)
                self.assertEqual(totals[1]-totals[0],delta)

    def test_absolute_patch_overhead_excluding_callee(self):
        for fast in (False,True):
            h = Harness([bytes([8]*256)]*2,bytes(256),raw_attributes=True,
                fast_mask_dispatch=True,selective_cache=True,skip_noop_runs=True,fast_noop_scan=fast)
            cpu = h.cpu;cpu.guarding = False
            cpu.write8(0xa7ff,0);cpu.write8(0xa4fe,128);cpu.write8(0xa4ff,0)
            word(cpu,h.recon['vectors'],0xa7ff);word(cpu,h.recon['bitmap_masks'],0xa4fe)
            word(cpu,h.recon['target'],0x6600);cpu.write8(h.recon['tiles_left'],16)
            cpu.pc = h.recon['tile'];started = cpu.tstates;calls = 0
            while True:
                cpu.step()
                if cpu.pc == h.recon['patches_nonzero']:
                    cpu.pc = cpu.pop();calls += 1  # exclude the callee, including its RET
                if cpu.pc == h.recon['tile']: break
            self.assertEqual(calls,1)
            self.assertEqual(cpu.tstates-started,251 if fast else 257)
            self.assertEqual(word(cpu,h.recon['vectors']),0xa800)
            self.assertEqual(word(cpu,h.recon['bitmap_masks']),0xa500)

    def test_irq_at_every_executed_scanner_boundary(self):
        from test_frame_output_pipeline import FrameOutputPipelineTests
        for empty in (False,True):
            self.assertGreater(FrameOutputPipelineTests().exercise_irq(raw=True,fast=True,
                selective=True,noops=True,empty_noops=empty,fast_noop_scan=True),0)

    def test_invalid_modes(self):
        for options in ({},dict(skip_noop_runs=True,encoded_noop_runs=True)):
            with self.assertRaises(ValueError):
                Harness([bytes([8]*256)]*2,bytes(256),fast_noop_scan=True,**options)

    def test_default_scanner_binary_unchanged(self):
        # Captured from main at 491db7b, with these synthetic tables/options.
        h = Harness([bytes([8]*256)]*2,bytes(256),raw_attributes=True,
            fast_mask_dispatch=True,selective_cache=True,skip_noop_runs=True)
        data = bytes(h.cpu.read8(a) for a in range(0x7a00,h.recon['noop_scanner_end']))
        self.assertEqual(sha256(data).hexdigest(),
            '3ed52ff9d4cde5e8e5c32e683ec238a24f75e8ab61d18c971c6f7dd4cbf4404d')


if __name__ == '__main__': unittest.main()
