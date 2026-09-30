"""One bounded fragment-selection comparison on an existing exact test clip.

No re-quantization and no full-movie search. Decoder opcodes remain unchanged;
measure the resulting instruction paths and physical delivery separately.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from build_five_level_test_trd import source_audio,save
from encode_fap3 import encode
from row_dictionary_video import Builder,reference_tables
from build_fap3_trd import sha
from build_integrated_bootstrap import check_cold
from build_inplace_keepalive import prime


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('baseline','states','metadata','options','zx0','output'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--slack',type=int,default=16,help='Optional pre-ZX0 bytes per eligible tile; experimental speed mode')
    p.add_argument('--probe-only',action='store_true',help='Measure the bounded stream before building a disk')
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    original=a.baseline.read_bytes();m=json.loads(a.metadata.read_text())
    with np.load(a.states,allow_pickle=False) as data:states=data['states']
    audio=source_audio(original)
    before,_=encode(states,audio)
    if before!=original:raise AssertionError('default encoder changed baseline bytes')
    raw,codec=encode(states,audio,fragment_byte_slack=a.slack)
    (a.output/'video.raw').write_bytes(raw)
    options=json.loads(a.options.read_text())['contract']['options'];options['startup_delta']=False
    with reference_tables(m['row_dictionary']):
        b=Builder(raw,states,a.zx0.resolve(),a.output/'zx0',row_dictionary=m['row_dictionary'],
            series_fingerprint=b'AYH1R5F1'+bytes.fromhex(sha(raw))[:6],**options)
        if a.probe_only:
            stream,blocks=b.stream(0,len(states))
            save(a.output/'probe.json',dict(complete=True,release=False,fragment_byte_slack=a.slack,
                default_encoder_exact=True,codec=codec,raw_sha256=sha(raw),states_sha256=sha(states.tobytes()),
                video_bytes=len(stream),video_sectors=(len(stream)+255)//256,blocks=blocks))
            print(json.dumps(dict(video_bytes=len(stream),video_sectors=(len(stream)+255)//256)),flush=True)
            return
        b.ends=[len(states)];image,meta=b.volume(0,len(states),1)
        if image is None:raise ValueError('candidate does not fit one disk')
        (a.output/'candidate.trd').write_bytes(image);save(a.output/'metadata.json',meta)
        checks=check_cold(image,meta,b.expected_banks);checks.update(prime(image,meta,states))
    report=dict(complete=True,release=False,scope=__doc__,default_encoder_exact=True,fragment_byte_slack=a.slack,
        baseline_raw_sha256=sha(original),raw_sha256=sha(raw),states_sha256=sha(states.tobytes()),
        codec=codec,checks=checks,trd_sha256=sha(image),
        **{k:meta[k] for k in ('video_bytes','video_sectors','used_sectors','free_sectors','frames')})
    save(a.output/'build.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('codec','checks','scope')}),flush=True)


if __name__=='__main__':main()
