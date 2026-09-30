"""Measure row-video producer and Fast ZX0 CPU, with a frozen service clock.

All output and sector bytes are checked. Fixed 256-byte decode demands are
component measurements, not a replay of the real queue/IRQ/ULA schedule.
Report observed disk windows separately; packet-copy LDI cost is a lower bound.
"""
import argparse
import json
from pathlib import Path
import struct
from unittest.mock import patch
import faster_zx0
from benchmark_faster_zx0 import fixture
from profile_fast_reservoir import payloads
from build_fap3_trd import sha


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('trd','metadata','timing','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();m=json.loads(a.metadata.read_text());t=json.loads(a.timing.read_text());image=a.trd.read_bytes()
    if sha(image)!=m['trd_sha256'] or m['trd_sha256']!=t['trd_sha256'] or not t['complete']:
        raise ValueError('incomplete or mismatched input')
    video,stream,_,_=payloads(image,m);old=faster_zx0.build;place=m['pre_fast_bank2_zx0']
    with patch.object(faster_zx0,'build',side_effect=lambda variant:old(variant,core=place['new_origin'],core_limit=place['new_end'])):
        h,_=fixture(stream,m['video_start_sector'],'fast')
    at=out=0
    while at<len(stream):
        n,size=struct.unpack_from('<HH',stream,at);at+=4
        h.block(stream[at:at+size],video[out:out+n],len(h.results));at+=size;out+=n
    result=h.finish()
    result.update(scope=__doc__,release=False,blocks=h.results,decoded_bytes=len(video),compressed_bytes=len(stream),
        trd_sha256=sha(image),packet_copy_ldi_lower_bound_tstates=16*len(video),
        observed_disk_read_windows_tstates=sum(r['tstates'] for r in t['reads']),
        observed_seek_windows_tstates=sum(r['tstates'] for r in t['seek_calls']),
        source_sha256_lf=sha(Path(__file__).read_bytes().replace(b'\r\n',b'\n')))
    a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('blocks','instruction_histogram','scope','source_sha256_lf')}))


if __name__=='__main__':main()
