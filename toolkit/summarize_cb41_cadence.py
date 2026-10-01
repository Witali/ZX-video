"""Authenticate and archive complete CB41 cadence runs, including failures."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
from profile_fap3 import summarize_fuse, FIELD


def sha(data): return hashlib.sha256(data).hexdigest()
def read(path): return json.loads(path.read_bytes())


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', type=Path, action='append', required=True)
    p.add_argument('--evidence', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    a.evidence.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parent
    old = json.loads(gzip.decompress((root/'cell_codebook_balanced_evidence/volume-1-metadata.json.gz').read_bytes()))
    artifacts, runs = [], []
    def archive(path, key):
        raw = path.read_bytes()
        target = a.evidence/(key+('.trd' if path.suffix=='.trd' else '.gz'))
        packed = raw if path.suffix=='.trd' else gzip.compress(raw,mtime=0)
        target.write_bytes(packed)
        artifacts.append(dict(file=target.name,raw_bytes=len(raw),raw_sha256=sha(raw),
                              archive_bytes=len(packed),archive_sha256=sha(packed)))
    for run in a.run:
        manifest = read(run/'conversion.json')
        assert manifest['complete']
        disks = []
        for record in manifest['volumes']:
            image = run/record['file']; m = read(run/record['metadata'])
            folder = run/'work'/image.stem
            timing = read(folder/'timing.json'); screens = read(folder/'screens.json')
            identity = sha(image.read_bytes())
            assert identity == record['sha256'] == m['trd_sha256'] == timing['trd_sha256'] == screens['trd_sha256']
            assert timing['complete'] and screens['complete'] and screens['full_screens_exact']
            assert m['cell_codebook']['native'] == old['cell_codebook']['native']
            assert m['cell_codebook']['packet_listing'] == old['cell_codebook']['packet_listing']
            assert m['video_cadence']['previous_tstates'] == m['video_cadence']['tstates'] == 10
            assert m['video_cadence']['delta_tstates'] == 0
            assert timing['ay_ticks'] == m['frames']*m['frame_fields']
            for name,field in (('timing.trace.txt','trace_sha256'),('timing.debugger.txt','debugger_script_sha256')):
                assert sha((folder/name).read_bytes()) == timing[field]
            for capture in screens['passes']:
                prefix = folder/'captures'/f'bytes-{capture["start"]}-{capture["end"]}'
                assert sha(prefix.with_suffix('.trace.txt').read_bytes()) == capture['trace_sha256']
                assert sha(prefix.with_suffix('.debugger.txt').read_bytes()) == capture['debugger_sha256']
            checked = summarize_fuse(timing)
            pubs = timing['publications']
            gaps = [b['field']-a['field'] for a,b in zip(pubs,pubs[1:])] if pubs and 'field' in pubs[0] else []
            disks.append(dict(file=image.name,sha256=identity,frames=m['frames'],ay_ticks=timing['ay_ticks'],
                fields_per_frame=m['frame_fields'],used_sectors=m['used_sectors'],free_sectors=m['free_sectors'],
                full_screens_exact=True,compared_screen_bytes=screens['compared_bytes'],
                actual_phase_tstates=[min(timing['actual_phase_tstates']),max(timing['actual_phase_tstates'])],
                normalized_fps=(len(pubs)-1)*FIELD*50/(pubs[-1]['tstate']-pubs[0]['tstate']) if len(pubs)>1 else None,
                timing=checked,native_instruction_delta_tstates=0))
        checked = read(run/'timing.json')
        assert checked['complete'] and all(d['cold']['dirty_ram_boot_exact'] for d in checked['disks'])
        if len(disks)>1:
            swaps = read(run/'disk-swaps.json')
            assert len(swaps)==len(disks)-1 and all(s['bootstrap_ram_exact'] for s in swaps)
        for path in sorted(run.rglob('*')):
            if not path.is_file(): continue
            relative = path.relative_to(run)
            if any(part in ('zx0','lzsa') for part in relative.parts): continue
            if path.suffix not in ('.json','.txt','.raw','.stream','.npz','.ayh1','.trd'): continue
            archive(path, run.name+'-'+str(relative).replace('\\','-').replace('/','-'))
        runs.append(dict(name=run.name,frames=manifest['frames'],ay_ticks=manifest['ay_ticks'],
            video_fps=manifest['video_fps'],disks=disks,
            all_nominal_deadlines_met=all(d['timing']['nominal_deadlines_met'] for d in disks),
            all_screens_exact=True,independent_cold_boots_exact=True))
    result = dict(complete=True,release=False,runs=runs,artifacts=artifacts,
        all_nominal_deadlines_met=all(r['all_nominal_deadlines_met'] for r in runs),
        frames=sum(r['frames'] for r in runs),ay_ticks=sum(r['ay_ticks'] for r in runs),
        hot_path='LD DE,6 becomes LD DE,5: 10 -> 10 T; no other runtime instruction changes',
        source_sha256_lf={n:sha((root/n).read_bytes().replace(b'\r\n',b'\n')) for n in
            ('video_cadence.py','cell_codebook_player.py','convert_cb41.py','convert_video.py',
             'measure_fap3_fuse.py','profile_fap3.py','summarize_cb41_cadence.py')})
    a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('frames','ay_ticks','all_nominal_deadlines_met')}),flush=True)


if __name__ == '__main__': main()
