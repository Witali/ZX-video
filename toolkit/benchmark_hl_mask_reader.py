"""Paired instruction execution of IX and alternate-HL masks on all volume frames."""
import argparse
import json
from pathlib import Path
import compiled_masks_z80 as compiled
from benchmark_bank_local_zx0 import disk_blocks
from build_fap3_trd import sha
from bulk_frame_stream import read_packet
from probe_motion_entropy import Reader
from probe_motion_metadata import restore
from probe_spatial_contexts import read_header
from test_compiled_masks_z80 import CompiledMaskTests,INPUT
from test_hl_mask_reader import HLMaskTests


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('directory','raw-directory','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();report=dict(complete=False,release=False,scope=__doc__,baseline_commit='1d69dbf',volumes=[],
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        source_sha256={n:sha(Path(__file__).with_name(n).read_bytes()) for n in
            ('benchmark_hl_mask_reader.py','compiled_masks_z80.py','test_compiled_masks_z80.py','test_hl_mask_reader.py','validate_fast_sparse.py')},
        stream_delta_bytes=0,code_growth_bytes=7,extra_stack_bytes=2,models_metadata_only=True,
        excludes=['ULA','IRQ','ROM','disk','full frame reconstruction and rendering'])
    def save():a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    a.output.parent.mkdir(parents=True,exist_ok=True);save();next_frame=0
    for part in (1,2,3):
        meta_path=a.directory/f'ZX-video-huffman-preview_part{part:02}.json';m=json.loads(meta_path.read_bytes())
        _,stream,blocks=disk_blocks(a.directory,part);actual=Reader(b''.join(decoded for _,decoded in blocks))
        raw=(a.raw_directory/f'volume-{part}.raw').read_bytes();start,end=m['frame_start'],m['frame_end_exclusive']
        if sha(raw)!=m['raw_sha256'] or start!=next_frame:raise ValueError('wrong input/partition')
        r=Reader(raw);_,_,count,_,_=read_header(r,magic=b'FAP3');fixtures=[]
        for cls in (CompiledMaskTests,HLMaskTests):
            h=cls();h.setUp();ticks=h.initialize()
            for address,blob in h.expected:
                if h.read(address,len(blob))!=blob:raise ValueError('generator differs')
            if ticks!=201509:raise ValueError('initializer changed timing')
            fixtures.append(h)
        row=dict(part=part,raw_sha256=sha(raw),metadata_sha256=sha(meta_path.read_bytes()),
            stream_sha256=sha(stream),frame_start=start,frame_end_exclusive=end,frames=[]);report['volumes'].append(row)
        for index in range(count):
            _,d=read_packet(r,stored_guards=False)
            if not start<=index<end:continue
            pos=sum(map(len,d['ticks']))+8+192;encoded=d['payload'][pos:pos+d['mask_bytes']]
            _,on_disk=read_packet(actual,stored_guards=False)
            disk_pos=sum(map(len,on_disk['ticks']))+8+192
            if encoded!=on_disk['payload'][disk_pos:disk_pos+on_disk['mask_bytes']]:raise ValueError('actual TRD masks differ')
            expected=restore(encoded,1,480,4);values=[]
            for h in fixtures:
                h.install(INPUT,encoded);h.install(compiled.MASKS,bytes(v^255 for v in expected))
                h.install(compiled.FLAGS,bytes([0xa5])*64);h.cpu.set_hl(INPUT)
                ticks=h.run_code(h.labels['decode'],[(compiled.MASKS,compiled.MASKS+480),(compiled.FLAGS,compiled.FLAGS+64)])
                if (ticks!=compiled.expected_tstates(encoded,hl_flags=h.hl_flags) or h.read(compiled.MASKS,480)!=expected or
                    h.read(compiled.FLAGS+60,4)!=bytes(4) or h.cpu.hl()!=INPUT+len(encoded) or h.read(INPUT,len(encoded))!=encoded):
                    raise ValueError(('decoded bytes, cursor or instruction timing differ',part,index))
                values.append(ticks)
            if values[1]-values[0]!=-499:raise ValueError('unexpected frame delta')
            row['frames'].append(dict(frame=index,encoded_bytes=len(encoded),baseline_tstates=values[0],hl_tstates=values[1],delta_tstates=-499))
            if len(row['frames'])%400==0:save();print(f'Disk {part}: {len(row["frames"])}/{end-start} exact masks',flush=True)
        r.end();actual.end();next_frame=end
        if len(row['frames'])!=end-start:raise ValueError('missing frames')
        row.update(checked_frames=len(row['frames']),**{k:sum(v[k] for v in row['frames']) for k in ('baseline_tstates','hl_tstates','delta_tstates')});save()
    if next_frame!=count:raise ValueError('missing ending')
    report.update(complete=True,checked_frames=next_frame,all_masks_exact=True,source_unchanged=True,
        **{k:sum(v[k] for v in report['volumes']) for k in ('baseline_tstates','hl_tstates','delta_tstates')})
    save();print(json.dumps({k:v for k,v in report.items() if k not in ('volumes','source_sha256')}),flush=True)


if __name__=='__main__':main()
