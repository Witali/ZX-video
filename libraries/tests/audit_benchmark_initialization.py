"""Audit initialization accounting from saved native evidence; no CPU replay.

Runtime entry/EOF costs remain in their original benchmark totals. Guarded
producer+decoder totals include guest setup and inline guard patching once.
Caller argument publication and CALL instructions are a separate convention.
"""
from collections import Counter
from datetime import date
import gzip
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
LIB=ROOT/'libraries'
JSON_PATH=LIB/'evidence/benchmark_initialization.json'
DOC_PATH=LIB/'BENCHMARK_INITIALIZATION.md'


def sha(blob):return hashlib.sha256(blob).hexdigest()


def main():
    evidence={};sources={};texts={}
    def raw(relative):
        path=ROOT/relative;blob=path.read_bytes()
        if Path(relative).suffix in ('.py','.asm','.c','.h'):
            sources[relative]=sha(blob.replace(b'\r\n',b'\n'))
        else:evidence[relative]=sha(blob)
        return blob
    def read(relative):
        blob=raw(relative)
        return json.loads(gzip.decompress(blob) if relative.endswith('.gz') else blob)
    def source(relative):
        if relative not in texts:texts[relative]=raw(relative).decode('utf-8')
        return texts[relative]
    def ref(relative,needle):
        text=source(relative)
        assert needle in text,(relative,needle)
        line=text[:text.index(needle)].count('\n')+1
        return dict(file=relative,line=line,text=needle)

    # This generated catalog is a discovery input, not a timing oracle. Hash a
    # stable selection subset: the root table will add accounting columns and
    # an audit-report link without invalidating selection names/bytes/counts.
    table_path=LIB/'evidence/decoder_variants_verification.json'
    table_blob=table_path.read_bytes();table=json.loads(table_blob)
    assert table['complete']
    selection_count=table['checked_public_calls_and_exact_exports']
    assert selection_count>=71
    fields=('name','codec','kind','builder','kwargs','real_cpu_tstates','regions')
    catalog=[{field:row[field] for field in fields} for row in table['profiles']]
    assert len(catalog)==selection_count
    modes=Counter(row['kind'] for row in catalog)
    assert modes==dict(block=selection_count-16,coroutine=12,**{'guarded-call':2,'guarded-direct':2})
    for row in table['profiles']:
        source('libraries/'+row['source_file'])
    for relative,digest in table['evidence_sha256'].items():
        if relative in ('evidence/benchmark_initialization.json','evidence/decoder_variants_verification.json'):
            continue
        blob=raw('libraries/'+relative)
        assert sha(blob)==digest,relative

    source_files=(
        'libraries/tests/native_block.py','libraries/tests/native_inplace_block.py','emulator/cpu.py',
        'emulator/src/codec_cpu.c','libraries/lzsa/src/lzsa/native.py',
        'libraries/tests/maximum_coroutine_native.py','libraries/tests/measure_compact_sync.py',
        'libraries/tests/measure_compact_frontier.py','libraries/tests/measure_compact_branches.py',
        'libraries/tests/measure_fast_jumps.py','libraries/tests/measure_bit_phases.py',
        'libraries/tests/measure_compact_profile.py','libraries/tests/measure_maximum_coroutine.py',
        'libraries/tests/measure_wide_coroutine.py','libraries/tests/measure_wide_guarded.py',
        'libraries/tests/wide_guarded_support.py','libraries/tests/summarize_wide_guarded.py',
        'libraries/lzsa/src/lzsa/streaming.py','libraries/zx0/src/zx0/resumable.py',
        'libraries/zx0/src/zx0/codec.py','libraries/zx0/src/zx0/_branch_tuning.py',
        'libraries/lzsa/src/lzsa/_branch_tuning.py',
        'libraries/zx0/src/zx0/asm/dzx0_standard.asm','libraries/zx0/src/zx0/asm/dzx0_turbo.asm',
        'libraries/zx0/src/zx0/asm/dzx0_mega.asm','libraries/zx0/src/zx0/asm/dzx0_fast.asm',
        'toolkit/benchmark_inplace_streaming.py','toolkit/benchmark_inplace_slot.py',
        'toolkit/test_streaming_lzsa2.py','toolkit/inplace_streaming_core.py',
        'toolkit/inplace_slot_input_z80.py','libraries/tests/audit_benchmark_initialization.py')
    for relative in source_files:source(relative)
    references=dict(
        resident_entry=ref('libraries/tests/native_block.py','m.pc,m.sp,m.hl,m.de=entry'),
        resident_timer=ref('libraries/tests/native_block.py','m.set_breakpoint(stop);budget=20_000_000;m.ticks_to_stop=budget'),
        resident_total=ref('libraries/tests/native_block.py','return dict(tstates=budget-m.ticks_to_stop'),
        ordinary_begin=ref('libraries/lzsa/src/lzsa/native.py',"entry=labels['begin' if index==0 else 'slice_until']"),
        ordinary_timer=ref('libraries/lzsa/src/lzsa/native.py','budget=20_000_000;m.ticks_to_stop=budget'),
        ordinary_total=ref('libraries/lzsa/src/lzsa/native.py','return dict(tstates=sum(slices)'),
        ordinary_arguments=ref('libraries/lzsa/src/lzsa/native.py',"put_word(m,labels['input_pointer'],source)"),
        ordinary_target=ref('libraries/lzsa/src/lzsa/native.py',"put_word(m,labels['slice_target'],output+target)"),
        compact_begin=ref('libraries/tests/measure_compact_sync.py',"entry=z['begin' if index==0 else 'slice_until']"),
        compact_timer=ref('libraries/tests/measure_compact_sync.py','m.ticks_to_stop=20_000_000'),
        compact_total=ref('libraries/tests/measure_compact_sync.py','return dict(tstates=sum(costs)'),
        maximum_begin=ref('libraries/tests/maximum_coroutine_native.py',"entry=z['begin' if index==0 else 'slice_until']"),
        maximum_timer=ref('libraries/tests/maximum_coroutine_native.py','m.ticks_to_stop=20_000_000'),
        maximum_total=ref('libraries/tests/maximum_coroutine_native.py','return dict(tstates=sum(costs)'),
        native_guard_helper=ref('libraries/tests/wide_guarded_support.py',"m.af=int(full)<<8;m.pc=z['update_guards']"),
        native_guard_helper_cost=ref('libraries/tests/wide_guarded_support.py','helper_cost.append(20_000_000-m.ticks_to_stop)'),
        native_guard_decoder_total=ref('libraries/tests/wide_guarded_support.py','return dict(exact=True,tstates=sum(cost)'),
        native_guard_separate_total=ref('libraries/tests/wide_guarded_support.py','guard_update_tstates=sum(helper_cost)'),
        producer_begin=ref('toolkit/benchmark_inplace_streaming.py',"begin=self.call(self.p['begin'],interrupt)"),
        producer_decoder_timer=ref('toolkit/benchmark_inplace_streaming.py','c.sp=STACK;c.push(STOP);c.decoding=True;start=c.tstates'),
        producer_target=ref('toolkit/benchmark_inplace_streaming.py',"word(c,self.z['slice_target'],0xc000+target)"),
        producer_totals=ref('toolkit/benchmark_inplace_streaming.py','producer_tstates=begin+sum(steps),decoder_tstates=sum(slices)'),
        producer_combined=ref('toolkit/benchmark_inplace_slot.py','total_tstates=producer+decoder'),
        guest_producer_begin=ref('toolkit/inplace_slot_input_z80.py',"a.label('begin'); e('CP 3'"),
        guest_descriptor=ref('toolkit/inplace_slot_input_z80.py',"ws(z['block_length'])"),
        guest_input_pointer=ref('toolkit/inplace_slot_input_z80.py',"ws(z['input_pointer'])"),
        guest_frontiers=ref('toolkit/inplace_streaming_core.py',"a.label('frontier');load(p['destination_high']);store(z['input_high'])"),
        guest_patcher=ref('toolkit/inplace_streaming_core.py','emit_guard_update(a,z,emit=e,operand=n)'),
        patcher=ref('libraries/lzsa/src/lzsa/streaming.py','def emit_guard_update'),
        zx0_begin=ref('libraries/zx0/src/zx0/resumable.py',"cold.label('slice_begin')"),
        zx0_sync=ref('libraries/zx0/src/zx0/resumable.py',"cold.label('slice_sync_target')"),
        maximum_init=ref('libraries/zx0/src/zx0/maximum_coroutine.py',"c.label('begin')"),
        lzsa_begin=ref('libraries/lzsa/src/lzsa/resumable.py',"cold.label('begin')"),
        lzsa_sync=ref('libraries/lzsa/src/lzsa/resumable.py',"cold.label('sync')"),
        wide_begin=ref('libraries/lzsa/src/lzsa/wide_coroutine.py',"cold.label('begin')"),
        wide_sync=ref('libraries/lzsa/src/lzsa/wide_coroutine.py',"cold.label('sync')"),
        wide_static_table=ref('libraries/lzsa/src/lzsa/wide.py',"a.label('dispatch_low')"))
    # A reset of the per-invocation budget occurs before executing begin,
    # never after begin. The first invocation is retained in the summed list.
    for name in ('ordinary','compact','maximum'):
        assert references[name+'_begin']['line']<references[name+'_timer']['line']<references[name+'_total']['line']
    assert references['producer_begin']['line']<references['producer_decoder_timer']['line']<references['producer_totals']['line']

    ledgers=dict(
        zx0_standard=dict(instructions=[['LD BC,FFFF',10],['PUSH BC',11],['INC BC',6],['LD A,80',7]],tstates=34),
        zx0_standard_smc=dict(instructions=[['LD BC,FFFF',10],['LD(offset),BC',20],['INC BC',6],['LD A,80',7]],tstates=43),
        zx0_turbo=dict(instructions=[['LD BC,FFFF',10],['LD(offset),BC',20],['INC BC',6],['LD A,80',7],['JR literals',12]],tstates=55),
        zx0_fast=dict(instructions=[['LD BC,FFFF',10],['LD(offset),BC',20],['INC BC',6],['LD A,80',7],['JP literals',10]],tstates=53),
        zx0_mega=dict(instructions=[['LD BC,FFFF',10],['LD(offset),BC',20],['INC BC',6],['JR literals0',12]],tstates=48),
        zx0_maximum=dict(instructions=[['LD BC,FFFF',10],['LD(offset),BC',20],['INC BC',6],['JP literals0',10]],tstates=46),
        lzsa_fast=dict(instructions=[['LD B,0',7],['SCF',4],["EX AF,AF'",4],['JP ReadToken',10]],tstates=25),
        lzsa_small=dict(instructions=[['XOR A',4],['LD B,A',4],["EX AF,AF'",4],['JR ReadToken',12]],tstates=24),
        lzsa_wide=dict(instructions=[['EXX',4],['PUSH HL',11],['EXX',4],['LD B,0',7],['SCF',4],["EX AF,AF'",4],['JP ReadToken',10]],tstates=44),
        producer_begin=dict(instructions=[['CP3',7],['JP NC,fatal not taken',10],['LD(slot),A',13],['XOR A',4],['LD(phase),A',13],['LD(header_count),A',13],['RET',10]],tstates=70))
    assert all(sum(t for _,t in row['instructions'])==row['tstates'] for row in ledgers.values())
    ordinary_init=dict(
        zx0_fast=dict(begin_wrapper_tstates=216,raw_init_tstates=53,total_to_first_parser_tstates=269),
        zx0_literal_prefix=dict(begin_wrapper_tstates=242,raw_init_tstates=53,total_to_first_parser_tstates=295,
            extra_sync_tstates_every_request=26),
        zx0_maximum_index=dict(begin_wrapper_nonfinal_tstates=258,raw_init_tstates=46,
            total_nonfinal_tstates=304,total_final_demand_tstates=309),
        lzsa_fast=dict(begin_wrapper_nonfinal_tstates=231,raw_init_tstates=25,total_nonfinal_tstates=256,total_final_demand_tstates=261),
        lzsa_fast_compact_sync=dict(begin_wrapper_nonfinal_tstates=223,raw_init_tstates=25,total_nonfinal_tstates=248,total_final_demand_tstates=253),
        lzsa_wide=dict(begin_wrapper_nonfinal_tstates=231,raw_init_tstates=44,total_nonfinal_tstates=275,total_final_demand_tstates=280),
        guarded_lzsa_fast=dict(begin_wrapper_nonfinal_tstates=261,raw_init_tstates=25,total_nonfinal_tstates=286,total_final_demand_tstates=291),
        guarded_lzsa_wide=dict(begin_wrapper_nonfinal_tstates=261,raw_init_tstates=44,total_nonfinal_tstates=305,total_final_demand_tstates=310))
    # These are static instruction ledgers, not new CPU measurements. The
    # callable sync17/RET10 and raw entry are already inside native totals.
    ordinary_derivation=dict(zx0_sync=112,zx0_prefix_sync=138,lzsa_sync_nonfinal=127,
        lzsa_compact_sync_nonfinal=119,maximum_index_sync_nonfinal=97,
        call_sync=17,common_begin_after_sync=87,guarded_flags_clear=30,
        maximum_quota_enter=40,maximum_begin_after_quota=104,
        final_sync_path_extra=5,scope='From begin through the raw entry jump, before the first token/literal parser; included, never add again.')
    assert 17+112+87+53==ordinary_init['zx0_fast']['total_to_first_parser_tstates']
    assert 17+138+87+53==ordinary_init['zx0_literal_prefix']['total_to_first_parser_tstates']
    assert 17+97+40+104+46==ordinary_init['zx0_maximum_index']['total_nonfinal_tstates']

    native=read('libraries/evidence/wide_guarded_native.json.gz')
    manifest=read('libraries/evidence/fast_jumps_verification.json')
    assert native['complete'] and len(native['profiles'])==4 and native['retained_producer_cases']==63
    archive_manifest={row['file']:row for row in manifest['archives']}
    fast={}
    for mode in ('call','direct'):
        fast[mode]={}
        for phase in ('before','after'):
            relative=f'evidence/fast_jumps_streaming/fast-jumps-{mode}-{phase}.json.gz'
            blob=raw('libraries/'+relative);item=archive_manifest[relative]
            assert sha(blob)==item['sha256'] and sha(gzip.decompress(blob))==item['decoded_sha256']
            proof=json.loads(gzip.decompress(blob))
            assert proof['complete'] and proof['stream_sha256']==native['retained_stream_sha256']
            assert len(proof['blocks'])==63
            fast[mode][phase]=proof
    guarded_profiles={};stream_bindings=None
    for key,item in native['profiles'].items():
        mode='direct' if key.endswith('direct') else 'call'
        reference=item['reference_producer_blocks']
        assert len(reference)==63
        real=[row for row in reference if row['case'].startswith('real-')]
        assert len(real)==21
        for phase in ('before','after'):
            for old,row in zip(fast[mode][phase]['blocks'],reference):
                new=row['candidate'];base=row['baseline']
                for field in ('payload_sha256','raw_sha256','producer_tstates','begin_tstates','step_tstates','decoded_bytes','payload_bytes','input_pointer'):
                    assert old[field]==base[field]==new[field],(key,phase,field)
                if phase=='after':assert old['decoder_tstates']==base['decoder_tstates']
        bindings=[dict(case=row['case'],payload_sha256=row['candidate']['payload_sha256'],raw_sha256=row['candidate']['raw_sha256'],
            input_pointer=row['candidate']['input_pointer'],input_bytes=row['candidate']['payload_bytes'],output_bytes=row['candidate']['decoded_bytes']) for row in reference]
        if stream_bindings is None:stream_bindings=bindings
        else:assert stream_bindings==bindings
        values={}
        for prefix,selected in (('real',real),('all',reference)):
            candidates=[row['candidate'] for row in selected]
            indices=[reference.index(row) for row in selected]
            decoder=sum(row['decoder_tstates'] for row in candidates)
            producer=sum(row['producer_tstates'] for row in candidates)
            assert all(row['decoder_tstates']==sum(row['slice_tstates']) for row in candidates)
            assert all(row['producer_tstates']==row['begin_tstates']+sum(row['step_tstates']) for row in candidates)
            assert all(row['begin_tstates']==70 for row in candidates)
            values.update({prefix+'_decoder_tstates':decoder,prefix+'_producer_tstates':producer,prefix+'_total_tstates':decoder+producer,
                prefix+'_blocks':len(selected),prefix+'_producer_begin_tstates':70*len(selected),
                prefix+'_decoder_calls':sum(len(row['slice_tstates']) for row in candidates),
                prefix+'_producer_steps':sum(len(row['step_tstates']) for row in candidates)})
            for phase,label in (('before','original'),('after','pass')):
                rows=[fast[mode][phase]['blocks'][index] for index in indices]
                values[prefix+'_'+label+'_fast_decoder_tstates']=sum(row['decoder_tstates'] for row in rows)
                values[prefix+'_'+label+'_fast_total_tstates']=sum(row['producer_tstates']+row['decoder_tstates'] for row in rows)
        assert values['real_decoder_tstates']==item['summary']['real_decoder_candidate_tstates']
        partial,full=(174,211) if mode=='direct' else (187,224)
        patch_scopes={}
        for scope,selected in (('real',real),('all',reference)):
            waits=sum(len(row['candidate']['input_waits']) for row in selected)
            count=len(selected)+waits
            complete=len(selected)
            initial_full=sum(not row['candidate']['input_waits'] for row in selected)
            initial_partial=len(selected)-initial_full
            initial=initial_partial*partial+initial_full*full
            total=(count-complete)*partial+complete*full
            patch_scopes[scope]=dict(calls=count,partial_calls=count-complete,complete_calls=complete,
                initial_partial_calls=initial_partial,initial_complete_calls=initial_full,
                initial_setup_tstates=initial,repeated_update_tstates=total-initial,total_tstates=total,
                included_in='producer_tstates; do not add to combined total')
        histogram=item['reference_producer_summary']['instruction_histogram']
        assert sum(row['count'] for row in histogram if row['instruction']=='LD A,PUSH AF')==patch_scopes['all']['calls']==795
        assert sum(row['count'] for row in histogram if row['instruction']=='LD A,RET')==63
        assert patch_scopes['real']['calls']==605
        # Every native standalone case completes one block. Its helper was
        # really executed and timed, but kept separate from sum(decode slices).
        native_offsets=[]
        for offset in native['placements']:
            all_placements=[];real_placements=[]
            for row in item['native_blocks']:
                point=next(p for p in row['placements'] if p['offset']==offset)
                assert point['guard_update_tstates']==(point['guard_update_calls']-1)*(partial+10)+(full+10)
                all_placements.append(point)
                if row['case'].startswith('real-'):real_placements.append(point)
            cost={}
            for scope,selected in (('real',real_placements),('all',all_placements)):
                decoder=sum(point['candidate_tstates'] for point in selected)
                helper=sum(point['guard_update_tstates'] for point in selected)
                cost[scope]=dict(cases=len(selected),decoder_tstates=decoder,guard_update_tstates=helper,
                    decoder_plus_guard_update_tstates=decoder+helper,guard_update_calls=sum(point['guard_update_calls'] for point in selected))
            native_offsets.append(dict(offset=offset,**cost))
        catalog_row=next(row for row in catalog if row['name']=='LZSA2 Wide '+('shared ' if 'shared' in key else 'expanded ')+mode)
        assert catalog_row['real_cpu_tstates']==values['real_decoder_tstates']
        guarded_profiles[key]=dict(**values,profile_name=catalog_row['name'],builder=catalog_row['builder'],kwargs=catalog_row['kwargs'],
            native_proof='libraries/evidence/wide_guarded_native.json.gz',native_proof_sha256=evidence['libraries/evidence/wide_guarded_native.json.gz'],
            stream_sha256=native['retained_stream_sha256'],input_binding_sha256=sha(json.dumps(bindings,sort_keys=True,separators=(',',':')).encode()),
            guard_patcher=dict(inline_partial_tstates=partial,inline_complete_tstates=full,
                callable_partial_entry_to_RET_tstates=partial+10,callable_complete_entry_to_RET_tstates=full+10,
                caller_CALL_extra_tstates=17,scopes=patch_scopes),
            standalone_native_decoder_plus_guard_update=native_offsets,
            total_scope='Saved guest producer begin+steps (including descriptor/frontier/carry/guard work) plus every decoder begin/resume/EOF/RET. Caller argument passing/CALL and hardware latency are outside this convention.')

    profiles=[]
    for row in catalog:
        item=dict(row)
        if row['kind']=='block':
            item.update(primary_cpu_tstates=row['real_cpu_tstates'],benchmark_boundary='metadata raw entry through EOF RET',
                required_external_library_initializer_tstates=0,required_entry_initialization_included=True)
            if row['builder']=='zx0.small.build':
                item['included_entry_setup_tstates']=43 if row['kwargs']['profile']=='smc' else 34
            elif row['builder']=='lzsa.compact.build' and row['kwargs'].get('compact_eof'):
                item['included_entry_setup_tstates']=24
            elif row['builder'] in ('zx0.maximum.build','zx0.maximum_branches.build'):
                item['included_entry_setup_tstates']=46
                item['included_offset_reset_tstates']=20
        elif row['kind']=='coroutine':
            item.update(primary_cpu_tstates=row['real_cpu_tstates'],benchmark_boundary='begin first invocation plus every slice_until entry through its RET; sum all invocations',
                required_external_library_initializer_tstates=0,required_entry_initialization_included=True)
        else:
            key=next(key for key,value in guarded_profiles.items() if value['profile_name']==row['name'])
            item.update(primary_cpu_tstates=guarded_profiles[key]['real_total_tstates'],guarded_profile_key=key,
                benchmark_boundary='producer begin+all producer steps+decoder begin+all resumes through RET',
                required_external_library_initializer='Required guard updates are included in producer work; standalone decode-only timing reports their separate measured cost.')
        profiles.append(item)
    scope=dict(native_cases_reexecuted=0,generated_target_code_changed=False,
        invocation='All recorded entry-through-RET costs exclude caller CALL17; every internal CALL/RET is included.',
        parameter_passing='HL/DE for raw decoders and input_pointer/block_end/slice_target for coroutines are ready at the API boundary. Host ABI fixture writes are not timed Z80 instructions; they are not a free implementation of a separate callable initializer.',
        required_initializer='No required external target table/cache/offset initializer for resident/ordinary profiles. Guarded suppliers must publish frontiers and run the guard patcher; the full guest producer evidence counts both.',
        static_image='Code, emitted tables and initial data are installed as binary image; there is no target table generation or runtime image-copy initializer in these APIs.',
        application_limits='Binary loading, caller argument preparation, disk/ROM latency, ULA, real IRQ scheduling and a complete application cold boot are outside this service-entry benchmark. Do not call it complete application CPU.',
        no_double_counting='Initialization, begin/sync, guard setup and updates are subsets of the reported entry or producer totals. Add only separately reported standalone guard helper time to its decode-only counter; never add it to producer+decoder again.')
    result=dict(date=date.today().isoformat(),complete=True,accounting_only=True,native_cases_reexecuted=0,
        profiles=profiles,profile_count=selection_count,mode_counts=dict(modes),guarded_profiles=guarded_profiles,
        initialization_scope=scope,entry_instruction_ledgers=ledgers,ordinary_begin_costs=ordinary_init,
        ordinary_derivation=ordinary_derivation,source_references=references,input_bindings=stream_bindings,
        retained_stream_sha256=native['retained_stream_sha256'],
        catalog_discovery=dict(path=str(table_path.relative_to(ROOT)).replace('\\','/'),
            required_timing_anchor=False,
            stable_selection_fields=list(fields),stable_selection_sha256=sha(json.dumps(catalog,sort_keys=True,separators=(',',':')).encode()),
            note='Regenerating accounting fields/evidence links is allowed; the selection subset is the catalog identity. New qualified resident calls extend it.'),
        source_sha256_lf=sources,evidence_sha256=evidence)
    assert all(sha((ROOT/name).read_bytes().replace(b'\r\n',b'\n'))==digest for name,digest in sources.items()),'Audited source changed during accounting'
    doc=render(result)
    DOC_PATH.write_text(doc,encoding='utf-8',newline='\n')
    result['document_sha256']=sha(DOC_PATH.read_bytes())
    JSON_PATH.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(complete=True,profiles=selection_count,native_cases_reexecuted=0,
        guarded_real_totals={key:row['real_total_tstates'] for key,row in guarded_profiles.items()},
        report_sha256=sha(JSON_PATH.read_bytes())),sort_keys=True))
    return result


def render(report):
    def link(key):
        item=report['source_references'][key]
        return f"[{item['file']}:{item['line']}](../{item['file']}#L{item['line']})"
    lines=['# Benchmark initialization accounting','',
        'Accounting audit of the '+str(report['profile_count'])+' linked selections, '+report['date']+'. No target code or saved native measurements are changed; no CPU replay is run.','',
        'The primary guarded service metric is **producer + decoder**, including producer initialization, descriptor/frontier publication, carry handling and guard patching. The preceding decoder-only counts remain historical components. All resident and ordinary-coroutine entry initialization was already included.','',
        '## Counter boundaries','',
        '- **'+str(report['mode_counts']['block'])+' resident selections:** start at the metadata entry and stop after exact EOF/restoration/RET. Offset/cache setup is inside this interval. '+link('resident_timer')+'.',
        '- **12 ordinary coroutines:** the first timed invocation selects `begin`; every later invocation selects `slice_until`. The first cost is retained in the sum, including sync, private-stack setup, raw initialization, yields and final return. '+link('ordinary_begin')+', '+link('ordinary_total')+', '+link('compact_begin')+', '+link('maximum_begin')+'.',
        '- **4 guarded selections:** producer `begin` is timed first; decoder timing starts before its `begin`, and supplier steps are separately timed. The full sum includes both. '+link('producer_begin')+', '+link('producer_decoder_timer')+', '+link('producer_totals')+'.','',
        'All external caller CALL instructions (17 T each) and argument publication are outside the entry-through-RET convention. Raw HL/DE and coroutine input_pointer/block_end/slice_target are ready at entry. Host writes of these API inputs are not timed guest instructions: '+link('ordinary_arguments')+', '+link('ordinary_target')+', '+link('producer_target')+'. Their application-specific loads/stores must be added when benchmarking a concrete caller. This is not full application CPU or a cold-boot benchmark.','',
        'There is no external callable table/cache/offset initializer for these resident/ordinary APIs. Tables and initial data are emitted in the binary; dynamic cache/default-offset setup runs at entry. The actual guarded producer publishes descriptors and frontiers in guest code: '+link('guest_descriptor')+', '+link('guest_input_pointer')+', '+link('guest_frontiers')+'. Code/image loading, disk/ROM latency, ULA and application IRQ scheduling remain separate.','',
        '## Included initialization ledgers','',
        'Static Z80 instruction counts below identify setup already inside the measured paths, before the first parser work. They are not additional costs to add again.','',
        '| Raw family | Included entry setup T |','| --- | ---: |']
    names=dict(zx0_standard='ZX0 Standard / gamma-JP',zx0_standard_smc='ZX0 Small SMC',zx0_turbo='ZX0 Turbo',zx0_fast='ZX0 Fast',zx0_mega='ZX0 original Mega',zx0_maximum='ZX0 Maximum / tuned Mega with JP',lzsa_fast='LZSA2 Fast',lzsa_small='LZSA2 Small / compact EOF',lzsa_wide='LZSA2 Wide / Hybrid / Hot')
    lines += [f"| {names[key]} | {row['tstates']} |" for key,row in report['entry_instruction_ledgers'].items() if key in names]
    lines += ['', 'Ordinary ZX0 Fast `begin` through raw setup is 269 T, or 295 T with the extra literal-prefix sync stores. Maximum index-quota initialization is 304 T (309 T when the initial demand equals block end). Ordinary LZSA2 Fast is 256/261 T, compact-sync 248/253 T, and Wide 275/280 T. Guarded Fast is 286/291 T; guarded Wide 305/310 T. These pairs differ only by the final-demand sync branch. Full instruction components and source hashes are in the JSON.','',
        'The producer initializer is 70 T per block: 4410 T across 63 retained cases and 1470 T across 21 real cases. Both amounts are already inside producer totals. The decoder’s own `begin` is a different initializer and is inside decoder totals.','',
        '## Guarded totals from saved guest execution','',
        'The four profiles and Fast references use the identical 63-block supplier stream (21 real blocks), recorded input/output hashes and 772 sector reads. The supplied totals include all guest library initialization and guard work within this API convention, without adding them twice.','',
        '| Profile | Real decoder T | Real producer T | Real full service T | All 63 full service T |',
        '| --- | ---: | ---: | ---: | ---: |']
    for key,row in report['guarded_profiles'].items():
        lines.append(f"| {key} | {row['real_decoder_tstates']:,} | {row['real_producer_tstates']:,} | {row['real_total_tstates']:,} | {row['all_total_tstates']:,} |")
    lines += ['', '| Fast reference | Real full service T | All 63 full service T |','| --- | ---: | ---: |']
    for mode in ('call','direct'):
        row=report['guarded_profiles']['wide-'+mode]
        for policy in ('original','pass'):
            lines.append(f"| {mode} {policy} | {row['real_'+policy+'_fast_total_tstates']:,} | {row['all_'+policy+'_fast_total_tstates']:,} |")
    lines += ['', '### Guard setup and repeated updates','',
        'The retained producer uses the inline patcher. Partial/complete calls cost 187/224 T in CALL mode and 174/211 T in direct mode; the callable consumer helper adds its RET 10 T, producing 197/234 and 184/221 T respectively. The caller CALL 17 T remains separate. '+link('patcher')+', '+link('guest_patcher')+'.','',
        'All 63 blocks execute 795 inline updates: 732 partial and 63 complete. The first update of each block is required initialization; 30 initial updates are partial and 33 complete. The remaining 732 updates follow input waits. The 21 real blocks execute 605 updates: 584 partial and 21 complete, with 21 initial partial setups. These counts are reconciled with the saved producer instruction histogram and input-wait lists.','',
        '| Mode / scope | Initial guard setup T | Repeated updates T | Total guard work already in producer T |','| --- | ---: | ---: | ---: |']
    for mode in ('call','direct'):
        scopes=report['guarded_profiles']['wide-'+mode]['guard_patcher']['scopes']
        for scope in ('real','all'):
            row=scopes[scope]
            lines.append(f"| {mode} / {scope} | {row['initial_setup_tstates']:,} | {row['repeated_update_tstates']:,} | {row['total_tstates']:,} |")
    lines += ['', 'The separate flat-native guarded runner executes and times `update_guards` outside the decode-slice counter. Its returned `tstates` alone excludes this work; use `tstates + guard_update_tstates` for its consumer-plus-patcher cost. The JSON records both components and their sum at every saved placement. '+link('native_guard_helper')+', '+link('native_guard_separate_total')+'. Do not add that standalone helper to the producer+decoder totals: the producer already executes its inline implementation.','',
        '## Reproduction and provenance','',
        '```powershell','python libraries/tests/audit_benchmark_initialization.py','```','',
        '[Machine-readable audit](evidence/benchmark_initialization.json) lists all '+str(report['profile_count'])+' selection names/calls, the four guarded keys, exact source lines, instruction ledgers, native-proof/stream/input hashes, standalone helper costs and full source/evidence SHA256. It derives totals from complete retained proof; it runs no emulator or decoder. The mutable generated table is discovery metadata, not the timing oracle.','']
    return '\n'.join(lines)


if __name__=='__main__':main()
