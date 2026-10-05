"""Verify cancelling EXX pairs, every coefficient and complete preparation costs."""
from collections import Counter
from contextlib import redirect_stdout
import gzip
import io
import json
import random
import struct
from check_coefficient_steps import full_domain,guarded
from check_primitives import symbols,call
from check_unpaced import preparation_audit
from check_constant_pitch import extra_stream
from verify import ROOT,native,sha

VARIANTS=('pure-r33','pure-r34')
REGISTERS=('af','bc','de','hl','alt_af','alt_bc','alt_de','alt_hl','ix','iy','sp')


def source_identity(out):
    sources=[(out/v/'decoder.s').read_text() for v in VARIANTS]
    def split(s):
        begin=s.index('coef_changed:\n');end=s.index('coef_next:\n',begin)
        return s[:begin],s[begin:end],s[end:]
    old,new=map(split,sources)
    assert old[0]==new[0] and old[2]==new[2]
    def instructions(s):return '\n'.join(x.split(';')[0].strip() for x in s.splitlines() if x.split(';')[0].strip())+'\n'
    a,b=map(instructions,(old[1],new[1]))
    assert a.count('exx\nexx\n')==64 and 'exx\nexx\n' not in b
    assert a.replace('exx\nexx\n','')==b
    assert (out/VARIANTS[0]/'filter.s').read_text()==(out/VARIANTS[1]/'filter.s').read_text()
    return dict(removed_identity_pairs=64,exx_tstates=4,page_saving=512,
                all_other_instructions_labels_and_filter_unchanged=True,code_byte_saving=128)


def masks(out):
    variants=[guarded(out/v) for v in VARIANTS];rng=random.Random(3434)
    coefficients=[0]*10;factors=[(n-16 if p==3 and n>=8 else n)<<(p*4) for p in range(4) for n in range(16)]
    hist=Counter();examples={}
    for mask in range(1024):
        for tap in range(10):
            if mask>>tap&1:coefficients[tap]=((coefficients[tap]+rng.randrange(1,65536)+32768)&65535)-32768
        data=struct.pack('<10h',*coefficients);snapshots=[];costs=[]
        seed={k:rng.randrange(65536) for k in REGISTERS if k!='sp'}
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
            snapshots.append(([getattr(m,k) for k in REGISTERS],bytes(m.memory[s['s__DATA']:s['s__DATA']+s['l__DATA']])))
        assert snapshots[0]==snapshots[1],mask
        changed=mask.bit_count();assert costs[0]-costs[1]==512*changed,(mask,costs)
        hist[changed]+=1
        if changed not in examples:examples[changed]=costs
        # An immediate repeat must be a cache hit, without any table write.
        for m,s in variants:
            m.mark_addrs(0x7200,2560,m.WRITE_MARK)
            assert call(m,s['_prepare_coefficients'],budget=1000000)==976
            assert bytes(m.memory[0x7200:0x7c00])==expected
    return dict(masks=1024,cached_repeats_per_variant=1024,changed_pages_histogram=dict(sorted(hist.items())),
                example_cost_pairs=dict(sorted(examples.items())),all_registers_including_flags_and_bss_identical=True,
                every_table_entry_exact=True,unchanged_pages_and_all_other_writes_guarded=True,
                page_saving=512,unchanged_cache_tstates=976)


def observe(out):
    arrays=[];reports=[];stats=[];rows=[]
    for v in VARIANTS:
        s=symbols(out/v);coefficients=[]
        def observer(name,m):
            address=s['_zx_lpc'];coefficients.append(bytes(m.memory[address:address+20]))
        with redirect_stdout(io.StringIO()):
            r=native(out,v+'-preparation-profile',out/v,profile=('_prepare_coefficients',),entry_observer=observer)
        plain=json.loads((out/v/'report.json').read_text())
        assert r['total_tstates']==plain['total_tstates'] and r['binary_sha256']==plain['binary_sha256']
        assert (out/(v+'-preparation-profile')/'out-times.u64.gz').read_bytes()==(out/v/'out-times.u64.gz').read_bytes()
        previous=None;pages=Counter();per_call=Counter()
        for data in coefficients:
            changed=[i for i in range(10) if previous is None or data[2*i:2*i+2]!=previous[2*i:2*i+2]]
            pages.update(changed);per_call[len(changed)]+=1;previous=data
        stats.append(dict(total=sum(pages.values()),by_tap=dict(pages),per_call=dict(sorted(per_call.items()))))
        arrays.append(coefficients);reports.append(r)
        rows.append(dict(variant=v,preparation_tstates=r['profile']['inclusive_tstates']['_prepare_coefficients'],
                         full_tstates=r['total_tstates'],binary_sha256=r['binary_sha256']))
    assert arrays[0]==arrays[1] and stats[0]==stats[1]
    assert len(arrays[0])==4672 and stats[0]['total']==44692
    saving=stats[0]['total']*512
    assert rows[0]['preparation_tstates']-rows[1]['preparation_tstates']==saving
    assert rows[0]['full_tstates']-rows[1]['full_tstates']==saving
    packed=b''.join(arrays[1]);(out/'pure-r34/observed-lpc-coefficients.i16.gz').write_bytes(gzip.compress(packed,mtime=0))
    return dict(calls=len(arrays[1]),coefficient_bytes_sha256=sha(packed),observed_changed_pages=stats[1],
                every_coefficient_unchanged=True,profile_preserves_every_out_in_both_variants=True,
                preparation_and_full_saving_reconcile=True,total_saving=saving,variants=rows,
                complete_pcm16_and_pcm8_samples=reports[1]['samples'])


def main():
    out=ROOT/'build/speex-port'
    r=dict(source=source_identity(out),full_coefficient_domain=full_domain(out/'pure-r33',out/'pure-r34',saving=512))
    print('All signed16 coefficient pages passed:',r['full_coefficient_domain'],flush=True)
    r['masks']=masks(out);r['audits']={v:preparation_audit(out/v) for v in VARIANTS}
    assert r['audits']['pure-r33']['tstates']-r['audits']['pure-r34']['tstates']==5120
    r['speech']=observe(out);print('Full preparation cost:',r['speech'],flush=True)
    r['all_pitches']=extra_stream(out/'pure-r34','pure-r34')
    (out/'pure-r34/preparation-exchange-checks.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
