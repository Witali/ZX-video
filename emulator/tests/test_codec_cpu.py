"""Native CPU layer regression and bounded old-backend equivalence runner.

Build with emulator/build_codec_cpu.ps1. Set CODEC_EMULATOR_DLL to override
the local artifact. --full-report writes all 417+56 ZX0 comparisons and
repeated real-corpus wall timings; it does not change any decoder or default.
"""
import ctypes as c
import gzip
import hashlib
import json
import os
from pathlib import Path
import statistics
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

ROOT=Path(__file__).resolve().parents[2]
DLL=Path(os.environ.get('CODEC_EMULATOR_DLL',os.environ.get('CODEC_CPU_DLL',str(ROOT/'.tmp/codec-cpu/codec_cpu.dll'))))

class Registers(c.Structure):
    _fields_=[(name,c.c_uint32) for name in
        'pc af bc de hl sp ix iy af2 bc2 de2 hl2 wz i r iff1 iff2 im halt q'.split()]

class Phase(c.Structure):
    _fields_=[(name,c.c_uint64) for name in 'cpu_tstates wait_tstates pins'.split()]+[
        (name,c.c_uint32) for name in 'step pc bc de hl sp addr wz opcode i r af'.split()]

class Guards(c.Structure):
    _fields_=[(name,c.c_uint32) for name in 'source input_bytes output output_bytes caller_stack'.split()]+[
        ('expected_output',c.POINTER(c.c_uint8))]

class Status(c.Structure):
    _fields_=[(name,c.c_uint64) for name in
        'cpu_tstates wait_tstates error error_address error_value input_cursor output_cursor stack_bytes memory_writes'.split()]

BUS=c.CFUNCTYPE(c.c_uint64,c.c_void_p,c.c_uint64,c.c_uint64)
BEFORE=c.CFUNCTYPE(c.c_uint32,c.c_void_p,c.POINTER(Phase),c.POINTER(c.c_uint64))

def load_library():
    library=c.CDLL(str(DLL))
    for name,args,result in (
        ('codec_cpu_abi_version',[],c.c_uint32),('codec_cpu_create',[],c.c_void_p),
        ('codec_cpu_destroy',[c.c_void_p],None),
        ('codec_cpu_memory',[c.c_void_p],c.POINTER(c.c_uint8)),
        ('codec_cpu_set_registers',[c.c_void_p,c.POINTER(Registers)],c.c_uint32),
        ('codec_cpu_get_registers',[c.c_void_p,c.POINTER(Registers)],None),
        ('codec_cpu_get_status',[c.c_void_p,c.POINTER(Status)],None),
        ('codec_cpu_get_phase',[c.c_void_p,c.POINTER(Phase)],None),
        ('codec_cpu_set_guards',[c.c_void_p,c.POINTER(Guards),c.POINTER(c.c_uint8)],c.c_uint32),
        ('codec_cpu_set_bus',[c.c_void_p,c.c_void_p,c.c_void_p],None),
        ('codec_cpu_set_before_t',[c.c_void_p,c.c_void_p,c.c_void_p],None),
        ('codec_cpu_set_lines',[c.c_void_p,c.c_uint64,c.c_uint64],None),
        ('codec_cpu_run_to_pc',[c.c_void_p,c.c_uint32,c.c_uint64,c.c_uint32],c.c_uint32),
        ('codec_cpu_step_instruction',[c.c_void_p,c.c_uint64,c.c_uint32],c.c_uint32),
        ('codec_cpu_fused_slices',[c.c_void_p],c.c_uint64),
        ('codec_cpu_watch_branch',[c.c_void_p,c.c_uint32,c.c_uint32],None),
        ('codec_cpu_branch_counts',[c.c_void_p,c.c_uint32,c.POINTER(c.c_uint64),c.POINTER(c.c_uint64)],None)):
        function=getattr(library,name);function.argtypes=args;function.restype=result
    assert library.codec_cpu_abi_version()==2
    return library

class CPU:
    def __init__(self):
        self.lib=load_library();self.handle=self.lib.codec_cpu_create();assert self.handle
        self.memory=self.lib.codec_cpu_memory(self.handle)
    def close(self):
        if self.handle:self.lib.codec_cpu_destroy(self.handle);self.handle=None
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
    def registers(self):
        result=Registers();self.lib.codec_cpu_get_registers(self.handle,c.byref(result));return result
    def status(self):
        result=Status();self.lib.codec_cpu_get_status(self.handle,c.byref(result));return result
    def init(self,code,entry=0x8000,**registers):
        c.memmove(c.addressof(self.memory.contents)+entry,code,len(code))
        self.memory[0xbfee]=0;self.memory[0xbfef]=1
        self.lib.codec_cpu_set_registers(self.handle,c.byref(Registers(pc=entry,af=2,sp=0xbfee,**registers)))
    def run(self,fast=True,budget=20_000_000):
        return self.lib.codec_cpu_run_to_pc(self.handle,0x100,budget,fast)

@unittest.skipUnless(DLL.is_file(),'build optional native CPU library first')
class TestCPU(unittest.TestCase):
    def test_local_generators_reproduce_included_headers(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'.tmp',prefix='cpu-regenerate-') as temporary:
            temporary=Path(temporary)
            subprocess.run([sys.executable,'-B',str(ROOT/'emulator/tools/generate_fast_decoder.py'),
                '--output',str(temporary/'fast_slices.h')],check=True,capture_output=True)
            shell=shutil.which('pwsh') or shutil.which('powershell')
            self.assertIsNotNone(shell,'PowerShell is required for Q-table regeneration')
            subprocess.run([shell,'-NoProfile','-File',str(ROOT/'emulator/tools/generate_q_table.ps1'),
                '-Output',str(temporary/'q_flags.h')],check=True,capture_output=True)
            for name in ('fast_slices.h','q_flags.h'):
                expected=(ROOT/'emulator/vendor/z80_tester'/name).read_bytes().replace(b'\r\n',b'\n')
                self.assertEqual((temporary/name).read_bytes().replace(b'\r\n',b'\n'),expected,name)
    def test_vendor_provenance_hashes(self):
        directory=ROOT/'emulator/vendor/z80_tester'
        manifest=json.loads((directory/'provenance.json').read_text())
        for name,digest in manifest['files'].items():
            self.assertEqual(hashlib.sha256((directory/name).read_bytes()).hexdigest(),digest,name)
    def test_documented_timing_and_registers_both_modes(self):
        for fast in (False,True):
            with self.subTest(fast=fast),CPU() as cpu:
                cpu.init(bytes.fromhex('3e 07 87 c9')) # LD A,7; ADD A,A; RET =21T.
                self.assertEqual(cpu.run(fast),0)
                self.assertEqual(cpu.status().cpu_tstates,21)
                self.assertEqual(cpu.registers().af>>8,14)
                self.assertEqual(cpu.registers().sp,0xbff0)
    def test_native_branch_outcomes(self):
        for value,taken in ((0,1),(1,0)):
            with CPU() as cpu:
                code=bytes((0x3e,value,0xb7,0xca,0x07,0x80,0x3c,0xc9))
                cpu.lib.codec_cpu_watch_branch(cpu.handle,0x8003,1)
                cpu.init(code);self.assertEqual(cpu.run(),0)
                no,yes=c.c_uint64(),c.c_uint64()
                cpu.lib.codec_cpu_branch_counts(cpu.handle,0x8003,c.byref(no),c.byref(yes))
                self.assertEqual((no.value,yes.value),(1-taken,taken))
                self.assertEqual(cpu.status().cpu_tstates,31+(0 if taken else 4))
    def test_setter_diagnostic_rejection_and_q_restore(self):
        with CPU() as cpu:
            self.assertEqual(cpu.lib.codec_cpu_set_registers(cpu.handle,c.byref(Registers(halt=1))),0)
            self.assertEqual(cpu.status().error,5)
            self.assertEqual(cpu.lib.codec_cpu_set_registers(cpu.handle,c.byref(Registers(pc=0x8000,q=0xa5))),1)
            self.assertEqual(cpu.registers().q,0xa5)
    def test_overflowing_guard_sizes_rejected(self):
        with CPU() as cpu:
            permissions=(c.c_uint8*65536)()
            for fields in (dict(source=0xffffffff,input_bytes=2),dict(source=1,input_bytes=0xffffffff),
                           dict(output=0xffffffff,output_bytes=2),dict(output=1,output_bytes=0xffffffff)):
                guard=Guards(caller_stack=0xbff0,**fields)
                self.assertEqual(cpu.lib.codec_cpu_set_guards(cpu.handle,c.byref(guard),permissions),0)
    def test_bad_flat_write_rejected(self):
        with CPU() as cpu:
            code=bytes.fromhex('3e 42 32 00 60 c9')
            permissions=bytearray(65536)
            permissions[0x8000:0x8000+len(code)]=b'\1'*len(code)
            permissions[0xbfb0:0xbff0]=b'\1'*64
            permissions[0x100]=1
            guard=Guards(source=0x2000,output=0xc000,caller_stack=0xbff0)
            self.assertEqual(cpu.lib.codec_cpu_set_guards(cpu.handle,c.byref(guard),
                (c.c_uint8*65536).from_buffer(permissions)),1)
            cpu.init(code);self.assertEqual(cpu.run(),2)
            self.assertEqual((cpu.status().error,cpu.status().error_address),(4,0x6000))
    def test_native_bus_clock_and_explicit_wait_accounting(self):
        with CPU() as cpu:
            times=[];previous=[0];delayed=[False]
            @BUS
            def bus(context,pins,tick):
                times.append(tick);at=pins&65535
                if pins&(1<<25):
                    if pins&(1<<27):pins=(pins&~0xff0000)|(cpu.memory[at]<<16)
                    elif pins&(1<<28) and not previous[0]&(1<<28):cpu.memory[at]=(pins>>16)&255
                previous[0]=pins;return pins
            @BEFORE
            def before(context,phase,pins):
                if not delayed[0]:delayed[0]=True;return 3
                return 0
            cpu.lib.codec_cpu_set_bus(cpu.handle,bus,None)
            cpu.lib.codec_cpu_set_before_t(cpu.handle,before,None)
            cpu.init(bytes.fromhex('3e 07 87 c9'));self.assertEqual(cpu.run(),0)
            self.assertEqual((cpu.status().cpu_tstates,cpu.status().wait_tstates),(21,3))
            self.assertEqual((min(times),max(times)),(0,24))
            guard=Guards(caller_stack=0xbff0)
            self.assertEqual(cpu.lib.codec_cpu_set_guards(cpu.handle,c.byref(guard),(c.c_uint8*65536)()),0)
    def test_im1_preserves_primary_shadow_registers(self):
        with CPU() as cpu:
            pending=[True];previous=[0];acknowledged=[]
            @BUS
            def bus(context,pins,tick):
                at=pins&65535
                if pins&(1<<25):
                    if pins&(1<<27):pins=(pins&~0xff0000)|(cpu.memory[at]<<16)
                    elif pins&(1<<28) and not previous[0]&(1<<28):cpu.memory[at]=(pins>>16)&255
                if pins&(1<<26) and pins&(1<<24):
                    pending[0]=False;acknowledged.append(tick);pins=(pins&~0xff0000)|0xff0000
                pins=(pins|(1<<30)) if pending[0] else (pins&~(1<<30))
                previous[0]=pins;return pins
            cpu.lib.codec_cpu_set_bus(cpu.handle,bus,None)
            cpu.init(bytes.fromhex('00 00 c9'))
            irq=bytes.fromhex('f5 08 f5 3e 55 ee aa f1 08 f1 fb ed 4d')
            c.memmove(c.addressof(cpu.memory.contents)+0x38,irq,len(irq))
            state=Registers(pc=0x8000,af=0x5a93,bc=0x1234,de=0x2345,hl=0x3456,sp=0xbfee,
                ix=0x4567,iy=0x5678,af2=0x6789,bc2=0x789a,de2=0x89ab,hl2=0x9abc,iff1=1,iff2=1,im=1)
            self.assertEqual(cpu.lib.codec_cpu_set_registers(cpu.handle,c.byref(state)),1)
            self.assertEqual(cpu.run(fast=True),0) # External bus forces single-T.
            result=cpu.registers()
            for name in 'af bc de hl ix iy af2 bc2 de2 hl2'.split():self.assertEqual(getattr(result,name),getattr(state,name),name)
            self.assertEqual(result.sp,0xbff0)
            self.assertTrue(acknowledged)
            self.assertEqual(cpu.status().cpu_tstates,113) # main18 + IM1ack13 + IRQ82.
    def test_repeat_xy_comes_from_ed_address_and_terminal_from_transfer(self):
        # David Banks' hardware rule: repeating LDxR sets Y=PC13,X=PC11.
        # The terminal iteration retains ordinary LDI transfer flags instead.
        for fast in (False,True):
            for pc,count,flags,ticks in ((0x826c,18,0x04,21),(0xa86c,18,0x2c,21),(0x826c,1,0x20,16)):
                with self.subTest(fast=fast,pc=pc,count=count),CPU() as cpu:
                    cpu.memory[pc]=0xed;cpu.memory[pc+1]=0xb0;cpu.memory[0x2003]=0
                    state=Registers(pc=pc,af=0x1200,bc=count,de=0xc000,hl=0x2003,sp=0xbfea)
                    self.assertEqual(cpu.lib.codec_cpu_set_registers(cpu.handle,c.byref(state)),1)
                    self.assertEqual(cpu.lib.codec_cpu_step_instruction(cpu.handle,100,fast),0)
                    result=cpu.registers()
                    self.assertEqual((result.af&255,result.bc,result.hl,result.de),(flags,count-1,0x2004,0xc001))
                    self.assertEqual(cpu.status().cpu_tstates,ticks)
                    self.assertEqual(cpu.lib.codec_cpu_fused_slices(cpu.handle)>0,fast)
    def test_scf_q_history_preserves_xy_after_non_flag_instruction(self):
        # For Q=0, SCF takes undocumented XY from old F OR A. Q=old F
        # instead takes them from A. Documented C/H/N behavior is identical.
        for q,expected in ((0,0x21),(0x20,0x01)):
            with CPU() as cpu:
                cpu.memory[0x820a]=0x37
                self.assertEqual(cpu.lib.codec_cpu_set_registers(cpu.handle,
                    c.byref(Registers(pc=0x820a,af=0x1220,q=q))),1)
                self.assertEqual(cpu.lib.codec_cpu_run_to_pc(cpu.handle,0x100,4,1),1)
                self.assertEqual(cpu.registers().af,0x1200|expected)

def full_report(output,repetitions=3):
    # Independent reference runners remain outside the shipped libraries.
    deps=Path(os.environ.get('CODEC_Z80_DEPS',str(ROOT.parents[1]/'.tmp/library-test-deps')))
    sys.path[:0]=[str(ROOT/'libraries/tests'),str(ROOT/'libraries/zx0/src'),
                 str(ROOT/'libraries/lzsa/src'),str(deps)]
    from zx0.maximum import build
    from measure_bit_phases import samples
    from measure_mega_prefix import high_word_samples
    from native_block import execute
    from z80 import Z80Machine
    from lzsa.hybrid import build as hybrid
    from measure_long_copy import samples as lzsa_samples
    from measure_full_token_dispatch import directed_tokens
    FIELDS='pc af bc de hl sp ix iy alt_af alt_bc alt_de alt_hl'.split()
    def image(profile,payload,expected,source,output,stack):
        memory=bytearray(b'\xa5'*65536);permissions=bytearray(65536)
        regions,labels,metadata=profile
        irq=bytes.fromhex('f5 08 f5 3e 55 ee aa f1 08 f1 fb ed 4d')
        allocations=[(at,at+len(blob)) for at,blob in regions]
        allocations.extend(((source,source+len(payload)),(stack-64,stack),
            (0x38,0x38+len(irq)),(0x200,0x207),(0x100,0x101)))
        if expected:allocations.append((output,output+len(expected)))
        for index,(lo,hi) in enumerate(allocations):
            assert 0<=lo<hi<=65536
            for other_lo,other_hi in allocations[index+1:]:assert hi<=other_lo or other_hi<=lo
        for at,blob in regions:
            memory[at:at+len(blob)]=blob;permissions[at:at+len(blob)]=b'\1'*len(blob)
        memory[source:source+len(payload)]=payload
        memory[stack-2:stack]=(0x100).to_bytes(2,'little')
        memory[0x38:0x38+len(irq)]=irq
        for at,n in ((stack-64,64),(0x38,len(irq)),(0x200,7),(0x100,1)):permissions[at:at+n]=b'\1'*n
        for at in metadata.get('patched_addresses',[]):permissions[at]|=2
        return memory,permissions
    def raw(profile,payload,expected,*,source=0x2000,output=0xc000,caller_stack=0xbff0):
        memory,_=image(profile,payload,expected,source,output,caller_stack)
        machine=Z80Machine();machine.memory[:]=memory
        machine.pc=profile[1][profile[2]['entry']];machine.sp=caller_stack-2
        machine.hl=source;machine.de=output
        for name,value in dict(ix=0x1357,alt_af=0,alt_bc=0x2468,alt_de=0x369a,alt_hl=0xace1).items():
            setattr(machine,name,value)
        machine.set_breakpoint(0x100);machine.ticks_to_stop=20_000_000
        while machine.pc!=0x100:
            event=machine.run();assert not event&machine._TICKS_LIMIT_HIT
        assert bytes(machine.memory[output:output+len(expected)])==expected
        return dict(tstates=20_000_000-machine.ticks_to_stop,
            registers={name:getattr(machine,name) for name in FIELDS},memory=bytes(machine.memory))
    sha=lambda data:hashlib.sha256(data).hexdigest()
    normal=build(core=0x8000,prefix_cap=228,shared_prefixes=True)
    high=build(core=0x0800,prefix_cap=228,shared_prefixes=True)
    golden={}
    proof_hashes={}
    for filename in ('shared_zero_prefix_native.json.gz','shared_zero_prefix_high_word.json.gz'):
        blob=(ROOT/'libraries/evidence'/filename).read_bytes();proof=json.loads(gzip.decompress(blob))
        proof_hashes[filename]=sha(blob)
        golden.update({row['case']:row for row in proof['profiles']['228']['blocks']})
    e00=json.loads(gzip.decompress((ROOT/'libraries/evidence/next_e00_zx0_profile.json.gz').read_bytes()))['profiles']['228']
    branch_golden={row['case']:row['branch_counts'] for row in e00['blocks']}
    sites=[row['address'] for row in e00['branches']]
    def native(profile,payload,expected,*,source=0x2000,output=0xc000,caller_stack=0xbff0,fast=True,counters=False):
        memory,permissions=image(profile,payload,expected,source,output,caller_stack)
        expected_buffer=(c.c_uint8*len(expected)).from_buffer_copy(expected)
        with CPU() as cpu:
            c.memmove(cpu.memory,(c.c_uint8*65536).from_buffer(memory),65536)
            guard=Guards(source,len(payload),output,len(expected),caller_stack,expected_buffer)
            assert cpu.lib.codec_cpu_set_guards(cpu.handle,c.byref(guard),
                (c.c_uint8*65536).from_buffer(permissions))
            registers=Registers(pc=profile[1][profile[2]['entry']],af=2,sp=caller_stack-2,
                hl=source,de=output,ix=0x1357,bc2=0x2468,de2=0x369a,hl2=0xace1)
            cpu.lib.codec_cpu_set_registers(cpu.handle,c.byref(registers))
            shift=profile[0][0][0]-0x8000
            if counters:
                for at in sites:cpu.lib.codec_cpu_watch_branch(cpu.handle,at+shift,1)
            assert cpu.run(fast)==0
            state=cpu.registers();status=cpu.status();assert not status.error and status.wait_tstates==0
            names=dict(alt_af='af2',alt_bc='bc2',alt_de='de2',alt_hl='hl2')
            result=dict(tstates=status.cpu_tstates,stack_bytes=status.stack_bytes,
                registers={name:getattr(state,names.get(name,name)) for name in FIELDS},memory=bytes(cpu.memory[:65536]))
            assert status.input_cursor==source+len(payload) and status.output_cursor==output+len(expected)
            counts={}
            if counters:
                for at in sites:
                    no,yes=c.c_uint64(),c.c_uint64()
                    cpu.lib.codec_cpu_branch_counts(cpu.handle,at+shift,c.byref(no),c.byref(yes))
                    if no.value+yes.value:counts[str(at)]=[no.value,yes.value]
                result['branch_counts']=counts
            return result
    cases=[(name,payload,expected,False) for name,payload,expected in samples()]
    cases.extend((name,payload,expected,True) for name,payload,expected in high_word_samples())
    rows=[]
    for index,(name,payload,expected,highword) in enumerate(cases):
        profile=high if highword else normal
        options=dict(source=0x0400,output=0x3000,caller_stack=0x2ff0) if highword else {}
        actual=native(profile,payload,expected,counters=True,**options)
        reference=raw(profile,payload,expected,**options)
        guarded=execute(profile,payload,expected,**options)
        assert actual['branch_counts']==branch_golden[name],(name,'branch counts')
        assert actual['tstates']==reference['tstates']==guarded['tstates']==golden[name]['candidate_tstates']
        assert actual['stack_bytes']==guarded['stack_bytes']
        assert actual['registers']==reference['registers'],(name,actual['registers'],reference['registers'])
        assert actual['memory']==reference['memory'],(name,'RAM')
        single=index<3 or name in ('literal-257','match-1','high-word-offset-1-length-49151')
        if single:
            other=native(profile,payload,expected,fast=False,counters=True,**options)
            assert other==actual,(name,'single/fused')
        rows.append(dict(case=name,input_sha256=sha(payload),output_sha256=sha(expected),
            tstates=actual['tstates'],registers=actual['registers'],memory_sha256=sha(actual['memory']),
            full_64k_memory_exact=True,stack_bytes=actual['stack_bytes'],single_tick_compared=single,
            native_branch_counts_exact=True))
        if index%50==0:print(index+1,len(cases),name,flush=True)
    for row in rows:row['codec']='zx0'
    lzsa_profile=hybrid('fast')
    selectors=json.loads((ROOT/'libraries/evidence/wide_hybrid_experiment_selectors.json').read_text())
    proof_path=ROOT/'libraries/evidence/wide_hybrid/wide_hybrid_experiment_short.json.gz'
    proof_blob=proof_path.read_bytes();proof_hashes[str(proof_path.relative_to(ROOT))]=sha(proof_blob)
    key=selectors['profiles']['short-budget-9500']['report_profile']
    lzsa_proof=json.loads(gzip.decompress(proof_blob))['profiles'][key]
    assert [dict(address=at,bytes=len(blob),sha256=sha(blob)) for at,blob in lzsa_profile[0]]==lzsa_proof['layout']['regions']
    lzsa_golden={row['case']:row for row in lzsa_proof['full_blocks']+lzsa_proof['directed_blocks']}
    lzsa_cases=list(lzsa_samples())+[(name,payload,expected) for name,payload,expected,token in directed_tokens()]
    assert len(lzsa_cases)==675
    for index,(name,payload,expected) in enumerate(lzsa_cases):
        old=lzsa_golden[name]
        assert sha(payload)==old['payload_sha256'] and sha(expected)==old['raw_sha256']
        actual=native(lzsa_profile,payload,expected)
        reference=raw(lzsa_profile,payload,expected)
        guarded=execute(lzsa_profile,payload,expected)
        assert actual['tstates']==reference['tstates']==guarded['tstates']==old['candidate_tstates'],('lzsa',name,'T')
        assert actual['stack_bytes']==guarded['stack_bytes']
        differences={field:dict(native=actual['registers'][field],reference=reference['registers'][field],
            xor=actual['registers'][field]^reference['registers'][field])
            for field in FIELDS if actual['registers'][field]!=reference['registers'][field]}
        # Deliberately record, rather than hide, every state mismatch. The
        # imported hardware-backed repeat/Q rules can differ from kosarev1.2
        # in clobbered undocumented F3/F5; no documented flag/A/preserved pair
        # may differ. This is constrained ABI equivalence, not full-state
        # equivalence for LZSA2. Full 64-KiB RAM must still match unmasked.
        assert all(field in ('af','alt_af') and value['xor']&~0x28==0
                   for field,value in differences.items()),('lzsa',name,differences)
        assert actual['memory']==reference['memory'],('lzsa',name,'RAM')
        single=index<3 or name in ('word-literal-3','word-match-2')
        if single:assert native(lzsa_profile,payload,expected,fast=False)==actual,('lzsa',name,'single/fused')
        rows.append(dict(codec='lzsa2',case=name,input_sha256=sha(payload),output_sha256=sha(expected),
            tstates=actual['tstates'],registers=actual['registers'],memory_sha256=sha(actual['memory']),
            reference_registers=reference['registers'],undocumented_flag_differences=differences,
            documented_flags_and_preserved_registers_exact=True,
            full_64k_memory_exact=True,stack_bytes=actual['stack_bytes'],single_tick_compared=single))
        if index%100==0:print('lzsa',index+1,675,name,flush=True)
    timings={};medians={};speedups={}
    zx0_real=[(name,payload,expected) for name,payload,expected,highword in cases if name.startswith('real-')]
    for codec,profile,real in (('zx0',normal,zx0_real),
            ('lzsa2',lzsa_profile,[row for row in lzsa_cases if row[0].startswith('real-')])):
        elapsed={key:[] for key in ('native_c_guards','kosarev_python_guards','kosarev_unprotected')}
        # Warm dispatch; rotate engine order in repeated end-to-end timings.
        native(profile,real[0][1],real[0][2]);execute(profile,real[0][1],real[0][2]);raw(profile,real[0][1],real[0][2])
        for iteration in range(repetitions):
            order=list(elapsed)
            order=order[iteration%3:]+order[:iteration%3]
            for key in order:
                function={'native_c_guards':native,'kosarev_python_guards':execute,'kosarev_unprotected':raw}[key]
                started=time.perf_counter()
                for name,payload,expected in real:function(profile,payload,expected)
                elapsed[key].append(time.perf_counter()-started)
            print(codec,'timing',iteration+1,{key:values[-1] for key,values in elapsed.items()},flush=True)
        timings[codec]=elapsed
        medians[codec]={key:statistics.median(values) for key,values in elapsed.items()}
        speedups[codec]=medians[codec]['kosarev_python_guards']/medians[codec]['native_c_guards']
    paths=[Path(__file__),ROOT/'emulator/src/codec_cpu.c',ROOT/'emulator/src/codec_cpu.h',
           ROOT/'emulator/build_codec_cpu.ps1',ROOT/'emulator/src/spectrum128.c',ROOT/'emulator/src/spectrum128.h',
           ROOT/'emulator/tools/generate_fast_decoder.py',ROOT/'emulator/tools/generate_q_table.ps1']
    report=dict(complete=True,release=False,cpu_layer_only=True,model='Zilog NMOS',abi_version=2,cases=len(rows),
        profiles={codec:dict(cases=sum(row['codec']==codec for row in rows),
            real_cases=sum(row['codec']==codec and row['case'].startswith('real-') for row in rows),
            cases_with_clobbered_undocumented_flag_differences=sum(row['codec']==codec and bool(row.get('undocumented_flag_differences')) for row in rows),
            real_cpu_tstates=sum(row['tstates'] for row in rows if row['codec']==codec and row['case'].startswith('real-')))
            for codec in ('zx0','lzsa2')},
        source_hashes_lf={str(path.relative_to(ROOT)).replace('\\','/'):sha(path.read_bytes().replace(b'\r\n',b'\n')) for path in paths},
        vendor=json.loads((ROOT/'emulator/vendor/z80_tester/provenance.json').read_text()),
        dll_sha256=sha(DLL.read_bytes()),native_proof_sha256=proof_hashes,
        native_build_manifest=json.loads(DLL.with_name('build.json').read_text(encoding='utf-8-sig')),
        wall_timings_seconds=timings,median_wall_seconds=medians,
        median_guarded_speedup=speedups,
        register_qualification='ZX0 all12 compared registers exact; LZSA2 documented flags/A/preserved pairs exact, '
            'with every clobbered F3/F5 difference listed; no blanket full-state equality claim',
        undocumented_flag_source=dict(url='https://raw.githubusercontent.com/wiki/hoglet67/Z80Decoder/Undocumented-Flags.md',
            repeat_xy_lines=[25,32],scf_q_lines=[52,65],
            first_repeat_vector=dict(pc=0x826c,opcode='edb0',af=0x1200,bc=18,hl=0x2003,de=0xc000,
                transferred_byte=0,native_after_f=0x04,kosarev_after_f=0x24,tstates=21),
            persistent_scf_vector=dict(pc=0x820a,opcode='37',af=0x1220,q=0,
                native_after_f=0x21,kosarev_after_f=0x01,tstates=4)),
        limitations=['No whole-decoder IRQ cross-check in this report; targeted native IM1 preservation is in unit tests',
            'Six ZX0/five LZSA2 explicit single-T/fused samples; all1148 fused',
            'No coroutine, guarded compressed-input supplier or Spectrum execution qualification',
            'Source/input/output exact guards apply only to flat bus; external bus owns banked-memory protection',
            'Spectrum contention requires verified before-T phase annotations; pins alone are insufficient'],blocks=rows)
    output.parent.mkdir(parents=True,exist_ok=True)
    raw_report=(json.dumps(report,indent=2)+'\n').encode()
    output.write_bytes(gzip.compress(raw_report,mtime=0) if output.suffix=='.gz' else raw_report)
    print(json.dumps({key:value for key,value in report.items() if key not in ('blocks','vendor','source_hashes_lf')}),flush=True)

if __name__=='__main__':
    if '--full-report' in sys.argv:
        at=sys.argv.index('--full-report');full_report(Path(sys.argv[at+1]))
    else:unittest.main()
