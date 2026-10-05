"""Read saved Fuse clocks and benchmark ordinary IMA encoding, without new playback.

This is a diagnostic, not a fixed-clock player or an end-to-end speed claim.
The source and measured clocks are authenticated against the saved experiment.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import platform
import time
import wave

import numpy as np
from ima_beam import encode as beam_encode
from ima_codec import encode as nearest_encode, decode, require_unclipped


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--evidence',type=Path,default=Path(__file__).parent/'experiments/ima4-full-disk')
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    if args.output.exists():p.error('output must not already exist')
    root=args.evidence.resolve();manifest=json.loads((root/'artifact-hashes.json').read_bytes())
    def read(name):
        data=(root/name).read_bytes()
        assert hashlib.sha256(data).hexdigest()==manifest[name],name
        return data
    rows=[]
    for number in range(1,6):
        timeline=np.frombuffer(gzip.decompress(read(f'release/verification/cold-0001/part-{number:02d}-times.u32.gz')),'<u4').astype(np.int64)
        report=json.loads(read(f'selected/part-{number:05d}/report.json'))
        source_count=report['source']['prepared_samples']-128
        boundaries=timeline[::16][:source_count+1]
        assert len(boundaries)==source_count+1
        periods=np.diff(boundaries)
        rows.append(dict(part=number,samples=len(periods),minimum_tstates=int(periods.min()),
            maximum_tstates=int(periods.max()),mean_tstates=float(periods.mean()),
            stddev_tstates=float(periods.std()),distinct_durations=len(np.unique(periods)),
            percentile_tstates={str(q):float(np.percentile(periods,q)) for q in (0,1,50,99,100)}))
    source_name='selected/part-00001/source-preview.wav'
    read(source_name)
    with wave.open(str(root/source_name),'rb') as w:
        assert (w.getnchannels(),w.getsampwidth(),w.getframerate())==(1,1,8000)
        source=np.frombuffer(w.readframes(w.getnframes()),'u1').copy()
    benchmarks=[]
    for name,encoder in [('nearest_delta',nearest_encode),('existing_beam32',beam_encode)]:
        started=time.perf_counter();packed=encoder(source);elapsed=time.perf_counter()-started
        decoded,_=decode(packed)
        target=(source.astype(np.int64)-128)*256
        mse=float(np.mean((decoded.astype(np.int64)-target)**2))
        snr=float(10*np.log10(np.mean(target**2)/mse))
        row=dict(encoder=name,samples=len(source),source_seconds=len(source)/8000,
            encode_seconds=elapsed,realtime_factor=elapsed/(len(source)/8000),
            codec_only_raw_snr_db=snr,packed_sha256=hashlib.sha256(packed).hexdigest(),
            scope='Encoding only: excludes source decode, tables, assembly, disk packing and verification')
        try:row['saturation_guard']=require_unclipped(packed)
        except ValueError as error:row['saturation_guard_failure']=str(error)
        benchmarks.append(row);print(json.dumps(row),flush=True)
    result=dict(date='2026-10-05',scope=__doc__,python=platform.python_version(),host=platform.processor(),
        current_measured_samples=rows,encoding_benchmarks=benchmarks,
        cpu_hz=3546900,exact_8000_hz_sample_tstates=3546900/8000,
        proposed_integer_periods=[dict(tstates=t,sample_rate_hz=3546900/t,
            pdm_rate_hz=16*3546900/t,source_8000_speed_error_percent=100*(3546900/t/8000-1))
            for t in (440,444)],
        fixed_sample_player_implemented=False,end_to_end_realtime_conversion_proven=False,
        player_tstate_change=0)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(timing=rows,report=str(args.output))),flush=True)


if __name__=='__main__':main()
