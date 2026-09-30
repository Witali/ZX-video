"""Guarded resumable LZ4-HC component benchmark on archived video blocks.

Use the same producer, bank bounds and 256-byte demands as the LZSA2 test.
ROM is mocked; real queues, IRQ, ULA and disk timing are measured separately.
"""
import argparse,gzip,json,struct
from collections import Counter
from pathlib import Path
from unittest.mock import patch
import benchmark_inplace_slot as base
from benchmark_inplace_streaming import CountedCPU
from test_fap3_disk import install
from build_fap3_trd import sha
from build_five_level_test_trd import save
from inplace_zx0 import layout
import inplace_slot_input_z80 as producer
import lz4_stream
import resumable_lz4


class Lz4CPU(CountedCPU):
    minimum_sp=65535
    def step(self):
        if self.decoding:self.minimum_sp=min(self.minimum_sp,self.sp)
        return super().step()


def fixture(stream,first,core=0x8de0,limit=0x8ef7,*,fast_short=True):
    h=base.Harness(stream,first,inplace=True);c=h.cpu
    regions,z,report=resumable_lz4.build(core=core,core_limit=limit,fast_short=fast_short)
    for at,data in regions:install(c,at,data)
    c.__class__=Lz4CPU;c.decoder_histogram=Counter()
    h.z=z;c.zlabels=z;c.patched=set(report['patched_addresses'])
    regions,h.p,rows=producer.build(z,h.d,elapsed_fields=h.elapsed_fields)
    for at,data in regions:install(c,at,data)
    h.regions=regions;h.instructions.update({r['address']:r for r in rows})
    return h,report


def benchmark(stream,raw,metadata,*,fast_short=True):
    place=metadata['pre_fast_bank2_zx0']
    h,native=fixture(stream,metadata['video_start_sector'],place['new_origin'],place['new_end'],fast_short=fast_short)
    at=out=0;proofs=[]
    with patch.object(base,'trace',lz4_stream.trace):
        while at<len(stream):
            n,size=struct.unpack_from('<HH',stream,at);offset=at;at+=4
            if not 1<=n<=15872:raise ValueError('native block length outside 1..15872')
            payload=stream[at:at+size];expected=raw[out:out+n]
            decoded,proof=lz4_stream.trace(payload,limit=n)
            if decoded!=expected:raise AssertionError('host decode differs')
            space=layout(size,n,proof['minimum_input_start'],offset)
            if not space['sector_aligned_fits']:raise AssertionError(('overlap',len(proofs),space))
            lz4_stream.trace(payload,limit=n,input_start=space['input_start'])
            proofs.append(dict(proof=proof,layout=space))
            h.block(payload,expected,len(h.results));at+=size;out+=n
    if at!=len(stream) or out!=len(raw):raise ValueError('stream/raw extent differs')
    result=h.finish();rows={r['address']:r for r in native['instruction_listing']}
    for (pc,t),count in h.cpu.decoder_histogram.items():
        expected=rows[pc]['tstates']
        if t not in (expected if isinstance(expected,list) else [expected]):raise AssertionError(('instruction cost',pc,t,expected))
    if sum(t*n for (_,t),n in h.cpu.decoder_histogram.items())!=result['decoder_tstates']:
        raise AssertionError('decoder histogram differs')
    result.update(release=False,scope=__doc__,blocks=h.results,proofs=proofs,native=native,
        all_instruction_timings_verified=True,max_slice_tstates=max(t for r in h.results for t in r['slice_tstates']),
        stream_sha256=sha(stream),raw_sha256=sha(raw),stream_bytes=len(stream),decoded_bytes=out,
        minimum_decoder_sp=h.cpu.minimum_sp,
        decoder_histogram=[dict(pc=pc,tstates=t,count=n) for (pc,t),n in sorted(h.cpu.decoder_histogram.items())])
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive',type=Path,default=Path('toolkit/modern_codec_evidence/lz4_hc12.stream.gz'))
    p.add_argument('--baseline',action='store_true',help='Use the generic-copy LZ4 baseline')
    for name in ('raw','metadata','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    stream=gzip.decompress(a.archive.read_bytes());raw=a.raw.read_bytes();m=json.loads(a.metadata.read_bytes())
    result=benchmark(stream,raw,m,fast_short=not a.baseline)
    (a.output/'video.stream').write_bytes(stream);save(a.output/'cpu.json',result)
    print(json.dumps({k:result[k] for k in ('complete','decoder_tstates','producer_tstates','total_tstates',
        'stream_bytes','sector_reads','max_slice_tstates','minimum_decoder_sp')}),flush=True)


if __name__=='__main__':main()
