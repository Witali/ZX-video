"""Bounded E03: static second-table bound and two private native prototypes.

No public emitter or shared runner is changed. Failed memory/speed gates do
not trigger IRQ, relocation or in-place promotion of the private candidates.
"""
import argparse
import ast
import ctypes as C
from datetime import date
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
for path in (ROOT/'lzsa/src',ROOT/'zx0/src',ROOT/'tests',REPO):
    sys.path.insert(0,str(path))

from emulator.cpu import CPU, Guards, load_library
from measure_long_copy import samples
from measure_full_token_dispatch import directed_tokens
from lzsa import decompress
import next_e03_profiles as profiles

DLL_SHA = '21e89129d040c6c29112c8977b5cb28573ae09f75632f5b993308204a76b2db8'
DOCUMENTED_FLAGS = 0xd7
SENTINELS = dict(ix=0x1357,iy=0x57b9,bc2=0x2468,de2=0x369a,hl2=0xace1)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_gzip(name):
    with gzip.open(ROOT/'evidence'/name,'rt',encoding='utf-8') as handle:
        return json.load(handle)


def bind(library):
    library.codec_cpu_watch_branch.argtypes = [C.c_void_p,C.c_uint32,C.c_uint32]
    library.codec_cpu_watch_branch.restype = None
    library.codec_cpu_branch_counts.argtypes = [C.c_void_p,C.c_uint32,C.POINTER(C.c_uint64),C.POINTER(C.c_uint64)]
    library.codec_cpu_branch_counts.restype = None


def counts(cpu,address):
    no,yes = C.c_uint64(),C.c_uint64()
    cpu.lib.codec_cpu_branch_counts(cpu.handle,address,C.byref(no),C.byref(yes))
    return no.value,yes.value


def replay(profile,payload,expected,*,library=None,watch=(),cpu=None,load_code=True,dirty=True):
    """Native live guards, exact cursors/ABI/code; optional persistent CPU reset.

    This runner deliberately keeps disjoint input/output. It makes no IRQ or
    compressed-overlap claim. Writes to declared embedded operands count as
    code storage, and call-stack low-water is returned independently.
    """
    owned = cpu is None
    cpu = CPU(library) if owned else cpu
    regions,labels,metadata = profile
    source,output,stack,stop = 0x2000,0xc000,0xbff0,0x100
    patches = set(metadata.get('patched_addresses',()))
    permissions = bytearray(65536)
    try:
        for at,blob in regions:
            assert at+len(blob) <= stack-64
            if load_code:
                cpu.load(at,blob)
            permissions[at:at+len(blob)] = b'\1'*len(blob)
        for at in patches:
            permissions[at] |= 2
            if dirty:
                cpu.memory[at] = 0xa5
        before = [(at,bytes(cpu.memory[at:at+len(blob)])) for at,blob in regions]
        permissions[stack-64:stack] = b'\1'*64
        permissions[stop] = 1
        cpu.load(source,payload)
        cpu.load(stack-2,stop.to_bytes(2,'little'))
        raw_buffer = (C.c_uint8*max(1,len(expected)))(*expected)
        permission_buffer = (C.c_uint8*65536).from_buffer(permissions)
        guard = Guards(source,len(payload),output,len(expected),stack,raw_buffer)
        assert cpu.lib.codec_cpu_set_guards(cpu.handle,C.byref(guard),permission_buffer)
        for at in watch:
            cpu.lib.codec_cpu_watch_branch(cpu.handle,at,1)
        prior = {at:counts(cpu,at) for at in watch}
        cpu.set_registers(pc=labels[metadata['entry']],sp=stack-2,hl=source,de=output,
            af=0x5a93,bc=0xb7d9,af2=0x9797,**SENTINELS)
        status = cpu.run()
        registers = cpu.registers()
        assert status['input_cursor'] == registers['hl'] == source+len(payload)
        assert status['output_cursor'] == registers['de'] == output+len(expected)
        assert registers['sp'] == stack
        assert all(registers[k] == v for k,v in SENTINELS.items())
        assert bytes(cpu.memory[output:output+len(expected)]) == bytes(expected)
        for at,blob in before:
            assert all(cpu.memory[at+i] == byte for i,byte in enumerate(blob) if at+i not in patches)
        observed = {str(at):dict(refill=counts(cpu,at)[0]-prior[at][0],
                                cached=counts(cpu,at)[1]-prior[at][1]) for at in watch}
        return dict(tstates=status['cpu_tstates'],stack_bytes=status['stack_bytes'],
            exact=True,branch_counts=observed,
            final_phase_low=cpu.memory[labels['e03_state_operand']] if 'e03_state_operand' in labels else None,
            live_source_output_guards=True,code_protected=True,raw_abi_exact=True,
            dirty_offset_startup_tested=dirty,interrupts=False,compressed_overlap=False)
    finally:
        if owned:
            cpu.close()


def documented_flags():
    return [value for value in range(256) if value&~DOCUMENTED_FLAGS==0]


def micro_screen(library,*,values=range(256),progress=False):
    """All bytes, phases, main documented flags and relevant alternate carry.

    Main flags are overwritten by SCF/EX or by the final OR. The only input
    F' bit read by the old reader is C; the other five documented bits die
    at OR and do not affect memory or control flow. For the SMC reader even
    C is dead: both values are enumerated independently of the main flags.
    """
    result = dict(complete=True,documented_main_flags=documented_flags(),
        alternate_dead_flags_proof='Only alternate C reaches JR NC in the original. OR F0 overwrites all documented output flags. The shared phase JP reads no flags.',
        no_input_prefetch=True,outer_ret_tstates=10,kernels={})
    for kind in ('baseline','known_empty','shared_smc'):
        profile = profiles.micro(kind)
        regions,labels,metadata = profile
        expected_costs = {'baseline':{'full':27,'empty':66},'known_empty':{'empty':51},
                          'shared_smc':{'full':68,'empty':104}}[kind]
        executed = 0
        phases = ('empty',) if kind=='known_empty' else ('full','empty')
        with CPU(library) as cpu:
            permission = bytearray(65536)
            for at,blob in regions:
                cpu.load(at,blob);permission[at:at+len(blob)] = b'\1'*len(blob)
            for at in metadata['patched_addresses']:
                permission[at] |= 2
            permission[0xbfb0:0xbff0] = b'\1'*64;permission[0x100] = 1
            permission_buffer = (C.c_uint8*65536).from_buffer(permission)
            empty_buffer = (C.c_uint8*1)()
            for byte in values:
                for phase in phases:
                    for flags in documented_flags():
                        alternate_carries = (0,1) if kind=='shared_smc' else (int(phase=='empty'),)
                        for alternate_carry in alternate_carries:
                            alternate_flags = (flags&~1)|alternate_carry
                            if kind=='shared_smc':
                                cpu.memory[labels['e03_state_operand']] = labels['e03_'+phase]&255
                            cpu.memory[0x2000] = byte
                            cpu.load(0xbfee,b'\0\1')
                            ninput = int(phase=='empty')
                            guard = Guards(0x2000,ninput,0xc000,0,0xbff0,empty_buffer)
                            assert cpu.lib.codec_cpu_set_guards(cpu.handle,C.byref(guard),permission_buffer)
                            cpu.set_registers(pc=labels['entry'],sp=0xbfee,hl=0x2000,de=0xc000,
                                af=(0x5a<<8)|flags,af2=(byte<<8)|alternate_flags,
                                bc=0x1234,**SENTINELS)
                            status = cpu.run(budget=1000)
                            regs = cpu.registers()
                            nibble = byte&15 if phase=='full' else byte>>4
                            expected_flags = 0xa0|(nibble&8)|(4 if nibble.bit_count()%2==0 else 0)
                            assert regs['af'] == ((0xf0|nibble)<<8)|expected_flags,(kind,byte,phase,flags,regs)
                            assert status['cpu_tstates']-10 == expected_costs[phase]
                            assert status['input_cursor'] == regs['hl'] == 0x2000+ninput
                            assert regs['sp']==0xbff0 and regs['bc']==0x1234 and regs['de']==0xc000
                            assert all(regs[k]==v for k,v in SENTINELS.items())
                            if phase=='empty':
                                assert regs['af2']>>8 == byte
                            if kind=='shared_smc':
                                next_phase = 'empty' if phase=='full' else 'full'
                                assert cpu.memory[labels['e03_state_operand']]==labels['e03_'+next_phase]&255
                            else:
                                assert regs['af2']&1 == int(phase=='full')
                            executed += 1
                if progress and byte%64==63:
                    print('micro',kind,byte+1,executed,flush=True)
        result['kernels'][kind] = dict(executions=executed,phases=list(phases),
            bytes=len(regions[0][1]),caller_stack_bytes=4 if kind=='shared_smc' else 2,
            reader_tstates=expected_costs,all_output_flags_exact=True,alternate_byte_and_phase_exact=True)
    return result


def resident_reset_screen(library):
    """Odd/even blocks on one resident SMC reader with a real20T reset.

    Reset writes the actual phase operand; the host never restores it or A'.
    A' is asserted only while the semantic phase says a cached nibble exists.
    """
    regions,labels,metadata = profiles.micro('shared_smc')
    origin,blob = regions[0]
    reset = origin+len(blob)
    operand = labels['e03_state_operand']
    blob += bytes([0x3e,labels['e03_empty']&255,0x32,operand&255,operand>>8,0xc9])
    permission = bytearray(65536)
    permission[origin:origin+len(blob)] = b'\1'*len(blob)
    permission[operand] |= 2
    permission[0xbfb0:0xbff0] = b'\1'*64;permission[0x100]=1
    permission_buffer = (C.c_uint8*65536).from_buffer(permission)
    empty_buffer = (C.c_uint8*1)()
    records=[]
    with CPU(library) as cpu:
        cpu.load(origin,blob);cpu.memory[operand]=0xa5
        last_af2=0xd597
        for block,nibbles in enumerate((1,2,3,4,1,2,4,3)):
            raw=bytes(((block*37+0x19+i*0x73)&255) for i in range((nibbles+1)//2))
            cpu.load(0x2000,raw)
            cpu.load(0xbfee,b'\0\1')
            guard=Guards(0x2000,0,0xc000,0,0xbff0,empty_buffer)
            assert cpu.lib.codec_cpu_set_guards(cpu.handle,C.byref(guard),permission_buffer)
            cpu.set_registers(pc=reset,sp=0xbfee,hl=0x2000,de=0xc000,af2=last_af2,**SENTINELS)
            reset_result=cpu.run(budget=1000)
            assert reset_result['cpu_tstates']==30
            assert cpu.memory[operand]==labels['e03_empty']&255
            assert cpu.registers()['af2']==last_af2
            cursor=0x2000
            reads=[]
            for index in range(nibbles):
                phase='empty' if index%2==0 else 'full'
                guard=Guards(cursor,int(phase=='empty'),0xc000,0,0xbff0,empty_buffer)
                assert cpu.lib.codec_cpu_set_guards(cpu.handle,C.byref(guard),permission_buffer)
                cpu.load(0xbfee,b'\0\1')
                cpu.set_registers(pc=labels['entry'],sp=0xbfee,hl=cursor,de=0xc000,
                    af=0x5a93,af2=last_af2,bc=0x1234,**SENTINELS)
                measured=cpu.run(budget=1000);regs=cpu.registers()
                nibble=(raw[index//2]>>4) if index%2==0 else raw[index//2]&15
                assert regs['af']>>8==0xf0|nibble
                cursor+=int(phase=='empty')
                assert regs['hl']==measured['input_cursor']==cursor
                next_phase='full' if phase=='empty' else 'empty'
                assert cpu.memory[operand]==labels['e03_'+next_phase]&255
                if next_phase=='full':
                    assert regs['af2']>>8==raw[index//2]
                last_af2=regs['af2']
                reads.append(dict(index=index,nibble=nibble,reader_tstates=measured['cpu_tstates']-10,next_phase=next_phase))
            records.append(dict(block=block,raw_hex=raw.hex(),nibbles=nibbles,reset_tstates=20,
                reset_outer_ret_tstates=10,reads=reads,final_phase='full' if nibbles%2 else 'empty'))
    return dict(complete=True,same_cpu=True,host_phase_or_cache_restores_between_blocks=False,blocks=records)


def region_binding(profile):
    regions,labels,metadata = profile
    return dict(regions=[dict(address=at,bytes=len(blob),sha256=sha(blob)) for at,blob in regions],
        labels=labels,labels_sha256=sha(json.dumps(labels,sort_keys=True).encode()),metadata=metadata)


def source_provenance():
    files = ['libraries/tests/next_e03_profiles.py','libraries/tests/next_e03_measure.py',
        'libraries/tests/test_next_e03.py','libraries/lzsa/src/lzsa/wide.py',
        'libraries/lzsa/src/lzsa/hybrid.py','libraries/lzsa/src/lzsa/_wide_kernels.py',
        'emulator/cpu.py','libraries/tests/measure_long_copy.py','libraries/tests/measure_full_token_dispatch.py']
    assert all((REPO/name).is_file() for name in files),'E03 provenance source is missing'
    return {name:sha((REPO/name).read_bytes().replace(b'\r\n',b'\n')) for name in files}


def alignment_screen():
    rows = []
    for low in range(256):
        base = profiles.baseline(core=0x8000+low)
        hot = profiles.build('hot_pair',core=0x8000+low)
        shared = profiles.build('shared_smc',core=0x8000+low)
        assert hot[2]['total_storage_bytes']-base[2]['total_storage_bytes']==16
        assert hot[1]['dispatch_low'] == base[1]['dispatch_low']
        assert hot[1]['dispatch_high'] == base[1]['dispatch_high']
        assert shared[1]['e03_full']>>8 == shared[1]['e03_empty']>>8
        assert len(set(shared[2]['patched_addresses']))==3
        for design,item in [('hot_pair',hot),('shared_smc',shared)]:
            assert sum(item[2]['service_memory'].values())==item[2]['total_storage_bytes']
            assert item[2]['test_only'] and item[2]['variant']=='next-e03-'+design
        rows.append(dict(low_byte=low,baseline_service=base[2]['total_storage_bytes'],
            hot_service=hot[2]['total_storage_bytes'],shared_service=shared[2]['total_storage_bytes'],
            hot_regions=region_binding(hot)['regions'],shared_regions=region_binding(shared)['regions']))
    return rows


def phase_counts(old_row):
    observed = old_row['observers']['nibble_phases']
    total = dict(cached=0,refill=0)
    for key,value in observed.items():
        _,phase = ast.literal_eval(key)
        total[phase] += value
    return total


def hot_family_cases():
    """All match-extension exits of literal-free class5/tokenA7, both phases.

    A 9000-byte literal seed plus an initializing match sets a full/empty
    cache independently of the target. Explicit word escapes include short
    counts2/3 without relying on canonical encoding, and EOF has no suffix.
    """
    forms = [('nibble-'+str(nibble),nibble,None,None,9+nibble) for nibble in range(15)]
    forms += [('byte-'+str(extra),15,extra,None,24+extra) for extra in (0,1,230,231)]
    forms += [('word-'+str(count),15,233,count,count) for count in (2,3,8,9,23,24,255,256)]
    forms += [('eof',15,232,None,0)]
    for phase in ('empty','full'):
        for name,half_count,extra,word_count,count in forms:
            data=bytearray();pending=None
            def half(value):
                nonlocal pending
                if pending is None:
                    pending=len(data);data.append(value<<4)
                else:
                    data[pending] |= value;pending=None
            # First token has9000 literals and a2-byte match. Nibble offset3
            # consumes the second half; byte offset34 leaves the low half.
            data.append(0x18 if phase=='empty' else 0x58)
            half(15);data.append(239);data.extend((9000).to_bytes(2,'little'));data.extend(b'A'*9000)
            if phase=='empty':half(14)
            else:data.append(222)
            data.append(0xa7);half(15);data.append(255) #distance769
            half(half_count)
            if extra is not None:data.append(extra)
            if word_count is not None:data.extend(word_count.to_bytes(2,'little'))
            if count:
                data.append(0xe7);half(15);data.append(232)
            raw=b'A'*(9002+count)
            assert decompress(data,limit=len(raw))==raw
            yield 'hot-family-'+phase+'-'+name,bytes(data),raw,phase,name


def hot_family_screen(library,baseline,builds):
    rows=[]
    sites=[site+2 for site in profiles.inventory(baseline)['reader_sites']]
    first=baseline[1]['body_167_0']+2
    for name,payload,raw,phase,exit_form in hot_family_cases():
        before=replay(baseline,payload,raw,library=library,watch=sites)
        first_counts=before['branch_counts'][str(first)]
        assert first_counts==dict(cached=int(phase=='full'),refill=int(phase=='empty'))
        total={key:sum(row[key] for row in before['branch_counts'].values()) for key in ('cached','refill')}
        candidates={}
        for design,profile in builds.items():
            got=replay(profile,payload,raw,library=library)
            model=-15*int(phase=='full') if design=='hot_pair' else 41*total['cached']+38*total['refill']+12
            assert got['tstates']-before['tstates']==model,(name,design,got,before,model)
            candidates[design]=dict(**got,delta_tstates=model,model_exact=True)
        rows.append(dict(case=name,input_bytes=len(payload),output_bytes=len(raw),
            payload_sha256=sha(payload),raw_sha256=sha(raw),first_phase=phase,match_exit_form=exit_form,
            baseline=before,candidates=candidates))
    return dict(complete=True,cases=len(rows),blocks=rows,host_output_exact=True)


def run(output=None):
    library = load_library();bind(library)
    dll = Path(library._name)
    assert sha(dll.read_bytes()) == DLL_SHA,'E03 requires the exact qualified native artifact'
    launch_sources = source_provenance()
    e00 = read_gzip('next_e00_lzsa_full.json.gz')['profiles']['fast']
    e01 = read_gzip('next_e01_lzsa_full.json.gz')['profiles']['hybrid-fast']
    assert e01['complete'] and e01['accepted']
    baseline = profiles.baseline()
    assert region_binding(baseline)['regions']==e01['candidate']['regions']
    assert baseline[1]==e01['candidate']['labels']
    assert baseline[2]['total_storage_bytes']==9499
    cases = list(samples())+[row[:3] for row in directed_tokens()]
    assert len(cases)==675
    assert [row[0] for row in cases] == [row['case'] for row in e01['blocks']]
    static = {name:profiles.inventory(name) for name in ('fast','balanced','compact')}
    assert [row['count'] for row in static.values()]==[123,75,48]
    report = dict(date=date.today().isoformat(),stage='E03',complete=False,release=False,
        public_decoder_changes=False,test_only=True,baseline_service_bytes=9499,
        baseline_real_tstates=14926306,native_backend='qualified z80-tester C guarded flat',
        native_dll=dict(path=str(dll),sha256=DLL_SHA,build=json.loads(dll.with_name('build.json').read_text())),
        launch_source_sha256_lf=launch_sources,
        evidence_sha256={name:sha((ROOT/'evidence'/name).read_bytes()) for name in
            ['next_e00_lzsa_full.json.gz','next_e01_lzsa_full.json.gz']},
        static_second_table=static,static_bound_scope='Two full 256-word dispatch tables; optimistic zero-extra-dispatch lower bound. Not a proof about compressed dispatch or all possible designs.',
        micro=micro_screen(library,progress=True),resident_phase_reset=resident_reset_screen(library),alignments=alignment_screen(),
        baseline=region_binding(baseline),profiles={},attempts=[dict(
        stage='pre-run construction',result='Fixed inventory(string) adapter, dispatch label name and evidence root path before the proof run. Native emitter bytes were unchanged by these harness fixes.')])
    print('micro and256 alignments complete',flush=True)
    builds = {name:profiles.build(name) for name in ('hot_pair','shared_smc')}
    watchers = [site+2 for site in profiles.inventory(baseline)['reader_sites']]
    hot_watch = baseline[1]['body_167_0']+2
    old_hot_watch = e00['labels']['body_167_0']+2
    base_rows = []
    for index,((name,payload,raw),old0,old1) in enumerate(zip(cases,e00['blocks'],e01['blocks'])):
        assert name==old0['case']==old1['case']
        assert sha(payload)==old0['payload_sha256']==old1['payload_sha256']
        assert sha(raw)==old0['raw_sha256']==old1['raw_sha256']
        measured = replay(baseline,payload,raw,library=library,watch=watchers)
        assert measured['tstates']==old1['candidate_tstates'],(name,measured['tstates'],old1['candidate_tstates'])
        count = phase_counts(old0)
        native_total = {phase:sum(row[phase] for row in measured['branch_counts'].values()) for phase in ('cached','refill')}
        assert native_total==count,(name,native_total,count)
        hot_count = measured['branch_counts'][str(hot_watch)]
        old_hot_count = {phase:old0['observers']['nibble_phases'].get(str((old_hot_watch,phase)),0) for phase in ('cached','refill')}
        assert hot_count==old_hot_count,(name,hot_count,old_hot_count)
        base_rows.append(dict(case=name,real=name.startswith('real-'),payload_sha256=sha(payload),raw_sha256=sha(raw),
            baseline_tstates=measured['tstates'],baseline_stack_bytes=measured['stack_bytes'],
            nibble_counts=count,hot_first_counts=hot_count,independent_E00_counts_exact=True,
            independent_E01_cpu_exact=True))
        if index%100==99:
            print('baseline',index+1,flush=True)
    assert sum(row['baseline_tstates'] for row in base_rows if row['real'])==14926306
    assert {phase:sum(row['nibble_counts'][phase] for row in base_rows if row['real']) for phase in ('cached','refill')}==dict(cached=19752,refill=19760)
    assert {phase:sum(row['hot_first_counts'][phase] for row in base_rows if row['real']) for phase in ('cached','refill')}==dict(cached=514,refill=497)
    for design,profile in builds.items():
        rows = []
        for index,((name,payload,raw),base) in enumerate(zip(cases,base_rows)):
            watch = [profile[1]['e03_hot_first']+2] if design=='hot_pair' else []
            measured = replay(profile,payload,raw,library=library,watch=watch)
            model = -15*base['hot_first_counts']['cached'] if design=='hot_pair' else 41*base['nibble_counts']['cached']+38*base['nibble_counts']['refill']+12
            assert measured['tstates']-base['baseline_tstates']==model,(design,name,measured,base,model)
            if watch:
                assert measured['branch_counts'][str(watch[0])]==base['hot_first_counts']
            rows.append(dict(**base,candidate_tstates=measured['tstates'],delta_tstates=model,
                model_exact=True,native=measured))
            if index%100==99:
                print(design,index+1,flush=True)
        # The same resident image is reused without host resets of mutable
        # operands. Entry must reset the private phase jump. A new offset is
        # initialized by a new-offset token before use; literal/EOF-only
        # blocks may leave the old offset operand unchanged.
        selected = [row for row in cases if row[0] in ('single-nibble-eof-empty','single-nibble-eof-one','literal-17','literal-18','word-literal-1','word-literal-2')]
        assert len(selected)>=4
        repeated = []
        with CPU(library) as cpu:
            for iteration,(name,payload,raw) in enumerate((selected+list(reversed(selected)))*3):
                got = replay(profile,payload,raw,library=library,cpu=cpu,load_code=iteration==0,dirty=iteration==0)
                oracle = next(row for row in rows if row['case']==name)
                assert got['tstates']==oracle['candidate_tstates']
                repeated.append(dict(iteration=iteration,case=name,**got))
        real = [row for row in rows if row['real']]
        slower = [dict(case=row['case'],delta_tstates=row['delta_tstates']) for row in rows if row['delta_tstates']>0]
        summary = dict(cases=len(rows),real_cases=len(real),
            candidate_real_tstates=sum(row['candidate_tstates'] for row in real),
            real_delta_tstates=sum(row['delta_tstates'] for row in real),
            service_bytes=profile[2]['total_storage_bytes'],service_delta_bytes=profile[2]['total_storage_bytes']-9499,
            faster_cases=sum(row['delta_tstates']<0 for row in rows),equal_cases=sum(row['delta_tstates']==0 for row in rows),
            slower_cases=slower,max_regression_tstates=max([row['delta_tstates'] for row in slower] or [0]),
            stack_peak_bytes=max(row['native']['stack_bytes'] for row in rows),
            accepted=False,reason='Fails strict less-service gate' if design=='hot_pair' else 'Fails strict faster gate',
            irq='unperformed: failed strict metrics',relocation_native='unperformed: failed strict metrics',
            inplace='unperformed: failed strict metrics',alignment_emitters_verified=256)
        report['profiles'][design] = dict(**region_binding(profile),complete=True,blocks=rows,repeated_resident_calls=repeated,summary=summary)
    report['hot_family_directed']=hot_family_screen(library,baseline,builds)
    report['format_scope'] = dict(minimum_match_bytes=2,
        excluded='Word-escaped match count1 is outside the pinned LZSA2 format; host trace acceptance does not expand the valid wire contract. Literal word1/2 remain in the675 corpus.',
        specification='https://raw.githubusercontent.com/emmanuel-marty/lzsa/15ee2dfe118eeb8f7683ca44f64821c3a61ca1e5/BlockFormat_LZSA2.md')
    report['instruction_ledgers'] = dict(
        baseline=dict(cached=[['SCF',4],['EX AF,AF\'',4],['JR NC taken',12],['OR F0',7]],
            refill=[['SCF',4],['EX AF,AF\'',4],['JR NC not taken',7],['LD A,(HL)',7],['OR A',4],['EX AF,AF\'',4],['LD A,(HL)',7],['INC HL',6],['RRCA x4',16],['OR F0',7]]),
        hot_pair=dict(offset_setup_tstates=62,cached_first_old=155,cached_first_new=140,refill_first_old=155,refill_first_new=155,
            extra_bytes=dict(cloned_offset_setup_and_jump=14,cached_branch_OR=2),real_cached_first=514,real_refill_first=497),
        shared_smc=dict(call=17,state_jump=10,state_immediate_and_store=20,full_core=11,empty_core=47,ret=10,
            cached_tstates=68,refill_tstates=104,startup_old=8,startup_new=20,startup_delta_per_block=12,
            reader_sites=123,original_reader_bytes=15,call_site_bytes=3,shared_helper_bytes=28,
            helper_padding_at_8000=builds['shared_smc'][1]['e03_reader']-builds['shared_smc'][1]['e03_padding_begin'],
            startup_byte_delta=3,stack_byte_delta=2,external_scratch_bytes=0,extra_embedded_SMC_bytes=1,
            embedded_SMC_counted_in_helper=True))
    report['complete'] = True
    report['static_second_table_decision'] = 'Rejected: positive optimistic service delta for each of the three actual reader inventories'
    report['final_source_sha256_lf'] = source_provenance()
    assert report['final_source_sha256_lf']==launch_sources,'Sources changed during E03 proof'
    destination = Path(output) if output else ROOT/'evidence/next_e03_full.json.gz'
    destination.parent.mkdir(parents=True,exist_ok=True)
    if destination.is_file():
        with gzip.open(destination,'rt',encoding='utf-8') as previous_handle:
            previous=json.load(previous_handle)
        report['prior_completed_run'] = dict(complete=previous['complete'],
            superseded_report_sha256=sha(destination.read_bytes()),launch_source_sha256_lf=previous['launch_source_sha256_lf'],
            scope='Same675 cases and114688 component calls before final provenance assertions, comment corrections and supplemental56 hot-family cases',
            summaries={name:{key:value for key,value in row['summary'].items() if key!='slower_cases'} for name,row in previous['profiles'].items()})
    with gzip.GzipFile(filename=str(destination),mode='wb',mtime=0) as handle:
        handle.write((json.dumps(report,sort_keys=True,separators=(',',':'))+'\n').encode())
    concise = {key:value for key,value in report.items() if key not in ('profiles','alignments','baseline','native_dll','hot_family_directed')}
    concise['hot_family_directed'] = dict(complete=True,cases=report['hot_family_directed']['cases'],
        scope='all15 nibble lengths, byte0/1/230/231, word2/3/8/9/23/24/255/256, EOF; both starting phases')
    concise['native_dll'] = dict(path=str(dll),sha256=DLL_SHA,build_json_sha256=sha(dll.with_name('build.json').read_bytes()))
    concise['profiles'] = {name:dict(regions=row['regions'],metadata=row['metadata'],summary=row['summary']) for name,row in report['profiles'].items()}
    concise['alignment_summary'] = {name:dict(min_service=min(row[name] for row in report['alignments']),max_service=max(row[name] for row in report['alignments'])) for name in ('baseline_service','hot_service','shared_service')}
    concise['full_report'] = dict(path=str(destination.relative_to(REPO)),sha256=sha(destination.read_bytes()))
    destination.with_name('next_e03.json').write_text(json.dumps(concise,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps({name:{key:value for key,value in row['summary'].items() if key!='slower_cases'} for name,row in report['profiles'].items()},sort_keys=True),flush=True)
    return report


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output')
    args = parser.parse_args()
    run(args.output)
