"""Build independently bootable resident-AY TRDs and check cold RAM/swaps.

Accepts existing encoded FAP3 input/state files; no scene-dependent code.
This does not establish playback timing. Run complete Fuse playback next.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from benchmark_bank_local_zx0 import disk_blocks
from build_fap3_trd import sha
from build_integrated_bootstrap import check_cold
from resident_audio_player import Builder
from test_fap3_disk import verify_swaps
from zx0_codec import decompress

ROOT=Path(__file__).parent


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('directory','raw-directory','states','zx0','output','report'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--read-cache',type=Path,action='append',default=[])
    p.add_argument('--stored-video',type=Path,help='Optional saved ZX0 probe blocks as validated cache')
    p.add_argument('--audio-batch',type=int,choices=range(1,32),default=6)
    p.add_argument('--foreground-audio',action='store_true')
    args=p.parse_args()
    inputs=[disk_blocks(args.directory,part) for part in (1,2,3)]
    ends=[m['frame_end_exclusive'] for m,_,_ in inputs]
    with np.load(args.states,allow_pickle=False) as saved:states=saved['states']
    if ends[-1]!=len(states) or [m['frame_start'] for m,_,_ in inputs]!=[0]+ends[:-1]:
        raise ValueError('incomplete input movie partition')
    keys=('fast_disk','cached_seek','interleaved','deferred_limit','keepalive_fields','frame_service',
          'cold_bitmaps','inline_matches','startup_delta','fast_noop_scan','irq_safe_paging',
          'static_cache_borders','carry_huffman','register_fragments','cached_huffman_byte')
    options={k:inputs[0][0][k] for k in keys}
    options.update(bank2_zx0=True,fast_return_irq=True,hl_mask_reader=True,
                   compact_cursor=True,cached_huffman_lookahead=True,
                   audio_batch=args.audio_batch,foreground_audio=args.foreground_audio)
    raws=[(args.raw_directory/f'volume-{part}.raw').read_bytes() for part in (1,2,3)]
    for (m,_,_),raw in zip(inputs,raws,strict=True):
        if sha(raw)!=m['raw_sha256'] or sha(states.tobytes())!=m['states_sha256']:
            raise ValueError('source video/state hash differs')
        if any(m[k]!=options[k] for k in keys):raise ValueError('baseline options differ')
    contract=dict(version='resident-ay-three-slot-1',ends=ends,options=options,
        raw_sha256=list(map(sha,raws)),states_sha256=sha(states.tobytes()),audio_threshold=24)
    fingerprint=b'AYH1ZXV1'+bytes.fromhex(sha(json.dumps(contract,sort_keys=True).encode()))[:6]
    cache={}
    if args.stored_video:
        stored=json.loads(args.stored_video.read_bytes())
        if not stored['complete']:raise ValueError('partial saved compression report')
        for v in stored['volumes']:
            for b in v['blocks']:
                coded=bytes.fromhex(b['code_hex']); raw=decompress(coded,limit=b['decoded_bytes'])
                if sha(coded)!=b['coded_sha256'] or sha(raw)!=b['sha256']:
                    raise ValueError('saved video cache differs')
                cache[sha(raw)]=coded
    args.output.mkdir(parents=True,exist_ok=True);args.report.parent.mkdir(parents=True,exist_ok=True)
    report=dict(complete=False,release=False,scope=__doc__,baseline_commit='8a49d3c',contract=contract,volumes=[])
    def save():args.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    save(); records=[]
    try:
        for part,((old,_,_),raw) in enumerate(zip(inputs,raws,strict=True),1):
            print(f'Build resident AY volume {part}',flush=True)
            b=Builder(raw,states,args.zx0.resolve(),args.output/'zx0',
                series_fingerprint=fingerprint,**options)
            b.ends=ends;b.read_cache=[args.directory/'zx0']+args.read_cache;b.memo.update(cache)
            image,m=b.volume(old['frame_start'],old['frame_end_exclusive'],part)
            row=dict(part=part,frames=m['frames'],used_sectors=m['used_sectors'],
                free_sectors=m['free_sectors'],video_bytes=m['video_bytes'],video_sectors=m['video_sectors'],
                video_start_sector=m['video_start_sector'],resident_audio=m['resident_audio'],sections=m['sections'])
            report['volumes'].append(row);save()
            if image is None:raise ValueError(('resident volume overflows',part))
            stem=f'ZX-video-huffman-preview_part{part:02}'
            (args.output/(stem+'.trd')).write_bytes(image)
            (args.output/(stem+'.json')).write_text(json.dumps(m,indent=2)+'\n',encoding='utf-8',newline='\n')
            loaded,stream,blocks=disk_blocks(args.output,part)
            expected_video,sound=b.separated(m['frame_start'],m['frame_end_exclusive'])
            if b''.join(decoded for _,decoded in blocks)!=expected_video:
                raise AssertionError('video-only TRD data differ')
            row.update(check_cold(image,m,b.expected_banks),trd_sha256=sha(image),
                metadata_sha256=sha((args.output/(stem+'.json')).read_bytes()),
                stream_sha256=sha(stream),raw_video_sha256=sha(expected_video),
                audio_sha256=sha(sound),independently_bootable=m['independently_bootable'])
            records.append(dict(part=part,file=stem+'.trd',metadata=stem+'.json',sha256=sha(image),
                frame_start=m['frame_start'],frame_end_exclusive=m['frame_end_exclusive']))
            save()
            print(json.dumps({k:v for k,v in row.items() if k not in ('resident_audio','sections','cold_sections')}),flush=True)
        (args.output/'volumes.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8',newline='\n')
        verify_swaps(args.output,args.output/'swaps.json')
        report.update(complete=True,mocked_rom_swaps=json.loads((args.output/'swaps.json').read_bytes()))
    except Exception as exc:
        report['failure']=repr(exc);raise
    finally:
        names=('build_resident_audio_player.py','resident_audio_player.py','resident_audio_z80.py',
               'integrated_bootstrap.py','slot_queue_player.py','slot_queue_z80.py','direct_slot_input_z80.py',
               'bulk_frame_z80.py','pipelined_frame_z80.py','build_fap3_trd.py','fap3_disk_z80.py')
        report['source_sha256_lf']={n:sha((ROOT/n).read_bytes().replace(b'\r\n',b'\n')) for n in names}
        save()


if __name__=='__main__':main()
