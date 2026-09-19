"""Audit frame-edge alignment and encoded pixels outside the source viewport.

No scaling, clipping, stream or player changes. Geometry comes from the
current fixed-centre converter. Nonzero border pixels are counted, not
silently removed: native output must still reproduce the accepted states.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import build_long_video_trd as video
from probe_lossless_layouts import sha


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--states',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args = p.parse_args()
    with np.load(args.states,allow_pickle=False) as saved: states = saved['states']
    if states.dtype != np.uint8 or states.ndim != 2 or states.shape[1] != 3840 or not len(states):
        raise ValueError('expected nonempty compact movie')
    bitmap = states[:,:3072].reshape(-1,96,32)
    y0,y1 = video.ACTIVE_Y0,video.ACTIVE_Y0+video.ACTIVE_HEIGHT
    outside = np.concatenate((bitmap[:,:y0],bitmap[:,y1:]),axis=1)
    affected = np.flatnonzero(np.any(outside,axis=(1,2)))
    levels = ((outside[...,None] >> np.array([6,4,2,0],dtype=np.uint8)) & 3)
    viewport = dict(left=0,top=2*y0,right=256,bottom=2*y1,width=256,height=2*(y1-y0))
    aligned = {str(cell):all(viewport[side]%cell == 0 for side in ('left','top','right','bottom'))
        for cell in (8,16)}
    by_row = np.count_nonzero(bitmap,axis=(0,2))
    result = dict(scope=__doc__,complete=True,release=False,player_changed=False,player_delta_tstates=0,
        states_sha256=sha(states.tobytes()),frames=len(states),native_viewport=viewport,
        rectangle_bounds='left/top inclusive, right/bottom exclusive',edge_alignment=aligned,
        native_output_cell=[8,8],reconstruction_tile_native=[16,16],
        native_partial_character_clip=False,
        native_output='A marked character cell is regenerated as a complete 8x8 bitmap; partial means a sparse band of whole cells.',
        nominal_border=dict(affected_frames=len(affected),first_affected_frame=int(affected[0]) if len(affected) else None,
            nonzero_compact_bytes=int(np.count_nonzero(outside)),nonzero_logical_pixels=int(np.count_nonzero(levels)),
            safe_to_omit_without_state_change=not bool(len(affected))),
        actual_nonzero_logical_rows=[int(y) for y in np.flatnonzero(by_row)],
        nonzero_compact_bytes_by_logical_row=by_row.tolist(),
        geometry_change_required_for_native_8x8_alignment=False,
        resize_performed=False,quality_change_measured=False,compression_change_measured=False)
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k != 'nonzero_compact_bytes_by_logical_row'},indent=2))


if __name__ == '__main__': main()
