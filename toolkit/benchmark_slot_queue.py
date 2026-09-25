"""Compare exact packet consumption by the four-slot and old stream readers.

Both consume the same two requests per frame. The new queue is filled before
each frame to exercise all four retained banks; this is an offline CPU cost
comparison, not a schedule. Old ring delivery is ideal, new ROM calls are
mocked. No frame reconstruction, IRQ, ULA or physical disk time is counted.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import struct

from benchmark_bank_local_zx0 import disk_blocks,sha
from benchmark_direct_slot_input import Harness as Producer
from test_slot_queue import QueueHarness
from stream_reader_harness import Harness as OldReader


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--directory',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();report=dict(complete=False,release=False,scope=__doc__,baseline_commit='248db65',volumes=[])
    def save():args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    for part in (1,2,3):
        meta,stream,blocks=disk_blocks(args.directory,part)
        image=(args.directory/f'ZX-video-huffman-preview_part{part:02}.trd').read_bytes()
        q=QueueHarness(Producer(image,meta['video_start_sector'],meta['video_sectors']),len(blocks))
        old=OldReader(stream,ring_start=0,token_boundaries=True,unrolled_copy=True,inline_matches=True)
        raw=b''.join(b for _,b in blocks);at=0;frames=[]
        row=dict(part=part,stream_sha256=sha(stream),raw_sha256=sha(raw),trd_sha256=sha(image),frames=frames)
        report['volumes'].append(row)
        for frame in range(meta['frames']):
            fill=q.call(q.q['prefill'])
            size=struct.unpack_from('<H',raw,at)[0];new_ticks=old_ticks=0
            for count in (2,size):
                wanted=raw[at:at+count];at+=count
                if q.take(count)!=wanted or old.take(count)!=wanted:raise AssertionError('packet bytes differ')
                new_ticks+=q.calls[-1][1];old_ticks+=old.rows[-1]['tstates']
            frames.append(dict(index=meta['frame_start']+frame,bytes=2+size,queue_fill_tstates=fill,
                queue_take_tstates=new_ticks,old_reader_tstates=old_ticks))
            if frame%300==0:save();print(f'Exact queue packets: disk {part}, frame {frame}/{meta["frames"]}',flush=True)
        if at!=len(raw) or q.cpu.read8(q.q['count']) or [r['sector'] for r in q.cpu.reads]!=q.h.positions:
            raise AssertionError('queue EOF or sector sequence differs')
        costs=Counter()
        for (pc,t),n in q.histogram.items():
            phase=q.instructions[pc]['phase'] if pc in q.instructions else 'local_zx0'
            costs[phase]+=t*n
        total=sum(t for _,t in q.calls)
        if total!=sum(costs.values()):raise AssertionError('CPU histogram differs')
        row.update(summary=dict(raw_bytes=at,blocks=len(blocks),packets=len(frames),sectors=len(q.cpu.reads),
            old_reader_tstates=sum(f['old_reader_tstates'] for f in frames),queue_total_tstates=total,stages=dict(costs)),
            instruction_histogram=[dict(address=pc,tstates=t,count=n) for (pc,t),n in sorted(q.histogram.items())])
        print(json.dumps(row['summary']),flush=True);save()
    report['complete']=True;save()


if __name__=='__main__':main()
