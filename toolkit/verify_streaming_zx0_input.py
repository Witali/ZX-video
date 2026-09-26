"""Archive exact input and audit streaming-ZX0 evidence without a new Fuse run.

No arguments revalidate source/code hashes, all 378 decoded blocks, CPU sums,
instruction timings and the two packet-prefix probes. This does not re-execute
the full CPU benchmark; --execute repeats both decoders from archived streams.
"""
import argparse
import gzip
import json
from pathlib import Path
import struct

from benchmark_bank_local_zx0 import Harness as Baseline,disk_blocks,sha
from benchmark_streaming_zx0_input import Harness,first_stall_probe
from zx0_codec import decompress

ROOT=Path(__file__).parent


def validate_histogram(code,origin,rows):
    """Uncontended instruction table, Zilog UM008011, no ROM/IRQ/ULA costs."""
    times={0x01:(10,),0x03:(6,),0x06:(7,),0x08:(4,),0x09:(11,),0x0c:(4,),0x0e:(7,),0x11:(10,),
        0x17:(4,),0x18:(12,),0x19:(11,),0x20:(7,12),0x21:(10,),0x22:(16,),
        0x23:(6,),0x24:(4,),0x28:(7,12),0x2a:(16,),0x2b:(6,),0x2c:(4,),
        0x30:(7,12),0x31:(10,),0x32:(13,),0x38:(7,12),0x3a:(13,),0x3c:(4,),
        0x3d:(4,),0x3e:(7,),0xc0:(5,11),0xc1:(10,),0xc2:(10,),0xc3:(10,),
        0xc5:(11,),0xc8:(5,11),0xc9:(10,),0xca:(10,),0xcc:(10,17),0xcd:(17,),
        0xce:(7,),0xd0:(5,11),0xd1:(10,),0xd2:(10,),0xd4:(10,17),0xd5:(11,),
        0xd8:(5,11),0xda:(10,),0xe1:(10,),0xe3:(19,),0xe5:(11,),0xeb:(4,),
        0xf1:(10,),0xf5:(11,),0xfe:(7,)}
    extended={0x42:(15,),0x43:(20,),0x44:(8,),0x4b:(20,),0x52:(15,),0x53:(20,),
        0x5b:(20,),0x73:(20,),0x7b:(20,),0xa0:(16,),0xb0:(16,21)}
    total=0
    for r in rows:
        at=r['pc']-origin
        if not 0<=at<len(code):raise ValueError('instruction outside generated code')
        op=code[at]
        if 0x40<=op<=0xbf and op!=0x76:
            allowed=(7,) if (op&7)==6 or (op<0x80 and (op>>3)&7==6) else (4,)
        elif op==0xed:allowed=extended[code[at+1]]
        elif op==0xcb:
            if code[at+1] not in (0x10,0x11,0x18,0x19):raise ValueError('unreviewed CB instruction')
            allowed=(8,)
        else:allowed=times[op]
        if r['tstates'] not in allowed or r['count']<=0:raise ValueError(('timing mismatch',r,allowed))
        total+=r['tstates']*r['count']
    return total


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--directory',type=Path,help='Archive exact streams from these baseline TRDs')
    p.add_argument('--execute',action='store_true',help='Re-execute all paired blocks from saved input')
    a=p.parse_args();report_path=ROOT/'streaming_zx0_input_cpu.json';report=json.loads(report_path.read_bytes())
    manifest_path=ROOT/'streaming_zx0_input_evidence.json';folder=ROOT/'streaming_zx0_input_evidence'
    if not report['complete'] or report['blocks']!=378 or len(report['volumes'])!=3:
        raise ValueError('incomplete CPU report')
    for n,digest in report['sources'].items():
        if sha((ROOT/n).read_bytes())!=digest:raise ValueError(('benchmark source changed',n))
    prior_path=ROOT/'zero_mask_history_profile.json';prior=json.loads(prior_path.read_bytes())
    if sha(prior_path.read_bytes())!=report['starvation_profile_sha256']:raise ValueError('different starvation trace')
    baseline=Baseline(dynamic_input=True,inline_literals=True);prototype=Harness()
    for label,h in (('baseline',baseline),('prototype',prototype)):
        if h.code.hex()!=report[label+'_code_hex'] or sha(h.code)!=report[label+'_code_sha256']:
            raise ValueError('generated code changed')
    # Metadata is already archived by the complete real-TRD HL-reader run.
    reference=json.loads((ROOT/'hl_mask_reader_summary.json').read_bytes())
    evidence=[]
    if a.directory:folder.mkdir(exist_ok=True)
    else:
        manifest=json.loads(manifest_path.read_bytes())
        if sha(report_path.read_bytes())!=manifest['cpu_report_sha256']:raise ValueError('CPU report changed')
        for n,digest in manifest['sources'].items():
            if sha((ROOT/n).read_bytes())!=digest:raise ValueError(('audit source changed',n))
    for v in report['volumes']:
        part=v['part'];meta_name=f'hl_part{part:02}.metadata.json.gz'
        entry=next(e for e in reference['evidence'] if e['file']==meta_name)
        packed=(ROOT/entry['directory']/meta_name).read_bytes();meta_raw=gzip.decompress(packed)
        if sha(packed)!=entry['sha256'] or sha(meta_raw)!=entry['uncompressed_sha256']:raise ValueError('metadata archive changed')
        m=json.loads(meta_raw);name=f'part{part:02}.stream.gz'
        if m['trd_sha256']!=v['trd_sha256']:raise ValueError('wrong baseline TRD')
        if a.directory:
            actual,stream,_=disk_blocks(a.directory,part)
            if actual!=m:raise ValueError('fresh TRD metadata differs')
            packed=gzip.compress(stream,mtime=0);(folder/name).write_bytes(packed)
        else:
            expected=next(e for e in manifest['evidence'] if e['part']==part)
            packed=(folder/name).read_bytes()
            if sha(packed)!=expected['sha256']:raise ValueError('stream archive changed')
            stream=gzip.decompress(packed)
        if sha(stream)!=v['stream_sha256']:raise ValueError('stream differs')
        blocks=[];position=0
        for b,cpu in zip(m['blocks'],v['blocks'],strict=True):
            size,compressed=struct.unpack_from('<HH',stream,position);position+=4
            payload=stream[position:position+compressed];position+=compressed
            raw=decompress(payload,limit=size);blocks.append((payload,raw))
            if (len(raw)!=size or size!=b['decoded_bytes'] or compressed!=b['zx0_bytes'] or
                sha(raw)!=b['sha256'] or sha(raw)!=cpu['raw_sha256'] or
                sha(payload)!=cpu['compressed_sha256']):raise ValueError('block evidence differs')
            if cpu['prototype_tstates']-cpu['baseline_tstates']!=cpu['delta_tstates']:
                raise ValueError('block CPU delta differs')
        if position!=len(stream):raise ValueError('trailing block data')
        for label,h,origin in (('baseline',baseline,0x7c00),('prototype',prototype,0x7800)):
            ticks=validate_histogram(h.code,origin,v[label+'_instruction_histogram'])
            if ticks!=v['totals'][label+'_tstates'] or ticks!=sum(b[label+'_tstates'] for b in v['blocks']):
                raise ValueError('instruction/block/volume CPU sums differ')
        if first_stall_probe(blocks,prior['volumes'][part-1]['first_starvation'])!=v['first_starvation_prefix']:
            raise ValueError('packet-prefix probe changed')
        if a.execute:
            for i,((payload,raw),b) in enumerate(zip(blocks,v['blocks'],strict=True)):
                for label,h in (('baseline',baseline),('prototype',prototype)):
                    h.begin(payload,raw,input_offset=b['input_offset'],slot=(0,1,3,4)[i%4])
                    if label=='prototype':result=h.decode()
                    else:
                        for target in list(range(256,len(raw),256))+[len(raw)]:h.run(target)
                        result=h.finish()
                    if result['tstates']!=b[label+'_tstates']:raise ValueError('CPU replay changed')
                if (i+1)%16==0:print(f'part {part}: replayed {i+1}/{len(blocks)}',flush=True)
        evidence.append(dict(part=part,file=name,sha256=sha(packed),stream_sha256=sha(stream),
            metadata_sha256=sha(meta_raw),blocks=len(blocks)))
        print(f'part {part}: {len(blocks)} blocks, code/timings/prefix probe exact',flush=True)
    if a.directory:
        manifest=dict(complete=True,release=False,cpu_report_sha256=sha(report_path.read_bytes()),
            sources={n:sha((ROOT/n).read_bytes()) for n in ('verify_streaming_zx0_input.py','test_streaming_zx0_input.py',
                'hl_mask_reader_summary.json')},evidence=evidence)
        manifest_path.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
