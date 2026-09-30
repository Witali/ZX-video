"""Guarded LZSA2 component benchmark; fixed 256-byte demands, ROM mocked.

Verifies exact bytes, every output/input cursor, all sector and bank bounds.
Does not model real queue deadlines, disk latency, IRQ or ULA contention.
"""
import argparse,json,struct
from collections import Counter
from pathlib import Path
from unittest.mock import patch
import benchmark_inplace_slot as base
from benchmark_inplace_streaming import CountedCPU
from test_fap3_disk import install
from validate_fast_sparse import CPU
from build_fap3_trd import sha
from inplace_zx0 import layout
import inplace_slot_input_z80 as producer
import lzsa2_stream
import resumable_lzsa2


class LzsaCPU(CountedCPU):
    def instruction(self):
        if CPU.read8(self,self.pc)==0x37:
            self.pc=(self.pc+1)&65535;self.carry=True;return 4
        return super().instruction()

    def read8(self,address):
        address &= 65535
        # LZSA2 inspects the token twice before advancing HL. Only decoder
        # LD/OR token instructions may reread a consumed input byte.
        if (self.decoding and self.pc in self.token_rereads
                and self.input_start<=address<self.input_start+self.input_reads):
            value=CPU.read8(self,address)
            if value!=self.payload[address-self.input_start]:raise AssertionError('overwritten token')
            return value
        return super().read8(address)


def fixture(stream,first,core,limit):
    h=base.Harness(stream,first,inplace=True);c=h.cpu
    regions,z,report=resumable_lzsa2.build(core=core,core_limit=limit)
    for at,data in regions:install(c,at,data)
    c.__class__=LzsaCPU;c.decoder_histogram=Counter()
    h.z=z;c.zlabels=z;c.patched=set(report['patched_addresses'])
    # CPU.step increments PC while fetching; token data reads see next PC.
    c.token_rereads={r['address']+1 for r in report['instruction_listing']
                    if r['instruction'] in ('LD A,(HL)','LD B,(HL)','OR (HL)')}
    regions,h.p,rows=producer.build(z,h.d,elapsed_fields=h.elapsed_fields)
    for at,data in regions:install(c,at,data)
    h.regions=regions;h.instructions.update({r['address']:r for r in rows})
    return h,report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('stream','raw','metadata','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--limit',type=int)
    a=p.parse_args();stream=a.stream.read_bytes();raw=a.raw.read_bytes();m=json.loads(a.metadata.read_text())
    placement=m['pre_fast_bank2_zx0'];h,native=fixture(stream,m['video_start_sector'],placement['new_origin'],placement['new_end'])
    at=out=0;proofs=[]
    with patch.object(base,'trace',lzsa2_stream.trace):
        while at<len(stream) and (a.limit is None or len(h.results)<a.limit):
            n,size=struct.unpack_from('<HH',stream,at);offset=at;at+=4
            payload=stream[at:at+size];expected=raw[out:out+n]
            decoded,proof=lzsa2_stream.trace(payload,limit=n)
            if decoded!=expected:raise AssertionError('host decode differs')
            space=layout(size,n,proof['minimum_input_start'],offset)
            if not space['sector_aligned_fits']:raise AssertionError(('overlap',len(proofs),space))
            lzsa2_stream.trace(payload,limit=n,input_start=space['input_start'])
            proofs.append(dict(proof=proof,layout=space))
            h.block(payload,expected,len(h.results));at+=size;out+=n
    result=h.finish() if a.limit is None else dict(complete=False)
    rows={r['address']:r for r in native['instruction_listing']}
    for (pc,t),count in h.cpu.decoder_histogram.items():
        expected=rows[pc]['tstates']
        if t not in (expected if isinstance(expected,list) else [expected]):raise AssertionError(('opcode timing',pc,t,expected))
    if sum(t*n for (_,t),n in h.cpu.decoder_histogram.items())!=sum(r['decoder_tstates'] for r in h.results):
        raise AssertionError('decoder histogram total differs')
    result.update(release=False,scope=__doc__,blocks=h.results,proofs=proofs,native=native,
        all_instruction_timings_verified=True,max_slice_tstates=max(t for r in h.results for t in r['slice_tstates']),
        stream_sha256=sha(stream),raw_sha256=sha(raw),stream_bytes=len(stream),decoded_bytes=out,
        decoder_histogram=[dict(pc=pc,tstates=t,count=n) for (pc,t),n in sorted(h.cpu.decoder_histogram.items())])
    a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('blocks','proofs','native','scope','instruction_histogram','decoder_histogram')}))


if __name__=='__main__':main()
