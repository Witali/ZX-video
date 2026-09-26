"""Verify saved decoder equivalence and cold-installed references, including JR.

This is not a new playback measurement. Complete Fuse evidence is checked by
summarize_integrated_bootstrap.py; deterministic decoder costs exclude ULA.
"""
import argparse
import json
from pathlib import Path

from bank2_zx0 import build
from benchmark_bank_local_zx0 import disk_blocks
from build_fap3_trd import player_harness,sha
import bulk_frame_z80 as packet
import fap3_disk_z80 as disk
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header
from test_fap3_disk import DiskCPU
from test_warm_continuation import player,until


def verify_cpu(path):
    r=json.loads(path.read_bytes());_,_,machine=build()
    if (not r['complete'] or r['machine']!=machine or
        r['source_sha256']!=sha(Path(__file__).with_name('benchmark_bank2_zx0.py').read_bytes())):
        raise ValueError('decoder evidence changed')
    count=decoded=total=0
    for volume in r['volumes']:
        subtotal=0
        if not volume['complete']:raise ValueError('incomplete volume')
        for block in volume['blocks']:
            slices=block['slices'];ticks=sum(s['tstates'] for s in slices)
            if (ticks!=block['tstates'] or ticks!=block['baseline_tstates'] or block['delta_tstates'] or
                slices[-1]['target']!=block['bytes'] or slices[-1]['produced']!=block['bytes'] or
                any(s['irq_tstates'] or not s['target']<=s['produced']<=block['bytes'] for s in slices)):
                raise ValueError('inconsistent block evidence')
            count+=1;decoded+=block['bytes'];subtotal+=ticks
        if subtotal!=volume['tstates'] or subtotal!=volume['baseline_tstates']:raise ValueError('volume CPU total')
        total+=subtotal
    if (count!=r['blocks'] or decoded!=r['decoded_bytes'] or total!=r['tstates'] or
        total!=r['baseline_tstates'] or r['delta_tstates']):raise ValueError('decoder CPU total')
    return dict(blocks=count,decoded_bytes=decoded,baseline_tstates=total,tstates=total,delta_tstates=0)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('directory','raw-directory','default-directory','baseline-directory','output'):
        p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--cpu',type=Path,default=Path('toolkit/bank2_zx0_cpu.json'))
    a=p.parse_args();cpu=verify_cpu(a.cpu);volumes=[]
    saved=json.loads(a.cpu.read_bytes())
    for part in (1,2,3):
        m,stream,blocks=disk_blocks(a.directory,part)
        default,default_stream,_=disk_blocks(a.default_directory,part)
        old,old_stream,_=disk_blocks(a.baseline_directory,part)
        if default['trd_sha256']!=old['trd_sha256'] or stream!=old_stream or default_stream!=old_stream:
            raise ValueError('default TRD or compressed stream changed')
        v=saved['volumes'][part-1]
        if v['trd_sha256']!=old['trd_sha256'] or len(blocks)!=len(v['blocks']):raise ValueError('different CPU input')
        for (packed,raw),b in zip(blocks,v['blocks']):
            if sha(packed)!=b['compressed_sha256'] or sha(raw)!=b['raw_sha256']:raise ValueError('CPU block changed')
        raw=(a.raw_directory/f'volume-{part}.raw').read_bytes()
        if sha(raw)!=m['raw_sha256']:raise ValueError('wrong raw stream')
        _,_,_,mapping,tables=read_header(Reader(raw),magic=b'FAP3')
        h=player_harness(bytes(4),tables,mapping,m['frames'],
            **{key:old[key] for key in ('inline_matches','fast_noop_scan','irq_safe_paging',
                'static_cache_borders','carry_huffman','register_fragments')},cached_huffman_byte=True)
        _,_,_,packet_rows=packet.build(m['decoder_labels'],m['queue_labels'],h.frame.w,h.frame.draw,
            m['compiled_masks']['labels'],h.audio,stored_guards=False,separate_prepare='idle',page_entry=0x9780)
        rows={pc:row for pc,row in h.frame.instructions.items() if pc<0xc000}
        rows.update({r['address']:r for r in m['slot_queue_instruction_listing']+packet_rows})
        image=(a.directory/f'ZX-video-huffman-preview_part{part:02}.trd').read_bytes()
        c=DiskCPU(player(image),image);until(c,disk.DRIVER)
        relocation=m['bank2_zx0'];checked=relative=0
        retired=[(r['start'],r['end']) for r in m['retired_fixed_code']]
        for pc,row in sorted(rows.items()):
            if (relocation['new_origin']<=pc<relocation['new_end'] or row.get('phase')=='cold_init' or
                any(lo<=pc<hi for lo,hi in retired)):continue
            op=c.read8(pc);name=row['instruction'];offset=None;branch=False
            if name.startswith(('JR ','DJNZ ')) and op in (0x10,0x18,0x20,0x28,0x30,0x38):
                target=pc+2+int.from_bytes(bytes([c.read8(pc+1)]),'little',signed=True)
                relative+=1;branch=True
            else:
                if name.startswith('LD '):
                    if op in (0x01,0x11,0x21,0x31,0x22,0x2a,0x32,0x3a):offset=1
                    if op in (0xdd,0xfd) and c.read8(pc+1) in (0x21,0x22,0x2a):offset=2
                    if op==0xed and c.read8(pc+1) in (0x43,0x4b,0x53,0x5b,0x63,0x6b,0x73,0x7b):offset=2
                if name.startswith(('JP ','CALL ')) and op in (0xc3,0xc2,0xca,0xd2,0xda,0xe2,0xea,0xf2,0xfa,0xcd,0xc4,0xcc,0xd4,0xdc,0xe4,0xec,0xf4,0xfc):
                    offset=1;branch=True
                if offset is None:continue
                target=c.read8(pc+offset)+256*c.read8(pc+offset+1)
            checked+=1
            if relocation['old_origin']<=target<relocation['old_end']:
                raise ValueError(('stale decoder reference',hex(pc),hex(target)))
            if branch and relocation['new_origin']<=target<relocation['new_end']:
                # Only the explicitly relocated ZX0 entry calls may enter.
                if not any(x['address']==pc and x['new_operand']==target for x in relocation['external_operands']):
                    raise ValueError(('old bitmap branch enters decoder',hex(pc),hex(target)))
        volumes.append(dict(part=part,trd_sha256=m['trd_sha256'],default_trd_sha256=default['trd_sha256'],
            default_byte_exact=True,stream_byte_exact=True,cold_operand_checks=checked,relative_branch_checks=relative))
    result=dict(complete=True,release=False,scope=__doc__,cpu=cpu,volumes=volumes,
        cpu_report_sha256=sha(a.cpu.read_bytes()),source_sha256=sha(Path(__file__).read_bytes()))
    a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
