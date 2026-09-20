"""Execute real FAP3/ZX0 with compact lookahead and IM2 screen publication.

Full verification means all source frames, both native screens, every 50-Hz
AY record and EOF in one CPU/RAM. Disk producer is ideal; ULA/TR-DOS latency
and physical volume boundaries are NOT verified. --limit makes a virtual
short volume for diagnostics; its final packet/audio drain are still tested.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import struct

import numpy as np

from benchmark_context_huffman import word
from bulk_frame_stream import unpack as unpack_bulk,read_packet
from cell_audio_stream import unpack as unpack_audio
from frame_packet_stream import unpack
from frame_output_pipeline import frames,display_screen
from frame_stream_harness import Harness
from pipelined_frame_harness import Clock,FIELD
import disk_progress_z80 as progress
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header
from probe_sparse_motion_cache import unpack as unpack_cache
from probe_lossless_layouts import sha


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('raw','states','storage-report','cache','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--limit',type=int,default=0)
    p.add_argument('--lookahead',action='store_true')
    p.add_argument('--unrolled-copy',action='store_true',help='Copy decoded packets with groups of 32 LDI')
    p.add_argument('--unrolled-cache',action='store_true',help='Copy motion cache rows in pairs; unchanged FAP3 bytes')
    p.add_argument('--attribute-groups',action='store_true',help='Render attributes using both preceding n-1 group lists')
    p.add_argument('--packet-ahead',action='store_true',help='Preparse another packet/AY while retaining the current native mask')
    p.add_argument('--packet-ahead-policy',choices=('always','idle'),default='always',
        help='With idle, draw a ready compact frame before optional input if the prior screen is already published')
    p.add_argument('--progress-frames',type=int)
    args=p.parse_args()
    raw=args.raw.read_bytes()
    if raw[:4]!=b'FAP3': raise ValueError('this experiment requires FAP3')
    with np.load(args.states,allow_pickle=False) as saved: states=saved['states']
    cells=unpack_audio(unpack_cache(unpack(unpack_bulk(raw)),32,4))[0]
    tables,mapping,packets=frames(cells)
    storage=json.loads(args.storage_report.read_text(encoding='utf-8'))
    if not storage['complete'] or storage['input_sha256']!=sha(raw): raise ValueError('wrong storage input')
    r=Reader(raw); _,_,count,_,_=read_header(r,magic=b'FAP3'); header=raw[:r.pos]
    if len(states)!=count or len(packets)!=count: raise ValueError('frame counts differ')
    if not np.all(states[:,3072:3168]==1) or not np.all(states[:,3744:]==1):
        raise ValueError('attribute borders differ')
    from causal_tile_z80 import validate_static_stripes
    for group,_ in packets: validate_static_stripes(group[3],group[4])
    target=args.limit or count
    if not 1<=target<=count: p.error('invalid limit')
    if args.progress_frames is not None and args.progress_frames!=target:
        p.error('--progress-frames must match the tested virtual volume length')
    details=[]; ticks=[]
    for _ in range(count):
        _,detail=read_packet(r,stored_guards=False); detail['raw_end']=r.pos
        details.append(detail); ticks.extend(detail['ticks'])
    r.end()
    ring=bytearray(); ends=[0]; position=0
    for block in storage['blocks']:
        data=raw[position:position+block['decoded_bytes']]; position+=len(data); ends.append(position)
        payload=(args.cache/(block['sha256']+'.zx0')).read_bytes()
        if sha(data)!=block['sha256'] or len(payload)!=block['zx0_bytes']: raise ValueError('cached block differs')
        ring+=struct.pack('<HH',len(data),len(payload))+payload
    if position!=len(raw): raise ValueError('incomplete blocks')
    h=Harness(bytes(ring),tables,mapping,target,bulk=True,zero_copy=True,stored_guards=False,
        skip_noop_runs=True,constant_attribute_borders=True,skip_black_borders=True,
        skip_static_stripes=True,token_boundaries=True,pipelined=True,progress_frames=args.progress_frames,
        packet_ahead='idle' if args.packet_ahead and args.packet_ahead_policy=='idle' else args.packet_ahead,
        unrolled_copy=args.unrolled_copy,unrolled_cache=args.unrolled_cache,attribute_groups=args.attribute_groups)
    header_result=h.consume_header(header); h.histogram.clear()
    checked=dict(compact=0,native=0,publish=0); bar_frames=0
    if args.packet_ahead: checked['packet']=0
    screens=dict(h.expected_screens)
    def observe(kind,clock):
        i=checked[kind]; cpu=h.cpu
        if i>=target: raise AssertionError(('extra frame',kind,i))
        if kind=='packet':
            detail=details[i]; pos=h.r['position']-0xc000
            consumed=ends[h.blocks-1]+int.from_bytes(cpu.banks[7][pos:pos+2],'little')
            if consumed!=detail['raw_end']: raise AssertionError(('packet input cursor differs',i))
            if bytes(cpu.read8(0xa6a0+j) for j in range(len(detail['payload'])))!=detail['payload']:
                raise AssertionError(('lookahead packet differs',i))
            if checked['compact']:
                previous_map=packets[checked['compact']-1][1]
                if bytes(cpu.read8(0xbf20+j) for j in range(80))!=previous_map:
                    raise AssertionError(('packet input overwrote pending native map',i))
        elif kind=='compact':
            if bytes(cpu.banks[5][0x2400:0x3300])!=states[i].tobytes(): raise AssertionError(('compact differs',i))
            group,native=packets[i]; detail=details[i]; base=0xa6a0+detail['coded_offset']
            pos=h.r['position']-0xc000
            consumed=ends[h.blocks-1]+int.from_bytes(cpu.banks[7][pos:pos+2],'little')
            bits=(word(cpu,h.frame.recon['source'])-base)*8+(cpu.read8(h.frame.recon['bit_page'])&7)
            if (consumed!=detail['raw_end'] or bits!=group[2]
                    or word(cpu,h.frame.recon['literal_source'])!=base+detail['coded_bytes']+detail['literal_bytes']):
                raise AssertionError(('packet/bit/literal cursor differs',i))
            for address,wanted in ((word(cpu,h.frame.w['vector_pointer']),group[3]),
                    (0xa4c0,group[4]+group[5]),(word(cpu,h.frame.w['native_pointer']),native),
                    (0xba40,detail['cache']),(0xa6a0,detail['payload']+b'\0')):
                if bytes(cpu.read8(address+j) for j in range(len(wanted)))!=wanted:
                    raise AssertionError(('input mutated',i,address))
            if args.packet_ahead and bytes(cpu.read8(0xbf20+j) for j in range(80))!=native:
                raise AssertionError(('saved native map differs',i))
            for address,wanted in h.frame.protected_regions:
                bank=5 if address<0x8000 else 2 if address<0xc000 else 6
                if bytes(cpu.banks[bank][address&16383:(address&16383)+len(wanted)])!=wanted:
                    raise AssertionError(('tables mutated',i,address))
        elif kind=='native':
            bank=7 if i%2==0 else 5; screens[bank]=display_screen(states[i].tobytes(),black_borders=True)
        elif (7 if cpu.port_7ffd&8 else 5)!=(7 if i%2==0 else 5):
            raise AssertionError(('published wrong bank',i))
        if kind not in ('compact','packet'):
            for bank,screen in screens.items():
                wanted=progress.reference_screen(screen,bar_frames,args.progress_frames) if h.progress else screen
                if bytes(cpu.banks[bank][:6912])!=wanted: raise AssertionError(('native differs',kind,i,bank))
        if bytes(cpu.banks[5][0x1b00:0x2400])!=b'\xa5'*0x900: raise AssertionError('TR-DOS workspace changed')
        checked[kind]+=1
    clock=Clock(h,ticks[:target*6],lookahead=args.lookahead,observer=observe)
    report=dict(scope=__doc__,baseline_commit='a4a3f82' if args.attribute_groups else '4b62e52' if args.unrolled_cache else '0e8acec' if args.unrolled_copy else 'a50aa55' if args.packet_ahead else '1f58971',complete=False,release=False,
        frames_expected=count,frames_requested=target,raw_sha256=sha(raw),states_sha256=sha(states.tobytes()),
        compressed_bytes=len(ring),compressed_stream_delta_bytes=0,lookahead=args.lookahead,packet_ahead=h.packet_ahead,
        unrolled_copy=args.unrolled_copy,
        unrolled_cache=args.unrolled_cache,
        attribute_groups=args.attribute_groups,
        progress_frames_on_virtual_volume=args.progress_frames,disk_delivery_verified=False,ula_verified=False,
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        code_regions=[dict(base=base,code_hex=blob.hex()) for base,blob in h.regions],
        reconstruction_bytes=len(h.frame.recon_code),wrapper_code_hex=h.frame.wrapper_code.hex(),
        output_code_hex=h.frame.draw_code.hex(),clock_labels=clock.labels,video_labels=h.video,
        audio_labels=h.audio,decoder_labels=h.z,reader_labels=h.r,packet_labels=h.p,
        instruction_listing=list(h.instructions.values()),header_results=header_result,runs=[])
    def save():
        report.update(checked=checked.copy(),publications=clock.publications,events=clock.events,
            played_ay_ticks=clock.ticks,irq_tstates=clock.irq_tstates,idle_tstates=clock.idle_tstates)
        report['instruction_histogram']=[dict(address=a,tstates=t,count=n) for (a,t),n in sorted(h.histogram.items())]
        report['irq_instruction_histogram']=[dict(address=a,tstates=t,count=n) for (a,t),n in sorted(clock.irq_histogram.items())]
        report['foreground_tstates']=sum(t*n for (a,t),n in h.histogram.items())
        phase=Counter()
        for (address,t),n in h.histogram.items():
            row=h.instructions.get(address)
            name=row['phase'] if row else 'banked_zx0' if 0x7c00<=address<h.z['state'] else 'audio'
            phase[name]+=t*n
        report['foreground_stages']=dict(phase)
        pubs=clock.publications
        if pubs:
            offsets=[r['tstates']-pubs[0]['tstates']-i*6*FIELD for i,r in enumerate(pubs)]
            report['timing']=dict(late_frames=sum(r['late_fields']>0 for r in pubs),
                first_late=next((i for i,r in enumerate(pubs) if r['late_fields']),None),
                max_late_fields=max(r['late_fields'] for r in pubs),max_phase_tstates=max(offsets),
                min_phase_tstates=min(offsets),on_time_phase_range_tstates=[min(x for x,r in zip(offsets,pubs) if not r['late_fields']),
                    max(x for x,r in zip(offsets,pubs) if not r['late_fields'])],
                phases_tstates=offsets,publication_interrupted_phases=dict(Counter(r['interrupted_phase'] for r in pubs)),
                publication_interrupted_banks=dict(Counter(r['interrupted_bank'] for r in pubs)))
        args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    try:
        report['prime']=clock.prime(); report['runs'].append(clock.start()); bar_frames=1
        for index in range(1,target):
            report['runs'].append(clock.play_one()); bar_frames+=1
            if index%100==0:
                save(); print(f'IRQ pipeline verified {index+1}/{target} publications, {clock.ticks} AY ticks',flush=True)
        report['drain']=clock.drain()
        if checked!=dict.fromkeys(checked,target) or clock.ticks!=target*6: raise AssertionError('incomplete video/AY')
        if word(h.cpu,h.r['position'])+ends[h.blocks-1]!=details[target-1]['raw_end']:
            raise AssertionError('read beyond final requested packet')
        if target==count and (h.cpu.consumed!=len(ring) or word(h.cpu,h.r['block_left'])):
            raise AssertionError('incomplete EOF')
        report['complete']=target==count
        report['requested_scope_complete']=True
    except (AssertionError,RuntimeError) as exc:
        report['failure']=dict(error=str(exc),pc=h.cpu.pc,tstates=h.cpu.tstates,
            fields=word(h.cpu,h.audio['elapsed_fields']),checked=checked.copy())
        save(); raise
    save()
    print(json.dumps(dict(checked=checked,timing={k:v for k,v in report['timing'].items() if k!='phases_tstates'},
        complete=report['complete'],foreground_tstates=report['foreground_tstates'])),flush=True)


if __name__=='__main__': main()
