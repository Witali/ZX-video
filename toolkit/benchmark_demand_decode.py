"""Pair full-block and demand-sized consumers on all exact TRD packets.

Both use inline ZX0 literals and the same stream. One initial prefill, no
background refill: CPU/ownership comparison only. ROM services are mocked;
rendering, IRQ/ULA and disk latency excluded. Each copied byte is guarded.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import struct

from benchmark_bank_local_zx0 import disk_blocks,sha
from benchmark_context_huffman import word
from benchmark_direct_slot_input import Harness as Producer
from benchmark_partial_slots import install_copy_guard
from test_slot_queue import QueueHarness
from zx0_speed import parse


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--directory',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    report=dict(complete=False,release=False,scope=__doc__,baseline_commit='673b794',
        source_sha256=sha(Path(__file__).read_bytes()),volumes=[],
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    def save():args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    for part in (1,2,3):
        meta,stream,blocks=disk_blocks(args.directory,part)
        image=(args.directory/f'ZX-video-huffman-preview_part{part:02}.trd').read_bytes()
        raw=b''.join(data for _,data in blocks)
        literal_tokens=0
        for payload,wanted in blocks:
            decoded,tokens=parse(payload)
            if decoded!=wanted:raise AssertionError('independent token parser differs')
            literal_tokens+=sum(not t.offset for t in tokens)
        hs={name:QueueHarness(Producer(image,meta['video_start_sector'],meta['video_sectors'],inline_literals=True),len(blocks),demand_decode=demand)
            for name,demand in (('baseline',False),('demand',True))}
        guards={name:install_copy_guard(h) for name,h in hs.items()}
        row=dict(part=part,trd_sha256=sha(image),stream_sha256=sha(stream),raw_sha256=sha(raw),
            frame_start=meta['frame_start'],frames_expected=meta['frames'],blocks=len(blocks),
            literal_tokens=literal_tokens,
            code={name:dict(bytes=len(h.h.decoder.code),sha256=sha(h.h.decoder.code),
                hex=h.h.decoder.code.hex(),labels=h.h.decoder.labels) for name,h in hs.items()},
            queue_regions={name:[dict(address=a,bytes=len(blob),sha256=sha(blob)) for a,blob in h.regions] for name,h in hs.items()},
            instruction_listing={name:list(h.instructions.values()) for name,h in hs.items()},
            prefill={},frames=[],complete=False)
        report['volumes'].append(row)
        for name,h in hs.items():row['prefill'][name]=h.call(h.q['prefill'])
        at=0
        for index in range(meta['frames']):
            size=struct.unpack_from('<H',raw,at)[0];frame=dict(frame=meta['frame_start']+index,bytes=size+2)
            for name,h in hs.items():
                start,reads=h.cpu.tstates,len(h.cpu.reads)
                if h.take(2)!=raw[at:at+2] or h.take(size)!=raw[at+2:at+2+size]:raise AssertionError('packet differs')
                frame[name]=dict(tstates=h.cpu.tstates-start,sectors=len(h.cpu.reads)-reads)
            frame['delta_tstates']=frame['demand']['tstates']-frame['baseline']['tstates']
            row['frames'].append(frame);at+=size+2
            if index%250==0:save();print(f'Disk {part}: paired exact packets {index+1}/{meta["frames"]}',flush=True)
        if at!=len(raw):raise AssertionError('raw EOF differs')
        row['summary']={}
        for name,h in hs.items():
            if (h.cpu.read8(h.q['count']) or word(h.cpu,h.q['blocks_left']) or
                [r['sector'] for r in h.cpu.reads]!=h.h.positions or guards[name]['checked_copy_bytes']!=len(raw)):
                raise AssertionError('queue EOF, copied byte count or disk order differs')
            stages=Counter()
            for (pc,t),n in h.histogram.items():stages[h.instructions[pc]['phase'] if pc in h.instructions else 'local_zx0']+=t*n
            total=sum(t for _,t in h.calls)
            if sum(stages.values())!=total:raise AssertionError('accounting differs')
            row['summary'][name]=dict(tstates=total,stages=dict(stages),sectors=len(h.cpu.reads),**guards[name],
                instruction_histogram=[dict(pc=pc,tstates=t,count=n) for (pc,t),n in sorted(h.histogram.items())])
        measured=row['summary']['demand']['tstates']-row['summary']['baseline']['tstates']
        row.update(complete=True,delta_tstates=measured);save()
        print(json.dumps(dict(part=part,delta_tstates=measured)),flush=True)
    report.update(complete=True,checked_frames=sum(len(v['frames']) for v in report['volumes']),
        totals={name:sum(v['summary'][name]['tstates'] for v in report['volumes']) for name in ('baseline','demand')},
        delta_tstates=sum(v['delta_tstates'] for v in report['volumes']))
    save();print(json.dumps({k:v for k,v in report.items() if k!='volumes'}),flush=True)


if __name__=='__main__':main()
