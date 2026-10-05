"""Verify register-held table steps, aligned group addresses and exact total cost."""
from collections import Counter
from contextlib import redirect_stdout
import gzip
import io
import json
import random
import struct
from check_coefficient_steps import full_domain,guarded
from check_primitives import machine,symbols,call
from check_inline_products import step
from check_unpaced import preparation_audit
from check_constant_pitch import extra_stream
from verify import ROOT,native,image,sha

VARIANTS=('pure-r34','pure-r35')
REGISTERS=('af','bc','de','hl','alt_af','alt_bc','alt_de','alt_hl','ix','iy')


def source_contract(out):
    old=(out/'pure-r34/decoder.s').read_text();new=(out/'pure-r35/decoder.s').read_text()
    aliases='.globl _coef35_unused_step, _coef35_page_cursor\n_coef35_unused_step = coef_step\n_coef35_page_cursor = coef_out\n'
    assert new.count(aliases)==1;new=new.replace(aliases,'')
    def split(s):
        a=s.index('coef_changed:\n');b=s.index('coef_next:\n',a)
        return s[:a],s[a:b],s[b:]
    a,b=map(split,(old,new))
    assert a[0]==b[0] and a[2]==b[2]
    assert 'coef_step' not in b[1] and new.count('coef_step')==1
    assert (out/'pure-r34/filter.s').read_text()==(out/'pure-r35/filter.s').read_text()
    return dict(changes_confined_to_changed_page_builder=True,unused_step_has_no_instruction_reference=True,
                caller_and_filter_assembly_unchanged=True,
                saved_step_old_save_reload_tstates=[40,48],new_save_reload_tstates=[24,24],groups_with_saved_step=3,
                old_group_address_tstates=[43]*4,new_group_address_tstates=[29,29,29,26],saving_per_page=179)


def addresses(folder):
    m=machine(folder);s=symbols(folder);cases=0;instructions=0
    m.mark_addrs(0,65536,m.WRITE_MARK)
    def bad(address,value):raise AssertionError(('address block write',address,value))
    m.set_write_callback(bad)
    for page in range(0x72,0x7c):
        m.memory[s['_coef35_page_cursor']:s['_coef35_page_cursor']+2]=(page<<8).to_bytes(2,'little')
        for part in range(4):
            for flags in range(256):
                m.af=0x5a00|flags;m.bc=0x1234;m.de=0x5678;m.hl=0x9abc
                m.alt_af=0xdef0;m.alt_bc=0x1256;m.alt_de=0x3478;m.alt_hl=0xabcd;m.ix=0xcafe;m.iy=0xdead;m.sp=0xbffe
                m.pc=s[f'_coef35_group_{part}_start'];end=s[f'_coef35_group_{part}_end'];cost=0
                while m.pc!=end:cost+=step(m);instructions+=1
                want=(page<<8)+64*(part+1)
                assert (m.hl,m.sp)==(want,want) and cost==(29 if part<3 else 26)
                assert (m.a,m.bc,m.de,m.alt_af,m.alt_bc,m.alt_de,m.alt_hl,m.ix,m.iy)==(0x5a,0x1234,0x5678,0xdef0,0x1256,0x3478,0xabcd,0xcafe,0xdead)
                if part<3:assert m.f==flags
                else:assert m.f&1==flags&1
                cases+=1
    return dict(aligned_pages=10,groups_per_page=4,initial_flag_values=256,cases=cases,instructions=instructions,
                exact_hl_and_sp=True,unrelated_registers_preserved=True,all_instruction_costs_exact=True,all_memory_writes_forbidden=True)


def masks(out):
    variants=[guarded(out/v) for v in VARIANTS];rng=random.Random(3535)
    unused=symbols(out/'pure-r35')['_coef35_unused_step'];sentinel=bytes.fromhex('297fa5c3')
    variants[1][0].memory[unused:unused+4]=sentinel
    variants[1][0].mark_addrs(unused,4,variants[1][0].WRITE_MARK)
    coefficients=[0]*10;factors=[(n-16 if p==3 and n>=8 else n)<<(p*4) for p in range(4) for n in range(16)]
    hist=Counter();examples={}
    for mask in range(1024):
        for tap in range(10):
            if mask>>tap&1:coefficients[tap]=((coefficients[tap]+rng.randrange(1,65536)+32768)&65535)-32768
        data=struct.pack('<10h',*coefficients);snapshots=[];costs=[]
        seed={k:rng.randrange(65536) for k in REGISTERS}
        expected=b''.join(struct.pack('<64I',*[(c*f)&0xffffffff for f in factors]) for c in coefficients)
        for m,s in variants:
            for k,v in seed.items():setattr(m,k,v)
            m.memory[s['_zx_lpc']:s['_zx_lpc']+20]=data
            m.mark_addrs(0x7200,2560,m.WRITE_MARK)
            for tap in range(10):
                if mask>>tap&1:m.unmark_addrs(0x7200+256*tap,256,m.WRITE_MARK)
            costs.append(call(m,s['_prepare_coefficients'],budget=1000000))
            assert bytes(m.memory[0x7200:0x7c00])==expected
            assert bytes(m.memory[s['_zx_lpc']:s['_zx_lpc']+20])==data
            assert (m.ix,m.iy,m.sp)==(seed['ix'],seed['iy'],0xbffe)
            state=bytearray(m.memory[s['s__DATA']:s['s__DATA']+s['l__DATA']]);offset=unused-s['s__DATA']
            state[offset:offset+4]=bytes(4)
            snapshots.append(([getattr(m,k) for k in REGISTERS if k not in ('bc','alt_bc')],state))
        # Only the documented BC/BC' scratch outputs and retired step slot may
        # differ. All remaining state, flags and register values must agree.
        assert snapshots[0]==snapshots[1],mask
        assert bytes(variants[1][0].memory[unused:unused+4])==sentinel
        changed=mask.bit_count();assert costs[0]-costs[1]==179*changed,(mask,costs)
        hist[changed]+=1
        if changed not in examples:examples[changed]=costs
        for m,s in variants:
            m.mark_addrs(0x7200,2560,m.WRITE_MARK)
            assert call(m,s['_prepare_coefficients'],budget=1000000)==976
            assert bytes(m.memory[0x7200:0x7c00])==expected
    return dict(masks=1024,cached_repeats_per_variant=1024,changed_pages_histogram=dict(sorted(hist.items())),
                example_cost_pairs=dict(sorted(examples.items())),non_scratch_outputs_and_remaining_bss_identical=True,
                allowed_differences=['BC','alternate BC','retired four-byte coef_step scratch'],
                retired_scratch_unchanged_and_write_protected=True,every_table_entry_exact=True,
                unchanged_pages_and_all_other_writes_guarded=True,page_saving=179,unchanged_cache_tstates=976)


def observe(out):
    archive=ROOT/'audiobook-beeper/speex-port/rounds/34'
    packed=gzip.decompress((archive/'observed-lpc-coefficients.i16.gz').read_bytes())
    previous=json.loads((archive/'preparation-exchange-checks.json').read_text())['speech']
    baseline=json.loads((archive/'report.json').read_text());assert sha(packed)==previous['coefficient_bytes_sha256']
    mem=image(out/'pure-r34/player.ihx');assert sha(bytes(mem[k] for k in sorted(mem)))==baseline['binary_sha256']
    s=symbols(out/'pure-r35');arrays=[]
    def observer(name,m):
        address=s['_zx_lpc'];arrays.append(bytes(m.memory[address:address+20]))
    with redirect_stdout(io.StringIO()):
        r=native(out,'pure-r35-preparation-profile',out/'pure-r35',profile=('_prepare_coefficients',),entry_observer=observer)
    assert b''.join(arrays)==packed
    plain=json.loads((out/'pure-r35/report.json').read_text())
    assert r['total_tstates']==plain['total_tstates'] and r['binary_sha256']==plain['binary_sha256']
    assert (out/'pure-r35-preparation-profile/out-times.u64.gz').read_bytes()==(out/'pure-r35/out-times.u64.gz').read_bytes()
    old=None;pages=Counter();per_call=Counter();cumulative=[];count=0
    for data in arrays:
        changed=[i for i in range(10) if old is None or data[2*i:2*i+2]!=old[2*i:2*i+2]]
        pages.update(changed);per_call[len(changed)]+=1;old=data;count+=len(changed);cumulative.append(count)
    assert count==44692 and len(arrays)==4672
    saving=count*179;old_cost=previous['variants'][-1]['preparation_tstates'];new_cost=r['profile']['inclusive_tstates']['_prepare_coefficients']
    assert old_cost-new_cost==baseline['total_tstates']-r['total_tstates']==saving
    times=[list(struct.iter_unpack('<Q',gzip.decompress((out/v/'out-times.u64.gz').read_bytes()))) for v in VARIANTS]
    assert len(times[0])==len(times[1])==r['samples']
    for i,(before,after) in enumerate(zip(*times)):assert before[0]-after[0]==179*cumulative[i//40],i
    return dict(calls=len(arrays),coefficient_bytes_sha256=sha(packed),operand_archive='rounds/34/observed-lpc-coefficients.i16.gz',
                changed_pages=count,changed_pages_by_tap=dict(pages),changed_per_call=dict(sorted(per_call.items())),
                every_coefficient_unchanged=True,profile_preserves_every_out=True,baseline_image_identity_verified=True,
                every_out_saving_matches_cumulative_changed_pages=True,preparation_and_full_saving_reconcile=True,total_saving=saving,
                previous_preparation_tstates=old_cost,selected_preparation_tstates=new_cost,
                previous_full_tstates=baseline['total_tstates'],selected_full_tstates=r['total_tstates'],
                complete_pcm16_and_pcm8_samples=r['samples'],binary_sha256=r['binary_sha256'])


def main():
    out=ROOT/'build/speex-port'
    r=dict(source=source_contract(out),full_coefficient_domain=full_domain(out/'pure-r34',out/'pure-r35',saving=179))
    print('Coefficient domain:',r['full_coefficient_domain'],flush=True)
    r['addresses']=addresses(out/'pure-r35');r['masks']=masks(out)
    r['audits']={v:preparation_audit(out/v) for v in VARIANTS}
    assert r['audits']['pure-r34']['tstates']-r['audits']['pure-r35']['tstates']==1790
    r['speech']=observe(out);print('Full cost:',r['speech'],flush=True)
    r['all_pitches']=extra_stream(out/'pure-r35','pure-r35')
    (out/'pure-r35/next-step-checks.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
