"""Authenticate public Small EOF option against its complete S01 raw proof."""
import gzip
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'libraries/lzsa/src'))

from lzsa import compact,block


def sha(blob):return hashlib.sha256(blob).hexdigest()


def regions(profile):
    return [dict(address=at,bytes=len(blob),sha256=sha(blob)) for at,blob in profile[0]]


class SmallEOFTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous=ROOT/'libraries/evidence/next_s01_prior_sources.json.gz'
        assert sha(previous.read_bytes())=='176d974d6335a21ca73c1a80a36fb55f575ed63447bb3bddde7d1e4b98da7bdb'
        archive=json.loads(gzip.decompress(previous.read_bytes()))
        cls.original={}
        for module,name in ((compact,'compact'),(block,'block')):
            source=archive['libraries/lzsa/src/lzsa/'+name+'.py']
            assert sha(source['text'].encode())==source['sha256_lf']
            namespace=dict(vars(module))
            exec(compile(source['text'],'<S01 archived '+name+'>','exec'),namespace)
            cls.original[name]=namespace['build']
        path=ROOT/'libraries/evidence/next_s01_lzsa_full.json.gz'
        assert sha(path.read_bytes())=='05cf06edbb09b2c1aea741f46aebabe13c6964370bd370875f994524b154f48f'
        cls.proof=json.loads(gzip.decompress(path.read_bytes()))
        assert cls.proof['complete']

    def test_all_existing_small_defaults_exact(self):
        for core in (0x8000,0x9103):
            expected=self.original['compact'](core=core,core_limit=core+512)
            self.assertEqual(compact.build(core=core,core_limit=core+512),expected)
            self.assertEqual(compact.build(core=core,core_limit=core+512,compact_eof=False),expected)
            self.assertEqual(block.build('small',core=core,core_limit=core+512),expected)
        # New routing does not alter old Fast/Wide default output or metadata.
        for variant in ('fast','wide','wide-shared'):
            expected=self.original['block'](variant,core_limit=0xc000)
            self.assertEqual(block.build(variant,core_limit=0xc000),expected)

    def test_new_bytes_labels_and_every_alignment_match_complete_proof(self):
        entry=self.proof['profiles']['eof_stack']
        self.assertTrue(entry['native_complete'])
        self.assertEqual(entry['qualification']['native_configs'],4098)
        for low,row in enumerate(entry['alignments']):
            p=compact.build(core=0x8000+low,core_limit=0x8200+low,compact_eof=True)
            self.assertEqual(regions(p),row['regions'])
            self.assertEqual(p[1],row['labels'])
            self.assertEqual(p[2]['service_memory_bytes'],144)
        p=compact.build(core=0x9103,core_limit=0x9303,compact_eof=True)
        self.assertEqual(regions(p),entry['relocated']['regions'])
        self.assertEqual(p[1],entry['relocated']['labels'])
        self.assertEqual(block.build('small',compact_eof=True),compact.build(compact_eof=True))

    def test_actual_inventory_initialization_and_reference(self):
        p=compact.build(compact_eof=True);meta=p[2]
        self.assertEqual(sum(len(blob) for _,blob in p[0]),136)
        self.assertEqual(meta['service_memory_bytes'],136+8)
        self.assertEqual(sum(meta['service_memory'].values()),144)
        self.assertEqual(meta['embedded_mutable_bytes'],len(meta['patched_addresses']))
        self.assertTrue(meta['embedded_state_counted_once_in_code'])
        self.assertEqual(meta['decoder_stack_bytes'],6)
        self.assertEqual(meta['per_block_setup_tstates'],24)
        self.assertEqual(meta['external_initialization_tstates'],0)
        self.assertEqual(meta['reference_real_tstates'],20423420)
        self.assertEqual(meta['compact_eof_path_delta_tstates'],dict(eof=-6,word_escape=14))
        self.assertEqual(self.proof['profiles']['eof_stack']['summary']['real_delta_tstates'],-126)
        # The shortened option fits a reservation which rejects old137B code.
        self.assertEqual(compact.build(core_limit=0x8088,compact_eof=True)[2]['code_bytes'],136)
        with self.assertRaises(ValueError):compact.build(core_limit=0x8088)

    def test_invalid_values_and_other_modes_rejected(self):
        for value in (None,0,1,'false',[],{}):
            with self.assertRaises(ValueError):compact.build(compact_eof=value)
            with self.assertRaises(ValueError):block.build('small',compact_eof=value)
        for variant in ('fast','wide','wide-shared','unknown'):
            with self.assertRaises(ValueError):block.build(variant,compact_eof=True)
        with self.assertRaises(ValueError):block.build('small',long_copy=True,compact_eof=True)


if __name__=='__main__':unittest.main()
