"""Measure zero-path opportunities before adding any runtime branches."""
import argparse
from collections import Counter
import json
from check_primitives import symbols
from check_s8_combined import expected_cost
from verify import native,ROOT


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--variant',default='pure-r20')
    a=p.parse_args();out=ROOT/'build/speex-port';folder=out/a.variant;s=symbols(folder)
    counts=Counter();gains=Counter();word_zero_old_t=0
    def observe(name,m):
        nonlocal word_zero_old_t
        if name=='_split_nibbles':
            counts['feedback_samples']+=1
            counts['zero_feedback']+=m.hl==0
        else:
            multiplier=m.a if m.a<128 else m.a-256
            ret=int.from_bytes(m.memory[m.sp:m.sp+2],'little')
            is_energy=s['mulq12']<=ret<s['_build_innovation']
            prefix='energy' if is_energy else 'pitch'
            counts[prefix+'_products']+=1
            counts[prefix+'_zero_gain']+=multiplier==0
            counts[prefix+'_zero_word']+=m.de==0
            if not is_energy:gains[str(multiplier)]+=1
            if multiplier:
                counts['nonzero_multiplier_calls']+=1
                if m.de==0:
                    counts['nonzero_multiplier_zero_word']+=1
                    word_zero_old_t+=expected_cost(multiplier,0)
    r=native(out,a.variant+'-zeros',folder,profile=('_split_nibbles','_mul_s8'),entry_observer=observe)
    baseline=json.loads((folder/'report.json').read_text())
    for k in ('total_tstates','binary_sha256','first_out_tstates','last_out_tstates'):
        assert r[k]==baseline[k]
    assert (out/(a.variant+'-zeros')/'out-times.u64.gz').read_bytes()==(folder/'out-times.u64.gz').read_bytes()
    assert counts['feedback_samples']==r['samples']
    assert counts['energy_products']+counts['pitch_products']==r['profile']['calls']['_mul_s8']
    n=r['samples'];z=counts['zero_feedback'];w=counts['nonzero_multiplier_zero_word']
    forecast=dict(
        feedback_copy_net_saving_tstates=3289*z-18*n,
        word_zero_net_saving_tstates=word_zero_old_t-59*w-24*(counts['nonzero_multiplier_calls']-w),
        pitch_zero_lower_bound_saving_tstates=303*counts['pitch_zero_gain']-27*3*n,
        pitch_zero_upper_bound_saving_tstates=322*counts['pitch_zero_gain']+77*(3*n-counts['pitch_products'])-27*3*n,
        estimates_only=True)
    result=dict(variant=a.variant,samples=n,counts=dict(counts),pitch_gain_histogram=dict(gains),
                forecasts=forecast,total_tstates=r['total_tstates'],binary_sha256=r['binary_sha256'],
                every_pcm16_pcm8_and_out_timestamp_unchanged=True)
    (out/(a.variant+'-zeros')/'zero-profile.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()
