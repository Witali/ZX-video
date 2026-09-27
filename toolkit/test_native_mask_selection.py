import unittest
import numpy as np
from benchmark_cell_screen import Harness
from native_mask_selection import band_cost,choose_map,maps_for_states,rewrite
from bulk_frame_stream import pack
from test_frame_stream_z80 import source


class NativeMaskSelectionTests(unittest.TestCase):
    def test_every_marked_count_and_group_distribution(self):
        # Every population of the four groups, including zero groups.
        for count in np.ndindex(9,9,9,9):
            flags=bytes((255<<(8-n))&255 for n in count)
            for band in (2,3):
                mask=bytearray(80); mask[band*4:band*4+4]=flags
                chosen=choose_map(bytes(mask))[band*4:band*4+4]
                self.assertEqual(band_cost(chosen,band),min(band_cost(flags,band),band_cost(b'\xff'*4,band)))
                self.assertTrue(all(a&b==a for a,b in zip(flags,chosen)))

    def test_native_execution_for_break_even_and_clearing(self):
        old=Harness(fast_mask_dispatch=True,gray_cells=True)
        new=Harness(fast_mask_dispatch=True,gray_cells=True)
        states=np.zeros((10,3840),dtype=np.uint8)
        for i,marked in enumerate((18,19,20,21,22,23,24,32,0,0)):
            states[i,12*32:16*32].reshape(4,32)[:,:marked]=(i+1)*11
            states[i,16*32:20*32].reshape(4,32)[:,-marked if marked else 32:]=(i+1)*13
        before,after=maps_for_states(states)
        for i,state in enumerate(states):
            a=old.run(state.tobytes(),before[i].tobytes(),i)
            b=new.run(state.tobytes(),after[i].tobytes(),i)
            expected=sum(band_cost(after[i,b*4:b*4+4].tobytes(),b)-band_cost(before[i,b*4:b*4+4].tobytes(),b) for b in range(1,19))
            self.assertEqual(b['tstates']-a['tstates'],expected)

    def test_packet_mutation_preserves_cold_start_and_all_other_bytes(self):
        states,_,fap1,_=source(4); raw,_=pack(fap1,stored_guards=False)
        before,after=maps_for_states(states)
        candidate,rows=rewrite(raw,before,after,1,4)
        self.assertTrue(rows[0]['cold_map_preserved']); self.assertTrue(rows[1]['cold_map_preserved'])
        recovered=bytearray(candidate)
        for row in rows: recovered[row['offset']:row['offset']+80]=bytes.fromhex(row['baseline_map_hex'])
        self.assertEqual(bytes(recovered),raw)


if __name__=='__main__': unittest.main()
