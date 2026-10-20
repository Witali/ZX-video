"""One frozen C encoding preset matched to the uniform16 table component.

Times use the renderer's reference-CPU units: sixteen equal intervals per
original8kHz sample. This is encoder evidence, not a complete player release.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import time

import numpy as np

from build_pdm import CPU_CLOCK
from convert_audio import pcm_wav
from ima_codec import decode
from pacing448_control import AUDIO, NAMES, PARAMETERS, PRODUCERS, encode
from probe_reconstruction_error import wav8
from table_pdm_uniform16 import model as component_model

HERE=Path(__file__).resolve().parent
MODEL=dict(holds=[28]*16,beta=.5,extent=.5,pcm_origin=0)
ORDER=('quiet997',)+tuple(name for name in NAMES if name!='quiet997')


def sha(value):return hashlib.sha256(value).hexdigest()
def save(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def fingerprint(value):return sha(json.dumps(value,sort_keys=True,allow_nan=False).encode())


def files(folder):
    return {path.relative_to(folder).as_posix():dict(bytes=path.stat().st_size,
            sha256=sha(path.read_bytes())) for path in sorted(folder.rglob('*'))
            if path.is_file() and path.name!='complete.json'}


def timeline(samples):
    # CPU_CLOCK is3546900 reference units/s, not the physical Pentagon clock.
    # An output interval is28 physical T at3.584MHz == CPU_CLOCK/128000 here.
    return np.arange(samples*16+1,dtype=np.float64)*(CPU_CLOCK/8000/16)


def configuration(inputs):
    producers={name:sha((AUDIO/name).read_bytes()) for name in PRODUCERS}
    for name in ('experiments/song-snr/table_pdm_uniform16.py',
                 'experiments/song-snr/table_pdm_uniform16_encode.py'):
        producers[name]=sha((AUDIO/name).read_bytes())
    identities={}
    for name in ORDER:
        path=inputs/(name+'.wav');source=wav8(path)
        assert len(source)%512==0 and np.all(source[-128:]==128)
        identities[name]=dict(wav_sha256=sha(path.read_bytes()),
            pcm8_sha256=sha(source.tobytes()),samples=len(source),
            last128_original_samples_silent=True)
    words,nxt,states,first,second=component_model()
    return dict(schema=1,model=MODEL,parameters=dict(PARAMETERS),source_order=list(ORDER),
        search=dict(width=32,horizon=128,commit=64,regularization=.1,
                    final_silent_guard_samples=128),
        source_rate_hz=8000,physical_CPU_hz=3584000,reference_CPU_units_per_second=CPU_CLOCK,
        physical_hold_T=28,physical_period_T=448,physical_PDM_hz=128000,
        renderer_interval_reference_units=CPU_CLOCK/8000/16,
        timeline='arange(N*16+1)*(reference_CPU/8000/16)',
        no_clock_gain_delay_fit=True,original_reference_samples_changed=0,
        source_independent_parameters=True,states=states,FIRST_patterns=len(first),
        SECOND_patterns=len(second),words_sha256=sha(words.astype('<u2').tobytes()),
        successors_sha256=sha(nxt.astype('<i8').tobytes()),sources=identities,
        producers=producers,emulator_verified=False,full_player_verified=False,
        scope='Matched standalone C encoder only; no quality or release claim')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=HERE/'evidence/table-pdm-uniform16-matched')
    parser.add_argument('--scratch',type=Path,default=AUDIO.parents[0]/'.tmp/table-pdm-uniform16-matched')
    parser.add_argument('--source',action='append',choices=NAMES)
    parser.add_argument('--resume',action='store_true')
    args=parser.parse_args();out=args.output.resolve();scratch=args.scratch.resolve()
    inputs=HERE/'evidence/general/inputs';out.mkdir(parents=True,exist_ok=True)
    scratch.mkdir(parents=True,exist_ok=True)
    frozen=configuration(inputs);identity=fingerprint(frozen);config=out/'configuration.json'
    if config.exists():
        if not args.resume or json.loads(config.read_bytes())!=frozen:
            raise ValueError('Existing evidence has different configuration; preserve it')
    else:
        save(config,frozen)
        snapshots=out/'producer-source';snapshots.mkdir()
        for name,expected in frozen['producers'].items():
            content=(AUDIO/name).read_bytes();assert sha(content)==expected
            dest=snapshots/(name.replace('/','__')+'.gz')
            dest.write_bytes(gzip.compress(content,mtime=0))
    selected=set(args.source or ORDER);rows=[]
    for name in ORDER:
        if name not in selected:continue
        dest=out/name;marker=dest/'complete.json'
        if marker.exists():
            old=json.loads(marker.read_bytes())
            if not args.resume or old['configuration_sha256']!=identity or old['files']!=files(dest):
                raise ValueError('Completed source identity or artifact hashes changed: '+name)
            rows.append(json.loads((dest/'report.json').read_bytes()));continue
        if dest.exists() and any(dest.iterdir()):
            raise ValueError('Preserve incomplete source and select fresh output: '+name)
        dest.mkdir(exist_ok=True);local=scratch/name;local.mkdir(parents=True,exist_ok=True)
        source=wav8(inputs/(name+'.wav'));source_id=frozen['sources'][name]
        assert sha(source.tobytes())==source_id['pcm8_sha256']
        started=time.perf_counter();times=timeline(len(source))
        assert abs(times[-1]/CPU_CLOCK-len(source)/8000)<1e-12
        print(json.dumps(dict(source=name,starting=True,samples=len(source),preset_frozen=identity)),flush=True)
        packed,target,result=encode(source,times,MODEL,local)
        pcm,index=decode(packed)
        assert len(packed)*2==len(source) and (int(pcm[-1]),int(index[-1]))==(0,0)
        (dest/'packed.ima.gz').write_bytes(gzip.compress(packed,mtime=0))
        pcm_wav(dest/'encoding-prior.wav',target)
        row=dict(source=name,configuration_sha256=identity,model=MODEL,
            source_identity=source_id,source_sha256=sha(source.tobytes()),source_samples=len(source),
            packed_sha256=sha(packed),packed_bytes=len(packed),decoded_samples=len(pcm),
            decoded_pcm16_sha256=sha(pcm.astype('<i2').tobytes()),
            final_predictor=int(pcm[-1]),final_index=int(index[-1]),
            encoded_prior_pcm8_sha256=sha(target.tobytes()),
            prior_differs_original_samples=int(np.count_nonzero(target!=source)),
            elapsed_seconds=time.perf_counter()-started,encoding=result,
            every_physical_hold_T=28,physical_period_T=448,reference_time_units=CPU_CLOCK,
            no_clock_gain_delay_fit=True,all_content_and_original128_guard_preserved=True,
            actual_player_execution=False,quality_scored=False)
        save(dest/'report.json',row)
        save(marker,dict(configuration_sha256=identity,files=files(dest)))
        rows.append(row)
        save(out/'partial.json',dict(complete=False,rows=rows))
        print(json.dumps(dict(source=name,complete=True,packed_bytes=len(packed),
            elapsed_seconds=row['elapsed_seconds'],statistics=result['statistics'])),flush=True)
    # Check live producer/input identities again after the entire selected run.
    assert configuration(inputs)==frozen
    complete=all((out/name/'complete.json').exists() for name in ORDER)
    all_rows=[json.loads((out/name/'report.json').read_bytes()) for name in ORDER
              if (out/name/'complete.json').exists()]
    save(out/'report.json',dict(complete=complete,configuration_sha256=identity,
        source_independent_preset=True,all_nine_sources_encoded=complete,
        rows=all_rows,actual_player_execution=False,quality_scored=False))
    manifest=[]
    for path in sorted(out.rglob('*')):
        if path.is_file() and path.name!='manifest.json':
            content=path.read_bytes();manifest.append(dict(path=path.relative_to(out).as_posix(),
                bytes=len(content),sha256=sha(content)))
    save(out/'manifest.json',dict(complete=complete,configuration_sha256=identity,files=manifest))


if __name__=='__main__':main()
