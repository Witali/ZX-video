"""Verify complete compiled-mask evidence and hashes, including after checkout."""
import gzip
import json
from pathlib import Path
from build_fap3_trd import sha
from summarize_uncontended_frame import metrics


def main():
    root=Path(__file__).parent
    def read(name):return json.loads((root/name).read_bytes())
    summary=read('compiled_masks_summary.json');cpu=read('compiled_masks_cpu.json')
    if sha((root/'compiled_masks_cpu.json').read_bytes())!=summary['cpu_report_sha256']:
        raise AssertionError('CPU report hash')
    if not summary['complete'] or not cpu['complete'] or cpu['checked_frames']!=4221:
        raise AssertionError('partial evidence')
    for row in summary['evidence']:
        blob=(root/'compiled_masks_evidence'/row['file']).read_bytes()
        if sha(blob)!=row['sha256']:raise AssertionError(row['file'])
        if 'uncompressed_sha256' in row and sha(gzip.decompress(blob))!=row['uncompressed_sha256']:
            raise AssertionError(('compressed evidence',row['file']))
    next_frame=0
    for c,v in zip(cpu['volumes'],summary['volumes'],strict=True):
        if c['start']!=next_frame or [f['frame'] for f in c['frames']]!=list(range(c['start'],c['end'])):
            raise AssertionError('frame gap')
        next_frame=c['end']
        if c['checked_frames']!=len(c['frames']):raise AssertionError('CPU count')
        for key in ('baseline_tstates','compiled_tstates','delta_tstates'):
            if c[key]!=sum(f[key] for f in c['frames']):raise AssertionError('CPU sum')
        if any(f['compiled_tstates']-f['baseline_tstates']!=f['delta_tstates'] or f['delta_tstates']>0 for f in c['frames']):
            raise AssertionError('CPU delta')
        r=read(f"compiled_masks_evidence/part{v['part']:02}.json")
        bpath=root/f"slot_queue_evidence/part{v['part']:02}.json"
        if sha(bpath.read_bytes())!=v['baseline_report_sha256']:raise AssertionError('baseline hash')
        if (not r['complete'] or not r['trace_nonce_exact'] or r['errors'] or not r['compiled_masks']
                or not r['ay_records_exact'] or r['frames']!=c['checked_frames']
                or metrics(r)!=v['compiled'] or metrics(json.loads(bpath.read_bytes()))!=v['baseline']):
            raise AssertionError('Fuse coverage or metrics')
        for suffix,key in (('trace.txt','trace_sha256'),('debugger.txt','debugger_script_sha256')):
            blob=gzip.decompress((root/f"compiled_masks_evidence/part{v['part']:02}.{suffix}.gz").read_bytes())
            if sha(blob)!=r[key]:raise AssertionError('Fuse source trace')
    if next_frame!=4221:raise AssertionError('missing ending')
    for key in ('baseline_tstates','compiled_tstates','delta_tstates'):
        if cpu[key]!=sum(v[key] for v in cpu['volumes']):raise AssertionError('CPU total')
    print('Verified: 4221 old/new metadata frames, three complete Fuse runs and all evidence hashes.')


if __name__=='__main__':main()
