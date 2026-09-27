"""Build three host-selected native-mask disks using unchanged player code.

Use the current resident-AY/in-place/drive-maintenance configuration with
a new set identity. Check actual capacity, dirty-RAM boots and handoffs.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from benchmark_bank_local_zx0 import disk_blocks
from build_fap3_trd import sha
from build_integrated_bootstrap import check_cold
from build_inplace_keepalive import prime
from inplace_keepalive_player import Builder
from test_fap3_disk import verify_swaps

ROOT=Path(__file__).parent


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('baseline-build','probe','raw-directory','states','zx0','output','report'):
        p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--read-cache',type=Path,action='append',default=[])
    a=p.parse_args(); old=json.loads(a.baseline_build.read_bytes()); probe=json.loads(a.probe.read_bytes())
    if not old['complete'] or not probe['complete'] or probe['baseline_build_sha256']!=sha(a.baseline_build.read_bytes()):
        raise ValueError('complete matching baseline/probe required')
    with np.load(a.states,allow_pickle=False) as saved: states=saved['states']
    contract=dict(old['contract'],version='native-mask-selection-1',native_map_policy=probe['policy'],raw_sha256=[v['raw_sha256'] for v in probe['volumes']])
    if sha(states.tobytes())!=contract['states_sha256']: raise ValueError('different states')
    fingerprint=b'AYH1NMS1'+bytes.fromhex(sha(json.dumps(contract,sort_keys=True).encode()))[:6]
    a.output.mkdir(parents=True,exist_ok=True); a.report.parent.mkdir(parents=True,exist_ok=True)
    names=(*old['source_sha256_lf'],'build_native_mask_selection.py','probe_native_mask_selection.py',
           'build_inplace_keepalive.py','inplace_keepalive_player.py')
    report=dict(complete=False,release=False,scope=__doc__,baseline_commit='a84451d',
        baseline_build_sha256=sha(a.baseline_build.read_bytes()),probe_sha256=sha(a.probe.read_bytes()),
        contract=contract,zx0_sha256=sha(a.zx0.read_bytes()),volumes=[],
        source_sha256_lf={n:sha((ROOT/n).read_bytes().replace(b'\r\n',b'\n')) for n in names})
    def save(): a.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    records=[]; start=0; save()
    try:
        for part,end in enumerate(contract['ends'],1):
            print(f'Building native-mask volume {part}',flush=True)
            selected=probe['volumes'][part-1]; raw=(a.raw_directory/selected['raw_file']).read_bytes()
            if sha(raw)!=contract['raw_sha256'][part-1]: raise ValueError('different raw')
            b=Builder(raw,states,a.zx0.resolve(),a.output/'zx0',series_fingerprint=fingerprint,**contract['options'])
            b.ends=contract['ends']; b.read_cache=a.read_cache
            image,m=b.volume(start,end,part)
            if image is None:
                report['rejected_layout']=dict(part=part,used_sectors=m['used_sectors'],free_sectors=m['free_sectors'])
                raise ValueError(('disk capacity exceeded',part,m['used_sectors']))
            stem=f'ZX-video-huffman-preview_part{part:02}'
            (a.output/(stem+'.trd')).write_bytes(image)
            (a.output/(stem+'.json')).write_text(json.dumps(m,indent=2)+'\n',encoding='utf-8',newline='\n')
            _,stream,blocks=disk_blocks(a.output,part); video,sound=b.separated(start,end)
            if (b''.join(chunk for _,chunk in blocks)!=video or sha(video)!=selected['raw_video_sha256'] or
                    sha(sound)!=old['volumes'][part-1]['audio_sha256'] or sha(stream)!=selected['compressed_stream_sha256']):
                raise AssertionError('TRD video/audio or measured compression differs')
            row=dict(part=part,frames=end-start,used_sectors=m['used_sectors'],free_sectors=m['free_sectors'],
                video_bytes=m['video_bytes'],video_sectors=m['video_sectors'],video_start_sector=m['video_start_sector'],
                trd_sha256=sha(image),metadata_sha256=sha((a.output/(stem+'.json')).read_bytes()),
                stream_sha256=sha(stream),raw_video_sha256=sha(video),audio_sha256=sha(sound),
                independently_bootable=m['independently_bootable'],exact_candidate_video_bytes=True,exact_ay_bytes=True)
            row.update(check_cold(image,m,b.expected_banks)); row.update(prime(image,m,states))
            report['volumes'].append(row); save()
            records.append(dict(part=part,file=stem+'.trd',metadata=stem+'.json',sha256=sha(image),
                                frame_start=start,frame_end_exclusive=end))
            print(json.dumps({k:row[k] for k in ('part','frames','used_sectors','free_sectors','video_bytes')}),flush=True)
            start=end
        (a.output/'volumes.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8',newline='\n')
        verify_swaps(a.output,a.output/'swaps.json')
        report.update(complete=True,mocked_rom_swaps=json.loads((a.output/'swaps.json').read_bytes()))
    except Exception as exc: report['failure']=repr(exc); raise
    finally: save()


if __name__=='__main__': main()
