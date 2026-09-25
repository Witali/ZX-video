"""Verify saved per-frame CPU deltas against the complete relocated baseline."""
import argparse
import json
from pathlib import Path
from build_fap3_trd import sha


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--report',type=Path,default=Path('toolkit/inline_huffman_patches_cpu.json'))
    p.add_argument('--baseline',type=Path,default=Path('toolkit/combined_uncontended_cpu.json'))
    args=p.parse_args();r=json.loads(args.report.read_bytes());old=json.loads(args.baseline.read_bytes())
    if (not r['complete'] or not old['complete'] or r['checked_frames']!=4221
        or r['states_sha256']!=old['states_sha256'] or r['model_sha256']!=sha(args.baseline.read_bytes())
        or r['source_sha256']!=sha(Path(__file__).with_name('benchmark_inline_huffman_patches.py').read_bytes())
        or len(r['volumes'])!=3 or not r['full_compact_and_both_native_exact']):
        raise ValueError('different or incomplete verification input')
    fields=('baseline_tstates','tstates','delta_tstates','entries','short','long')
    total={key:0 for key in fields};slower=0
    for v,b in zip(r['volumes'],old['volumes']):
        if (any(v[k]!=b[k] for k in ('part','start','end','raw_sha256','checked_frames'))
            or len(v['frames'])!=v['end']-v['start']):raise ValueError('different volume')
        code=v['inline_patches'];blob=bytes.fromhex(code['code_hex'])
        if (sha(blob)!=code['code_sha256'] or len(blob)!=code['code_bytes']
            or code['origin']<0xc000+code['table_body_bytes'] or code['end']!=code['origin']+len(blob)
            or code['end']>0xf000 or code['free_bytes_before_shift']!=0xf000-code['end']
            or code['extra_stream_bytes'] or code['extra_stack_bytes']
            or len(code['symbol_entries'])!=16 or len(code['long_stubs'])!=16):
            raise ValueError('invalid generated code or RAM placement')
        for f,prior in zip(v['frames'],b['frames']):
            difference=10*f['entries']-24*f['short']+8*f['long']
            if (f['frame']!=prior['frame'] or f['baseline_tstates']!=prior['tstates']
                or f['delta_tstates']!=difference or f['tstates']-f['baseline_tstates']!=difference):
                raise ValueError('frame timing formula or reference differs')
            slower+=difference>0
        for key in fields:
            actual=sum(f[key] for f in v['frames'])
            if v[key]!=actual:raise ValueError('volume aggregate differs')
            total[key]+=actual
    if any(r[key]!=value for key,value in total.items()) or r['slower_frames']!=slower:
        raise ValueError('full aggregate differs')
    print(json.dumps(dict(complete=True,frames=r['checked_frames'],**total,
        slower_frames=slower,stage_cpu_percent=100*r['delta_tstates']/r['baseline_tstates'],
        fuse_verified=False,bootstrap_capacity_verified=False,release=False),indent=2))


if __name__=='__main__':main()
