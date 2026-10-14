"""Endpoint-consistent idle pair: independent exact replay and unchanged defaults."""
import argparse
from fractions import Fraction
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
from endpoint_idle_pair_model import ENDPOINT_IDLE_PAIR_WORDS, apply_endpoint_idle_pair
from probe_feedback_packets import integral_table
from verify_direct import reference, independent_idle_endpoint, independent_endpoint_idle_pair
from verify_pcm import save
from verify_stream_trd import cold_load, native_check

HERE=Path(__file__).resolve().parent
EXPORT_ROOT=None
PROOF={}


def model(enabled=True):
    result=dict(dict(models())['duration_zero'],compact_stream_loader=True,pcm_quantization_bias=512)
    if enabled:result['endpoint_idle_pair_words']=list(ENDPOINT_IDLE_PAIR_WORDS)
    return result


def original_tables():
    config=model(False)
    return integral_table(64,2,holds=config['holds'],beta=.5,extent=1.,pcm_origin=0)


def archived_producers(root):
    folder=root/'prior-producer';folder.mkdir()
    for name in ('build_stream_trd.py','direct_player.py','stream-player.asm','stream-worker.asm','stream-progress.asm','ram-cache.asm'):
        data=subprocess.run(['git','show','6e06d009:audiobook-beeper/'+name],cwd=HERE.parent,
                            capture_output=True,check=True).stdout
        (folder/name).write_bytes(data)
    namespaces=[]
    for name in ('direct_player.py','build_stream_trd.py'):
        namespace=dict(__file__=str(folder/name),__name__='_prior_endpoint_idle_pair_'+name[:-3])
        exec(compile((folder/name).read_bytes(),str(folder/name),'exec'),namespace)
        namespaces.append(namespace)
    for name in ('layout','canonical_pcm_model','pcm_high_lookup','pcm_quantization_metadata',
                 'neutral_packet_metadata','idle_cycle_packet_metadata','idle_pair_packet_metadata'):
        namespaces[1][name]=namespaces[0][name]
    return folder,namespaces[1]['build']


class EndpointIdlePairPlayerTests(unittest.TestCase):
    def setUp(self):
        scratch=HERE.parent/'.tmp/endpoint-idle-pair-player-tests';scratch.mkdir(parents=True,exist_ok=True)
        self.temporary=tempfile.TemporaryDirectory(dir=scratch);self.root=Path(self.temporary.name)

    def tearDown(self):self.temporary.cleanup()

    def fixture(self):
        root=HERE/'experiments/song-snr/evidence/pcm-quantization-bias/centered'
        return root,gzip.decompress((root/'soundtrack.ima.gz').read_bytes())

    def test_exact_two_cells_every_successor_and_half_mean_area(self):
        words,nxt,_=original_tables();original_words=words.copy();original_next=nxt.copy()
        same_words,same_next=apply_endpoint_idle_pair(words,nxt,model(False))
        self.assertIs(same_words,words);self.assertIs(same_next,nxt)
        changed_words,changed_next=apply_endpoint_idle_pair(words,nxt,model())
        self.assertIs(changed_next,nxt)
        expected=original_words.copy();expected[32,16:18]=ENDPOINT_IDLE_PAIR_WORDS
        np.testing.assert_array_equal(changed_words,expected);np.testing.assert_array_equal(changed_next,original_next)
        np.testing.assert_array_equal(words,original_words);np.testing.assert_array_equal(nxt,original_next)
        self.assertEqual(tuple(map(int,changed_next[32,16:18])),(17,16))
        self.assertEqual(np.argwhere(changed_words!=original_words).tolist(),[[32,16],[32,17]])
        holds=model()['holds']
        on=[sum(hold for slot,hold in enumerate(holds) if word&(1<<(15-slot))) for word in ENDPOINT_IDLE_PAIR_WORDS]
        self.assertEqual(on,[224,225]);self.assertEqual(sum(on)/(2*sum(holds)),.5)
        _,packed=self.fixture()
        actual=layout(packed[:256],dict(model(),extended_ram=True),resident_limit=16384)
        plain=layout(packed[:256],dict(model(False),extended_ram=True),resident_limit=16384)
        np.testing.assert_array_equal(actual[0],expected);np.testing.assert_array_equal(actual[1],original_next)
        self.assertLessEqual(len(actual[2]),18)
        PROOF['table']=dict(changed_cells=[[32,16],[32,17]],all_successors_preserved=True,
            idle_successor_cycle=[17,16],input_tables_unchanged=True,absent_option_identity=True,
            ordinary_on_tstates=on,pair_on_tstates=449,pair_period_tstates=898,pair_mean_duty=.5,
            reachable_states=len(actual[2]),first_patterns=len(actual[3]),second_patterns=len(actual[4]),
            prior_first_patterns=len(plain[3]),prior_second_patterns=len(plain[4]),
            whole64_bin_closure=True,closure_covers_every_pcm_bin=True)

    def test_independent_mixed_and_silent_recurrence_with_primary_helpers_blocked(self):
        _,packed=self.fixture()
        with (patch('endpoint_idle_pair_model.apply_endpoint_idle_pair',side_effect=AssertionError('primary helper called')),
              patch('endpoint_idle_pair_model.validate_endpoint_idle_pair',side_effect=AssertionError('primary validator called')),
              patch('endpoint_idle_pair_model.derive_idle_endpoint',side_effect=AssertionError('primary endpoint replay called'))):
            pcm,indices,levels,bits=reference(packed,cycles=1,model=model())
        self.assertEqual(len(bits),len(pcm)*16+1);self.assertEqual((int(pcm[-1]),int(indices[-1])),(0,0))
        words,nxt,_=original_tables();words[32,16:18]=ENDPOINT_IDLE_PAIR_WORDS
        state=16;expected_words=[]
        for sample in np.r_[pcm,pcm[0]]:
            bucket=min(63,(int(sample)+32768+512)//1024)
            expected_words.append(words[bucket,state]);state=int(nxt[bucket,state])
        expected=np.unpackbits(np.asarray(expected_words,dtype='>u2').view('u1'))[:len(bits)]
        np.testing.assert_array_equal(bits,expected)
        silent=reference(bytes(256),cycles=1,model=model())[3]
        literal=np.unpackbits(np.asarray(ENDPOINT_IDLE_PAIR_WORDS,dtype='>u2').view('u1'))
        np.testing.assert_array_equal(silent[:512*16],np.tile(literal,256))
        PROOF['independence']=dict(reference_uses_neither_primary_helper_nor_validator=True,
            every_mixed_source_bit_matches_manual_recurrence=True,full_silent_source_repeats_pair=True,
            words=list(ENDPOINT_IDLE_PAIR_WORDS),successor_cycle=[17,16])

    def test_exact_endpoints_are_independent_and_required(self):
        # Independently derive neutral endpoints with an affine recurrence.
        # It accumulates duration-weighted area separately from the recent
        # residual, then applies the same documented epsilon and clipped floor.
        epsilon=Fraction(1,10**12);details=[]
        for state,word,wanted in zip((16,17),ENDPOINT_IDLE_PAIR_WORDS,(17,16)):
            prior=Fraction(-1 if state==16 else 1,2);area=Fraction(0)
            for position,hold in enumerate(model()['holds']):
                duration=Fraction(16*hold,449);bit=(word>>(15-position))&1
                prior=Fraction(1,2)+area/duration+prior/2-bit
                area+=duration*(Fraction(1,2)-bit)
            qcode=max(0,min(15,(8*area+Fraction(17,2)+epsilon).__floor__()))
            rcode=max(0,min(1,(prior+1+epsilon).__floor__()))
            actual=independent_idle_endpoint(word,state)
            self.assertEqual((actual['q'],actual['recent']),(area,prior))
            self.assertEqual((actual['qcode'],actual['rcode'],actual['successor']),(qcode,rcode,wanted))
            details.append(dict(state=state,word=word,successor=wanted,
                q=dict(numerator=area.numerator,denominator=area.denominator),
                recent=dict(numerator=prior.numerator,denominator=prior.denominator)))
        # Bad conceptual endpoints fail even when the words and model are valid.
        with patch('verify_direct.independent_idle_endpoint',return_value=dict(successor=16)):
            with self.assertRaises(ValueError):independent_endpoint_idle_pair(model())
            with self.assertRaises(ValueError):reference(bytes(256),cycles=1,model=model())
        for state in (True,15,18,16.):
            with self.assertRaises(ValueError):independent_idle_endpoint(ENDPOINT_IDLE_PAIR_WORDS[0],state)
        PROOF['exact_endpoints']=dict(primary_replay_unused=True,forced_successors=[17,16],
            epsilon=str(epsilon),fraction_endpoints=details,incorrect_derived_successor_rejected=True,
            scope='Exact final labels only; not equivalence to original individual bit decisions or a bounded internal-history proof')

    def test_malformed_shapes_types_duty_and_models_fail_before_mkdir(self):
        base=model();w16,w17=ENDPOINT_IDLE_PAIR_WORDS;invalid=[]
        for value in (None,[],[w16],[w16,w17,w16],[[w16],w17],str([w16,w17]),
                      {0:w16,1:w17},np.asarray([w16,w17]),[True,w17],[float(w16),w17],
                      [np.int64(w16),w17],[-1,w17],[65536,w17],[0,w17],[w16,65535],
                      [w17,w16],[w16,w16],[w17,w17],[0xa952,0xa965],[0x569a,0x56ad]):
            invalid.append(('endpoint_idle_pair_words='+repr(value),dict(base,endpoint_idle_pair_words=value)))
        for key,value in (('pcm_origin',.5),('pcm_origin',False),('extent',.5),('extent',True),('beta',.25),
                          ('pcm_quantization_bias',0),('pcm_bins',128),('pcm_bins',64.),('family',None),
                          ('family','sigma_delta2'),('q_clip',(0,14)),('q_clip',None),('q_clip',(0.,15.)),
                          ('holds',None),('neutral_packet_word',0x56ad),('neutral_packet_successor',16),
                          ('idle_cycle_word',0x56ad),('idle_pair_words',[0x569a,0x56ad]),
                          ('neutral_packet_word',None),('neutral_packet_successor',None),
                          ('idle_cycle_word',None),('idle_pair_words',None)):
            invalid.append((key+'='+repr(value),dict(base,**{key:value})))
        wrong=base.copy();wrong['holds']=base['holds'].copy();wrong['holds'][0]+=1;wrong['holds'][1]-=1
        invalid.append(('same period but wrong individual holds',wrong))
        invalid.append(('both old neutral flags',dict(base,neutral_packet_word=0x56ad,neutral_packet_successor=16)))
        for label,config in invalid:
            with self.subTest(label=label):
                with self.assertRaises(ValueError):canonical_pcm_model(config)
                with self.assertRaises(ValueError):build(bytes(256),self.root/'invalid',bytes(6912),config)
                with self.assertRaises(ValueError):reference(bytes(256),cycles=1,model=config)
        self.assertFalse((self.root/'invalid').exists())
        PROOF['guards']=dict(rejected_cases=[label for label,_ in invalid],before_output_creation=True)

    def test_primary_and_independent_original_cycle_guards(self):
        words,nxt,extra=original_tables();bad_next=nxt.copy();bad_next[32,16]=16
        with self.assertRaises(ValueError):apply_endpoint_idle_pair(words,bad_next,model())
        from verify_direct import rational_tables as original_rational
        def broken_rational(*args,**kwargs):
            result_words,result_next=original_rational(*args,**kwargs)
            result_next=result_next.copy();result_next[32,17]=17
            return result_words,result_next
        with patch('verify_direct.rational_tables',side_effect=broken_rational):
            with self.assertRaises(ValueError):reference(bytes(256),cycles=1,model=model())
        PROOF['cycle_guards']=dict(primary_rejects_modified16_successor=True,
            independent_rejects_modified17_successor=True)

    def test_absent_option_golden_disk_and_6e06_metadata_are_exact(self):
        root,packed=self.fixture();original=(root/'audio.trd').read_bytes()
        previous=json.loads((root/'player.json').read_bytes())
        folder,prior_build=archived_producers(self.root)
        prior_disk,prior_meta=prior_build(packed,self.root/'prior-result',bytes(6912),previous['model'])
        disk,meta=build(packed,self.root/'current',bytes(6912),previous['model'])
        self.assertEqual(prior_disk,original);self.assertEqual(disk,original)
        self.assertEqual(meta,prior_meta);self.assertEqual(meta,previous)
        self.assertNotIn('endpoint_idle_pair',meta);self.assertNotIn('endpoint_idle_pair_words',meta['model'])
        PROOF['default']=dict(prior_version='6e06d009',old_centered_disk_exact=True,
            prior_metadata_exact=True,trd_sha256=hashlib.sha256(original).hexdigest(),
            metadata_sha256=hashlib.sha256(json.dumps(prior_meta,sort_keys=True).encode()).hexdigest())
        if EXPORT_ROOT is not None:
            shutil.copytree(folder,EXPORT_ROOT/'prior-producer');save(EXPORT_ROOT/'default-player.json',meta)

    def test_short_native_all_four_and_conditional_maximum_cold_bounds(self):
        root,packed=self.fixture()
        before,before_meta=build(packed,self.root/'before',bytes(6912),model(False))
        after,meta=build(packed,self.root/'after',bytes(6912),model())
        option=meta['endpoint_idle_pair']
        self.assertEqual(option['words'],list(ENDPOINT_IDLE_PAIR_WORDS));self.assertEqual(option['feedback_states'],[16,17])
        self.assertTrue(option['preserve_successors']);self.assertEqual(option['successor_cycle'],[17,16])
        self.assertEqual(option['ordinary_on_tstates'],[224,225]);self.assertEqual(option['ordinary_period_tstates'],449)
        self.assertEqual(option['pair_mean_duty'],.5);self.assertFalse(option['live_instruction_changes'])
        self.assertEqual(option['exact_derived_endpoint_successors'],[17,16])
        self.assertEqual(option['endpoint_epsilon'],'1/1000000000000')
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
        shape=lambda config:(len(config['first_addresses']),len(config['second_addresses']),
                             config['memory']['resident_table_end'],config['memory']['worker_origin'])
        changed=shape(meta)!=shape(before_meta);maximum={}
        if changed:
            max_disk,max_meta=build(bytes(2392*256),self.root/'maximum',bytes(6912),model())
            self.assertLessEqual(max_meta['player_labels']['stream_worker_end'],0xbfff)
            self.assertLessEqual(len(max_meta['feedback_states']),18)
            loaded,loading=cold_load(max_disk,max_meta,'pentagon1024')
            self.assertEqual(loading['remaining_sectors'],0);self.assertFalse(loaded.locked)
            self.assertEqual(sum(item['bytes'] for item in loading['loaded_sections']),2392*256)
            maximum=dict(maximum_cold_loading=loading,maximum_worker_origin=max_meta['memory']['worker_origin'],
                maximum_worker_end=max_meta['player_labels']['stream_worker_end'],maximum_bank2_end=0xbfff)
            if EXPORT_ROOT is not None:save(EXPORT_ROOT/'maximum-player.json',max_meta)
        PROOF['native']=dict(complete_short_native_runs=8,profiles=results,
            ordinary_tstates={'128':423,'scorpion':423,'pentagon512':449,'pentagon1024':449},
            instruction_table_HOLDS=[36,28,28,31,24,26,22,20,22,26,22,30,31,27,34,16],
            pentagon_slot7_extra=26,native_tstate_delta=0,page_extra_tstates=14,
            bank_extra_tstates={'128':243,'scorpion':267,'pentagon512':243,'pentagon1024':243},
            dictionary_or_worker_footprint_changed=changed,**maximum,
            actual_Fuse_or_hardware_or_audio_quality_claim=False,
            ula_scope='128/Scorpion address-dependent contention is outside native CPU proofs')
        if EXPORT_ROOT is not None:
            for name,disk in (('before',before),('after',after)):
                (self.root/name/'audio.trd').write_bytes(disk)
                (self.root/name/'soundtrack.ima.gz').write_bytes(gzip.compress(packed,mtime=0))
                (self.root/name/'source-preview.wav').write_bytes((root/'source-preview.wav').read_bytes())
                shutil.copytree(self.root/name,EXPORT_ROOT/name)


if __name__=='__main__':
    parser=argparse.ArgumentParser(add_help=False);parser.add_argument('--evidence',type=Path)
    args,remaining=parser.parse_known_args()
    if args.evidence is not None:
        EXPORT_ROOT=args.evidence.resolve()
        if EXPORT_ROOT.exists() and any(EXPORT_ROOT.iterdir()):parser.error('evidence output must be empty')
        EXPORT_ROOT.mkdir(parents=True,exist_ok=True)
    result=unittest.main(argv=[sys.argv[0],*remaining],exit=False).result
    if result.wasSuccessful() and EXPORT_ROOT is not None:
        names=('test_endpoint_idle_pair_player.py','build_stream_trd.py','direct_player.py',
               'verify_direct.py','verify_stream_trd.py','endpoint_idle_pair_model.py')
        hashes={name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in names}
        save(EXPORT_ROOT/'report.json',dict(complete=True,date='2026-10-14',proof=PROOF,current_producer_sha256=hashes,
            scope='Opt-in exact endpoint-label and functional native proof; no individual-greedy-rule, bounded-history, full Fuse or audio acceptance claim',
            reproducer='python audiobook-beeper/test_endpoint_idle_pair_player.py --evidence NEW_EMPTY_FOLDER -v'))
    raise SystemExit(0 if result.wasSuccessful() else 1)
