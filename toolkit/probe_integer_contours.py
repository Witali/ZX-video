"""Full movie lossless contour/hybrid storage experiment, not a Z80 player.

Trace before dithering at the existing 128x72 logical active area; keep the
same native 256x144 pixels, attributes and AY. Exact grid contours and
simplified integer polygons with lossless span corrections are compared
with a hybrid that can select n-2 flat rectangles or a packed bitmap.
DEFLATE is only a layout screen; it does not predict ZX0 size or CPU time.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import struct

import cv2
import numpy as np
from PIL import Image,ImageDraw

import integer_contours as codec
from bulk_frame_stream import read_packet
from cell_audio_stream import take_tick
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header
from probe_lossless_layouts import sha,measure
from build_long_video_trd import expand_compact_screen
from build_zxv_trd import render_spectrum_screen


def levels(state):
    packed=state[384:2688]
    return ((packed[:,None]>>np.array([6,4,2,0]))&3).reshape(72,128).astype(np.uint8)


def rgb(values,attrs):
    state=bytearray(3072)+bytearray([1]*768)
    state[384:2688]=codec.packed_packet(values)[1:]; state[3168:3744]=attrs.tobytes()
    return render_spectrum_screen(*expand_compact_screen(bytes(state)))


def preview(states,rows,path):
    eligible=[r for r in rows if r['grid']['vertices']>20]
    best=min(eligible,key=lambda r:r['polygon']['bytes']/r['baseline_packet_bytes'])['index']
    worst=max(rows,key=lambda r:r['polygon']['pixels_before_correction'])['index']
    selected=list(dict.fromkeys((best,408,2858,3009,3686,worst)))
    sheet=Image.new('RGB',(3*256,len(selected)*220),(22,22,22)); draw=ImageDraw.Draw(sheet)
    for line,index in enumerate(selected):
        value=levels(states[index]); attrs=states[index,3168:3744]
        paths={s:codec.trace(value==s) for s in range(4)}
        epsilon=rows[index]['polygon']['epsilon']; _,detail,loops,approx=codec.polygon_packet(value,paths,epsilon)
        original=Image.fromarray(rgb(value,attrs)); overlay=original.copy(); pen=ImageDraw.Draw(overlay)
        for shade,polygons in loops.items():
            for polygon in polygons:
                if len(polygon)<2: continue
                points=[(int(x)*2,int(y)*2+24) for x,y in polygon]
                pen.line(points+[points[0]],fill=((255,90,90),(80,255,120),(80,170,255),(255,230,60))[shade])
        for col,(title,picture) in enumerate((('accepted',original),('integer contours',overlay),
                ('before exact corrections',Image.fromarray(rgb(approx,attrs))))):
            x,y=col*256,line*220
            draw.text((x+4,y+3),f'{index} | {title}',fill='white'); sheet.paste(picture,(x,y+23))
    path.parent.mkdir(parents=True,exist_ok=True); sheet.save(path)
    return dict(frames=selected,columns=['accepted','contour overlay','uncorrected diagnostic'],
        final_candidate_equals_accepted=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('states','raw','output','cache','preview'): p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--limit',type=int,default=0)
    args=p.parse_args()
    with np.load(args.states,allow_pickle=False) as f: states=f['states']
    raw=args.raw.read_bytes(); source=Reader(raw); _,_,count,_,_=read_header(source,magic=b'FAP3')
    if count!=len(states): raise ValueError('frame count differs')
    if not np.all(states[:,3072:3168]==1) or not np.all(states[:,3744:]==1): raise ValueError('attribute border differs')
    target=args.limit or count; args.cache.mkdir(parents=True,exist_ok=True)
    streams={name:bytearray(b'IVC1'+struct.pack('<HHH',128,72,target)) for name in ('grid','polygon','hybrid')}
    history=[np.zeros((72,128),dtype=np.uint8) for _ in range(2)]
    attr_history=[np.ones(576,dtype=np.uint8) for _ in range(2)]
    rows=[]; report=dict(scope=__doc__,complete=False,release=False,baseline_commit='2b3b4ce',
        states_sha256=sha(states.tobytes()),raw_sha256=sha(raw),frames_expected=count,frames_requested=target,
        opencv_version=cv2.__version__,player_changed=False,player_delta_tstates=0,
        z80_decoder_implemented=False,cadence_verified=False,disk_delivery_verified=False,
        sources=['https://potrace.sourceforge.net/potrace.pdf','https://docs.opencv.org/4.13.0/d3/dc0/group__imgproc__shape.html'])
    def save():
        prefix=json.dumps(report,indent=2)
        args.output.write_text(prefix[:-2]+',\n  "frames": [\n'+',\n'.join('    '+json.dumps(r) for r in rows)+'\n  ]\n}\n',encoding='utf-8')
    try:
        for i,state in enumerate(states[:target]):
            start=source.pos; _,packet=read_packet(source,stored_guards=False)
            value=levels(state); attrs=state[3168:3744]; ay=b''.join(packet['ticks'])
            attribute_packet=codec.pack_attributes(attrs,attr_history[i%2]); common=ay+attribute_packet
            paths={shade:codec.trace(value==shade) for shade in range(4)}
            grid,gstats,_,_=codec.polygon_packet(value,paths,0)
            if gstats['pixels_before_correction']: raise AssertionError(('exact grid differs',i))
            options=[codec.polygon_packet(value,paths,epsilon) for epsilon in (.5,1)]
            polygon,pstats,_,_=min(options,key=lambda item:len(item[0]))
            rect,rstats=codec.rectangle_packet(value,history[i%2]); raster=codec.packed_packet(value)
            choices=[('polygon',polygon),('rectangles',rect),('raster',raster)]
            hybrid_name,hybrid=min(choices,key=lambda pair:len(pair[1]))
            # Every stream is serialized, independently parsed and replayed.
            for name,geometry in (('grid',grid),('polygon',polygon),('hybrid',hybrid)):
                body=common+geometry; framed=struct.pack('<I',len(body))+body
                rr=codec.Reader(framed); br=codec.Reader(rr.take(struct.unpack('<I',rr.take(4))[0])); rr.end()
                if [take_tick(br) for _ in range(6)]!=packet['ticks']: raise AssertionError('AY changed')
                actual_attrs=codec.read_attributes(br,attr_history[i%2])
                restored=codec.decode_pixels(br.take(len(br.data)-br.pos),history[i%2]); br.end()
                if not np.array_equal(restored,value) or not np.array_equal(actual_attrs,attrs):
                    raise AssertionError(('vector frame differs',name,i))
                streams[name]+=framed
            row=dict(index=i,baseline_packet_bytes=source.pos-start,ay_bytes=len(ay),attribute_bytes=len(attribute_packet),
                grid=dict(bytes=len(grid),**gstats),polygon=dict(bytes=len(polygon),**pstats),
                rectangle_bytes=len(rect),rectangles=rstats['rectangles'],raster_bytes=len(raster),
                hybrid_mode=hybrid_name,hybrid_pixel_bytes=len(hybrid),final_pixel_errors=0,attribute_errors=0,ay_errors=0)
            rows.append(row); history[i%2]=value; attr_history[i%2]=attrs.copy()
            if i%200==0:
                save(); print(f'Integer contours verified {i+1}/{target}',flush=True)
        if target==count: source.end()
        results={}
        for name,stream in streams.items():
            (args.cache/(name+'.raw')).write_bytes(stream)
            results[name]=dict(raw_bytes=len(stream),sha256=sha(stream),deflate_8192_layout_screen=measure(stream,8192))
        report.update(complete=target==count,checked_frames=target,checked_ay_ticks=target*6,
            streams=results,baseline_raw_bytes=len(raw),baseline_deflate_8192_layout_screen=measure(raw,8192),
            modes=dict(Counter(r['hybrid_mode'] for r in rows)),
            summary=dict(mean_grid_vertices=float(np.mean([r['grid']['vertices'] for r in rows])),
                max_grid_vertices=max(r['grid']['vertices'] for r in rows),
                mean_polygon_vertices=float(np.mean([r['polygon']['vertices'] for r in rows])),
                max_polygon_vertices=max(r['polygon']['vertices'] for r in rows),
                mean_polygon_correction_pixels=float(np.mean([r['polygon']['pixels_before_correction'] for r in rows])),
                mean_polygon_edge_row_updates=float(np.mean([r['polygon']['edge_row_updates'] for r in rows])),
                mean_polygon_native_byte_touches=float(np.mean([r['polygon']['native_byte_touches_including_clear'] for r in rows])),
                max_polygon_native_byte_touches=max(r['polygon']['native_byte_touches_including_clear'] for r in rows),
                max_polygon_record_bytes=max(r['polygon']['bytes'] for r in rows)),
            preview=preview(states,rows,args.preview) if target==count else None)
        save(); print(json.dumps({k:v for k,v in report.items() if k not in ('scope','sources')},indent=2),flush=True)
    except Exception as exc:
        report['failure']=repr(exc); save(); raise


if __name__=='__main__': main()
