"""Bounded decoder replay on the native, uncontended Spectrum128 bus.

All eight physical RAM banks are checked after execution. This is a final
memory-state gate: it does not observe transient illegal writes, unread-source
overwrites or source read order. Use the independent flat guarded and actual
in-place runners for those live-access contracts. ROM IRQ/return stubs are host
test setup, not a booted Spectrum ROM or a disk/player qualification.
"""
import argparse
import ctypes as C
import gzip
import hashlib
import json
from pathlib import Path
import sys

try:
    from .cpu import CPU, Spectrum128, load_library
except ImportError:
    from cpu import CPU, Spectrum128, load_library


ROOT = Path(__file__).resolve().parents[1]
SOURCE, OUTPUT, STACK, STOP = 0x4000, 0xc000, 0xbff0, 0x100
OUTPUT_BANKS = (0,1,3,4,6,7)
IRQ = bytes.fromhex('f5 08 f5 3e 55 ee aa f1 08 f1 fb ed 4d')
IRQ_OVERHEAD_TSTATES = 95  # IM1 acknowledge13 + handler82, no setup bootstrap.


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _layout(profile, payload, expected, output_bank):
    if type(output_bank) is not int or output_bank not in OUTPUT_BANKS:
        raise ValueError('Output bank must be0/1/3/4/6/7; bank2 aliases code/stack and bank5 aliases source')
    if not payload or len(payload) > 16384 or len(expected) > 16383:
        raise ValueError('Source must fit4000h..7FFFh and output must not wrapFFFFh')
    regions, labels, metadata = profile
    allocations = []
    for origin, blob in regions:
        if not 0x8000 <= origin < origin+len(blob) <= STACK-64:
            raise ValueError('All code/table regions must fit fixed RAM2 below the64-byte caller/IRQ test window')
        for lo, hi in allocations:
            if not (origin+len(blob) <= lo or hi <= origin):
                raise ValueError('Code/table regions overlap')
        allocations.append((origin, origin+len(blob)))
    if not any(lo <= labels[metadata['entry']] < hi for lo, hi in allocations):
        raise ValueError('Entry is outside emitted code')
    patches = sorted(set(metadata.get('patched_addresses', ())))
    if len(patches) not in (0,2) or any(not any(lo <= at < hi for lo,hi in allocations) for at in patches):
        raise ValueError('Only a declared two-byte embedded offset may be mutable')
    return regions, labels, metadata, patches


def _copy_bank(bus, bank):
    # Bulk native copies are setup/verification calls, never per-byte CPU callbacks.
    function = bus.lib.spectrum128_copy_ram
    function.argtypes = [C.c_void_p,C.c_uint32,C.c_uint32,C.c_void_p,C.c_uint32]
    function.restype = C.c_int
    data = (C.c_uint8*16384)()
    if not function(bus.handle,bank,0,data,16384):
        raise AssertionError('Cannot copy physical RAM bank')
    return bytes(data)


def _protected_spans(allowed):
    merged = []
    for lo,hi in sorted(allowed):
        if lo == hi:
            continue
        if merged and lo <= merged[-1][1]:
            merged[-1] = (merged[-1][0],max(hi,merged[-1][1]))
        else:
            merged.append((lo,hi))
    cursor = 0
    for lo,hi in merged:
        if cursor < lo:
            yield cursor,lo
        cursor = hi
    if cursor < 16384:
        yield cursor,16384


def execute(profile, payload, expected, *, codec, library=None, output_bank=0,
            interrupts=False, frame_phase=0, budget=20_000_000):
    """Replay one normal block; code8000/source4000/outputC000/stackBFF0.

    Output bank2/5 is rejected before any setup because logical separation
    would hide physical aliases of code/stack or compressed source. All other
    banks share the same uncontended benchmark CPU timing. Frame IRQs follow
    the36T ULA pulse, and the native ROM stub preserves both AF banks.
    """
    if codec not in ('zx0','lzsa2'):
        raise ValueError('codec must be zx0 or lzsa2')
    if type(frame_phase) is not int or not 0 <= frame_phase < 70908:
        raise ValueError('Frame phase must be0..70907')
    payload, expected = bytes(payload), bytes(expected)
    regions, labels, metadata, patches = _layout(profile,payload,expected,output_bank)
    library = library if library is not None else load_library()
    preserved = dict(ix=0x1357,iy=0x57b9,bc2=0x2468,de2=0x369a,hl2=0xace1)
    if codec == 'zx0':
        preserved['af2'] = 0x9797
    allowed = {bank:[] for bank in range(8)}
    allowed[output_bank].append((0,len(expected)))
    allowed[2].append(((STACK-64)&16383,STACK&16383))
    allowed[2].extend((at&16383,(at&16383)+1) for at in patches)
    with CPU(library) as cpu, Spectrum128(library=library,contention=False) as bus:
        dirty = C.create_string_buffer(b'\xa5'*16384)
        for bank in range(8):
            assert library.spectrum128_load_ram(bus.handle,bank,0,dirty,16384)
        assert bus.out(0x7ffd,output_bank)
        for at,blob in regions:
            bus.load(at,blob)
        for at in patches:
            bus.load(at,b'\xa5')
        bus.load(SOURCE,payload)
        bus.load(STACK-2,STOP.to_bytes(2,'little'))
        bus.load_rom(0,IRQ,offset=0x38)
        bus.load_rom(0,b'\0',offset=STOP)
        bus.set_phase(frame_phase)
        initial = [_copy_bank(bus,bank) for bank in range(8)]
        bus.attach(cpu)
        cpu.set_registers(pc=labels[metadata['entry']],hl=SOURCE,de=OUTPUT,sp=STACK-2,
            af=0x5a93,bc=0xb7d9,af2=0x9797,im=int(bool(interrupts)),
            iff1=int(bool(interrupts)),iff2=int(bool(interrupts)),
            ix=0x1357,iy=0x57b9,bc2=0x2468,de2=0x369a,hl2=0xace1)
        status = cpu.run(stop=STOP,budget=budget,fast=False)
        registers, state = cpu.registers(), bus.state()
        final = [_copy_bank(bus,bank) for bank in range(8)]
        assert registers['hl'] == SOURCE+len(payload) and registers['de'] == OUTPUT+len(expected), 'return cursors differ'
        assert registers['sp'] == STACK and registers['pc'] == STOP, 'caller return differs'
        assert registers['iff1'] == registers['iff2'] == int(bool(interrupts)), 'interrupt-enable state changed'
        for name,value in preserved.items():
            assert registers[name] == value, ('preserved register changed',name,registers[name])
        assert final[output_bank][:len(expected)] == expected, 'output differs'
        assert final[5] == initial[5], 'compressed-source physical bank changed'
        protected = []
        for bank in range(8):
            spans = list(_protected_spans(allowed[bank]))
            for lo,hi in spans:
                if final[bank][lo:hi] != initial[bank][lo:hi]:
                    at = next(i for i in range(lo,hi) if final[bank][i] != initial[bank][i])
                    raise AssertionError(('protected physical RAM changed',bank,hex(at),initial[bank][at],final[bank][at]))
            protected.append(dict(bank=bank,initial_sha256=sha(initial[bank]),final_sha256=sha(final[bank]),
                protected_spans_sha256=sha(b''.join(final[bank][lo:hi] for lo,hi in spans)),
                protected_bytes=sum(hi-lo for lo,hi in spans),allowed_changed_ranges=allowed[bank]))
        assert state['memory_writes'] >= len(expected), 'too few memory writes for output'
        assert state['cpu_tstates'] == status['cpu_tstates'] and state['ula_wait_tstates'] == status['wait_tstates'] == 0
        assert state['master_tstates'] == frame_phase+status['cpu_tstates']
        assert (state['frame_tstate'],state['frame_number']) == (state['master_tstates']%70908,state['master_tstates']//70908)
        assert state['paging_latch'] == output_bank and state['paging_writes'] == 1 and not state['paging_locked']
        assert state['screen_bank'] == 5 and state['rom_bank'] == 0
        assert not any(state[name] for name in ('ignored_rom_writes','ignored_paging_writes',
            'unmodeled_port_reads','unmodeled_port_writes')), ('unexpected ROM/port activity',state)
        if not interrupts:
            assert state['irq_acknowledgements'] == 0
        return dict(tstates=status['cpu_tstates'],ula_wait_tstates=0,exact=True,codec=codec,
            output_bank=output_bank,frame_phase=frame_phase,interrupts=bool(interrupts),
            irq_acknowledgements=state['irq_acknowledgements'],registers=registers,bus_state=state,
            final_physical_banks=protected,payload_sha256=sha(payload),raw_sha256=sha(expected),
            input_bytes=len(payload),output_history_bytes=len(expected),
            dirty_offset_startup_tested=True,final_memory_verified=True,
            live_source_order_guard=False,live_write_guard=False,compressed_overlap=False,
            contention=False,rom_booted=False,irq_stub_bytes=len(IRQ),irq_overhead_tstates=IRQ_OVERHEAD_TSTATES)


def baseline(report_path, *, library=None):
    """All417+675 normal cases; IRQ representatives across all six safe banks."""
    sys.path[:0] = [str(ROOT/'libraries/tests'),str(ROOT/'libraries/zx0/src'),str(ROOT/'libraries/lzsa/src')]
    from measure_bit_phases import samples as zx_samples
    from measure_long_copy import samples as lz_samples
    from measure_full_token_dispatch import directed_tokens
    from native_block import execute as original
    from zx0.maximum import build as zx_build
    from lzsa.hybrid import build as lz_build
    library = library if library is not None else load_library()
    profiles = dict(zx0=zx_build(prefix_cap=228,shared_prefixes=True),lzsa2=lz_build(profile='fast'))
    cases = [('zx0',row) for row in zx_samples()]
    cases += [('lzsa2',row) for row in lz_samples()]
    cases += [('lzsa2',row[:3]) for row in directed_tokens()]
    report = dict(date='2026-10-20',complete=False,release=False,contention=False,
        scope='Native Spectrum128 normal-corpus bus replay; final all-bank state/cursors/registers; no live source-read/write observer and no boot/player/AY/disk qualification.',
        source=SOURCE,output=OUTPUT,caller_stack=STACK,output_banks=list(OUTPUT_BANKS),
        source_sha256_lf={str(path.relative_to(ROOT)).replace('\\','/'):sha(path.read_text(encoding='utf-8').encode())
            for path in (Path(__file__),ROOT/'emulator/tests/test_spectrum_decoders.py',ROOT/'emulator/cpu.py',
                ROOT/'emulator/src/spectrum128.c',ROOT/'emulator/src/spectrum128.h',
                ROOT/'emulator/src/codec_cpu.c',ROOT/'emulator/src/codec_cpu.h',ROOT/'libraries/tests/native_block.py',
                ROOT/'libraries/zx0/src/zx0/maximum.py',ROOT/'libraries/lzsa/src/lzsa/hybrid.py',
                ROOT/'libraries/lzsa/src/lzsa/wide.py',ROOT/'libraries/lzsa/src/lzsa/_wide_kernels.py')},
        native_library=dict(path=library._name,sha256=sha(Path(library._name).read_bytes()),cpu_abi=library.codec_cpu_abi_version(),spectrum_abi=library.spectrum128_abi_version()),
        profiles={codec:dict(metadata=p[2],regions=[dict(address=at,bytes=len(blob),sha256=sha(blob)) for at,blob in p[0]]) for codec,p in profiles.items()},
        blocks=[],irq_probes=[])
    report_path = Path(report_path)
    def save():
        report_path.parent.mkdir(parents=True,exist_ok=True)
        with gzip.open(report_path,'wt',encoding='utf-8',newline='\n') as stream:
            json.dump(report,stream,sort_keys=True)
            stream.write('\n')
    try:
        for index,(codec,(name,payload,raw)) in enumerate(cases):
            result = execute(profiles[codec],payload,raw,codec=codec,library=library)
            before = original(profiles[codec],payload,raw,source=SOURCE)
            assert before['tstates'] == result['tstates'], ('original CPU differs',codec,name,before['tstates'],result['tstates'])
            result.update(case=name,original_tstates=before['tstates'],original_stack_bytes=before['stack_bytes'])
            report['blocks'].append(result)
            if (index+1)%50 == 0:
                save()
                print(json.dumps(dict(completed=index+1,total=len(cases),codec=codec,case=name)),flush=True)
        # Include complete real blocks, literal-only length1/large and long
        # distance-one history; the latter is not compressed-source overlap.
        representatives = []
        for codec in profiles:
            group = [(c,row) for c,row in cases if c==codec]
            wanted = {'real-1-0','real-0','literal-1','literal-15872',
                      'match-1','distance-1','single-nibble-eof-empty','single-nibble-eof-one'}
            representatives += [(c,row) for c,row in group if row[0] in wanted]
        for codec,(name,payload,raw) in representatives:
            before = next(row for row in report['blocks'] if row['codec']==codec and row['case']==name)
            for bank in OUTPUT_BANKS:
                for phase in (0,35,36,14361,70907):
                    result = execute(profiles[codec],payload,raw,codec=codec,library=library,
                        output_bank=bank,interrupts=True,frame_phase=phase)
                    assert result['tstates'] == before['tstates']+IRQ_OVERHEAD_TSTATES*result['irq_acknowledgements'], (
                        'IRQ overhead differs',codec,name,bank,phase,result['tstates'],result['irq_acknowledgements'])
                    result.update(case=name,plain_tstates=before['tstates'],irq_cpu_formula_exact=True)
                    report['irq_probes'].append(result)
        report['summary'] = {}
        for codec in profiles:
            rows = [row for row in report['blocks'] if row['codec']==codec]
            probes = [row for row in report['irq_probes'] if row['codec']==codec]
            report['summary'][codec] = dict(cases=len(rows),real_blocks=sum(r['case'].startswith('real-') for r in rows),
                real_tstates=sum(r['tstates'] for r in rows if r['case'].startswith('real-')),
                original_cpu_exact_cases=len(rows),final_all_banks_exact_cases=len(rows),
                irq_probes=len(probes),irq_acknowledgements=sum(r['irq_acknowledgements'] for r in probes),
                irq_cpu_formula_exact=all(r['irq_cpu_formula_exact'] for r in probes))
        report['complete'] = True
    except BaseException as error:
        report['failure'] = dict(codec=codec,case=name,error=repr(error))
        raise
    finally:
        save()
    print(json.dumps(report['summary']),flush=True)
    return report


def revalidate(report_path, *, library=None):
    """Recheck saved native results on a final build without rerunning the oracle.

    The old report retains its DLL and launch-file snapshots. New per-case
    native machine results must exactly equal the saved results, including all
    register/bank hashes, bus counters, IRQ counts and CPU values. This does not
    retroactively attribute an earlier execution to changed source files.
    """
    report_path = Path(report_path)
    packed = report_path.read_bytes()
    report = json.loads(gzip.decompress(packed))
    assert report['complete'] and 'failure' not in report
    sys.path[:0] = [str(ROOT/'libraries/tests'),str(ROOT/'libraries/zx0/src'),str(ROOT/'libraries/lzsa/src')]
    from measure_bit_phases import samples as zx_samples
    from measure_long_copy import samples as lz_samples
    from measure_full_token_dispatch import directed_tokens
    from zx0.maximum import build as zx_build
    from lzsa.hybrid import build as lz_build
    library = library if library is not None else load_library()
    profiles = dict(zx0=zx_build(prefix_cap=228,shared_prefixes=True),lzsa2=lz_build(profile='fast'))
    cases = {('zx0',name):(payload,raw) for name,payload,raw in zx_samples()}
    cases.update({('lzsa2',name):(payload,raw) for name,payload,raw in lz_samples()})
    cases.update({('lzsa2',name):(payload,raw) for name,payload,raw,_ in directed_tokens()})
    assert set(cases) == {(row['codec'],row['case']) for row in report['blocks']}
    digest = hashlib.sha256()
    count = 0
    for mode in ('blocks','irq_probes'):
        for old in report[mode]:
            codec,name = old['codec'],old['case']
            payload,raw = cases[codec,name]
            current = execute(profiles[codec],payload,raw,codec=codec,library=library,
                output_bank=old['output_bank'],interrupts=old['interrupts'],frame_phase=old['frame_phase'])
            saved = {key:value for key,value in old.items() if key not in (
                'case','original_tstates','original_stack_bytes','plain_tstates','irq_cpu_formula_exact')}
            serialized = json.dumps(current,sort_keys=True)
            assert serialized == json.dumps(saved,sort_keys=True), ('final native build differs',mode,codec,name)
            digest.update(serialized.encode())
            count += 1
    paths = list(report['source_sha256_lf']) + [
        'emulator/vendor/z80_tester/z80.h','emulator/vendor/z80_tester/fast_slices.h',
        'emulator/vendor/z80_tester/q_flags.h','emulator/tests/test_spectrum128.py']
    current_sources = {path:sha((ROOT/path).read_text(encoding='utf-8').encode()) for path in paths}
    manifest = Path(library._name).parent/'build.json'
    build = json.loads(manifest.read_text(encoding='utf-8-sig')) if manifest.exists() else None
    if build is not None:
        assert build['dll_sha256'] == sha(Path(library._name).read_bytes()), 'build manifest DLL differs'
        for path,value in build['source_sha256_lf'].items():
            if Path(path).suffix in ('.c','.h'):
                assert sha((ROOT/path).read_text(encoding='utf-8').encode()) == value, ('compiled source changed',path)
    report['final_build_revalidation'] = dict(complete=True,
        previous_report_archive_sha256=sha(packed),
        native_library=dict(path=library._name,sha256=sha(Path(library._name).read_bytes()),
            cpu_abi=library.codec_cpu_abi_version(),spectrum_abi=library.spectrum128_abi_version()),
        source_sha256_lf=current_sources,
        changed_since_launch_source_paths=[path for path,old in report['source_sha256_lf'].items()
                                           if current_sources[path] != old],
        manifest_path=str(manifest) if manifest.exists() else None,
        manifest_sha256=sha(manifest.read_bytes()) if manifest.exists() else None,
        compiled_source_sha256_lf=build['source_sha256_lf'] if build else None,
        compiled_c_and_headers_current=build is not None,
        normal_cases=len(report['blocks']),irq_probes=len(report['irq_probes']),
        exact_machine_result_cases=count,machine_results_sha256=digest.hexdigest(),
        scope='All final native per-case results equal the saved originals, including every final physical bank hash, register, bus counter and CPU/IRQ count; original-backend CPU oracle reused without another Python replay. Launch source snapshots identify files at report creation; executed DLL identity is authoritative.')
    with gzip.open(report_path,'wt',encoding='utf-8',newline='\n') as stream:
        json.dump(report,stream,sort_keys=True)
        stream.write('\n')
    print(json.dumps(report['final_build_revalidation']),flush=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--revalidate',action='store_true',help='recheck saved native results on the selected final artifact')
    args = parser.parse_args()
    (revalidate if args.revalidate else baseline)(args.report)
