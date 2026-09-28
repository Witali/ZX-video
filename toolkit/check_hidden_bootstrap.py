"""Rebuild only PLAYER, then check hidden loading and exact cold/prime state.

All disk sectors except the fixed four-sector bootstrap remain identical.
ROM reads are mocked; the separate optional Fuse startup check covers ROM
paging. No claim about complete playback or improved video deadlines is made.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path

import numpy as np

from build_fap3_trd import sha
from build_inplace_keepalive import prime
import fap3_disk_z80 as disk
from probe_startup_tables import undifference
from test_fap3_disk import DiskCPU
from test_warm_continuation import player
from zx0_codec import decompress


def expected_banks(image, metadata):
    banks = [bytearray(16384) for _ in range(8)]
    for section in metadata['sections']:
        start = section['sector']*256+section.get('source_offset', 0)
        raw = decompress(image[start:start+section['compressed_bytes']], limit=section['decoded_bytes'])
        if section.get('startup_delta'):
            raw = undifference(raw)
        if sha(raw) != section['sha256']:
            raise ValueError('section bytes differ')
        offset = section['address'] & 16383
        banks[section['bank']][offset:offset+len(raw)] = raw
    return banks


def rebuild(image, metadata):
    if sha(image) != metadata['trd_sha256']:
        raise ValueError('input TRD hash differs')
    original = player(image)
    at = metadata['bootstrap_labels']['next_id']-0x6000
    code, labels = disk.build_bootstrap(metadata['sections'], metadata['video_start_sector'],
        metadata['video_sectors'], next_id=original[at:at+16], interleaved=metadata['interleaved'],
        preload_sectors=metadata.get('bootstrap_video_preload_sectors', 256),
        runtime_entry=metadata.get('startup_overlay_entry'))
    if len(code) != len(original) or image[17*256:21*256] != original:
        raise ValueError('PLAYER is not the fixed four-sector file')
    if 'hide_staging_screen' not in labels:
        raise ValueError('input layout does not restore a complete shadow screen')
    result = image[:17*256]+code+image[21*256:]
    updated = deepcopy(metadata)
    updated.update(trd_sha256=sha(result), bootstrap_labels=labels,
        startup_display=dict(hidden_screen_staging=True, loading_display_bank=7, loading_ink=0,
            loading_paper=0, additional_bootstrap_tstates=16171, runtime_tstates_delta=0))
    return result, updated


class VisibleBootCPU(DiskCPU):
    watching = False

    def write8(self, address, value):
        if self.watching:
            bank = 5 if address < 0x8000 else 2 if address < 0xc000 else self.port_7ffd & 7
            offset = address & 16383
            visible = 7 if self.port_7ffd & 8 else 5
            if bank == 5 and offset < 6912:
                if visible != 7:
                    raise AssertionError('normal-screen staging became visible')
                self.hidden_writes += 1
            if bank == 7 and offset < 6144 and visible == 7:
                if any(self.banks[7][6144:6912]):
                    raise AssertionError('shadow bitmap changed after revealing attributes')
                self.masked_bitmap_writes += 1
            if bank == 7 and 6144 <= offset < 6912 and visible == 7:
                if bytes(self.banks[7][:6144]) != self.expected_shadow[:6144]:
                    raise AssertionError('attributes reveal an unfinished shadow bitmap')
                if value != self.expected_shadow[offset]:
                    raise AssertionError('visible attribute is not a real screen attribute')
        super().write8(address, value)


def boot(image, metadata, banks, *, monitor):
    cpu = VisibleBootCPU(player(image), image)
    for bank in (0, 1, 2, 3, 4, 6, 7):
        cpu.banks[bank][:] = b'\xa7'*16384
    cpu.banks[5][:6912] = b'\xa7'*6912
    cpu.banks[5][0x2400:] = b'\xa7'*(16384-0x2400)
    cpu.expected_shadow = bytes(banks[7][:6912])
    cpu.hidden_writes = cpu.masked_bitmap_writes = 0
    labels = metadata['bootstrap_labels']
    started = None
    fill_tstates = None
    while cpu.pc != disk.DRIVER:
        if monitor and cpu.pc == labels['hide_staging_screen']:
            started = cpu.tstates
        if monitor and cpu.pc == labels['staging_attributes_hidden']:
            fill_tstates = cpu.tstates-started
            if fill_tstates != 16171 or any(cpu.banks[7][6144:6912]):
                raise AssertionError('black attributes or startup instruction timing differ')
            cpu.watching = True
        if monitor and cpu.pc == labels['restore_boot_display']:
            cpu.watching = False
            if bytes(cpu.banks[5][:6912]) != bytes(banks[5][:6912]):
                raise AssertionError('normal screen is incomplete at display restore')
        cpu.step()
        if cpu.steps > 3000000:
            raise AssertionError('bootstrap stalled')
    for section in metadata['sections']:
        lo = section['address'] & 16383
        hi = lo+section['decoded_bytes']
        if section['bank'] == 5 and section['address'] == 0x6400:
            lo = 0x7600 & 16383
        if bytes(cpu.banks[section['bank']][lo:hi]) != bytes(banks[section['bank']][lo:hi]):
            raise AssertionError('cold section differs')
    if cpu.port_7ffd != 0x17 or cpu.dos_reads != sum(s['sectors'] for s in metadata['sections']):
        raise AssertionError('cold page or sector count differs')
    if monitor and (fill_tstates is None or not cpu.hidden_writes or not cpu.masked_bitmap_writes):
        raise AssertionError('missing visibility coverage')
    return dict(tstates=cpu.tstates, reads=cpu.dos_reads, cold_sections_exact=True,
        final_page=cpu.port_7ffd, masked_bitmap_writes=cpu.masked_bitmap_writes,
        hidden_normal_screen_writes=cpu.hidden_writes, attribute_fill_tstates=fill_tstates)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--states', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('output directory must be new')
    args.output.mkdir(parents=True)
    with np.load(args.states, allow_pickle=False) as data:
        states = data['states']
    result = dict(complete=False, release=False, rom_mocked=True,
        full_playback_verified=False, runtime_instruction_delta_tstates=0, volumes=[])
    records = []
    for path in sorted(args.directory.glob('ZX-video-huffman-preview_part*.json')):
        metadata = json.loads(path.read_bytes())
        image = path.with_suffix('.trd').read_bytes()
        banks = expected_banks(image, metadata)
        new_image, updated = rebuild(image, metadata)
        before, after = boot(image, metadata, banks, monitor=False), boot(new_image, updated, banks, monitor=True)
        if after['tstates']-before['tstates'] != 16171:
            raise AssertionError('whole bootstrap cost delta differs')
        row = dict(part=metadata['part'], old_trd_sha256=sha(image), trd_sha256=sha(new_image),
            before=before, after=after, additional_bootstrap_tstates=16171,
            unchanged_sectors=2556, player_bytes=1024, input_metadata_sha256=sha(path.read_bytes()),
            prime=prime(new_image, updated, states))
        if image[:17*256] != new_image[:17*256] or image[21*256:] != new_image[21*256:]:
            raise AssertionError('non-PLAYER sectors changed')
        target = args.output/path.name
        target.write_text(json.dumps(updated, indent=2)+'\n', encoding='utf-8', newline='\n')
        target.with_suffix('.trd').write_bytes(new_image)
        result['volumes'].append(row)
        records.append(dict(part=metadata['part'], file=target.with_suffix('.trd').name,
            metadata=target.name, frame_start=metadata['frame_start'],
            frame_end_exclusive=metadata['frame_end_exclusive'], sha256=sha(new_image)))
        print(json.dumps(row), flush=True)
    if not records:
        raise ValueError('no disk metadata found')
    (args.output/'volumes.json').write_text(json.dumps(records, indent=2)+'\n', encoding='utf-8', newline='\n')
    from test_fap3_disk import verify_swaps
    verify_swaps(args.output, args.output/'swaps.json')
    result.update(complete=True, swaps=json.loads((args.output/'swaps.json').read_bytes()),
        source_sha256_lf={name: sha((Path(__file__).parent/name).read_bytes().replace(b'\r\n', b'\n'))
            for name in ('check_hidden_bootstrap.py', 'fap3_disk_z80.py', 'build_fap3_trd.py')})
    (args.output/'report.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':
    main()
