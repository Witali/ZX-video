"""Verify two-bank AY movie windows and archive exact inputs, failures and traces."""
import argparse
import gzip
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

from build_fap3_trd import sha
from build_long_video_trd import AyFrame
from convert_video import write_json
from measure_cell_codebook_movie import audio_size
from profile_fap3 import summarize_fuse


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('fixture','window','prepared','fuse','tests','evidence','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--failed-build',type=Path,action='append',default=[])
    args=p.parse_args();root=Path(__file__).resolve().parent
    args.evidence.mkdir(parents=True,exist_ok=True)
    artifacts=[];runs=[];failures=[]
    def archive(path,key):
        raw=path.read_bytes();target=args.evidence/(key if path.suffix=='.trd' else key+'.gz')
        target.write_bytes(raw if path.suffix=='.trd' else gzip.compress(raw,mtime=0))
        artifacts.append(dict(file=target.name,raw_sha256=sha(raw),archive_sha256=sha(target.read_bytes()),
            raw_bytes=len(raw),archive_bytes=target.stat().st_size))
    for folder in args.failed_build:
        failed=json.loads((folder/'conversion.json').read_bytes())
        assert not failed['complete'] and failed['failure']
        failures.append(dict(folder=folder.name,failure=failed['failure']))
        for path in sorted(folder.glob('*')):
            if path.is_file() and path.suffix in ('.json','.trd'):
                archive(path,'failed-'+folder.name+'-'+path.name)
    for name,folder in (('fixture',args.fixture),('window',args.window)):
        volumes=json.loads((folder/'volumes.json').read_bytes());assert len(volumes)==1
        record=volumes[0];image=folder/record['file'];meta_path=folder/record['metadata']
        m=json.loads(meta_path.read_bytes());work=folder/'work'/image.stem
        assert sha(image.read_bytes())==m['trd_sha256']==record['sha256']
        compiled=m['resident_audio']['compiled'];assert compiled['wire']=='AYB1'
        assert compiled['banks']==[4,6] and sum(compiled['segment_ticks'])==m['frames']*5
        assert m['cell_codebook']['memory']['audio']==[4,6]
        assert m['resident_audio']['segment_hooks']['labels']['end']<=0x7900
        with np.load(folder/record['states'],allow_pickle=False) as cache:states=cache['states']
        assert sha(states.tobytes())==m['states_sha256']
        cpu=json.loads((work/'cpu.json').read_bytes());assert cpu['complete'] and cpu['all_native_screens_exact']
        cold=json.loads((folder/'timing.json').read_bytes())['disks'][0]['cold']
        rows=json.loads((work/'dynamic-rows.json').read_bytes())
        common=['--fuse',str(args.fuse.resolve()),'--trd',str(image.resolve()),
            '--metadata',str(meta_path.resolve()),'--states',str((folder/record['states']).resolve()),'--timeout','600']
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
        runs.append(dict(name=name,frames=m['frames'],trd_sha256=m['trd_sha256'],
            segment_ticks=compiled['segment_ticks'],bank_bytes=[s['image_bytes'] for s in compiled['segments']],
            row_updates=rows['updates'],cold=cold,full_screens_exact=True,compared_bytes=visual['compared_bytes'],
            cpu_screens_exact=True,timing=summarize_fuse(measured)))
        for path in sorted(folder.rglob('*')):
            if not path.is_file() or any(part in ('lzsa','zx0') for part in path.relative_to(folder).parts):continue
            if path.suffix in ('.json','.trd','.npz','.raw','.stream','.txt','.ayh1'):
                archive(path,name+'-'+path.relative_to(folder).as_posix().replace('/','-'))
    prepared=json.loads(args.prepared.read_bytes());data=(args.prepared.parent/'audio.bin').read_bytes()
    assert sha(data)==prepared['ay_sha256'] and len(data)==prepared['frames']*5*9
    audio=[AyFrame.deserialize(data[i:i+9]) for i in range(0,len(data),9)]
    cuts=[round(prepared['frames']*i/4) for i in range(5)];quarters=[]
    for index,(lo,hi) in enumerate(zip(cuts,cuts[1:]),1):
        coded,size=audio_size(audio,lo,hi,m['audio_labels'],frame_fields=5,audio_banks=2)
        assert size['resident_fits']
        # Store the exact compact input for reproducing each native bank size.
        path=args.evidence/f'quarter{index}.ayb1.gz';packed=gzip.compress(coded,mtime=0);path.write_bytes(packed)
        artifacts.append(dict(file=path.name,raw_sha256=sha(coded),archive_sha256=sha(packed),
            raw_bytes=len(coded),archive_bytes=len(packed)))
        quarters.append(dict(start=lo,end=hi,**size))
    assert args.tests.read_text().strip().endswith('OK');archive(args.tests,'tests.txt')
    report=dict(complete=True,release=False,scope=__doc__,whole_movie_timing_verified=False,
        prepared_sha256=sha(args.prepared.read_bytes()),ay_sha256=sha(data),pixel_changes=0,
        native_cycle_deltas=dict(init=40,ordinary_refill=50,bank_switch_refill=209,eof_refill=80,per_ay_tick=0,
            excludes='IRQs, contention, TR-DOS ROM and physical latency; full Fuse measurements include them'),
        quarter_memory=quarters,runs=runs,failed_placements=failures,artifacts=artifacts,
        source_sha256_lf={name:sha((root/name).read_bytes().replace(b'\r\n',b'\n')) for name in (
            'banked_resident_audio.py','resident_audio_z80.py','resident_audio_player.py',
            'benchmark_resident_audio_z80.py','test_banked_resident_audio.py',
            'cell_codebook_player.py','convert_cb41.py','build_cb41_cadence_movie.py',
            'measure_cell_codebook_movie.py','verify_banked_resident_audio.py')})
    write_json(args.output,report)
    print(json.dumps(dict(complete=True,quarter_bank_bytes=[q['bank_bytes'] for q in quarters],
        runs=[dict(name=r['name'],frames=r['frames'],late=r['timing']['missed_nominal_frames']) for r in runs])))


if __name__=='__main__':main()
