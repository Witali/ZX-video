"""Move LZSA2 reset boundaries near packets in one bounded stream tail.

Keep decoded bytes, block count, earlier blocks and the 15872-byte native
ceiling. This is a compression/component probe, not a playback release.
"""
import argparse,gzip,json,struct,time
from pathlib import Path
from build_fap3_trd import sha
from build_five_level_test_trd import save
from inplace_zx0 import layout
from lzsa2_oracle_host import Author
from verify_lzsa2_dispatch import execute
import lzsa2_stream
import resumable_lzsa2

ROOT=Path(__file__).resolve().parent
MAX=15872


def blocks(stream):
    at=out=0;rows=[]
    while at<len(stream):
        n,size=struct.unpack_from('<HH',stream,at)
        payload=stream[at+4:at+4+size]
        if len(payload)!=size or not 1<=n<=MAX:raise ValueError('invalid block extent')
        rows.append(dict(start=out,end=out+n,payload=payload,stream_start=at))
        at+=4+size;out+=n
    if at!=len(stream):raise ValueError('invalid stream extent')
    return rows


def packet_bounds(raw):
    at=0;positions=[0]
    while at<len(raw):
        n=struct.unpack_from('<H',raw,at)[0]
        if n<288 or at+2+n>len(raw):raise ValueError('invalid video packet')
        at+=2+n;positions.append(at)
    return positions


def choose_cuts(start,end,count,packets,first_slack):
    cuts=[start];decisions=[]
    for i in range(count-1):
        left=count-i-1
        low=max(cuts[-1]+1,end-left*MAX)
        high=min(cuts[-1]+MAX,end-left)
        target=high-(first_slack if i==0 else 0)
        if target<low:raise ValueError('requested slack cannot retain block count')
        valid=[p for p in packets if low<=p<=target]
        chosen=max(valid) if valid else target
        cuts.append(chosen)
        decisions.append(dict(lower=low,upper=high,target=target,chosen=chosen,packet_aligned=chosen in packets))
    cuts.append(end)
    assert all(1<=b-a<=MAX for a,b in zip(cuts,cuts[1:]))
    return cuts,decisions


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('raw','stream','author','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--tail-blocks',type=int,default=5)
    p.add_argument('--first-slack',type=int,default=0)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    raw=a.raw.read_bytes();stream=a.stream.read_bytes();old=blocks(stream)
    baseline=json.loads(gzip.decompress((ROOT/'lzsa2_stage_evidence/transport.json.gz').read_bytes()))
    assert sha(raw)==baseline['raw_sha256'] and sha(stream)==baseline['stream_sha256']
    assert 1<a.tail_blocks<=len(old) and 0<=a.first_slack<MAX
    assert old[-1]['end']==len(raw)
    first=len(old)-a.tail_blocks;start=old[first]['start'];packets=packet_bounds(raw)
    cuts,decisions=choose_cuts(start,len(raw),a.tail_blocks,packets,a.first_slack)
    author=Author(a.author);regions,labels,native=resumable_lzsa2.build()
    assert native==baseline['native']
    candidate=bytearray(stream[:old[first]['stream_start']]);rows=[];seconds=0
    for i,(lo,hi) in enumerate(zip(cuts,cuts[1:]),first):
        previous=old[i];old_raw=raw[previous['start']:previous['end']]
        assert author.compress(old_raw)==previous['payload'],'author build differs from baseline'
        part=raw[lo:hi];t=time.perf_counter();payload=author.compress(part);seconds+=time.perf_counter()-t
        assert author.decompress(payload,len(part))==part
        decoded,proof=lzsa2_stream.trace(payload,limit=len(part));assert decoded==part
        space=layout(len(payload),len(part),proof['minimum_input_start'],len(candidate))
        assert space['sector_aligned_fits'],('unsafe overlap',i,space)
        lzsa2_stream.trace(payload,limit=len(part),input_start=space['input_start'])
        measured=execute(regions,labels,native,payload,part,source=0x1000)
        irq=execute(regions,labels,native,payload,part,source=0x1000,interrupts=True)
        rows.append(dict(index=i,start=lo,end=hi,decoded_bytes=len(part),payload_bytes=len(payload),
            raw_sha256=sha(part),payload_sha256=sha(payload),proof=proof,layout=space,
            native=measured,interrupt_run=irq))
        candidate+=struct.pack('<HH',len(part),len(payload))+payload
    old_t=sum(r['decoder_tstates'] for r in baseline['blocks'][first:]);new_t=sum(r['native']['tstates'] for r in rows)
    first_frame=next(i for i,(lo,hi) in enumerate(zip(packets,packets[1:])) if lo<=start<hi)
    report=dict(complete=True,release=False,scope=__doc__,baseline_commit='8b03511',
        input_raw_sha256=sha(raw),baseline_stream_sha256=sha(stream),candidate_stream_sha256=sha(candidate),
        baseline_stream_bytes=len(stream),candidate_stream_bytes=len(candidate),
        byte_delta=len(candidate)-len(stream),baseline_sectors=(len(stream)+255)//256,
        candidate_sectors=(len(candidate)+255)//256,baseline_decoder_tstates=baseline['decoder_tstates'],
        candidate_decoder_tstates=baseline['decoder_tstates']-old_t+new_t,decoder_delta_tstates=new_t-old_t,
        tail_baseline_decoder_tstates=old_t,tail_candidate_decoder_tstates=new_t,
        first_changed_block=first,first_affected_frame=first_frame,last_affected_frame=len(packets)-2,
        changed_raw_bytes=len(raw)-start,block_count=len(old),first_slack=a.first_slack,
        cuts=cuts,cut_decisions=decisions,rows=rows,pc_compression_seconds=seconds,
        author_dll_sha256=sha(a.author.read_bytes()),native_code_sha256=sha(b''.join(data for _,data in regions)),
        original_prefix_identical=bytes(candidate[:old[first]['stream_start']])==stream[:old[first]['stream_start']],
        source_sha256_lf={n:sha((ROOT/n).read_bytes().replace(b'\r\n',b'\n')) for n in (
            'probe_lzsa2_resets.py','lzsa2_oracle_host.py','lzsa2_oracle_host.c','lzsa2_stream.py',
            'resumable_lzsa2.py','verify_lzsa2_dispatch.py','inplace_zx0.py')},
        caveat='Tail native decoder costs are measured on independent full-flags CPU with fixed 256-byte demands; unchanged prefix costs reused. Producer/carry and actual playback require separate verification.')
    (a.output/'video.stream').write_bytes(candidate);(a.output/'video.raw').write_bytes(raw)
    save(a.output/'probe.json',report)
    print(json.dumps({k:report[k] for k in ('byte_delta','baseline_sectors','candidate_sectors',
        'decoder_delta_tstates','first_affected_frame','last_affected_frame','cuts','pc_compression_seconds')}),flush=True)


if __name__=='__main__':main()
