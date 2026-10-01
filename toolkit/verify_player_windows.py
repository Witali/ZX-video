"""Complete native/Fuse window checks and archive evidence for player revisions."""
import argparse
import gzip
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

from build_fap3_trd import sha
from cell_codebook_player import packet_code
import cell_codebook_z80
from convert_video import write_json
from profile_fap3 import summarize_fuse


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=Path,action='append',required=True)
    p.add_argument('--failed-build',type=Path,action='append',default=[])
    p.add_argument('--profile',type=Path,help='Directory containing the additional complete pipeline trace and analysis')
    p.add_argument('--mask-comparison',type=Path,help='Exact mask-path stream and per-frame CPU comparison')
    for name in ('fuse','tests','evidence','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();root=Path(__file__).resolve().parent
    a.evidence.mkdir(parents=True,exist_ok=True);artifacts=[];runs=[];failed=[]
    def archive(path,key):
        raw=path.read_bytes();image=path.suffix=='.trd';packed=raw if image else gzip.compress(raw,mtime=0)
        target=a.evidence/(key if image else key+'.gz');target.write_bytes(packed)
        artifacts.append(dict(file=target.name,raw_sha256=sha(raw),archive_sha256=sha(packed),
            raw_bytes=len(raw),archive_bytes=len(packed)))
    for folder in a.failed_build:
        result=json.loads((folder/'conversion.json').read_bytes());assert not result['complete']
        failed.append(dict(build=folder.name,failure=result['failure']))
        for path in folder.glob('*.json'):archive(path,folder.name+'-'+path.name)
    for folder in a.build:
        records=json.loads((folder/'volumes.json').read_bytes());assert len(records)==1
        record=records[0];image=folder/record['file'];meta_path=folder/record['metadata']
        m=json.loads(meta_path.read_bytes());work=folder/'work'/image.stem;c=m['cell_codebook']
        front=c['wire']=='CB44';dynamic=c.get('dynamic_rows',{}).get('enabled',False)
        assert sha(image.read_bytes())==m['trd_sha256']==record['sha256']
        fast_masks=c['native'].get('fast_masks',False)
        _,labels,native=cell_codebook_z80.build(dictionary=True,front_reuse=front,fast_masks=fast_masks)
        assert labels==c['native_labels'] and native['instruction_listing']==c['native']['instruction_listing']
        _,_,listing=packet_code(m,labels,c['screen_base'],dynamic_rows=dynamic,front_reuse=front)
        assert listing==c['packet_listing']
        with np.load(folder/record['states'],allow_pickle=False) as saved:states=saved['states']
        assert sha(states.tobytes())==m['states_sha256']
        cpu=json.loads((work/'cpu.json').read_bytes());assert cpu['complete'] and cpu['all_native_screens_exact']
        cold=json.loads((folder/'timing.json').read_bytes())['disks'][0]['cold']
        common=['--fuse',str(a.fuse.resolve()),'--trd',str(image.resolve()),'--metadata',str(meta_path.resolve()),
            '--states',str((folder/record['states']).resolve()),'--timeout','600']
        timing=work/'timing.json';screens=work/'screens.json'
        if not timing.exists():
            subprocess.run([sys.executable,str(root/'measure_fap3_fuse.py'),*common,
                '--raw',str((folder/'work/stream.raw').resolve()),'--output',str(timing.resolve())],check=True)
        measured=json.loads(timing.read_bytes());assert measured['complete'] and measured['ay_records_exact']
        if not screens.exists():
            subprocess.run([sys.executable,str(root/'capture_cell_codebook_full.py'),*common,
                '--timing',str(timing.resolve()),'--work',str((work/'captures').resolve()),'--output',str(screens.resolve())],check=True)
        visual=json.loads(screens.read_bytes());assert visual['complete'] and visual['full_screens_exact']
        assert visual['trd_sha256']==measured['trd_sha256']==m['trd_sha256']
        runs.append(dict(build=folder.name,wire=c['wire'],fast_masks=fast_masks,start=m['frame_start'],frames=m['frames'],cold=cold,
            trd_sha256=m['trd_sha256'],used_sectors=m['used_sectors'],video_bytes=m['video_bytes'],
            complete_native_screens=True,new_instruction_stages=cpu['new_instruction_stages'],
            full_fuse_screens_exact=True,compared_bytes=visual['compared_bytes'],timing=summarize_fuse(measured)))
        for path in sorted(folder.rglob('*')):
            if not path.is_file() or any(part in ('lzsa','zx0') for part in path.relative_to(folder).parts):continue
            if path.suffix in ('.json','.trd','.npz','.raw','.stream','.txt','.ayh1'):
                archive(path,folder.name+'-'+path.relative_to(folder).as_posix().replace('/','-'))
    assert a.tests.read_text().strip().endswith('OK');archive(a.tests,'tests.txt')
    profile=None
    if a.profile:
        profile=json.loads((a.profile/'profile.json').read_bytes())
        assert profile['complete'] and profile['trd_sha256'] in [r['trd_sha256'] for r in runs]
        for path in sorted(a.profile.iterdir()):
            if path.is_file():archive(path,'profile-'+path.name)
    mask_comparison=None
    if a.mask_comparison:
        mask_comparison=json.loads(a.mask_comparison.read_bytes())
        assert mask_comparison['complete'] and mask_comparison['trd_sha256_after'] in [r['trd_sha256'] for r in runs]
        archive(a.mask_comparison,'mask-comparison.json')
    from test_front_cell_z80 import FrontCellZ80Tests
    cases=FrontCellZ80Tests();cases.test_modes_both_screens_and_counted_tstates()
    report=dict(complete=True,release=False,whole_movie_timing_verified=False,scope=__doc__,runs=runs,
        failed_builds=failed,cycle_cases=cases.case_results,profile=profile,mask_comparison=mask_comparison,
        cycles=dict(no_refill_before=dict(book=268,literal=304),no_refill_after=dict(book=281,literal=317,front=299),
            formula='-16 + 13*N + 16*(ceil(N/4)-ceil(N/8)) + 18*(front_from_book-front_from_literal)',
            scope='CB44 mode reader against CB41, both with fast_masks=False; IRQ, ULA, packet copy, audio and disk excluded',
            fast_mask_formula='3168-119*zero_bitmap_groups-139*zero_attribute_groups-empty_attribute_carries-22*changed_attributes'),
        artifacts=artifacts,source_sha256_lf={name:sha((root/name).read_bytes().replace(b'\r\n',b'\n')) for name in
            ('cell_codebook_z80.py','cell_codebook_player.py','front_cell_reuse.py','convert_cb41.py',
             'build_cb41_cadence_movie.py','convert_video.py','verify_cell_codebook_z80.py',
             'test_front_cell_z80.py','verify_player_windows.py','measure_fap3_fuse.py','profile_cell_delivery.py',
             'test_fast_cell_masks.py','compare_fast_cell_masks.py')})
    write_json(a.output,report)
    print(json.dumps(dict(complete=True,runs=[dict(build=r['build'],frames=r['frames'],
        late=r['timing']['missed_nominal_frames'],fallback=r['timing']['fallback_one_field_met']) for r in runs])))


if __name__=='__main__':main()
