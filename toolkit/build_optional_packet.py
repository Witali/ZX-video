"""Build three disks with a separate optional packet consumer."""
import argparse
import json
from pathlib import Path
import numpy as np
from benchmark_bank_local_zx0 import disk_blocks
from build_fap3_trd import sha
from build_integrated_bootstrap import check_cold
from build_inplace_keepalive import prime
from optional_packet_player import Builder
from test_fap3_disk import verify_swaps

ROOT = Path(__file__).parent


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('baseline-build', 'raw-directory', 'states', 'zx0', 'output', 'report'):
        p.add_argument('--'+key, type=Path, required=True)
    p.add_argument('--read-cache', type=Path, action='append', default=[])
    a = p.parse_args(); old = json.loads(a.baseline_build.read_bytes())
    if not old['complete']: raise ValueError('complete baseline required')
    with np.load(a.states, allow_pickle=False) as saved: states = saved['states']
    contract = dict(old['contract'], version='separate-optional-consumer-1')
    if sha(states.tobytes()) != contract['states_sha256']: raise ValueError('different states')
    fingerprint = b'AYH1OPC1'+bytes.fromhex(sha(json.dumps(contract, sort_keys=True).encode()))[:6]
    a.output.mkdir(parents=True, exist_ok=True); a.report.parent.mkdir(parents=True, exist_ok=True)
    names = (*old['source_sha256_lf'], 'build_optional_packet.py', 'optional_packet_player.py', 'resumable_packet_player.py')
    report = dict(complete=False, release=False, scope=__doc__, baseline_commit='a84451d',
        baseline_build_sha256=sha(a.baseline_build.read_bytes()), contract=contract,
        zx0_sha256=sha(a.zx0.read_bytes()), volumes=[],
        source_sha256_lf={n:sha((ROOT/n).read_bytes().replace(b'\r\n',b'\n')) for n in names})
    def save(): a.report.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')
    records = []; start = 0; save()
    try:
        for part, end in enumerate(contract['ends'], 1):
            print(f'Building separate-consumer volume {part}', flush=True)
            raw = (a.raw_directory/f'volume-{part}.raw').read_bytes()
            if sha(raw) != contract['raw_sha256'][part-1]: raise ValueError('different raw')
            b = Builder(raw, states, a.zx0.resolve(), a.output/'zx0', series_fingerprint=fingerprint, **contract['options'])
            b.ends = contract['ends']; b.read_cache = a.read_cache
            image, m = b.volume(start, end, part)
            if image is None: raise ValueError(('disk capacity exceeded', part, m['used_sectors']))
            stem = f'ZX-video-huffman-preview_part{part:02}'
            (a.output/(stem+'.trd')).write_bytes(image)
            (a.output/(stem+'.json')).write_text(json.dumps(m, indent=2)+'\n', encoding='utf-8', newline='\n')
            _, stream, blocks = disk_blocks(a.output, part); video, sound = b.separated(start, end)
            ref = old['volumes'][part-1]
            if (b''.join(chunk for _, chunk in blocks) != video or sha(video) != ref['raw_video_sha256']
                    or sha(sound) != ref['audio_sha256'] or sha(stream) != ref['stream_sha256']):
                raise AssertionError('video/audio or compressed bytes differ')
            row = dict(part=part, frames=end-start, used_sectors=m['used_sectors'], free_sectors=m['free_sectors'],
                video_bytes=m['video_bytes'], video_sectors=m['video_sectors'], video_start_sector=m['video_start_sector'],
                trd_sha256=sha(image), metadata_sha256=sha((a.output/(stem+'.json')).read_bytes()),
                stream_sha256=sha(stream), raw_video_sha256=sha(video), audio_sha256=sha(sound),
                independently_bootable=m['independently_bootable'], exact_video_and_ay_bytes=True,
                resumable_packet=m['resumable_packet'])
            row.update(check_cold(image, m, b.expected_banks)); row.update(prime(image, m, states))
            report['volumes'].append(row); save()
            records.append(dict(part=part, file=stem+'.trd', metadata=stem+'.json', sha256=sha(image),
                                frame_start=start, frame_end_exclusive=end))
            print(json.dumps({k:row[k] for k in ('part', 'frames', 'used_sectors', 'free_sectors', 'video_bytes')}), flush=True)
            start = end
        (a.output/'volumes.json').write_text(json.dumps(records, indent=2)+'\n', encoding='utf-8', newline='\n')
        verify_swaps(a.output, a.output/'swaps.json')
        report.update(complete=True, mocked_rom_swaps=json.loads((a.output/'swaps.json').read_bytes()))
    except Exception as exc: report['failure'] = repr(exc); raise
    finally: save()


if __name__ == '__main__': main()
