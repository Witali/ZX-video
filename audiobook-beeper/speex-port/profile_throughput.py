"""Reconcile nested function costs against the exact complete uninstrumented run."""
import argparse
from collections import Counter
import json
import struct
from check_primitives import symbols
from verify import native,ROOT


WATCHES=('_zx_speex_decode','_zx_speex_filter','_zx_speex_lpc',
         '_prepare_coefficients','_coefficient_product','_split_nibbles',
         '_build_innovation','_mul_s8','mulq12','mulq14','_zx_mul_table',
         '_zx_mul8','cosine','_zx_clip')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--variant',default='pure-r16');a=p.parse_args()
    out=ROOT/'build/speex-port';binary=out/a.variant
    previous=json.loads((binary/'report.json').read_text())
    syms=symbols(binary);observed=None;changed_pages=Counter();changed_per_call=Counter()
    def observe(name,m):
        nonlocal observed
        if name!='_prepare_coefficients':return
        address=syms['_zx_lpc'];current=bytes(m.memory[address:address+20])
        changed=[tap for tap in range(10) if observed is None or
                 current[tap*2:tap*2+2]!=observed[tap*2:tap*2+2]]
        changed_pages.update(changed);changed_per_call[len(changed)]+=1;observed=current
    spans={'filter_feedback':('_filter_feedback_start','_filter_emit')} if '_filter_feedback_start' in syms else None
    # Separate output folder; breakpoints do not alter code or CPU timing.
    r=native(out,a.variant+'-profile',binary,profile=WATCHES,entry_observer=observe,blocks=spans)
    for k in ('total_tstates','binary_sha256','first_out_tstates','last_out_tstates','phases_tstates'):
        if k=='phases_tstates':
            assert all(r[k][name]==value for name,value in previous[k].items())
        else:assert r[k]==previous[k],(k,r[k],previous[k])
    assert (out/(a.variant+'-profile')/'out-times.u64.gz').read_bytes()==(binary/'out-times.u64.gz').read_bytes()
    counts=r['profile']['calls'];frames=r['samples']//160
    reference=(out/'reference.pcm16').read_bytes()
    zeros=sum(x==0 for x in struct.unpack('<'+'h'*(len(reference)//2),reference))
    helper_samples=0 if syms.get('_immutable_playback_code') else r['samples']-(zeros if spans else 0)
    for name,count in [('_zx_speex_decode',frames),('_zx_speex_filter',frames*4),
                       ('_zx_speex_lpc',frames*4),('_prepare_coefficients',frames*4),
                       ('_coefficient_product',helper_samples*10),('_split_nibbles',helper_samples)]:
        assert counts.get(name,0)==count,(name,counts.get(name,0),count)
    profile=r['profile'];assert all(t>=0 for t in profile['exclusive_tstates'].values())
    assert sum(profile['exclusive_tstates'].values())+profile['unprofiled_tstates']==r['total_tstates']
    profile['observed_coefficient_pages']=dict(total=sum(changed_pages.values()),by_tap=dict(changed_pages),
        changed_pages_per_call=dict(changed_per_call),first_use_forces_all_pages=True)
    if spans:
        block=profile['inline_blocks']['filter_feedback']
        assert block['calls']==r['samples']
        if a.variant=='pure-r24':
            assert block['duration_histogram']=={847:zeros,3603:r['samples']-zeros}
            assert sum(changed_pages.values())==44692
        if syms.get('_immutable_playback_code'):
            # No profiled callees occur inside the inline feedback block.
            # Split it out of the filter's exclusive cost without double-counting.
            separate=dict(profile['exclusive_tstates'])
            separate['_zx_speex_filter']-=block['total_tstates']
            separate['inline_filter_feedback']=block['total_tstates']
            assert all(t>=0 for t in separate.values())
            assert sum(separate.values())+profile['unprofiled_tstates']==r['total_tstates']
            profile['exclusive_with_inline_feedback_separated']=separate
    r.pop('out_intervals_histogram')
    r['profile']['every_saved_out_timestamp_unchanged']=True
    (out/(a.variant+'-profile')/'profile.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(profile,indent=2),flush=True)


if __name__=='__main__':main()
