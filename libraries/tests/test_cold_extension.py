"""Opt-in cold length escapes preserve old raw profiles and strict contracts."""
import gzip
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'libraries/lzsa/src'))
from lzsa.hybrid import build as hybrid
from lzsa.wide import build as wide
from measure_next_cold_extension import selections,identity,branch_address,spans


class ColdExtensionTests(unittest.TestCase):
    def test_classic_defaults_and_opt_in_layout(self):
        saved=json.loads(gzip.decompress((ROOT/'libraries/evidence/next_e01_lzsa_defaults.json.gz').read_bytes()))
        for name,builder,kwargs in selections():
            for low in (0,1,3,127,255):
                old=saved['profiles'][name]['alignments'][low]
                if not old['accepted']:continue
                profile=builder(core=0x8000+low,**kwargs)
                self.assertEqual(identity(profile),old['complete_profile_sha256'])
                self.assertEqual(profile,builder(core=0x8000+low,cold_match_extension=False,**kwargs))
                changed=builder(core=0x8000+low,cold_match_extension=True,**kwargs)
                self.assertEqual(changed[2]['service_memory_bytes'],profile[2]['service_memory_bytes']-1)
                at=branch_address(changed)
                branch=next(row for row in spans(changed) if row['address']==at)
                self.assertEqual((branch['opcode'],branch['displacement']),(0x30,26))
                self.assertNotIn('ColdExtendedMatch',profile[1])
                self.assertTrue(changed[2]['cold_match_extension'])
                self.assertEqual(changed[2]['caller_stack_bytes'],6)

    def test_unqualified_options_and_hooks_are_rejected(self):
        for value in (0,1,None,'cold'):
            with self.assertRaises(ValueError):wide(cold_match_extension=value)
            with self.assertRaises(ValueError):hybrid(cold_match_extension=value)
        for kwargs in (dict(short_lengths=(2,)),dict(repeat_lengths=(4,)),
            dict(shared_literals=True,short_lengths=range(3,9)),
            dict(_boundary=lambda a:None),dict(_external_labels={}),dict(_literal_guards=True)):
            with self.assertRaises(ValueError):wide(cold_match_extension=True,**kwargs)
        self.assertTrue(wide(short_lengths=(2,))[0])
        self.assertEqual(wide(core=0x9003,short_lengths=range(2,9),cold_match_extension=True)[2]['service_memory_bytes'],10000)
        for origin in (0x9001,0x9002):
            with self.assertRaises(ValueError):wide(core=origin,short_lengths=range(2,9),cold_match_extension=True)

    def test_native_exact_eof_word_short_forms_and_overlap_guard(self):
        from measure_full_token_dispatch import directed_tokens
        from native_inplace_block import execute,host_trace
        from lzsa import encode
        profile=hybrid(cold_match_extension=True)
        for name,payload,raw,wanted in directed_tokens():
            if name not in ('word-literal-1','word-literal-2','single-nibble-eof-empty','single-nibble-eof-one'):continue
            for interrupts in (False,True):
                result=execute(profile,payload,raw,codec='lzsa2',interrupts=interrupts)
                self.assertTrue(result['host_read_order_exact'])
                self.assertTrue(result['code_protected'])
                self.assertTrue(result['raw_abi_exact'])
        raw=b'A'*8192;payload=encode(raw,[(1,len(raw)-1,1)])
        proof=host_trace('lzsa2',payload,raw)
        self.assertTrue(execute(profile,payload,raw,codec='lzsa2')['host_read_order_exact'])
        with self.assertRaisesRegex(AssertionError,'overwrites unread input'):
            execute(profile,payload,raw,codec='lzsa2',source=0xc000+proof['minimum_input_start']-1)


if __name__=='__main__':unittest.main()
