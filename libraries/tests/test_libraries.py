"""Portable imports, native relocation and extraction baseline regression checks."""
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
for package in ('zx0', 'lzsa'):
    sys.path.insert(0, str(ROOT / package / 'src'))

import zx0
import lzsa
from zx0 import bank_local, banked, split_bank2, split_streaming, streaming, streaming_inline
from zx0._z80 import MiniAssembler
from zx0.resumable import build as zx0_build
from lzsa.resumable import build as lzsa_build


def profiles():
    rows = {}
    def record(name, regions, labels):
        rows[name] = dict(regions=[dict(address=at, bytes=len(blob),
            sha256=hashlib.sha256(blob).hexdigest()) for at, blob in regions],
            labels_sha256=hashlib.sha256(json.dumps(labels,sort_keys=True).encode()).hexdigest())
    for variant in ('standard','turbo'):
        a=MiniAssembler(0x6000);zx0.emit_decoder(a,variant)
        record('zx0/'+variant,[(a.origin,a.resolve())],a.labels)
    for variant in ('fast','turbo_tuned'):
        regions,labels,_=zx0_build(variant);record('zx0/'+variant,regions,labels)
    for dynamic,inline in itertools.product((False,True),repeat=2):
        blob,labels=bank_local.build(dynamic_input=dynamic,inline_literals=inline)
        record(f'zx0/local-{dynamic}-{inline}',[(bank_local.CODE,blob)],labels)
    for fast,refill in itertools.product((False,True),repeat=2):
        for boundary in (False,True,'decrement'):
            for inline in ((False,True) if boundary is True else (False,)):
                blob,labels=banked.build(fast_literal=fast,fast_refill=refill,
                    token_boundaries=boundary,inline_matches=inline)
                record(f'zx0/ring-{fast}-{refill}-{boundary}-{inline}',[(banked.CODE,blob)],labels)
    for module in (streaming,streaming_inline):
        blob,labels=module.build()
        old_name='streaming_local_zx0' if module is streaming else 'streaming_inline_zx0'
        record('zx0/'+old_name,[(module.CODE,blob)],labels)
    for module,name in ((split_bank2,'bank2_zx0'),(split_streaming,'streaming_zx0_layout')):
        regions,labels,_=module.build();record('zx0/'+name,regions,labels)
    for supply,direct in ((False,False),(True,False),(True,True)):
        regions,labels,_=lzsa_build(streaming=supply,direct_header=direct)
        record(f'lzsa/{supply}-{direct}',regions,labels)
    return rows


class LibraryTests(unittest.TestCase):
    def test_31_pre_extraction_decoder_configurations(self):
        expected=json.loads((ROOT/'tests/decoder_baseline.json').read_text())
        self.assertEqual(profiles(),expected['profiles'])

    def test_no_converter_imports_for_independent_packages(self):
        for package in ('zx0','lzsa'):
            code=('import sys;sys.path.insert(0,'+repr(str(ROOT/package/'src'))+');'
                  f'import {package};import {package}.resumable;'
                  "assert not any(n.startswith(('toolkit','cv2','numpy')) for n in sys.modules)")
            subprocess.run([sys.executable,'-I','-c',code],check=True,capture_output=True)

    def test_host_formats_overlap_and_exact_eof(self):
        for n in (1,2,3,17,18,237,238,239,255,256,257,4096,15872):
            raw=bytes(i%251 for i in range(n))
            for package,payload in ((zx0,zx0.encode(raw,[zx0.Token(0,n)])),(lzsa,lzsa.encode(raw,[]))):
                self.assertEqual(package.decompress(payload,limit=n),raw)
                output,proof=package.trace(payload,limit=n)
                self.assertEqual(output,raw)
                self.assertEqual(package.trace(payload,limit=n,input_start=proof['minimum_input_start'],
                    bank_bytes=proof['minimum_footprint'])[0],raw)
                for broken in (payload[:-1],payload+b'!'):
                    with self.assertRaises(ValueError):package.decompress(broken,limit=n)
                with self.assertRaises(ValueError):package.decompress(payload,limit=n-1)

    def test_zx0_rewrite_and_capacity_selection(self):
        from zx0.selection import choose_cpu
        raw=b'abcabcabc!abc'
        tokens=[zx0.Token(0,3),zx0.Token(3,6,3),zx0.Token(9,1),zx0.Token(10,3,4)]
        payload=zx0.encode(raw,tokens)
        for minimum in (0,2,4,8):
            self.assertEqual(zx0.decompress(zx0.rewrite(payload,minimum)),raw)
        result=choose_cpu([[dict(name='small',bytes=5,tstates=100),dict(name='fast',bytes=8,tstates=50)]]*2,13)
        self.assertEqual((result['stream_bytes'],result['decoder_tstates']),(13,150))

    def test_exact_short_lzsa_oracle(self):
        for size in range(1,7):
            for sequence in itertools.product((0,1),repeat=size):
                raw=bytes(sequence);payload,report=lzsa.optimal(raw)
                self.assertTrue(report['exact'])
                self.assertEqual(lzsa.decompress(payload,limit=size),raw)
                self.assertLessEqual(len(payload),len(lzsa.encode(raw,[])))
        with self.assertRaises(ValueError):lzsa.optimal(bytes(257))

    def test_export_is_a_complete_commented_include(self):
        from zx0.export import export as zx_export
        from lzsa.export import export as lz_export
        for build,export in ((zx0_build,zx_export),(lzsa_build,lz_export),
                (lambda:lzsa_build(long_copy=True,core_limit=0x9000),lz_export)):
            regions,labels,metadata=build()
            with tempfile.TemporaryDirectory() as directory:
                export(directory,regions,labels,metadata)
                text=(Path(directory)/'decoder.asm').read_text()
                # Independently read ORG/DB instead of relying on the exporter
                # implementation; each emitted region must assemble exactly.
                reconstructed=[]
                for line in text.splitlines():
                    if line.startswith('org '):reconstructed.append((int(line[5:],16),bytearray()))
                    elif line.startswith('db '):
                        reconstructed[-1][1].extend(int(x[1:],16) for x in line[3:].split(','))
                self.assertEqual([(at,bytes(blob)) for at,blob in reconstructed],regions)
                self.assertIn('private',text)
                self.assertIn('slice_yield:',text)
                self.assertTrue((Path(directory)/'LICENSE').is_file())

    def test_invalid_reservations_are_rejected(self):
        for build in (zx0_build,lzsa_build):
            with self.assertRaises(ValueError):build(core=0x7000,core_limit=0x8000)
            with self.assertRaises(ValueError):build(core=-1)
            with self.assertRaises(ValueError):build(stack=65536)
        with self.assertRaises(ValueError):lzsa_build(direct_header=True)
        with self.assertRaises(ValueError):lzsa_build(long_copy=True)
        with self.assertRaises(ValueError):lzsa_build(near_literals=True)
        with self.assertRaises(ValueError):lzsa_build(word_state_init=True)
        with self.assertRaises(ValueError):lzsa_build(long_copy=True,near_literals=True,streaming=True,core_limit=0x9000)


@unittest.skipUnless(importlib.util.find_spec('z80'), 'install lzsa[native] for native tests')
class NativeTests(unittest.TestCase):
    def test_relocated_zx0_fast_and_turbo(self):
        from z80 import Z80Machine
        raw=b'AB'*1024
        payload=zx0.encode(raw,[zx0.Token(0,2),zx0.Token(2,len(raw)-2,2)])
        for variant in ('fast','turbo_tuned'):
            for layout in ({},dict(prefix=0x5000,prefix_limit=0x5400,core=0x6000,
                    core_limit=0x6400,stack=0x4ff0,output_base=0xa000)):
                regions,z,report=zx0_build(variant,**layout)
                m=Z80Machine();m.memory[:]=b'\xa5'*65536
                for at,blob in regions:m.set_memory_block(at,blob)
                source,stop,caller_stack=0x2000,0x100,0x9df0
                output=report['output_base'];m.set_memory_block(source,payload)
                def word(at,value):m.set_memory_block(at,value.to_bytes(2,'little'))
                word(z['input_pointer'],source);word(z['block_end'],output+len(raw))
                m.set_breakpoint(stop);m.set_breakpoint(z['fatal'])
                for i,target in enumerate((1,2,255,256,len(raw))):
                    word(z['slice_target'],output+target);word(caller_stack-2,stop)
                    m.pc=z['begin' if i==0 else 'slice_until'];m.sp=caller_stack-2
                    m.ticks_to_stop=2_000_000
                    while m.pc!=stop:
                        self.assertFalse(m.run()&m._TICKS_LIMIT_HIT)
                        self.assertNotEqual(m.pc,z['fatal'])
                    self.assertEqual(m.sp,caller_stack)
                    for name in ('af','bc','de','hl','alt_af','alt_bc','alt_de','alt_hl'):
                        setattr(m,name,0x9797)
                self.assertEqual(bytes(m.memory[output:output+len(raw)]),raw)

    def test_lzsa_native_offsets_lengths_and_relocation(self):
        from lzsa.native import execute
        for layout in ({},dict(prefix=0x5000,prefix_limit=0x5400,core=0x6000,
                core_limit=0x6400,stack=0x4ff0,output_base=0xa000)):
            regions,z,report=lzsa_build(**layout)
            for distance in (1,2,32,33,511,512,513,8704,8705):
                seed=bytes(i%251 for i in range(distance));raw=seed+(seed*300)[:257]
                payload=lzsa.encode(raw,[(distance,257,distance)])
                self.assertTrue(execute(regions,z,report,payload,raw,source=0x2000,
                    caller_stack=0x9df0,interrupts=True)['exact'])

    def test_distance_selection_and_short_match_budget(self):
        from lzsa.distance_cost import Costs
        from lzsa.distances import optimize
        from lzsa.budget import fit
        from lzsa.native import execute
        raw=b'AB'*12;matches=[(p,2,2) for p in range(2,len(raw),2)]
        payload=lzsa.encode(raw,matches);costs=Costs()
        for objective in ('cycles','size-no-slower-tokens'):
            candidate,report=optimize(payload,len(raw),costs,objective=objective)
            self.assertEqual(lzsa.decompress(candidate,limit=len(raw)),raw)
            self.assertLessEqual(len(candidate),len(payload))
            self.assertLessEqual(report['modeled_delta_tstates'],0)
        regions,z,native=lzsa_build();baseline=execute(regions,z,native,payload,raw)['tstates']
        result,measured,report=fit(payload,raw,100,baseline-1,costs,regions,z,native)
        self.assertTrue(report['budget_met'])
        self.assertLess(measured['tstates'],baseline)
        self.assertGreater(report['removed_matches'],0)
        self.assertEqual(lzsa.decompress(result,limit=len(raw)),raw)

    def test_streaming_guard_patcher_restores_and_bypasses(self):
        from z80 import Z80Machine
        from lzsa.streaming import emit_guard_update
        for direct,long_copy,word_init in itertools.product((False,True),repeat=3):
            regions,z,_=lzsa_build(streaming=True,direct_header=direct,long_copy=long_copy,
                                  word_state_init=word_init,core_limit=0x9000)
            a=MiniAssembler(0x6000);rows=emit_guard_update(a,z);a.emit(0xc9)
            m=Z80Machine()
            for at,data in regions:m.set_memory_block(at,data)
            m.set_memory_block(a.origin,a.resolve());m.set_breakpoint(0x100)
            for complete in (True,False,True):
                m.set_memory_block(0x9dee,b'\x00\x01');m.sp=0x9dee;m.pc=a.origin
                m.a=int(complete);m.alt_af=0x6537;m.bc=0x1234;m.de=0x2345
                m.ticks_to_stop=10000
                while m.pc!=0x100:self.assertFalse(m.run()&m._TICKS_LIMIT_HIT)
                # Shared patcher only, plus the example helper's 10-T RET.
                expected=(221 if complete else 184) if direct else (234 if complete else 197)
                self.assertEqual(10000-m.ticks_to_stop,expected)
                for name in ('header_patch','guard_literals'):
                    if name in z:self.assertEqual(m.memory[z[name]],0xc9 if complete else 0xf5)
                for operand,active,done in (
                    ('token_high_target','token_guard','token_body'),
                    ('token_low_target','token_guard','token_body'),
                    ('token_end_target','token_guard','token_body'),
                    ('long8_target','guard_long8','CopyMoreLiterals'),
                    ('long16_target','guard_long16','NextUseBC')):
                    value=m.memory[z[operand]]+256*m.memory[z[operand]+1]
                    done=z.get(operand.replace('_target','_complete'),z[done])
                    self.assertEqual(value,done if complete else z[active])
                self.assertEqual((m.alt_af,m.bc,m.de),(0x6537,0x1234,0x2345))

    def test_long_copy_length_boundaries_and_overlap(self):
        from lzsa.native import execute
        for layout in ({},dict(prefix=0x5000,prefix_limit=0x5400,core=0x6000,
                stack=0x4ff0,output_base=0xa000)):
            baseline=lzsa_build(**layout,core_limit=0x6400 if layout else 0x9000)
            candidate=lzsa_build(**layout,core_limit=0x6400 if layout else 0x9000,long_copy=True)
            for literal in (1,2,3,17,18,237,238,239,255,256,257):
                for match in (2,8,9,23,24,255,256,257):
                    raw=bytes(i%251 for i in range(literal));raw+=bytes([raw[-1]])*match
                    payload=lzsa.encode(raw,[(literal,match,1)])
                    old=execute(*baseline,payload,raw,source=0x2000,caller_stack=0x9df0)
                    new=execute(*candidate,payload,raw,source=0x2000,caller_stack=0x9df0)
                    self.assertTrue(new['exact'])
                    self.assertLessEqual(new['tstates'],old['tstates'])
            from measure_long_copy import noncanonical_cases
            for _,payload,raw in noncanonical_cases():
                self.assertEqual(lzsa.decompress(payload,limit=len(raw)),raw)
                old=execute(*baseline,payload,raw,source=0x2000,caller_stack=0x9df0)
                new=execute(*candidate,payload,raw,source=0x2000,caller_stack=0x9df0)
                self.assertEqual(new['tstates'],old['tstates'])

    def test_near_literal_helper_relocation_and_escaped_words(self):
        from lzsa.native import execute
        from measure_long_copy import noncanonical_cases
        for config in ({},dict(prefix=0x5000,prefix_limit=0x5400,core=0x6000,
                              stack=0x4ff0,output_base=0xa000)):
            old=lzsa_build(**config,long_copy=True,core_limit=0x6400 if config else 0x9000)
            new=lzsa_build(**config,long_copy=True,near_literals=True,core_limit=0x6400 if config else 0x9000)
            self.assertEqual(new[2]['code_bytes'],old[2]['code_bytes']-3)
            for length in (3,17,18,237,238,255,256,257):
                raw=bytes(index%251 for index in range(length));payload=lzsa.encode(raw,[])
                before=execute(*old,payload,raw,source=0x2000,caller_stack=0x9df0)
                after=execute(*new,payload,raw,source=0x2000,caller_stack=0x9df0,interrupts=True)
                plain=execute(*new,payload,raw,source=0x2000,caller_stack=0x9df0)
                self.assertTrue(after['exact'])
                self.assertEqual(plain['tstates']-before['tstates'],-10 if 18<=length<=255 else 0)
            for _,payload,raw in noncanonical_cases():
                before=execute(*old,payload,raw,source=0x2000,caller_stack=0x9df0)
                after=execute(*new,payload,raw,source=0x2000,caller_stack=0x9df0)
                self.assertEqual(after['tstates'],before['tstates'])

    def test_mega_relocation_long_gamma_and_dirty_offset(self):
        from measure_bit_phases import build
        from native_block import execute
        from zx0.tokens import Token,encode
        for origin in (0x8000,0x9103):
            regions,z,meta=build('mega',origin)
            self.assertEqual(len(regions[0][1]),673)
            at,blob=regions[0];blob=bytearray(blob)
            offset=z['dzx0m_last_offset+1']-at
            blob[offset:offset+2]=b'\x23\x81'
            for distance in (1,2,127,128,256):
                raw=bytes(i%251 for i in range(distance));raw+=(raw*16000)[:8192-distance]
                payload=encode(raw,[Token(0,distance),Token(distance,8192-distance,distance)])
                self.assertTrue(execute(([(at,bytes(blob))],z,meta),payload,raw,interrupts=True)['exact'])

    def test_resident_profile_contract_and_exact_word_eof(self):
        from lzsa.block import build as lblock
        from zx0.block import build as zblock
        from native_block import execute
        from measure_long_copy import noncanonical_cases
        from zx0.tokens import Token,encode
        for origin in (0x7c00,0x9103):
            for options in ({},dict(long_copy=True),dict(long_copy=True,near_literals=True)):
                profile=lblock(core=origin,core_limit=origin+512,**options)
                self.assertNotIn('state',profile[1]);self.assertNotIn('slice_until',profile[1])
                for _,payload,raw in noncanonical_cases():
                    self.assertTrue(execute(profile,payload,raw,interrupts=True)['exact'])
            for variant in ('fast','standard','turbo','mega'):
                profile=zblock(variant,core=origin,core_limit=origin+768)
                raw=b'AB'*256;payload=encode(raw,[Token(0,2),Token(2,510,2)])
                self.assertTrue(execute(profile,payload,raw,interrupts=True)['exact'])
        for build in (lblock,zblock):
            with self.assertRaises(ValueError):build(core=0xfffe,core_limit=65536)

    def test_compact_lzsa_nibble_phases_word_eof_and_dirty_state(self):
        from lzsa.block import build
        from native_block import execute
        from measure_long_copy import noncanonical_cases
        from measure_tricks import run
        for origin in (0x8000,0x9103):
            profile=build('small',core=origin,core_limit=origin+256)
            regions,z,meta=profile;self.assertEqual(meta['code_bytes'],137)
            for value in range(256):
                for cached in (False,True):
                    def prepare(m):m.alt_af=(0xf0|value)<<8|0x80 if cached else 0
                    m,t=run('cd '+z['ReadNibble'].to_bytes(2,'little').hex(' '),dict(hl=0x6000,af=0x0941),
                        memory=tuple(regions)+((0x6000,bytes([value])),),prepare=prepare)
                    self.assertEqual(t,40 if cached else 98)
                    self.assertEqual(m.c,9)
                    self.assertEqual(m.a,(value|0xf0) if cached else 0xf0|(value>>4))
                    self.assertEqual(m.hl,0x6000 if cached else 0x6001)
            at,blob=regions[0];blob=bytearray(blob)
            offset=z['offset']-at;blob[offset:offset+2]=b'\x23\x81'
            dirty=([(at,bytes(blob))],z,meta)
            for _,payload,raw in noncanonical_cases():
                self.assertTrue(execute(dirty,payload,raw,interrupts=True,alternate_af=0xf580)['exact'])
        with self.assertRaises(ValueError):build('small',long_copy=True)

    def test_word_state_init_clears_prior_stream_status(self):
        from lzsa.native import execute
        for direct in (False,True):
            regions,labels,metadata=lzsa_build(streaming=True,direct_header=direct,word_state_init=True)
            self.assertEqual(labels['finished'],labels['input_needed']+1)
            changed=[]
            for at,data in regions:
                data=bytearray(data)
                for name,value in (('finished',1),('input_needed',1),('header_frontier',255),('literal_frontier',255)):
                    if at<=labels[name]<at+len(data):data[labels[name]-at]=value
                changed.append((at,bytes(data)))
            raw=b'AB'*128;payload=lzsa.encode(raw,[(2,254,2)])
            self.assertTrue(execute(changed,labels,metadata,payload,raw,source=0x2000,interrupts=True)['exact'])

    def test_compare_restore_sync_bounds_and_combined_profiles(self):
        from z80 import Z80Machine
        from lzsa.native import execute
        for target,end in ((0,1),(1,0),(0xffff,0xffff),(0xfffe,0xffff),
                           (0x8000,0x7fff),(0xc100,0xc200),(0xc200,0xc200)):
            for optimized in (False,True):
                regions,z,meta=lzsa_build(restore_compare=optimized)
                machine=Z80Machine()
                for address,data in regions:machine.set_memory_block(address,data)
                machine.set_memory_block(z['slice_target'],target.to_bytes(2,'little'))
                machine.set_memory_block(z['block_end'],end.to_bytes(2,'little'))
                machine.set_memory_block(0x9dee,b'\x00\x01');machine.sp=0x9dee;machine.pc=z['sync']
                machine.set_breakpoint(0x100);machine.ticks_to_stop=10000
                while machine.pc!=0x100:self.assertFalse(machine.run()&machine._TICKS_LIMIT_HIT)
                wanted=0xffff if target==end else target
                self.assertEqual((machine.memory[z['high_operand']],machine.memory[z['low_operand']]),
                                 (wanted>>8,wanted&255))
                self.assertEqual(10000-machine.ticks_to_stop,(132 if target==end else 127)-(5 if optimized else 0))
        raw=b'AB'*256;payload=lzsa.encode(raw,[(2,510,2)])
        for streaming in (False,True):
            regions,z,meta=lzsa_build(core_limit=0x9000,long_copy=True,near_literals=not streaming,
                streaming=streaming,direct_header=streaming,word_state_init=streaming,restore_compare=True)
            if streaming:
                changed=[]
                for address,data in regions:
                    data=bytearray(data)
                    for name in ('header_frontier','literal_frontier'):
                        if address<=z[name]<address+len(data):data[z[name]-address]=255
                    changed.append((address,bytes(data)))
                regions=changed
            self.assertTrue(execute(regions,z,meta,payload,raw,source=0x2000,interrupts=True)['exact'])


if __name__=='__main__':unittest.main()
