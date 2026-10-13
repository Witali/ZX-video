"""Capacity, ordering, directory and visible-footer invariants of RAM volumes."""
import unittest

from audio_cover import prepare,render
from pcm_player import spectrum_bitmap_offset
from ram_series import capacity_samples,plan_parts,plan_volumes,section_sizes


class AdaptiveVolumes(unittest.TestCase):
    def test_all_source_is_retained_with_exact_sector_layout(self):
        for codec,capacity in [('ima4',179712),('ima3',239600)]:
            self.assertEqual(capacity_samples(codec),capacity)
            for length in (1,720000,8_000_000):
                parts=plan_parts(length,codec=codec)
                self.assertEqual(parts[0]['start'],0)
                self.assertEqual(parts[-1]['stop'],length)
                self.assertEqual([p['stop'] for p in parts[:-1]],[p['start'] for p in parts[1:]])
                for part in parts:self.assertEqual(part['sectors'],157+sum(section_sizes(part['samples'],codec)))
                for volume in plan_volumes(parts):
                    self.assertLessEqual(56+sum(parts[i]['sectors'] for i in volume),2560)
                    self.assertLessEqual(4+sum(parts[i]['file_count'] for i in volume),128)

    def test_single_disk_and_small_parts_obey_directory_limit(self):
        parts=plan_parts(1_000_000,part_samples=8192)
        volumes=plan_volumes(parts)
        self.assertEqual(plan_volumes(parts,single=True),volumes[:1])
        self.assertEqual([i for volume in volumes for i in volume],list(range(len(parts))))
        self.assertTrue(all(len(v)<=31 for v in volumes))

    def test_screen_footer_is_a_real_outlined_spectrum_bar(self):
        screen=prepare(title='AUDIO DISK')
        self.assertEqual(len(screen),6912)
        self.assertEqual(render(screen).size,(256,192))
        for y in range(160,192):
            expected=255 if y in (176,183) else 0
            self.assertTrue(all(screen[spectrum_bitmap_offset(x,y)]==expected for x in range(32)))
        self.assertEqual(screen[6144+22*32:6144+23*32],bytes([4]*32))


if __name__=='__main__':unittest.main()
