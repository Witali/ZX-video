"""Reconcile nested function costs against the exact complete uninstrumented run."""
import argparse
import json
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
    # Separate output folder; breakpoints do not alter code or CPU timing.
    r=native(out,a.variant+'-profile',binary,profile=WATCHES)
    for k in ('total_tstates','binary_sha256','first_out_tstates','last_out_tstates','phases_tstates'):
        if k=='phases_tstates':
            assert all(r[k][name]==value for name,value in previous[k].items())
        else:assert r[k]==previous[k],(k,r[k],previous[k])
    assert (out/(a.variant+'-profile')/'out-times.u64.gz').read_bytes()==(binary/'out-times.u64.gz').read_bytes()
    counts=r['profile']['calls'];frames=r['samples']//160
    for name,count in [('_zx_speex_decode',frames),('_zx_speex_filter',frames*4),
                       ('_zx_speex_lpc',frames*4),('_prepare_coefficients',frames*4),
                       ('_coefficient_product',r['samples']*10),('_split_nibbles',r['samples'])]:
        assert counts[name]==count,(name,counts[name],count)
    profile=r['profile'];assert all(t>=0 for t in profile['exclusive_tstates'].values())
    assert sum(profile['exclusive_tstates'].values())+profile['unprofiled_tstates']==r['total_tstates']
    r.pop('out_intervals_histogram')
    r['profile']['every_saved_out_timestamp_unchanged']=True
    (out/(a.variant+'-profile')/'profile.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(profile,indent=2),flush=True)


if __name__=='__main__':main()
