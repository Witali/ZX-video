"""Build one common duration-aware table preset and fully execute holdouts."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import gzip
import json
from pathlib import Path

from build_stream_trd import build
from general import models
from verify_pcm import save
from verify_stream_trd import native_check,fuse_check


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('evidence',type=Path);p.add_argument('--fuse',required=True,type=Path)
    p.add_argument('--jobs',type=int,default=3);p.add_argument('--captured',action='store_true')
    p.add_argument('--source',action='append',help='Explicit corpus subset for a separate full run; not parameter tuning')
    a=p.parse_args();root=a.evidence.resolve();inputs=root/'study/inputs';out=root/'prototype';out.mkdir(exist_ok=True)
    baseline=json.loads((inputs/'song/player.json').read_bytes());current=(inputs/'current-main.trd').read_bytes()
    entry=next(x for x in baseline['directory'] if x['name']=='COVER');offset=(entry['track']*16+entry['sector'])*256
    cover=current[offset:offset+6912];model=dict(models())['duration_zero_half_recent']
    def run(name):
        packed=gzip.decompress((root/'general/inputs'/(name+'.ima.gz')).read_bytes());dest=out/name;dest.mkdir(exist_ok=True)
        disk,meta=build(packed,dest/'assembly',cover,model)
        if a.captured:
            assert (dest/'audio.trd').read_bytes()==disk
            assert json.loads((dest/'player.json').read_bytes())==meta
        else:
            (dest/'audio.trd').write_bytes(disk);save(dest/'player.json',meta)
            (dest/'soundtrack.ima.gz').write_bytes(gzip.compress(packed,mtime=0))
            (dest/'source-preview.wav').write_bytes((root/'general/inputs'/(name+'.wav')).read_bytes())
        verify=dest/'verification';verify.mkdir(exist_ok=True);native=[]
        for profile in ('128','scorpion','pentagon512','pentagon1024'):
            native.append(native_check(disk,meta,packed,profile,out=verify/f'native-{profile}.json'))
        print('Native complete: '+name,flush=True)
        actual=[]
        for profile in ('pentagon512','pentagon1024') if name=='sea_foam' else ('pentagon512',):
            actual.append(fuse_check(dest/'audio.trd',meta,packed,profile,verify/profile,a.fuse,captured=a.captured))
            print('Fuse complete: '+name+'/'+profile,flush=True)
        report=dict(complete=True,source=name,model=model,native=native,fuse=actual,
                    source_independent_preset=True,worker_origin=meta['memory']['worker_origin'],
                    hot_path_instruction_delta_tstates=0,
                    scope='Research prototype: full functional native checks on four models; own-clock Fuse proof for listed Pentagon profiles')
        save(verify/'report.json',report);return report
    names=a.source or ['speech','entertainer','sea_foam','loud3000','silence','quiet997']
    with ThreadPoolExecutor(max_workers=a.jobs) as pool:results=list(pool.map(run,names))
    save(out/('subset-report.json' if a.source else 'report.json'),dict(complete=True,results=results,source_independent_preset=True,main_release_unchanged=True))


if __name__=='__main__':main()
