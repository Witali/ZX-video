"""Movie/audio format identity, shared CLI encoding and unchanged IRQ records."""
from fractions import Fraction
import gzip
import json
import pickle
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import ay_interrupt
from build_long_video_trd import AyFrame
import build_long_video_trd as legacy_video
from convert_video import convert_audio


class SharedAudioTests(unittest.TestCase):
    def test_envelope_actions_keep_phase_and_repeat_shape_writes_explicit(self):
        first=AyFrame((251,731,1977),(16,11,14),19,0x30,2000,13,12)
        held=AyFrame(first.periods,first.volumes,19,0x30,2000,255,12)
        actions=ay_interrupt.encode_ticks([first,held,first])
        self.assertEqual(actions[0][0],14)
        self.assertEqual(actions[1],b'\0')
        self.assertEqual(actions[2],bytes([1,13,13]))
        from cell_audio_stream import take_tick
        from probe_motion_entropy import Reader
        for action in actions:self.assertEqual(take_tick(Reader(action)),action)

    def test_extended_mixers_round_trip_into_movie_register_records(self):
        for period in range(32):
            for mixer in range(64):
                frame = AyFrame((1,2048,4095),(3,7,11),period,mixer)
                restored = AyFrame.deserialize(frame.serialize())
                self.assertEqual(restored,frame)
                self.assertEqual(ay_interrupt.registers(restored),
                    bytes([1,0,0,8,255,15,period,mixer,3,7,11]))
        frame = AyFrame((251,731,1977),(8,11,14),19,0x30)
        self.assertEqual(pickle.loads(pickle.dumps(frame)), frame)
        packet = legacy_video.make_packet(bytes(3840), None, frame.serialize())
        with self.assertRaisesRegex(ValueError, 'modern IRQ'):
            legacy_video.serialize_video([packet],25/3,25/3)

    def test_movie_calls_the_same_core_and_preserves_silent_tail(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            # A finite pure tone followed by a silent tail; both entry points
            # receive exactly the same aligned float32 PCM, with no resampling.
            t = np.arange(4410)/22050
            pcm = np.r_[.1*np.sin(2*np.pi*440*t),np.zeros(4410)].astype('<f4')
            with patch('convert_video.run',return_value=pcm.tobytes()):
                frames,info = convert_audio(Path('fixture.mov'),'ffmpeg',root,
                    dict(start_time='0'),dict(index=1),4,Fraction(10))
            source = root/'source.f32'; pcm.tofile(source)
            standalone = root/'standalone'
            subprocess.run([sys.executable,str(Path(__file__).resolve().parents[1]/'ay-converter/encode_pcm.py'),
                str(source),'--output',str(standalone),'--node',r'C:\Program Files\nodejs\node.exe'],check=True)
            self.assertEqual((root/'ay.bin').read_bytes(),(standalone/'ay.bin').read_bytes())
            self.assertEqual(len(frames),20)
            self.assertTrue(all(f.volumes == (0,0,0) for f in frames[10:]))
            self.assertEqual(info['chip_fit']['shared_core'],'ay-converter/engine.py')
            expected = b''.join(ay_interrupt.registers(f) for f in frames)
            self.assertEqual(expected,gzip.decompress((standalone/'registers.gz').read_bytes()))
            self.assertEqual(json.loads((standalone/'analysis.json').read_bytes())['sound_quantum_ms'],20)
            ym=root/'ym';ym.mkdir()
            with patch('convert_video.run',return_value=pcm.tobytes()):
                ym_frames,ym_info=convert_audio(Path('fixture.mov'),'ffmpeg',ym,
                    dict(start_time='0'),dict(index=1),4,Fraction(10),chip='YM2149')
            ym_direct=root/'ym-direct'
            subprocess.run([sys.executable,str(Path(__file__).resolve().parents[1]/'ay-converter/encode_pcm.py'),
                str(source),'--output',str(ym_direct),'--node',r'C:\Program Files\nodejs\node.exe','--chip','YM2149'],check=True)
            self.assertEqual((ym/'ay.bin').read_bytes(),(ym_direct/'ay.bin').read_bytes())
            self.assertEqual(ym_info['chip_fit']['target_chip'],'YM2149')
            self.assertTrue(all(f.volumes==(0,0,0) for f in ym_frames[10:]))


if __name__ == '__main__':
    unittest.main()
