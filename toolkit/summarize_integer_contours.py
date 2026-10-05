"""Compare verified contour data with the current ZX0 stream, without a speed claim."""
import argparse
import json
from pathlib import Path

from build_zxv_trd import TRD_SIZE
from probe_lossless_layouts import sha


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('contours','zx0','baseline','output'): p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--compact',type=Path,help='Use compact integer-delta hybrid instead of the first absolute-coordinate hybrid')
    args=p.parse_args(); paths=(args.contours,args.zx0,args.baseline)
    source,new,old=[json.loads(path.read_text(encoding='utf-8')) for path in paths]
    selected=source; variant='hybrid'
    if args.compact:
        selected=json.loads(args.compact.read_text(encoding='utf-8')); variant='compact_hybrid'
        if not selected['complete'] or selected['states_sha256']!=source['states_sha256'] or selected['raw_sha256']!=source['raw_sha256']:
            raise ValueError('different compact-contour inputs')
        paths=(*paths,args.compact)
    if not all(r['complete'] for r in (source,new,old)): raise ValueError('complete inputs required')
    if selected['streams'][variant]['sha256']!=new['input_sha256'] or source['raw_sha256']!=old['input_sha256']:
        raise ValueError('different input streams')
    if any(new[k]!=old[k] for k in ('block_bytes','encoder_mode','encoder_sha256')):
        raise ValueError('different ZX0 settings')
    rows=selected['frames']; before=old['zx0_with_headers_bytes']; after=new['zx0_with_headers_bytes']
    result=dict(scope=__doc__,complete=True,release=False,player_changed=False,player_delta_tstates=0,
        input_reports=[dict(file=p.name,sha256=sha(p.read_bytes())) for p in paths],
        checked_frames=source['checked_frames'],checked_ay_ticks=source['checked_ay_ticks'],
        exact_active_pixels_attributes_ay=all(not any(r[k] for k in ('final_pixel_errors','attribute_errors','ay_errors')) for r in rows),
        mode_selection='minimum uncompressed geometry bytes per frame, not a global ZX0 optimum',
        hybrid_modes=selected['modes'],mean_hybrid_geometry_bytes=sum(r.get('hybrid_pixel_bytes',r.get('pixel_bytes')) for r in rows)/len(rows),
        raw_streams=selected['streams'],baseline_raw_bytes=source['baseline_raw_bytes'],
        baseline_deflate_layout_screen=source['baseline_deflate_8192_layout_screen'],
        zx0_before_bytes=before,zx0_hybrid_bytes=after,zx0_delta_bytes=after-before,
        zx0_change_percent=100*(after-before)/before,
        absolute_three_trd_bytes=3*TRD_SIZE,
        exceeds_even_three_whole_disk_images=after>3*TRD_SIZE,
        minimum_disks_ignoring_all_filesystem_loader_overhead=(after+TRD_SIZE-1)//TRD_SIZE,
        speed_measured=False,cadence_verified=False,disk_delivery_verified=False,
        summary=source['summary'],
        decision='Retain as separate experiment. Choose no replacement without Z80 timing and a complete playable build. '
            'This hybrid has no temporal contour-ID/vertex reuse; its result does not bound other vector codecs.')
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__': main()
