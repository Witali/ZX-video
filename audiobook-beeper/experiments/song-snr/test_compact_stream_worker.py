"""Optional persistent startup loader bounds and unchanged default disk bytes.

Cold loads execute the complete native loader on all four memory profiles.
These tests prove allocation/immutability and assembly feasibility, not new
filtered audio quality, complete live playback or physical floppy timing.
"""
import gzip
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import sys

from build_stream_trd import build,sections
from general import models
from ram_cache import PROFILES
from verify_stream_trd import cold_load,native_check
from verify_pcm import save


HERE=Path(__file__).resolve().parent
EXPECTED_DEFAULT='226388fb795ac70cfd940545a9eb73e3e81b6c7e96533dc6deb0c215257338ea'


class CompactStreamWorker(unittest.TestCase):
    def setUp(self):
        root=HERE.parents[2]/'.tmp';root.mkdir(exist_ok=True)
        self.temporary=tempfile.TemporaryDirectory(dir=root,prefix='compact-worker-')
        self.work=Path(self.temporary.name)
        self.packed=gzip.decompress((HERE/'evidence/study/inputs/song/soundtrack.ima.gz').read_bytes())
        self.legacy_meta=json.loads((HERE/'evidence/study/inputs/song/player.json').read_bytes())
        control=(HERE/'evidence/study/inputs/current-main.trd').read_bytes()
        cover_entry=next(e for e in self.legacy_meta['directory'] if e['name']=='COVER')
        sector=cover_entry['track']*16+cover_entry['sector']
        self.cover=control[sector*256:(sector+27)*256]

    def tearDown(self):self.temporary.cleanup()

    def midpoint(self):
        return dict(dict(models())['duration_midpoint'],compact_stream_loader=True)

    def assert_regions(self,disk,meta):
        labels=meta['player_labels']
        self.assertEqual(labels['startup_hot_end'],0x808a)
        self.assertEqual(labels['stream_probe_start'],0x808a)
        self.assertEqual(labels['stream_probe_end']-labels['stream_probe_start'],311)
        self.assertEqual(labels['stream_bounce'],0x81c1)
        self.assertEqual(labels['startup_end'],0x82c1)
        self.assertLessEqual(labels['startup_end'],min(meta['first_addresses']))
        self.assertEqual(labels['resident_end'],0xbc40)
        self.assertEqual(meta['memory']['worker_origin'],0xbc40)
        self.assertEqual(meta['memory']['worker_origin']%64,0)
        self.assertLess(labels['stream_worker_end'],0xbfff)
        self.assertEqual(len(meta['feedback_states']),18)
        self.assertEqual(meta['ordinary_holds_tstates'],[36,28,28,31,24,26,22,20,22,26,22,30,31,27,34,16])
        self.assertEqual(meta['page_extra_tstates'],14)
        self.assertEqual(len(disk),655360)

    def test_default_and_explicit_false_keep_original_trd_bytes(self):
        disk,meta=build(self.packed,self.work/'default',self.cover)
        self.assertEqual(hashlib.sha256(disk).hexdigest(),EXPECTED_DEFAULT)
        self.assertNotIn('compact_stream_loader',meta['memory'])
        self.assertNotIn('compact_stream_loader',meta['model'])
        self.assertNotIn('compact_stream_loader',meta['player_labels'])
        explicit,explicit_meta=build(self.packed,self.work/'explicit-false',self.cover,
                         dict(self.legacy_meta['model'],compact_stream_loader=False))
        self.assertEqual(explicit,disk)
        self.assertEqual(explicit_meta,meta)
        # Archived source/cover metadata differs only in disk identity from
        # the twelve-pixel current cover. Every address/model/layout export
        # and independently assembled player byte must retain its old value.
        expected=json.loads(json.dumps(self.legacy_meta))
        expected['trd_sha256']=meta['trd_sha256']
        # The prior worker-budget milestone already exported these three
        # values. This older main-image snapshot predates that metadata-only
        # addition; all values come from its existing exact assembly labels.
        expected['player_labels']['worker_origin']=self.legacy_meta['player_labels']['cache_map']
        expected['memory']['worker_origin']=self.legacy_meta['player_labels']['cache_map']
        expected['memory']['resident_table_end']=self.legacy_meta['player_labels']['resident_end']
        self.assertEqual(meta,expected)

    def test_full_song_midpoint_layout_is_source_independent_and_bounded(self):
        disk,meta=build(self.packed,self.work/'song',self.cover,self.midpoint())
        self.assert_regions(disk,meta)
        self.assertEqual(meta['packed_bytes'],360192)
        self.assertEqual(meta['pcm_samples'],720384)
        self.assertEqual(meta['audio_sectors'],1407)
        self.assertEqual(meta['player_labels']['stream_worker_end'],0xbf8f)
        # The explicit opt-in is required; old builders retain their proved
        # table/worker budget instead of silently relocating archived images.
        with self.assertRaises(AssertionError):
            build(self.packed,self.work/'unflagged',self.cover,dict(models())['duration_midpoint'])

    def test_existing_half_recent_disk_and_metadata_are_identical(self):
        archived=HERE/'evidence/clock-joint/sea_foam'
        old=json.loads((archived/'player.json').read_bytes())
        packed=gzip.decompress((archived/'soundtrack.ima.gz').read_bytes())
        control=(archived/'audio.trd').read_bytes()
        entry=next(e for e in old['directory'] if e['name']=='COVER')
        at=(entry['track']*16+entry['sector'])*256
        disk,meta=build(packed,self.work/'old-half-recent',control[at:at+6912],old['model'])
        self.assertEqual(disk,control)
        self.assertEqual(meta,old)

    def test_maximum_disk_cold_loads_all_physical_memory_profiles(self):
        packed=bytes(2392*256)
        disk,meta=build(packed,self.work/'maximum',bytes(6912),self.midpoint())
        self.assert_regions(disk,meta)
        self.assertEqual(meta['player_labels']['stream_worker_end'],0xbfbc)
        labels=meta['player_labels']
        entry=next(e for e in meta['directory'] if e['name']=='PLAYER')
        start=(entry['track']*16+entry['sector'])*256
        player=disk[start:start+16384]
        probe=player[labels['stream_probe_start']-0x8000:labels['stream_probe_end']-0x8000]
        for profile in PROFILES:
            with self.subTest(profile=profile):
                machine,loaded=cold_load(disk,meta,profile)
                expected,left=sections(len(packed),PROFILES[profile]['pages'])
                self.assertEqual(loaded['remaining_sectors'],left//256)
                self.assertEqual(loaded['loaded_sections'],[
                    dict(bank=s['bank'],address=s['address'],bytes=s['bytes']) for s in expected])
                self.assertEqual(sum(s['bytes'] for s in loaded['loaded_sections']),len(packed)-left)
                self.assertFalse(machine.locked)
                self.assertEqual(bytes(machine.read(a) for a in range(labels['stream_probe_start'],labels['stream_probe_end'])),probe)
                last_sector=meta['audio_sector']+(len(packed)-left)//256-1
                bounce=bytes(machine.read(a) for a in range(labels['stream_bounce'],labels['stream_bounce']+256))
                self.assertEqual(bounce,disk[last_sector*256:(last_sector+1)*256])


def native_evidence(output):
    """Reproduce complete native layout/refill evidence, without running Fuse."""
    from concurrent.futures import ThreadPoolExecutor
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(CompactStreamWorker),
                            unittest.defaultTestLoader.loadTestsFromName('test_worker_budget')])
    log=io.StringIO();result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    (output/'producer.testlog').write_text(log.getvalue(),encoding='utf-8')
    print(log.getvalue(),flush=True)
    if not result.wasSuccessful():raise AssertionError('Compact-loader tests failed')
    root=HERE.parents[2]/'.tmp';root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=root,prefix='compact-native-') as temporary:
        helper=CompactStreamWorker();helper.setUp()
        try:
            model=helper.midpoint()
            disk,meta=build(helper.packed,Path(temporary)/'song',helper.cover,model)
            helper.assert_regions(disk,meta)
            def run(profile):
                report=native_check(disk,meta,helper.packed,profile,out=output/('native-'+profile+'.json'))
                print('Complete native compact midpoint: '+profile,flush=True)
                return report
            with ThreadPoolExecutor(max_workers=4) as pool:reports=list(pool.map(run,PROFILES))
            maximum,max_meta=build(bytes(2392*256),Path(temporary)/'maximum',bytes(6912),model)
            helper.assert_regions(maximum,max_meta)
            cold=[]
            for profile in PROFILES:
                _,loaded=cold_load(maximum,max_meta,profile)
                cold.append(loaded)
                save(output/('maximum-cold-'+profile+'.json'),loaded)
            save(output/'song-player.json',meta);save(output/'maximum-player.json',max_meta)
            identities=dict(source_pcm='../study/inputs/song/source-preview.wav',
                            source_packed='../study/inputs/song/soundtrack.ima.gz',
                            packed_sha256=hashlib.sha256(helper.packed).hexdigest(),
                            cover_source='../study/inputs/current-main.trd',
                            cover_source_sha256=hashlib.sha256((HERE/'evidence/study/inputs/current-main.trd').read_bytes()).hexdigest(),
                            cover_sha256=hashlib.sha256(helper.cover).hexdigest(),
                            unretimed_historical_source_preserved=True)
            save(output/'source-inputs.json',identities)
        finally:helper.tearDown()
    producers={}
    for path in (HERE.parents[1]/'build_stream_trd.py',HERE.parents[1]/'stream-player.asm',
                 HERE.parents[1]/'stream-worker.asm',Path(__file__)):
        producers[str(path.relative_to(HERE.parents[2]))]=hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()
    save(output/'report.json',dict(complete=True,date='2026-10-14',explicit_opt_in='model.compact_stream_loader=True',
        default_false_disk_and_metadata_unchanged=True,default_trd_sha256=EXPECTED_DEFAULT,
        tests_passed=result.testsRun,source_inputs=identities,producer_sha256_lf=producers,
        song_trd_sha256=meta['trd_sha256'],song_player_binary_sha256=meta['binary_sha256'],
        full_native_song_profiles=reports,maximum_audio_sectors=2392,maximum_cold_profiles=cold,
        layout=dict(probe_start=meta['player_labels']['stream_probe_start'],probe_end=meta['player_labels']['stream_probe_end'],
            bounce_start=meta['player_labels']['stream_bounce'],bounce_bytes=256,startup_end=meta['player_labels']['startup_end'],
            first_base=min(meta['first_addresses']),resident_end=meta['player_labels']['resident_end'],
            worker_origin=meta['memory']['worker_origin'],song_worker_end=meta['player_labels']['stream_worker_end'],
            maximum_worker_end=max_meta['player_labels']['stream_worker_end'],fixed_bank2_bytes=16384),
        tstates=dict(before={'128':423,'scorpion':423,'pentagon512':449,'pentagon1024':449},
            after={'128':423,'scorpion':423,'pentagon512':449,'pentagon1024':449},hot_path_delta=0,
            page_extra_before_after=14,bank_extra_before_after={'128':243,'scorpion':267,'pentagon512':243,'pentagon1024':243}),
        new_fuse_execution=False,physical_hardware_tested=False,new_encoder_quality_verified=False,
        reproducer='PYTHONPATH=<audiobook-beeper>;<toolkit>;<song-snr>;<z80-dependencies> python test_compact_stream_worker.py --native-evidence evidence/compact-midpoint',
        scope='Complete native old-packed whole-song and maximum-disk cold-load layout/refill proof. This enables a universal midpoint table; it is not new encoded audio quality, real-ROM/disk timing, a release or proof of absence of audible artifacts.'))


if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--native-evidence':
        if len(sys.argv)!=3:raise SystemExit('Usage: test_compact_stream_worker.py --native-evidence OUTPUT')
        native_evidence(sys.argv[2])
    else:unittest.main()
