"""Rebuild standalone volumes with cached-byte decoding and identical ZX0 payloads.

Execute cold boot and disk swaps with mocked ROM sector reads. This verifies
capacity and RAM restoration, not physical disk delivery or frame deadlines.
"""
import argparse
import json
from pathlib import Path

import numpy as np

from benchmark_bank_local_zx0 import disk_blocks
from build_fap3_trd import sha
import fap3_disk_z80 as disk
from measure_volume_huffman import identify
from probe_startup_tables import undifference
from run_deferred_disk import ReadThroughBuilder
from test_fap3_disk import DiskCPU, verify_swaps
from test_warm_continuation import player, until
from zx0_codec import decompress


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('directory', 'raw-directory', 'states', 'zx0', 'output', 'report'):
        p.add_argument('--'+name, type=Path, required=True)
    args = p.parse_args()
    with np.load(args.states, allow_pickle=False) as saved:
        states = saved['states']
    inputs = [disk_blocks(args.directory, part) for part in (1,2,3)]
    ends = [m['frame_end_exclusive'] for m,_,_ in inputs]
    if ends[-1] != len(states) or [m['frame_start'] for m,_,_ in inputs] != [0]+ends[:-1]:
        raise ValueError('incomplete or overlapping input partition')
    keys = ('fast_disk','cached_seek','interleaved','deferred_limit','keepalive_fields',
            'frame_service','cold_bitmaps','inline_matches','startup_delta','fast_noop_scan',
            'irq_safe_paging','static_cache_borders','carry_huffman','register_fragments')
    options = {key:inputs[0][0][key] for key in keys}
    raws = [(args.raw_directory/f'volume-{part}.raw').read_bytes() for part in (1,2,3)]
    for (m,_,_),raw in zip(inputs,raws):
        if any(m[key] != options[key] for key in keys) or m.get('cached_huffman_byte'):
            raise ValueError('different baseline options')
        if sha(raw) != m['raw_sha256'] or sha(states.tobytes()) != m['states_sha256']:
            raise ValueError('input hash differs')
    options['cached_huffman_byte'] = True
    contract = dict(version='standalone-cached-byte-1', ends=ends, options=options,
                    raw_sha256=list(map(sha,raws)), states_sha256=sha(states.tobytes()))
    fingerprint = b'FAP3ZXV1'+bytes.fromhex(sha(json.dumps(contract,sort_keys=True).encode()))[:6]
    args.output.mkdir(parents=True,exist_ok=True)
    args.report.parent.mkdir(parents=True,exist_ok=True)
    report = dict(complete=False,release=False,scope=__doc__,contract=contract,
                  source_sha256=sha(Path(__file__).read_bytes()),volumes=[])
    def save():
        args.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    records = [];save()
    for part,((old,stream,blocks),raw) in enumerate(zip(inputs,raws),1):
        print(f'Rebuild cached-byte bootstrap: part {part}',flush=True)
        b = ReadThroughBuilder(raw,states,args.zx0.resolve(),args.output/'zx0',**options)
        b.read_cache = [args.directory/'zx0'];b.ends = ends
        # Preserve exact compressed payloads even across ZX0 executable versions.
        b.memo.update({sha(decoded):payload for payload,decoded in blocks})
        image,m = b.volume(old['frame_start'],old['frame_end_exclusive'],part)
        row = dict(part=part,baseline_trd_sha256=old['trd_sha256'],baseline_used_sectors=old['used_sectors'],
                   used_sectors=m['used_sectors'],free_sectors=m['free_sectors'],fits=image is not None)
        report['volumes'].append(row);save()
        if image is None: raise ValueError(f'cached bootstrap overfills disk {part}')
        image = identify(image,m,fingerprint)
        stem = f'ZX-video-huffman-preview_part{part:02}'
        (args.output/(stem+'.trd')).write_bytes(image)
        (args.output/(stem+'.json')).write_text(json.dumps(m,indent=2)+'\n',encoding='utf-8',newline='\n')
        rebuilt,new_stream,_ = disk_blocks(args.output,part)
        if new_stream != stream or m['blocks'] != old['blocks']:
            raise AssertionError('compressed movie changed')
        c = DiskCPU(player(image),image);until(c,disk.DRIVER)
        sections_checked = []
        for section in m['sections']:
            # This section also contains compressed startup staging and is
            # deliberately overwritten while the remaining sections load.
            if section['bank'] == 2 and section['address'] == 0xa000: continue
            at = section['sector']*256
            decoded = decompress(image[at:at+section['compressed_bytes']],limit=section['decoded_bytes'])
            if section.get('startup_delta'): decoded = undifference(decoded)
            offset = section['address'] & 16383
            if sha(decoded) != section['sha256'] or bytes(c.banks[section['bank']][offset:offset+len(decoded)]) != decoded:
                raise AssertionError(('cold RAM differs',part,section['bank'],section['address']))
            sections_checked.append(dict(bank=section['bank'],address=section['address'],bytes=len(decoded),sha256=sha(decoded)))
        row.update(trd_sha256=sha(image),raw_sha256=sha(raw),video_bytes=len(stream),stream_sha256=sha(stream),
                   video_start_sector=m['video_start_sector'],video_sectors=m['video_sectors'],
                   independently_bootable=m['independently_bootable'],compressed_stream_exact=True,
                   cold_sections_exact=sections_checked,mocked_boot_tstates=c.tstates,
                   reconstruction_bytes=m['reconstruction_bytes'],sections=m['sections'])
        records.append(dict(part=part,file=stem+'.trd',metadata=stem+'.json',frame_start=m['frame_start'],
                            frame_end_exclusive=m['frame_end_exclusive'],sha256=sha(image)))
        save();print(json.dumps({k:v for k,v in row.items() if k not in ('cold_sections_exact','sections')}),flush=True)
    (args.output/'volumes.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8')
    verify_swaps(args.output,args.output/'swaps.json')
    report.update(complete=True,mocked_rom_swaps=json.loads((args.output/'swaps.json').read_text()))
    save()


if __name__ == '__main__':
    main()
