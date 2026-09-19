"""Framewise quality and instruction-table projection for static black borders.

Only the accepted compact frame's external fields are zeroed for display;
the active picture, all encoded bytes and AY remain unchanged. This does
not stand in for a full Z80 cadence/disk run.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image,ImageDraw

import build_long_video_trd as video
from cell_screen_z80 import expected_tstates
from frame_output_pipeline import frames,display_screen
from probe_lossless_layouts import sha


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('states','cells','baseline','output','preview'):
        p.add_argument('--'+name,type=Path,required=True)
    args = p.parse_args()
    with np.load(args.states,allow_pickle=False) as saved: states = saved['states']
    old = json.loads(args.baseline.read_text(encoding='utf-8'))
    data = args.cells.read_bytes(); _,_,packets = frames(data)
    if (not old['complete'] or old['states_sha256'] != sha(states.tobytes()) or len(packets) != len(states)
            or not np.all(states[:,3072:3168] == 1) or not np.all(states[:,3744:] == 1)):
        raise ValueError('matching full baseline and black-paper borders required')
    top,bottom = video.build_player_dither_tables()
    weights = np.array([a.bit_count()+b.bit_count() for a,b in zip(top,bottom)],dtype=np.uint8)
    if weights[0]: raise AssertionError('zero compact pixels must expand to black')
    outside = np.concatenate((states[:,:384],states[:,2688:3072]),axis=1)
    native_changes = weights[outside].sum(axis=1)
    logical_changes = np.count_nonzero((outside[...,None] >> np.array([6,4,2,0],dtype=np.uint8))&3,axis=(1,2))
    rows = []
    for i,(_,mask) in enumerate(packets):
        original = expected_tstates(mask,fast_mask_dispatch=True)
        attrs = expected_tstates(mask,fast_mask_dispatch=True,constant_attribute_borders=True)
        clean = expected_tstates(mask,fast_mask_dispatch=True,constant_attribute_borders=True,skip_black_borders=True)
        if original != old['frames'][i]['stages']['output']: raise AssertionError('native mask/CPU baseline differs')
        rows.append(dict(index=i,changed_logical_border_pixels=int(logical_changes[i]),
            changed_native_border_pixels=int(native_changes[i]),changed_active_pixels=0,
            output_before=original,output_after=clean,output_delta=clean-original,
            bitmap_border_delta=clean-attrs,projected_foreground=old['frames'][i]['tstates']+clean-original))
    affected = np.flatnonzero(native_changes)
    chosen = list(dict.fromkeys([int(affected[0]),*map(int,np.argsort(native_changes,kind='stable')[-3:][::-1])])) if len(affected) else [0]
    sheet = Image.new('RGB',(3*512,len(chosen)*414),(28,28,28)); draw = ImageDraw.Draw(sheet)
    for y,i in enumerate(chosen):
        before = b''.join(video.expand_compact_screen(states[i].tobytes()))
        after = display_screen(states[i].tobytes(),black_borders=True)
        first = Image.fromarray(video.base.render_spectrum_screen(before[:6144],before[6144:]))
        second = Image.fromarray(video.base.render_spectrum_screen(after[:6144],after[6144:]))
        delta = np.any(np.asarray(first) != np.asarray(second),axis=2)
        if np.count_nonzero(delta) != native_changes[i] or np.any(delta[24:168]):
            raise AssertionError('rendered RGB change differs from bit profile')
        marked = np.zeros((192,256,3),dtype=np.uint8); marked[delta] = [255,100,40]
        for x,(label,picture) in enumerate((('Before',first),('Black borders',second),('Changed pixels',Image.fromarray(marked)))):
            sheet.paste(picture.resize((512,384),Image.Resampling.NEAREST),(x*512,y*414+30))
            draw.text((x*512+8,y*414+8),f'{label}; frame {i}; changed {int(native_changes[i])}',fill='white')
    args.preview.parent.mkdir(parents=True,exist_ok=True); sheet.save(args.preview)
    totals = [r['projected_foreground'] for r in rows]
    result = dict(scope=__doc__,complete=True,release=False,baseline_commit='3d91f10',
        states_sha256=sha(states.tobytes()),cells_sha256=sha(data),frames=len(states),
        stream_changed=False,compression_change_bytes=0,stream_extra_sectors=0,
        active_geometry=[0,24,256,144],active_pixel_changes=0,attribute_changes=0,ay_changed=False,
        affected_frames=len(affected),changed_logical_border_pixels=int(logical_changes.sum()),
        changed_native_border_pixels=int(native_changes.sum()),max_changed_native_pixels=int(native_changes.max()),
        preview_frames=chosen,preview_sha256=sha(args.preview.read_bytes()),
        instruction_table_projection=dict(full_execution_measured=False,
            output_before=sum(r['output_before'] for r in rows),output_after=sum(r['output_after'] for r in rows),
            output_delta=sum(r['output_delta'] for r in rows),
            bitmap_border_delta=sum(r['bitmap_border_delta'] for r in rows),
            minimum_bitmap_saving=min(-r['bitmap_border_delta'] for r in rows),
            maximum_bitmap_saving=max(-r['bitmap_border_delta'] for r in rows),
            total_tstates=sum(totals),mean_tstates=sum(totals)/len(totals),max_tstates=max(totals),
            worst_frame=totals.index(max(totals)),frames_above_425448=sum(t>425448 for t in totals)),
        foreground_code_size_delta=0,extra_buffers_bytes=0,frames_detail=rows)
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k != 'frames_detail'},indent=2))


if __name__ == '__main__': main()
