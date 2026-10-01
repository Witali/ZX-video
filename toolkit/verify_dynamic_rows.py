"""Complete native/Fuse window checks and preserve the interrupted hash-gate attempt."""
import argparse
import gzip
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

from build_fap3_trd import sha
from cell_codebook_player import packet_code
from convert_video import write_json
from profile_fap3 import summarize_fuse


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('fixture','window','probe','fuse','evidence','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--rebuilt-fixture',type=Path)
    p.add_argument('--tests',type=Path)
    args=p.parse_args()
    args.evidence.mkdir(parents=True,exist_ok=True)
    root=Path(__file__).resolve().parent
    checked=[];artifacts=[]
    def archive(path,key):
        raw=path.read_bytes()
        target=args.evidence/(key if path.suffix=='.trd' else key+'.gz')
        target.write_bytes(raw if path.suffix=='.trd' else gzip.compress(raw,mtime=0))
        artifacts.append(dict(file=target.name,raw_sha256=sha(raw),archive_sha256=sha(target.read_bytes()),
            raw_bytes=len(raw),archive_bytes=target.stat().st_size))
    for path in args.evidence.glob('*-metadata-before-reference-fix.json.gz'):
        packed=path.read_bytes();raw=gzip.decompress(packed)
        artifacts.append(dict(file=path.name,raw_sha256=sha(raw),archive_sha256=sha(packed),
            raw_bytes=len(raw),archive_bytes=len(packed)))
    for name,folder in (('fixture',args.fixture),('window',args.window)):
        volumes=json.loads((folder/'volumes.json').read_bytes());assert len(volumes)==1
        record=volumes[0];image=folder/record['file'];meta_path=folder/record['metadata']
        m=json.loads(meta_path.read_bytes());work=folder/'work'/image.stem
        assert sha(image.read_bytes())==m['trd_sha256']==record['sha256']
        with np.load(folder/record['states'],allow_pickle=False) as f:states=f['states']
        correct=sha(states.tobytes())
        if correct!=m['states_sha256']:
            placeholder=np.zeros((len(states),3840),dtype=np.uint8);placeholder[:,3072:]=states[:,3840:]
            assert sha(placeholder.tobytes())==m['states_sha256'],'not the known placeholder metadata bug'
            archive(meta_path,name+'-metadata-before-reference-fix.json')
            m['reference_hash_fix']=dict(previous=m['states_sha256'],correct=correct,
                reason='Parent volume builder overwrote five-level reference hash with build-only placeholder hash',
                image_changed=False)
            m['states_sha256']=correct;write_json(meta_path,m)
        _,_,listing=packet_code(m,m['cell_codebook']['native_labels'],m['cell_codebook']['screen_base'],dynamic_rows=True)
        assert listing==m['cell_codebook']['packet_listing']
        cpu=json.loads((work/'cpu.json').read_bytes());assert cpu['complete'] and cpu['all_native_screens_exact']
        rows=json.loads((work/'dynamic-rows.json').read_bytes())
        batches=sum(bool(f['row_updates']) for f in rows['frames'])
        expected=207*batches+74*rows['updates']
        assert cpu['new_instruction_stages'].get('cb42_row_updates',0)==expected
        common=['--fuse',str(args.fuse.resolve()),'--trd',str(image.resolve()),
            '--metadata',str(meta_path.resolve()),'--states',str((folder/record['states']).resolve()),'--timeout','600']
        timing=work/'timing.json'
        if not timing.exists():
            subprocess.run([sys.executable,str(root/'measure_fap3_fuse.py'),*common,
                '--raw',str((folder/'work/stream.raw').resolve()),'--output',str(timing.resolve())],check=True)
        measured=json.loads(timing.read_bytes());assert measured['complete'] and measured['trd_sha256']==sha(image.read_bytes())
        screens=work/'screens.json'
        if not screens.exists():
            subprocess.run([sys.executable,str(root/'capture_cell_codebook_full.py'),*common,
                '--timing',str(timing.resolve()),'--work',str((work/'captures').resolve()),'--output',str(screens.resolve())],check=True)
        visual=json.loads(screens.read_bytes());assert visual['complete'] and visual['full_screens_exact']
        assert visual['trd_sha256']==measured['trd_sha256']
        checked.append(dict(name=name,frames=m['frames'],trd_sha256=m['trd_sha256'],row_updates=rows['updates'],
            update_batches=batches,row_update_cpu_tstates=expected,full_screens_exact=True,
            compared_bytes=visual['compared_bytes'],cpu_all_native_screens_exact=True,timing=summarize_fuse(measured),
            states_sha256=correct))
        for path in sorted(folder.rglob('*')):
            if not path.is_file() or any(part in ('lzsa','zx0') for part in path.relative_to(folder).parts):continue
            if path.suffix in ('.json','.trd','.npz','.raw','.stream','.txt','.ayh1'):
                archive(path,name+'-'+path.relative_to(folder).as_posix().replace('/','-'))
    for path in sorted(args.probe.glob('*')):
        if path.is_file() and path.suffix in ('.json','.raw','.stream'):archive(path,'probe-'+path.name)
    rebuilt=None
    if args.rebuilt_fixture:
        rows=json.loads((args.rebuilt_fixture/'volumes.json').read_bytes());assert len(rows)==1
        row=rows[0];m=json.loads((args.rebuilt_fixture/row['metadata']).read_bytes())
        with np.load(args.rebuilt_fixture/row['states'],allow_pickle=False) as f:states=f['states']
        assert sha(states.tobytes())==m['states_sha256']
        assert sha((args.rebuilt_fixture/row['file']).read_bytes())==checked[0]['trd_sha256']
        rebuilt=dict(reference_hash_correct_without_repair=True,identical_verified_trd=True,trd_sha256=m['trd_sha256'])
        archive(args.rebuilt_fixture/row['metadata'],'fresh-build-metadata.json')
        archive(args.rebuilt_fixture/'timing.json','fresh-build-cpu-and-cold.json')
    if args.tests:
        assert args.tests.read_text().strip().endswith('OK')
        archive(args.tests,'tests.txt')
    report=dict(complete=True,release=False,scope=__doc__,whole_movie_verified=False,
        fresh_builder_check=rebuilt,runs=checked,artifacts=artifacts,source_sha256_lf={name:sha((root/name).read_bytes().replace(b'\r\n',b'\n'))
            for name in ('dynamic_row_dictionary.py','cell_codebook_player.py','convert_cb41.py',
                'build_cell_codebook_trd.py','row_dictionary_video.py','verify_dynamic_rows.py')})
    write_json(args.output,report)
    print(json.dumps(dict(complete=True,runs=[dict(name=r['name'],frames=r['frames'],updates=r['row_updates'],
        late=r['timing']['missed_nominal_frames'],fallback=r['timing']['fallback_one_field_met']) for r in checked])))


if __name__=='__main__':main()
