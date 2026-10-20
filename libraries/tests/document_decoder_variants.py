"""Rebuild the linked decoder table from retained CPU evidence and public APIs.

This validates documented calls/exports and saved evidence; it does not rerun
native benchmarks or change any decoder/default. Run from the repository root.
"""
from datetime import date
from decimal import Decimal
import gzip
import hashlib
import importlib
import inspect
import json
from pathlib import Path
import re
import sys
import tempfile


ROOT=Path(__file__).resolve().parents[2]
LIB=ROOT/'libraries'
for package in ('zx0','lzsa'):
    sys.path.insert(0,str(LIB/package/'src'))

LAYOUTS=dict(
    SMALL=dict(core=0x8000,core_limit=0x8400),
    WIDE=dict(core=0x8000,core_limit=0xb000),
    GUARDED=dict(core=0xa000,core_limit=0xbc00,prefix=0x7000,
                 prefix_limit=0x7400,stack=0x7be0,output_base=0xc000))


def sha(blob):return hashlib.sha256(blob).hexdigest()


def main():
    used={}
    def read(relative):
        path=LIB/relative;blob=path.read_bytes();used[relative]=sha(blob)
        return json.loads(gzip.decompress(blob) if relative.endswith('.gz') else blob)
    integrated=read('evidence/frontier_completed_profiles_verification.json')
    existing=integrated['profiles']
    old_zx=read('evidence/trick_23.json')
    old_lz=read('evidence/trick_29.json')
    jumps=read('evidence/fast_jumps.json')
    compact=read('evidence/compact_frontier.json')
    guarded=read('evidence/wide_guarded_native.json.gz')
    jump_auth=read('evidence/fast_jumps_verification.json')
    second=read('second_pass_verification.json')
    shared_zx0=read('evidence/shared_zero_prefix_native.json.gz')
    originals={
        ('zx0','block'):old_zx['summary']['fast']['real_tstates'],
        ('zx0','coroutine'):compact['profiles']['zx0-coroutine']['summary']['real_baseline_tstates'],
        ('lzsa2','block'):jumps['profiles']['lzsa-block']['summary']['real_baseline_tstates'],
        ('lzsa2','coroutine'):jumps['profiles']['lzsa-coroutine']['summary']['real_baseline_tstates']}
    baselines=dict(originals)
    for kind,key in (('block','lzsa-block'),('coroutine','lzsa-coroutine')):
        baselines['lzsa2',kind]=jumps['profiles'][key]['summary']['real_candidate_tstates']

    # Bind the older guarded recordings to the same 63-block producer replay,
    # rather than deriving original costs from an ordinary/raw decoder total.
    manifest={item['file']:item for item in jump_auth['archives']}
    for mode in ('call','direct'):
        reference=guarded['profiles']['wide-'+mode]['reference_producer_blocks']
        for phase in ('before','after'):
            relative=f'evidence/fast_jumps_streaming/fast-jumps-{mode}-{phase}.json.gz'
            item=manifest[relative];blob=(LIB/relative).read_bytes()
            assert sha(blob)==item['sha256'] and sha(gzip.decompress(blob))==item['decoded_sha256']
            report=read(relative)
            assert report['complete'] and report['stream_sha256']==guarded['retained_stream_sha256']
            assert len(report['blocks'])==len(reference)==63
            total=0
            for previous,row in zip(report['blocks'],reference):
                for key in ('raw_sha256','payload_sha256','producer_tstates'):
                    assert previous[key]==row['baseline'][key]
                if row['case'].startswith('real-'):total+=previous['decoder_tstates']
            if phase=='before':originals['lzsa2','guarded-'+mode]=total
            else:
                baselines['lzsa2','guarded-'+mode]=total
                assert total==guarded['profiles']['wide-'+mode]['summary']['real_decoder_baseline_tstates']

    def regions(profile):
        return [dict(address=at,bytes=len(blob),sha256=sha(blob)) for at,blob in profile[0]]
    records=[];sources={}
    def add(name,codec,kind,module,options,*,layout=None,catalog=None,cpu=None,stack=None,frozen=None):
        builder=importlib.import_module(module).build
        kwargs=dict(LAYOUTS.get(layout,{}),**options)
        profile=builder(**kwargs);code=sum(len(blob) for _,blob in profile[0])
        full=None
        if catalog:
            saved=existing[catalog]
            assert regions(profile)==saved['emitted_regions'],name
            cpu=saved['real_candidate_tstates']
            if kind.startswith('guarded-'):
                service=saved['library_consumer_service_bytes']
                full=saved['full_reference_service_with_workspace_and_irq_bytes']
                assert service==code+28
            else:
                service=saved['library_service_bytes']
                assert service==code+saved['caller_stack_bytes']+saved['private_stack_bytes']
        else:
            service=code+stack
            if isinstance(frozen,str):assert sha(profile[0][0][1])==frozen,name
            elif frozen is not None:
                expected=[{k:r[k] for k in ('address','bytes','sha256')} for r in frozen['regions']]
                assert regions(profile)==expected,name
        path=Path(inspect.getsourcefile(builder));line=inspect.getsourcelines(builder)[1]
        relative=path.relative_to(LIB).as_posix()
        sources[relative]=sha(path.read_bytes().replace(b'\r\n',b'\n'))
        # Source labels link to the actual function, with copyable arguments.
        parts=['**'+layout] if layout else []
        parts += [key+'='+repr(value) for key,value in options.items()]
        call=module+'.build('+', '.join(parts)+')'
        delta=lambda reference:100*(Decimal(cpu)/Decimal(reference)-1)
        records.append(dict(name=name,codec=codec,kind=kind,builder=module+'.build',kwargs=kwargs,
            display_call=call,source_file=relative,source_line=line,code_state_table_padding_bytes=code,
            service_bytes=service,full_reference_service_bytes=full,real_cpu_tstates=cpu,
            pass_baseline_cpu_tstates=baselines[codec,kind],original_fast_cpu_tstates=originals[codec,kind],
            delta_time_vs_pass_percent=str(delta(baselines[codec,kind])),
            delta_time_vs_original_percent=str(delta(originals[codec,kind])),regions=regions(profile)))
        return profile

    for variant,label,stack in (('standard','Standard (minimum)',6),('turbo','Turbo',4),
                                ('fast','Fast (original and pass baseline)',4),('mega','Mega (original)',4)):
        add('ZX0 '+label,'zx0','block','zx0.block',dict(variant=variant),layout='SMALL',
            cpu=old_zx['summary'][variant]['real_tstates'],stack=stack,
            frozen=old_zx['profiles'][variant]['code_sha256'])
    add('ZX0 Fast tuned','zx0','block','zx0.block',dict(branch_tuned=True),layout='SMALL',catalog='zx0-small-fast')
    add('ZX0 Fast tuned +prefix +tail','zx0','block','zx0.block',
        dict(branch_tuned=True,literal_prefix=True,inline_tail_refill=True),layout='SMALL',catalog='zx0-compact-block')
    add('ZX0 Mega tuned','zx0','block','zx0.block',dict(variant='mega',mega_tuned=True,fast_jumps=True),
        layout='SMALL',catalog='zx0-tuned-mega')
    for cap in (31,63,127,227,228):
        add('ZX0 Maximum '+str(cap),'zx0','block','zx0.maximum',dict(prefix_cap=cap),catalog='zx0-maximum-'+str(cap))
    for cap in (31,63,127,227,228):
        saved=shared_zx0['profiles'][str(cap)]
        add('ZX0 Maximum shared '+str(cap),'zx0','block','zx0.maximum',
            dict(prefix_cap=cap,shared_prefixes=True),cpu=saved['summary']['real_candidate_tstates'],
            stack=4,frozen=saved)
    for fast,label,key in ((False,'original','baseline'),(True,'pass baseline','candidate')):
        add('LZSA2 Fast ('+label+')','lzsa2','block','lzsa.block',dict(fast_jumps=fast),layout='SMALL',
            cpu=originals['lzsa2','block'] if not fast else baselines['lzsa2','block'],stack=4,
            frozen=jumps['profiles']['lzsa-block'][key])
    small=add('LZSA2 Small (minimum)','lzsa2','block','lzsa.block',dict(variant='small'),layout='SMALL',
              cpu=old_lz['summary']['real_candidate_tstates'],stack=old_lz['summary']['stack_bytes'])
    assert small[2]==old_lz['candidate_metadata']
    assert sources['lzsa/src/lzsa/block.py']==integrated['source_sha256_lf']['libraries/lzsa/src/lzsa/block.py']
    compact_source=LIB/'lzsa/src/lzsa/compact.py'
    assert sha(compact_source.read_bytes().replace(b'\r\n',b'\n'))==second['source_sha256_lf']['lzsa\\src\\lzsa\\compact.py']
    add('LZSA2 Fast compact branches','lzsa2','block','lzsa.block',dict(fast_jumps=True,compact_branches=True),
        layout='SMALL',catalog='lzsa-small-fast')
    add('LZSA2 Fast tuned +prefill','lzsa2','block','lzsa.block',dict(fast_jumps=True,branch_tuned=True,nibble_prefill=True),
        layout='SMALL',catalog='lzsa-compact-block')
    for variant in ('wide-shared','wide'):
        add('LZSA2 '+('Wide shared' if variant=='wide-shared' else 'Wide expanded'),'lzsa2','block',
            'lzsa.block',dict(variant=variant),layout='WIDE',catalog='lzsa-'+variant+'-block')

    add('ZX0 Fast (original and pass baseline)','zx0','coroutine','zx0.resumable',{},layout='SMALL',
        cpu=originals['zx0','coroutine'],stack=16,frozen=compact['profiles']['zx0-coroutine']['baseline'])
    add('ZX0 tuned +tail','zx0','coroutine','zx0.resumable',dict(branch_tuned=True,inline_tail_refill=True),
        layout='SMALL',catalog='zx0-compact-coroutine-smaller')
    add('ZX0 tuned +prefix +tail','zx0','coroutine','zx0.resumable',
        dict(branch_tuned=True,literal_prefix=True,inline_tail_refill=True),layout='SMALL',catalog='zx0-compact-coroutine')
    for cap in (31,63,127):
        add('ZX0 Maximum coroutine '+str(cap),'zx0','coroutine','zx0.maximum_coroutine',dict(prefix_cap=cap),
            catalog='zx0-maximum-coroutine-'+str(cap))
    for fast,label,key in ((False,'original','baseline'),(True,'pass baseline','candidate')):
        add('LZSA2 Fast ('+label+')','lzsa2','coroutine','lzsa.resumable',dict(fast_jumps=fast),layout='SMALL',
            cpu=originals['lzsa2','coroutine'] if not fast else baselines['lzsa2','coroutine'],stack=18,
            frozen=jumps['profiles']['lzsa-coroutine'][key])
    for policy,key in (('compact_branches','compact_branches'),('branch_tuned','branch_tuned')):
        add('LZSA2 Fast '+policy+' +prefill +sync','lzsa2','coroutine','lzsa.resumable',
            dict(fast_jumps=True,nibble_prefill=True,compact_sync=True,**{policy:True}),layout='SMALL',
            catalog='lzsa-'+key+'-coroutine')
    for shared in (True,False):
        key='wide-shared-coroutine' if shared else 'wide-coroutine'
        add('LZSA2 Wide '+('shared' if shared else 'expanded'),'lzsa2','coroutine','lzsa.wide_coroutine',
            dict(shared_literals=shared),layout='WIDE',catalog='lzsa-'+key)
    for shared in (False,True):
        for direct in (False,True):
            mode='direct' if direct else 'call';key=('wide-shared-' if shared else 'wide-')+mode
            add('LZSA2 Wide '+('shared ' if shared else 'expanded ')+mode,'lzsa2','guarded-'+mode,
                'lzsa.wide_coroutine',dict(streaming=True,direct_header=direct,shared_literals=shared),
                layout='GUARDED',catalog='lzsa-'+key+'-guarded')

    # Check that every documented call produces a usable standalone include.
    # This is export validation, not a new timing/correctness benchmark.
    (ROOT/'.tmp').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=ROOT/'.tmp',prefix='variant-doc-') as temporary:
        for index,row in enumerate(records):
            module=importlib.import_module(row['builder'].removesuffix('.build'))
            profile=module.build(**row['kwargs']);destination=Path(temporary)/str(index)
            package='zx0' if row['codec']=='zx0' else 'lzsa'
            importlib.import_module(package+'.export').export(destination,*profile)
            rebuilt=[]
            for line in (destination/'decoder.asm').read_text().splitlines():
                if line.startswith('org '):rebuilt.append((int(line[5:],16),bytearray()))
                elif line.startswith('db '):rebuilt[-1][1].extend(int(value[1:],16) for value in line[3:].split(','))
            assert [(address,bytes(blob)) for address,blob in rebuilt]==profile[0],row['name']

    def number(value):return f'{value:,}'
    def percent(value):
        value=Decimal(value)
        return '0.0000%' if value==0 else f'{value:+.4f}%'
    lines=['# Decoder variants, function links and baseline comparisons','',
        f'Updated {date.today().isoformat()}. These are selectable decoder implementations of',
        'forward ZX0 v2 and raw LZSA2; switching implementations does not require',
        'recompressing a valid compatible block. The table covers the named measured',
        'selection points, including the smallest retained valid decoders.','',
        '## Reading the measurements','',
        '- **CPU T** is the complete real-corpus deterministic instruction count.',
        '- **Delta vs pass** compares with Fast at `f5a0362c`; LZSA2 includes `fast_jumps=True`.',
        '- **Delta vs original** compares with the project\'s pre-policy adapted Fast:',
        '  all optional tuning flags off, with the same ABI and input data.',
        '- Both deltas are `100 * (candidate_T / reference_T - 1)`: **negative is faster**.',
        '  They measure CPU-time change, not the reciprocal throughput percentage.',
        '- **Service B** includes code, state, tables, alignment and required caller/private',
        '  stack. Embedded state counts once. Compressed input and output/history are separate.',
        '  Ordinary/resident totals exclude the application\'s IRQ code and extra stack.',
        '- ZX0 uses 364 real blocks; LZSA2 uses 21. Compare variants within one codec/mode;',
        '  these different corpora do not establish which format wins on a common workload.',
        '- IRQ execution, ULA contention, physical disk/ROM latency and player publication',
        '  deadlines are outside these CPU totals. Directed/slice regressions remain in',
        '  [FRONTIER.md](FRONTIER.md) and the linked complete native evidence.','',
        'Original means the retained pre-policy project implementation; no timing claim',
        'for an unmodified upstream executable is implied. ZX0 Standard and LZSA2 Small',
        'are additional size-oriented choices, not substituted for the Fast baselines.','',
        '| Codec / mode | Original Fast CPU T | Pass baseline CPU T |',
        '| --- | ---: | ---: |']
    for codec,kind in originals:
        lines.append(f'| {codec} / {kind} | {number(originals[codec,kind])} | {number(baselines[codec,kind])} |')
    lines += ['','## Shared placement arguments','',
        'Import the module named in a linked call. The source link targets its actual',
        '`build` function; the visible call includes all variant-selection arguments.',
        'Use these common placements to reproduce the table instead of relying on a',
        'coroutine\'s smaller legacy core reservation. Addresses are examples requiring',
        'a disjoint application layout. Changing placement can change alignment cost.','',
        '```python','SMALL = dict(core=0x8000, core_limit=0x8400)',
        'WIDE = dict(core=0x8000, core_limit=0xb000)',
        'GUARDED = dict(core=0xa000, core_limit=0xbc00,',
        '               prefix=0x7000, prefix_limit=0x7400,',
        '               stack=0x7be0, output_base=0xc000)','```','']
    for title,kinds in (('Resident complete-block decoders',('block',)),
                        ('Ordinary output-demand coroutines',('coroutine',)),
                        ('Guarded-input LZSA2',('guarded-call','guarded-direct'))):
        lines += ['## '+title,'']
        if kinds==('coroutine',):lines += ['Measured with 256-byte output demands and unchanged publication cursors.','']
        if 'guarded-call' in kinds:
            lines += ['Service is **consumer / full aligned reference**. The consumer includes the',
                'guard patcher. The full reference additionally includes the retained supplier,',
                '256-byte carry, I/O code/state, 1,280-byte mock workspace, required stacks and',
                'the tested IRQ. Carry is specific to that supplier, not every possible supplier.',
                'CPU columns compare decoder work only, using the same original 63-case supplier',
                'harness and its 21 real blocks; producer CPU and sector delivery are separate.','']
        lines += ['| Variant | Service B | CPU T | Delta vs pass | Delta vs original | Builder call / source |',
                  '| --- | ---: | ---: | ---: | ---: | --- |']
        for row in records:
            if row['kind'] not in kinds:continue
            memory=number(row['service_bytes'])
            if row['full_reference_service_bytes'] is not None:memory+=' / '+number(row['full_reference_service_bytes'])
            call=f'[{row["display_call"]}]({row["source_file"]}#L{row["source_line"]})'
            lines.append(f'| {row["name"]} | {memory} | {number(row["real_cpu_tstates"])} | '
                f'{percent(row["delta_time_vs_pass_percent"])} | {percent(row["delta_time_vs_original_percent"])} | {call} |')
        lines.append('')
    lines += ['## Selection and runtime contracts','',
        '- Smallest resident decoders: **ZX0 Standard 74 B** (68 code +6 stack),',
        '  **LZSA2 Small 145 B** (137 code +8 stack). Both are slower than Fast.',
        '- Fastest measured resident choices: **ZX0 Maximum shared 228, 7,578 B** and',
        '  **LZSA2 Wide expanded, 7,004 B**. Shared 127 uses 5,114 B and is faster',
        '  than the original unshared 228. Shared suffixes support resident calls only.',
        '- Useful intermediate choices include Mega tuned 674 B and Wide shared 3,452 B.',
        '- Maximum ZX0 coroutine requires Spectrum-style undocumented `CP IXH/IXL`.',
        '  Caller IX is restored on every return; IRQ must preserve live IX and AF/AF\'.',
        '- Wide figures assume an aligned core. Arbitrary alignment adds up to 255 B.',
        '  A full guarded reference can therefore exceed 10,000 B after relocation.',
        '- Original unshared Maximum 228 has only 10 service bytes left. The 13-byte/six-stack-byte',
        '  IRQ example makes 10,009 B; use 227 (9,985 B with that IRQ) or reserve the',
        '  actual handler through `irq_code_bytes` / `irq_stack_bytes`. The verified',
        '  minimal `EI; RETI` handler makes 228 total 9,995 B.','',
        'Resident calls use HL=input, DE=output and the caller stack. Ordinary coroutines',
        'configure `input_pointer`, `block_end`, `slice_target` and call generated `begin`,',
        'then `slice_until`. Guarded callers additionally publish input frontiers and',
        'call the embedded `update_guards` only while suspended. Keep required source/',
        'history readable and respect the linked function\'s writable-code/IRQ contract.',
        'The Python `build` functions are generators returning `(regions, labels, metadata)`;',
        'the generated labels are the Z80 runtime entry points.','',
        '```python','import zx0.block','from zx0.export import export','',
        'profile = zx0.block.build(**SMALL, branch_tuned=True,',
        '                          literal_prefix=True, inline_tail_refill=True)',
        'export("build/zx0", *profile)','```','',
        'For LZSA2 use `lzsa.export.export`. Existing CLI selectors remain documented in',
        '[ZX0 README](zx0/README.md) and [LZSA2 README](lzsa/README.md); no new mode key',
        'or runtime format switch is introduced by this table.','',
        '## Implementation files','',
        'The tables above link public selection functions. For the Z80 instruction',
        'emitters behind a dispatcher, use these implementation functions:','',
        '| Decoder family | Implementation function / file |',
        '| --- | --- |']
    for family,module,function in (
        ('ZX0 Standard / Turbo / Mega','zx0.codec','emit_decoder'),
        ('ZX0 Fast','zx0.resumable','emit_fast'),
        ('ZX0 Maximum resident','zx0.maximum','build'),
        ('ZX0 shared-prefix layout','zx0._shared_prefixes','transform'),
        ('ZX0 Maximum coroutine','zx0.maximum_coroutine','build'),
        ('LZSA2 Small','lzsa.compact','build'),
        ('LZSA2 Fast and its coroutine','lzsa.resumable','build'),
        ('LZSA2 Wide resident','lzsa.wide','build'),
        ('LZSA2 Wide ordinary / guarded coroutine','lzsa.wide_coroutine','build')):
        implementation=getattr(importlib.import_module(module),function)
        path=Path(inspect.getsourcefile(implementation));line=inspect.getsourcelines(implementation)[1]
        relative=path.relative_to(LIB).as_posix()
        sources[relative]=sha(path.read_bytes().replace(b'\r\n',b'\n'))
        lines.append(f'| {family} | [{module}.{function}]({relative}#L{line}) |')
    lines += ['','## Evidence and reproduction','',
        '[Shared Maximum native proof](evidence/shared_zero_prefix_native.json.gz),',
        '[shared-prefix contracts](ZX0_SHARED_PREFIXES.md),',
        '[previous full native integration](evidence/frontier_completed_profiles_verification.json),',
        '[original ZX0 counts](evidence/trick_23.json), [original LZSA2 and jump pass](evidence/fast_jumps.json),',
        '[Small counts](evidence/trick_29.json), [guarded native replay](evidence/wide_guarded_native.json.gz),',
        '[authenticated original guarded recordings](evidence/fast_jumps_verification.json).','',
        '[Table/API/export validation](evidence/decoder_variants_verification.json) records',
        'exact calls, source-function lines, memory arithmetic, both timing references',
        'and source/evidence hashes. It reuses complete saved native timings and verifies',
        'the current public calls and ORG/DB exports; it is not a new benchmark or release.',
        'Rebuild the table and its validation with:','',
        '```powershell','python libraries/tests/document_decoder_variants.py','```','']
    text='\n'.join(lines)
    links=re.findall(r'\[[^\]]*\]\(([^)]+)\)',text)
    for target in links:
        filename,_,anchor=target.partition('#');path=LIB/filename
        assert path.is_file(),target
        if anchor.startswith('L'):
            assert path.read_text(encoding='utf-8').splitlines()[int(anchor[1:])-1].startswith('def '),target
    document=LIB/'DECODER_VARIANTS.md';document.write_text(text,encoding='utf-8',newline='\n')
    result=dict(date=date.today().isoformat(),complete=True,documentation_only=True,native_benchmark_rerun=False,
        metric='100*(candidate_CPU_T/reference_CPU_T-1); negative is faster',
        original_reference='adapted Fast before optional policies, same features/corpus',
        pass_reference='f5a0362c Fast; LZSA2 includes fast_jumps',document_sha256=sha(document.read_bytes()),
        checked_public_calls_and_exact_exports=len(records),checked_local_links=len(links),references=[dict(codec=c,kind=k,
            original_fast_cpu_tstates=originals[c,k],pass_baseline_cpu_tstates=baselines[c,k]) for c,k in originals],
        profiles=records,evidence_sha256=used,source_sha256_lf=sources,
        reproducer_sha256_lf=sha(Path(__file__).read_bytes().replace(b'\r\n',b'\n')),
        default_code_delta_bytes=0,default_instruction_delta_tstates=0)
    (LIB/'evidence/decoder_variants_verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(complete=True,document=str(document),checked_calls=len(records),exact_exports=len(records))))


if __name__=='__main__':main()
