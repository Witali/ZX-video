"""Execute both packet readers with real ZX0 on the entire unchanged stream.

No frame reconstruction or rendering. AY is drained manually after each
packet to verify bytes, not 50-Hz timing. All ring input, block transitions,
copies, metadata and queue insertion execute on Z80. No idle lookahead,
ULA, ROM or physical disk; clocked playback is measured separately.
"""
import argparse
import json
from pathlib import Path
import struct
from collections import Counter

from bulk_frame_stream import read_packet
from benchmark_context_huffman import word
from frame_stream_harness import Harness
from frame_output_pipeline import INPUT
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header
from probe_lossless_layouts import sha
from probe_motion_metadata import restore


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('raw','storage','cache','output'): p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args(); raw=args.raw.read_bytes(); storage=json.loads(args.storage.read_text())
    if not storage['complete'] or storage['input_sha256']!=sha(raw): raise ValueError('different storage input')
    r=Reader(raw); _,_,count,mapping,tables=read_header(r,magic=b'FAP3'); header=raw[:r.pos]
    ring=bytearray(); ends=[0]; pos=0
    for block in storage['blocks']:
        data=raw[pos:pos+block['decoded_bytes']]; pos+=len(data); ends.append(pos)
        payload=(args.cache/(block['sha256']+'.zx0')).read_bytes()
        if sha(data)!=block['sha256'] or len(payload)!=block['zx0_bytes']: raise ValueError('cache differs')
        ring+=struct.pack('<HH',len(data),len(payload))+payload
    if pos!=len(raw): raise ValueError('incomplete block storage')
    variants={name:Harness(bytes(ring),tables,mapping,count,bulk=True,zero_copy=True,stored_guards=False,
        skip_noop_runs=True,constant_attribute_borders=True,skip_black_borders=True,skip_static_stripes=True,
        token_boundaries=True,pipelined=True,packet_ahead='idle',unrolled_copy=True,unrolled_cache=True,
        attribute_groups=True,attribute_flags=True,gray_cells=True,early_ay=early)
        for name,early in (('before',False),('after',True))}
    for h in variants.values(): h.consume_header(header); h.histogram.clear()
    report=dict(scope=__doc__,baseline_commit='c829610',complete=False,release=False,
        raw_sha256=sha(raw),compressed_bytes=len(ring),compressed_delta_bytes=0,frames_expected=count,
        parser_delta_formula_tstates=83,manual_ay_only=True,nominal_timing_verified=False,
        disk_delivery_verified=False,ula_verified=False,frames=[],variants={})
    def save():
        head=json.dumps({k:v for k,v in report.items() if k!='frames'},indent=2)
        args.output.write_text(head[:-2]+',\n  "frames": [\n'+',\n'.join('    '+json.dumps(v) for v in report['frames'])+'\n  ]\n}\n',encoding='utf-8')
    try:
        for i in range(count):
            _,d=read_packet(r,stored_guards=False); row=dict(index=i,raw_end=r.pos)
            ay_length=sum(map(len,d['ticks'])); offset=ay_length+5+195
            masks=restore(d['payload'][offset:offset+d['mask_bytes']],1,480,4)
            for name,h in variants.items():
                result=h.execute(h.p['read_packet']); cpu=h.cpu
                consumed=ends[h.blocks-1]+word(cpu,h.r['position'])
                if consumed!=r.pos: raise AssertionError(('raw cursor differs',i,name))
                expected=((INPUT,d['payload']+b'\0'),(0xba40,d['cache']),
                    (0xa4c0,masks),(word(cpu,h.frame.w['vector_pointer']),d['payload'][ay_length+8:ay_length+200]),
                    (word(cpu,h.frame.w['native_pointer']),d['payload'][d['coded_offset']-80:d['coded_offset']]))
                for address,blob in expected:
                    if bytes(cpu.read8(address+j) for j in range(len(blob)))!=blob:
                        raise AssertionError(('packet/metadata differs',i,name,address))
                if word(cpu,h.frame.w['coded_pointer'])!=INPUT+d['coded_offset'] or word(cpu,h.frame.w['literal_pointer'])!=INPUT+d['coded_offset']+d['coded_bytes']:
                    raise AssertionError('coded/literal cursor differs')
                for bank,screen in h.expected_screens.items():
                    if bytes(cpu.banks[bank][:6912])!=screen: raise AssertionError('parser wrote a native screen')
                if bytes(cpu.banks[5][0x1b00:0x2400])!=b'\xa5'*0x900: raise AssertionError('TR-DOS changed')
                h.drain_six(d['ticks'])
                row[name]=dict(tstates=result['tstates'],stages=result['stages'])
            if row['after']['stages']['packet']-row['before']['stages']['packet']!=83:
                raise AssertionError('parser timing delta differs')
            report['frames'].append(row)
            if i%250==0: save(); print(f'Early AY packet pair verified {i+1}/{count}',flush=True)
        r.end()
        for name,h in variants.items():
            if h.cpu.consumed!=len(ring) or word(h.cpu,h.r['block_left']): raise AssertionError('incomplete EOF')
            stages=Counter()
            for row in report['frames']: stages.update(row[name]['stages'])
            report['variants'][name]=dict(tstates=sum(stages.values()),stages=dict(stages),
                parser_bytes=h.p['end']-0xdc00,parser_end=h.p['end'],
                parser_code_hex=next(blob.hex() for base,blob in h.regions if base==0xdc00),
                instruction_listing=[v for v in h.instructions.values() if v['phase']=='packet'])
        report.update(complete=True,checked_frames=count,verified_manual_ay_ticks=count*6,
            delta_tstates=report['variants']['after']['tstates']-report['variants']['before']['tstates'])
    except Exception as exc:
        report['failure']=repr(exc); save(); raise
    save(); print(json.dumps({k:v for k,v in report.items() if k in ('complete','checked_frames','delta_tstates','verified_manual_ay_ticks')},indent=2),flush=True)


if __name__=='__main__': main()
