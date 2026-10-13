"""Envelope phase, real rendered feedback, packed actions and native timing."""
import gzip
from pathlib import Path
import subprocess
import tempfile
import unittest
import numpy as np
from ay_format import AyFrame, registers
import hardware_envelope as envelope
import noise_colour
from music_player import build_disk,MAX_ENVELOPE_TICKS
from verify_preview import expected_registers,extract_player,native_check,write_pairs

NODE=r'C:\Program Files\nodejs\node.exe'


def render(rows, root, name):
    (root/f'{name}.gz').write_bytes(gzip.compress(rows.tobytes(),mtime=0))
    subprocess.run([NODE,str(envelope.HERE/'render_ym2149.js'),str(root/f'{name}.gz'),
        str(root/f'{name}.f32'),'50',str(root/f'{name}.json'),'14'],check=True)
    return np.fromfile(root/f'{name}.f32','<f4').astype(float)


class HardwareEnvelopeTests(unittest.TestCase):
    def test_ay_dac_shapes_periods_and_phase_against_manual_rules(self):
        subprocess.run([NODE,str(envelope.HERE/'test_chip_capabilities.js')],check=True)
    def test_packed_envelope_actions_survive_independent_decode(self):
        for shape in (*range(16),255):
            frame=AyFrame((1,2048,4095),(16,31,7),19,0x30,65535,shape,12)
            self.assertEqual(AyFrame.deserialize(frame.serialize()),frame)
            self.assertEqual(registers(frame),expected_registers(frame.serialize(),12))
            self.assertEqual(13 in dict(write_pairs(registers(frame))),shape!=255)
        with self.assertRaises(ValueError):AyFrame((1,1,1),(16,0,0)).serialize()

    def test_holding_shape_preserves_multi_field_envelope_phase(self):
        raw=np.tile([251,0,1,0,1,0,0,0x38,16,0,0,0,30,255],(10,1)).astype(np.uint8)
        raw[0,13]=13
        restarted=raw.copy();restarted[:,13]=13
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);held=render(raw,root,'held');reset=render(restarted,root,'reset')
            # A .02-s restart cannot complete the ~1.1-s attack; the held
            # hardware ramp advances through all ten fields instead.
            self.assertGreater(np.sqrt(np.mean(held[-882:]**2)),np.sqrt(np.mean(reset[-882:]**2))*4)

    def test_real_envelope_wave_is_selected_against_a_square_seed(self):
        count=60
        seed=np.tile([0,2,1,0,1,0,0,0x38,15,0,0],(count,1)).astype(np.uint8)
        target=envelope.extend(seed.tobytes());target[:,7]=0x39;target[:,8]=16
        target[:,11]=16;target[0,13]=14
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=noise_colour.downsample(render(target,root,'source'))
            result,info=envelope.optimize(source,seed.tobytes(),NODE,work_parent=root,calibration_gain=1.)
            self.assertTrue(info['selected'])
            self.assertLess(info['final']['objective_db'],info['baseline']['objective_db'])
            self.assertGreater(info['envelope_channel_ticks'],0)
            self.assertLess(info['shape_restarts'],count)
            self.assertEqual(len(result),count*14)

    def test_native_sentinel_bank_boundary_eof_and_instruction_counts(self):
        for count in (1170,1171,MAX_ENVELOPE_TICKS):
            rows=np.tile([251,0,1,0,1,0,0,0x38,16,0,0,10,1,255],(count,1)).astype(np.uint8)
            rows[::7,13]=13;raw=rows.tobytes()
            disk,metadata=build_disk(raw,loop=False,register_bytes=14)
            result=native_check(extract_player(disk),metadata,raw)
            self.assertTrue(result['eof_mutes'])
            self.assertEqual(result['register_writes'],count*13+len(rows[::7]))
            self.assertTrue(set(result['deterministic_field_work_tstates'])<={1166,1206,1184,1224,1283,1323,1199,1239})
        with self.assertRaises(ValueError):build_disk(bytes((MAX_ENVELOPE_TICKS+1)*14),register_bytes=14)
        rows=np.tile([251,0,1,0,1,0,0,0x38,16,0,0,10,1,255],(1171,1)).astype(np.uint8)
        rows[0,13]=14
        disk,metadata=build_disk(rows.tobytes(),loop=True,register_bytes=14)
        result=native_check(extract_player(disk),metadata,rows.tobytes())
        self.assertTrue(result['seamless_loop'])
        self.assertEqual(result['deterministic_field_work_tstates'][1311],1)


if __name__=='__main__':unittest.main()
