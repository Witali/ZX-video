"""Run the documented cold-start scenarios and summarize observed windows."""
from __future__ import annotations
import argparse
from collections import Counter
import concurrent.futures
import json
from pathlib import Path
import subprocess
import sys


def aggregate(windows):
    fields=['instructions','base_t','elapsed_t','idle_m1','idle_t','halts','repeated_block_continuations']
    out={k:0 for k in fields}
    out.update(duration_t=0,unattributed_t=0)
    histogram=Counter()
    groups={k:{f:0 for f in fields} for k in ['ram','rom','trdos']}
    for window in windows:
        out['duration_t'] += window['end_t']-window['start_t']
        out['unattributed_t'] += window['unattributed_t']
        for name,g in window['groups'].items():
            for key in fields:
                out[key] += g[key]
                groups[name][key] += g[key]
            histogram.update({int(k):v for k,v in g['histogram'].items()})
    assert sum(histogram.values())==out['instructions']
    assert all(t<255 for t in histogram), 'Histogram overflow must be investigated'
    assert sum(t*n for t,n in histogram.items())==out['base_t']
    assert out['duration_t']==out['elapsed_t']+out['idle_t']+out['unattributed_t']
    n=out['instructions']
    out['mean_base_t']=out['base_t']/n
    out['mean_elapsed_active_t']=out['elapsed_t']/n
    out['mean_collapsing_block_repeats']=out['base_t']/(n-out['repeated_block_continuations'])
    out['mean_including_idle_and_interrupt_entry']=out['duration_t']/n
    out['idle_percent']=100*out['idle_t']/out['duration_t']
    out['histogram']={str(t):histogram[t] for t in sorted(histogram)}
    out['groups']=groups
    return out


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--work',type=Path,required=True)
    ap.add_argument('--summarize-only',action='store_true')
    args=ap.parse_args();work=args.work.resolve()
    here=Path(__file__).resolve().parent
    cases=json.loads((here/'cases.json').read_text())
    manifest={x['name']:x for x in json.loads((work/'disks/manifest.json').read_text())}
    def run(case):
        name=case['name'];out=work/'final'/name;out.mkdir(parents=True,exist_ok=True)
        keys=out/'keys.json';keys.write_text(json.dumps(case['keys']))
        if not args.summarize_only:
            with (out/'log.txt').open('w') as log:
                subprocess.run([sys.executable,str(here/'run.py'),
                    '--core',str(work/'fuse-libretro-master/fuse_libretro.so'),
                    '--system',str(work/'system'),'--disk',str(work/'disks'/manifest[name]['files'][0]['file']),
                    '--out',str(out),'--frames',str(case['sample_frames'][1]),
                    '--window','500','--keys',str(keys)],check=True,stdout=log,stderr=subprocess.STDOUT)
        raw=json.loads((out/'raw.json').read_text())
        assert raw['machine']=='pentagon' and raw['frame_tstates']==71680
        lo,hi=case['sample_frames']
        selected=[w for w in raw['windows'] if lo<w['frontend_frame_end']<=hi]
        assert len(selected)==3
        result={**case,'source':manifest[name], 'core_sha256':raw['core_sha256'],
                'sample':aggregate(selected),'cold_first_500_frames':aggregate(raw['windows'][:1]),
                'whole_run':aggregate(raw['windows'])}
        result['sample']['seconds']=result['sample']['duration_t']/3500000
        print(name,round(result['sample']['mean_base_t'],6),flush=True)
        return result,selected
    with concurrent.futures.ThreadPoolExecutor(4) as ex:
        values=list(ex.map(run,cases))
    report={'machine':'Pentagon 128K + Beta Disk, Fuse libretro (Fuse 1.6.0 core)',
            'clock_hz':3500000,'cases':[v[0] for v in values],
            'pooled':aggregate([w for _,rows in values for w in rows])}
    report['equal_program_mean']=sum(x['sample']['mean_base_t'] for x,_ in values)/len(values)
    (work/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print('pooled',report['pooled']['mean_base_t'],'equal',report['equal_program_mean'])


if __name__=='__main__':main()
