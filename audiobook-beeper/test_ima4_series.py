"""IMA4 capacity, exact source coverage and public-command integration."""
import unittest
from unittest.mock import patch
from ima4_series import capacity_samples,plan_parts,plan_volumes,FIRST_PLAYER_SECTOR


class Ima4Series(unittest.TestCase):
    def test_full_disk_uses_every_sector(self):
        parts=plan_parts(8000*600)
        first=plan_volumes(parts,single=True)[0]
        self.assertEqual(len(first),5)
        self.assertEqual([parts[i]['samples'] for i in first],[186880]*4+[162816])
        self.assertEqual(FIRST_PLAYER_SECTOR+sum(parts[i]['sectors'] for i in first),2560)
        self.assertEqual(parts[first[-1]]['stop'],909696)

    def test_source_coverage_and_tail_guard(self):
        for total in (1,8064,186752,186753,909696,909697,8000*600):
            parts=plan_parts(total)
            self.assertEqual(parts[0]['start'],0)
            self.assertEqual(parts[-1]['stop'],total)
            self.assertEqual(sum(p['stop']-p['start'] for p in parts),total)
            self.assertEqual([p['stop'] for p in parts[:-1]],[p['start'] for p in parts[1:]])
            for part in parts:
                self.assertGreaterEqual(part['samples']-part['stop']+part['start'],128)
                self.assertEqual(part['samples']%512,0)
                self.assertLessEqual(part['samples'],capacity_samples())
            volumes=plan_volumes(parts)
            self.assertEqual([i for volume in volumes for i in volume],list(range(len(parts))))
            for volume in volumes:
                self.assertLessEqual(FIRST_PLAYER_SECTOR+sum(parts[i]['sectors'] for i in volume),2560)

    def test_public_ima4_disk_modes(self):
        from convert_audio import main
        base=['input.wav','--codec','ima4','--output','unused','--ffmpeg','ffmpeg','--fuse','fuse']
        for flags,mode in (([],'single'),(['--disk-mode','all'],'all'),(['--disk-mode','preview'],'preview')):
            with patch('convert_audio.convert',return_value={'quality_gate_passed':True}) as convert:
                main(base+flags)
                self.assertEqual(convert.call_args.args[0].disk_mode,mode)

    def test_invalid_part_sizes(self):
        for size in (0,512,8193,capacity_samples()+512):
            with self.assertRaises(ValueError):plan_parts(20000,part_samples=size)
        with self.assertRaises(ValueError):plan_parts(0)


if __name__=='__main__':unittest.main()
