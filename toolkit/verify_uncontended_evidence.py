"""Check saved hashes and complete coverage after Git's line-ending conversion."""
import gzip
import hashlib
import json
from pathlib import Path


def main():
    root=Path(__file__).parent
    def sha(data):return hashlib.sha256(data).hexdigest()
    def read(name):return json.loads((root/name).read_bytes())
    summary=read('uncontended_frame_summary.json')
    for name,key in (('uncontended_frame_cpu.json','cpu_report_sha256'),
                     ('uncontended_frame_machine.json','machine_report_sha256')):
        if sha((root/name).read_bytes())!=summary[key]:raise AssertionError(name)
    cpu=read('uncontended_frame_cpu.json');machine=read('uncontended_frame_machine.json')
    if not cpu['complete'] or cpu['checked_frames']!=4221 or not machine['complete']:raise AssertionError('partial evidence')
    if sha((root/'uncontended_frame_machine.trace.txt').read_bytes())!=machine['trace_sha256']:raise AssertionError('machine trace')
    for row in summary['evidence']:
        blob=(root/'uncontended_frame_evidence'/row['file']).read_bytes()
        if sha(blob)!=row['sha256']:raise AssertionError(row['file'])
        if 'uncompressed_sha256' in row and sha(gzip.decompress(blob))!=row['uncompressed_sha256']:
            raise AssertionError(('compressed evidence',row['file']))
    for v in cpu['volumes']:
        if len(v['frames'])!=v['end']-v['start']:raise AssertionError('partial volume')
        if [f['frame'] for f in v['frames']]!=list(range(v['start'],v['end'])):raise AssertionError('frame gap')
        if any(f['tstates']!=f['baseline_tstates'] or f['delta_tstates'] for f in v['frames']):raise AssertionError('CPU delta')
    for v in summary['volumes']:
        r=read(f"uncontended_frame_evidence/part{v['part']:02}.json")
        if not r['complete'] or not r['trace_nonce_exact'] or r['errors'] or r['frames']!=v['relocated']['frames']:
            raise AssertionError('Fuse coverage')
        for suffix,key in (('trace.txt','trace_sha256'),('debugger.txt','debugger_script_sha256')):
            blob=gzip.decompress((root/f"uncontended_frame_evidence/part{v['part']:02}.{suffix}.gz").read_bytes())
            if sha(blob)!=r[key]:raise AssertionError('Fuse source trace')
    print('Verified: 4221 CPU frames, three complete Fuse runs, machine audit and all evidence hashes.')


if __name__=='__main__':main()
