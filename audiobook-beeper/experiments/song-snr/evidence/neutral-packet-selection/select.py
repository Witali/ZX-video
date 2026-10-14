"""Reproduce the complete neutral-packet enumeration without audio inputs."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
from neutral_packet_model import (NEUTRAL_PACKET_WORD,NEUTRAL_PACKET_SUCCESSOR,
    ORDINARY_PENTAGON_HOLDS,apply_neutral_packet,select_neutral_packet)
from probe_feedback_packets import integral_table


sha=lambda data:hashlib.sha256(data).hexdigest()


def catalogue(words,nxt):
    reachable={16}
    while True:
        expanded=reachable|set(map(int,nxt[:,sorted(reachable)].ravel()))
        if expanded==reachable:break
        reachable=expanded
    used=words[:,sorted(reachable)]
    first=len(np.unique(used>>8));second=len(np.unique(used&255))
    code=first*42+second*64;pointer=(0x8340+code+255)&~255
    resident_end=pointer+256+1024+1088
    return dict(closed_feedback_states=sorted(reachable),state_count=len(reachable),
                packet_bytes_per_bin=len(reachable)*6,protected_cache_state_fits=len(reachable)<=18,
                first_patterns=first,second_patterns=second,unrolled_code_bytes=code,
                table_pointer=pointer,resident_end=resident_end,resident_end_hex=hex(resident_end),
                compact_worker_estimate_maximum_one_trd_end=resident_end+892,
                compact_worker_estimate_fits=resident_end+892<0xbfff,
                scope='Closure over every64 PCM bin from state16; dictionary/layout arithmetic, not new assembly or execution proof')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('.tmp/neutral-selection-proof'))
    args=parser.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    report,arrays=select_neutral_packet()
    assert report['source_audio_opened'] is False
    model=dict(holds=list(ORDINARY_PENTAGON_HOLDS),beta=.5,extent=1.,pcm_origin=0,
               pcm_quantization_bias=512,neutral_packet_word=NEUTRAL_PACKET_WORD,
               neutral_packet_successor=NEUTRAL_PACKET_SUCCESSOR)
    before,next_before,_=integral_table(64,2,holds=model['holds'],beta=.5,extent=1.,pcm_origin=0)
    after,next_after=apply_neutral_packet(before,next_before,model)
    report['model']=model;report['before_catalogue']=catalogue(before,next_before)
    report['after_catalogue']=catalogue(after,next_after)
    report['before_table_sha256']=sha(before.astype('<u2').tobytes()+next_before.astype('<u2').tobytes())
    report['after_table_sha256']=sha(after.astype('<u2').tobytes()+next_after.astype('<u2').tobytes())
    report['changed_word_entries']=int(np.count_nonzero(before!=after))
    report['changed_successor_entries']=int(np.count_nonzero(next_before!=next_after))
    # Store every enumerated word, including forbidden DC patterns, as compact
    # numeric columns. Allowed ranking is explicit; no favorable rows omitted.
    full=dict(columns=['word','on_tstates','allowed','variance','second_moment','midpoint_mean'],
              rows=[[int(word),int(on),bool(allowed),float(var),float(moment),float(mean)]
                    for word,on,allowed,var,moment,mean in zip(arrays['words'],arrays['on_tstates'],
                        arrays['allowed'],arrays['variance'],arrays['second_moment'],arrays['midpoint_weighted_mean'])],
              allowed_word_ranking=list(map(int,arrays['ranking'])))
    packed=gzip.compress(json.dumps(full,separators=(',',':')).encode(),mtime=0)
    (out/'enumeration.json.gz').write_bytes(packed)
    report['full_enumeration']=dict(file='enumeration.json.gz',sha256=sha(packed),bytes=len(packed),
                                    rows=65536,allowed_ranking_rows=848)
    sources=('audiobook-beeper/neutral_packet_model.py','audiobook-beeper/test_neutral_packet_model.py',
             'audiobook-beeper/ima_waveform_encoder.py','audiobook-beeper/probe_feedback_packets.py',str(Path(__file__)))
    report['producer_sha256']={name:sha(Path(name).read_bytes()) for name in sources}
    originals={}
    for name in ('ima_waveform_encoder.py','ima_beam.py'):
        path='audiobook-beeper/'+name
        original=subprocess.check_output(['git','show','13819086:'+path]).replace(b'\r\n',b'\n')
        current=Path(path).read_bytes().replace(b'\r\n',b'\n');assert current==original
        originals[path]=dict(git_reference='13819086',normalized_lf_sha256=sha(current),unchanged=True)
    report['original_python']=originals
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({key:report[key] for key in ('selected_hex','balanced_candidates',
        'selected_estimated_rms','after_catalogue','full_enumeration')}))


if __name__=='__main__':main()
