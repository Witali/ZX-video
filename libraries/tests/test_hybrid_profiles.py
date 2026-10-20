"""Public fixed hybrids preserve the complete independent native layouts."""
import gzip
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'lzsa/src'))


class HybridProfileTests(unittest.TestCase):
    def test_six_fixed_profiles_match_native_proofs(self):
        from lzsa.hybrid import build
        from hashlib import sha256
        vectors=json.loads((ROOT/'evidence/wide_hybrid_experiment_selectors.json').read_text())
        mapping={'compact-base':'basic-budget-3452','balanced-base':'basic-budget-4500',
            'fast-base':'basic-budget-5500','compact':'short-budget-5000',
            'balanced':'short-budget-6500','fast':'short-budget-9500'}
        for name,key in mapping.items():
            saved=vectors['profiles'][key]
            profile=build(profile=name)
            self.assertEqual(sha256(profile[0][0][1]).hexdigest(),saved['aligned_blob_sha256'])
            self.assertEqual(profile[2]['service_memory_bytes'],saved['service_memory_bytes'])
            moved=build(profile=name,core=0x9103)
            self.assertEqual(moved[2]['service_memory_bytes']+19,saved['service_with_irq_at_9103_bytes'])
            self.assertLessEqual(moved[2]['service_memory_bytes']+19,10000)
        with self.assertRaises(ValueError):build(profile='missing')
        with self.assertRaises(ValueError):build(core_limit=0x8100)

    def test_short_options_cap_alignment_and_raw_only_contract(self):
        from lzsa.wide import build
        for shared,lengths,repeats,size in ((True,range(2,9),(),4138),
            (True,range(2,9),range(4,9),4228),(False,range(3,9),(),9524),
            (False,range(2,9),(),9748)):
            profile=build(shared_literals=shared,short_lengths=lengths,repeat_lengths=repeats)
            self.assertEqual(profile[2]['service_memory_bytes'],size)
        with self.assertRaises(ValueError):build(core=0x9003,short_lengths=range(2,9))
        for kwargs in (dict(short_lengths=(1,)),dict(short_lengths=(9,)),
                       dict(repeat_lengths=(2,)),dict(repeat_lengths=(3,)),
                       dict(short_lengths=(4,),_boundary=lambda a:None),
                       dict(short_lengths=(4,),_literal_guards=True)):
            with self.assertRaises(ValueError):build(**kwargs)

    def test_standalone_export_preserves_regions_and_contract_comments(self):
        from lzsa.hybrid import build
        from lzsa.export import export
        with tempfile.TemporaryDirectory() as temporary:
            profile=build(profile='fast');export(temporary,*profile)
            text=(Path(temporary)/'decoder.asm').read_text();restored=[]
            self.assertIn('short',text.lower())
            self.assertIn('shared',text.lower())
            for line in text.splitlines():
                if line.startswith('org '):restored.append((int(line[5:],16),bytearray()))
                elif line.startswith('db '):restored[-1][1].extend(int(v[1:],16) for v in line[3:].split(','))
            self.assertEqual([(at,bytes(blob)) for at,blob in restored],profile[0])


if __name__=='__main__':unittest.main()
