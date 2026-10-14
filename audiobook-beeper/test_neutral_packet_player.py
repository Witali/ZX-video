"""Optional neutral-row wiring, independent guards and unchanged defaults."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from build_stream_trd import build
from direct_player import canonical_pcm_model, layout
from general import models
from neutral_packet_model import NEUTRAL_PACKET_WORD, NEUTRAL_PACKET_SUCCESSOR, apply_neutral_packet
from probe_feedback_packets import integral_table
from verify_direct import reference
from verify_pcm import save
from verify_stream_trd import cold_load, native_check


HERE=Path(__file__).resolve().parent
EXPORT_ROOT=None
PROOF={}


def model(enabled=True):
    result=dict(dict(models())['duration_zero'],compact_stream_loader=True,pcm_quantization_bias=512)
    if enabled:result.update(neutral_packet_word=NEUTRAL_PACKET_WORD,neutral_packet_successor=NEUTRAL_PACKET_SUCCESSOR)
    return result


def archived_producers(root):
    folder=root/'prior-producer';folder.mkdir()
    for name in ('build_stream_trd.py','direct_player.py','stream-player.asm','stream-worker.asm','stream-progress.asm','ram-cache.asm'):
        data=subprocess.run(['git','show','1d5bd8e0:audiobook-beeper/'+name],cwd=HERE.parent,
                            capture_output=True,check=True).stdout
        (folder/name).write_bytes(data)
    namespaces=[]
    for name in ('direct_player.py','build_stream_trd.py'):
        namespace=dict(__file__=str(folder/name),__name__='_prior_neutral_'+name[:-3])
        exec(compile((folder/name).read_bytes(),str(folder/name),'exec'),namespace)
        namespaces.append(namespace)
    for name in ('layout','canonical_pcm_model','pcm_high_lookup','pcm_quantization_metadata'):
        namespaces[1][name]=namespaces[0][name]
    return folder,namespaces[1]['build']


class NeutralPacketPlayerTests(unittest.TestCase):
    def setUp(self):
        scratch=HERE.parent/'.tmp/neutral-packet-player-tests';scratch.mkdir(parents=True,exist_ok=True)
        self.temporary=tempfile.TemporaryDirectory(dir=scratch);self.root=Path(self.temporary.name)

    def tearDown(self):self.temporary.cleanup()

    def fixture(self):
        root=HERE/'experiments/song-snr/evidence/pcm-quantization-bias/centered'
        return root,gzip.decompress((root/'soundtrack.ima.gz').read_bytes())

    def test_only_bin32_changes_and_layout_uses_the_literal(self):
        config=model();plain=model(False)
        words,nxt,_=integral_table(64,2,holds=config['holds'],beta=.5,extent=1.,pcm_origin=0)
        original_words=words.copy();original_next=nxt.copy()
        same_words,same_next=apply_neutral_packet(words,nxt,plain)
        self.assertIs(same_words,words);self.assertIs(same_next,nxt)
        changed_words,changed_next=apply_neutral_packet(words,nxt,config)
        rows=np.r_[np.arange(32),np.arange(33,64)]
        np.testing.assert_array_equal(changed_words[rows],original_words[rows])
        np.testing.assert_array_equal(changed_next[rows],original_next[rows])
        self.assertTrue(np.all(changed_words[32]==NEUTRAL_PACKET_WORD))
        self.assertTrue(np.all(changed_next[32]==16))
        np.testing.assert_array_equal(words,original_words);np.testing.assert_array_equal(nxt,original_next)
        _,packed=self.fixture()
        actual=layout(packed[:256],dict(config,extended_ram=True),resident_limit=16384)
        np.testing.assert_array_equal(actual[0],changed_words)
        np.testing.assert_array_equal(actual[1],changed_next)
        self.assertLessEqual(len(actual[2]),18)
        self.assertIn(NEUTRAL_PACKET_WORD>>8,actual[3])
        self.assertIn(NEUTRAL_PACKET_WORD&255,actual[4])
        PROOF['table']=dict(only_bin32_modified=True,all32_neutral_successors=16,
                            input_tables_unchanged=True,absent_option_identity=True,
                            reachable_states=len(actual[2]),first_patterns=len(actual[3]),second_patterns=len(actual[4]))

    def test_independent_reference_does_not_call_primary_helper(self):
        _,packed=self.fixture()
        with (patch('neutral_packet_model.apply_neutral_packet',side_effect=AssertionError('primary helper called')),
              patch('neutral_packet_model.validate_neutral_packet',side_effect=AssertionError('primary validator called'))):
            pcm,indices,levels,bits=reference(packed,cycles=1,model=model())
        self.assertEqual(len(bits),len(pcm)*16+1)
        self.assertEqual((int(pcm[-1]),int(indices[-1])),(0,0))
        silent=reference(bytes(256),cycles=1,model=model())[3]
        expected=np.unpackbits(np.asarray([NEUTRAL_PACKET_WORD],dtype='>u2').view('u1'))
        np.testing.assert_array_equal(silent[:512*16],np.tile(expected,512))
        PROOF['independence']=dict(reference_uses_neither_primary_helper_nor_validator=True,
                                   full_silent_source_repeats_literal=True,word=NEUTRAL_PACKET_WORD,successor=16)

    def test_invalid_flags_duty_and_model_contract_fail_before_mkdir(self):
        base=model();invalid=[]
        for key,value in (('neutral_packet_word',True),('neutral_packet_word',None),
                          ('neutral_packet_word',float(NEUTRAL_PACKET_WORD)),('neutral_packet_word','56AD'),
                          ('neutral_packet_word',-1),('neutral_packet_word',65536),('neutral_packet_word',0),
                          ('neutral_packet_word',65535),('neutral_packet_successor',True),
                          ('neutral_packet_successor',16.),('neutral_packet_successor',17),
                          ('pcm_origin',.5),('pcm_origin',False),('extent',.5),('extent',True),
                          ('beta',.25),('pcm_quantization_bias',0),('pcm_bins',128),('pcm_bins',64.),
                          ('family',None),('family','sigma_delta2'),('q_clip',(0,14)),
                          ('q_clip',None),('q_clip',(0.,15.)),('holds',None)):
            invalid.append((key+'='+repr(value),dict(base,**{key:value})))
        for key in ('neutral_packet_word','neutral_packet_successor'):
            changed=base.copy();changed.pop(key);invalid.append(('missing '+key,changed))
        wrong=base.copy();wrong['holds']=base['holds'].copy();wrong['holds'][0]+=1;wrong['holds'][1]-=1
        invalid.append(('same period but wrong individual holds',wrong))
        for label,config in invalid:
            with self.subTest(label=label):
                with self.assertRaises(ValueError):canonical_pcm_model(config)
                with self.assertRaises(ValueError):build(bytes(256),self.root/'invalid',bytes(6912),config)
                with self.assertRaises(ValueError):reference(bytes(256),cycles=1,model=config)
        self.assertFalse((self.root/'invalid').exists())
        PROOF['guards']=dict(rejected_cases=[label for label,_ in invalid],before_output_creation=True)

    def test_absent_option_golden_disk_and_1d5_metadata_are_exact(self):
        root,packed=self.fixture();original=(root/'audio.trd').read_bytes()
        previous=json.loads((root/'player.json').read_bytes())
        folder,prior_build=archived_producers(self.root)
        prior_disk,prior_meta=prior_build(packed,self.root/'prior-result',bytes(6912),previous['model'])
        disk,meta=build(packed,self.root/'current',bytes(6912),previous['model'])
        self.assertEqual(prior_disk,original);self.assertEqual(disk,original)
        self.assertEqual(meta,prior_meta);self.assertEqual(meta,previous)
        self.assertNotIn('neutral_packet',meta)
        PROOF['default']=dict(prior_version='1d5bd8e0',old_centered_disk_exact=True,
            prior_metadata_exact=True,trd_sha256=hashlib.sha256(original).hexdigest(),
            metadata_sha256=hashlib.sha256(json.dumps(prior_meta,sort_keys=True).encode()).hexdigest())
        if EXPORT_ROOT is not None:
            shutil.copytree(folder,EXPORT_ROOT/'prior-producer');save(EXPORT_ROOT/'default-player.json',meta)

    def test_short_native_all_four_and_maximum_cold_layout_bounds(self):
        root,packed=self.fixture()
        before,before_meta=build(packed,self.root/'before',bytes(6912),model(False))
        after,meta=build(packed,self.root/'after',bytes(6912),model())
        self.assertEqual(meta['neutral_packet']['word'],NEUTRAL_PACKET_WORD)
        self.assertEqual(meta['neutral_packet']['successor'],16)
        self.assertEqual(meta['neutral_packet']['ordinary_on_tstates'],225)
        self.assertEqual(meta['neutral_packet']['ordinary_period_tstates'],449)
        self.assertEqual(meta['neutral_packet']['ordinary_mean_duty'],225/449)
        self.assertFalse(meta['neutral_packet']['live_instruction_changes'])
        results=[]
        for profile in ('128','scorpion','pentagon512','pentagon1024'):
            with self.subTest(profile=profile):
                old=native_check(before,before_meta,packed,profile,out=self.root/'before'/('native-'+profile+'.json'))
                actual=native_check(after,meta,packed,profile,out=self.root/'after'/('native-'+profile+'.json'))
                self.assertTrue(actual['complete']);self.assertTrue(actual['memory_guards_passed'])
                self.assertTrue(actual['every_bit_predictor_index_exact']);self.assertTrue(actual['every_continuous_native_hold_exact'])
                self.assertEqual(actual['ordinary_tstates'],449 if profile.startswith('pentagon') else 423)
                self.assertEqual(actual['ordinary_tstates'],old['ordinary_tstates'])
                self.assertEqual(actual['interval_extras'],old['interval_extras'])
                results.append(dict(profile=profile,before=old,after=actual))
        max_disk,max_meta=build(bytes(2392*256),self.root/'maximum',bytes(6912),model())
        self.assertLessEqual(max_meta['player_labels']['stream_worker_end'],0xbfff)
        self.assertLessEqual(len(max_meta['feedback_states']),18)
        loaded,loading=cold_load(max_disk,max_meta,'pentagon1024')
        self.assertEqual(loading['remaining_sectors'],0);self.assertFalse(loaded.locked)
        self.assertEqual(sum(item['bytes'] for item in loading['loaded_sections']),2392*256)
        PROOF['native']=dict(complete_short_native_runs=8,profiles=results,ordinary_tstates={'128':423,'scorpion':423,'pentagon512':449,'pentagon1024':449},
            instruction_table_HOLDS=[36,28,28,31,24,26,22,20,22,26,22,30,31,27,34,16],pentagon_slot7_extra=26,native_tstate_delta=0,
            page_extra_tstates=14,bank_extra_tstates={'128':243,'scorpion':267,'pentagon512':243,'pentagon1024':243},
            maximum_cold_loading=loading,maximum_worker_origin=max_meta['memory']['worker_origin'],
            maximum_worker_end=max_meta['player_labels']['stream_worker_end'],maximum_bank2_end=0xbfff,
            actual_Fuse_or_hardware_or_audio_quality_claim=False,
            ula_scope='128/Scorpion address-dependent contention is outside native CPU proofs')
        if EXPORT_ROOT is not None:
            for name,disk in (('before',before),('after',after)):
                (self.root/name/'audio.trd').write_bytes(disk)
                (self.root/name/'soundtrack.ima.gz').write_bytes(gzip.compress(packed,mtime=0))
                (self.root/name/'source-preview.wav').write_bytes((root/'source-preview.wav').read_bytes())
                shutil.copytree(self.root/name,EXPORT_ROOT/name)
            save(EXPORT_ROOT/'maximum-player.json',max_meta)


if __name__=='__main__':
    parser=argparse.ArgumentParser(add_help=False);parser.add_argument('--evidence',type=Path)
    args,remaining=parser.parse_known_args()
    if args.evidence is not None:
        EXPORT_ROOT=args.evidence.resolve()
        if EXPORT_ROOT.exists() and any(EXPORT_ROOT.iterdir()):parser.error('evidence output must be empty')
        EXPORT_ROOT.mkdir(parents=True,exist_ok=True)
    result=unittest.main(argv=[sys.argv[0],*remaining],exit=False).result
    if result.wasSuccessful() and EXPORT_ROOT is not None:
        names=('test_neutral_packet_player.py','build_stream_trd.py','direct_player.py','verify_direct.py','verify_stream_trd.py','neutral_packet_model.py')
        hashes={name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in names}
        save(EXPORT_ROOT/'report.json',dict(complete=True,date='2026-10-14',proof=PROOF,current_producer_sha256=hashes,
            scope='Opt-in functional native proof and source-independent table bounds; no full Fuse or audio acceptance claim',
            reproducer='python audiobook-beeper/test_neutral_packet_player.py --evidence NEW_EMPTY_FOLDER -v'))
    raise SystemExit(0 if result.wasSuccessful() else 1)
