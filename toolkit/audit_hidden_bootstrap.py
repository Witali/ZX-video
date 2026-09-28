"""Archive and check startup visibility evidence; never pass playback gates."""
import argparse
import gzip
import json
from pathlib import Path

from build_fap3_trd import sha
from summarize_native_mask_selection import read_archive
from test_warm_continuation import player

ROOT = Path(__file__).parent
EVIDENCE = ROOT/'hidden_bootstrap_evidence'
OUTPUT = ROOT/'hidden_bootstrap_summary.json'


def archive(build, fuse):
    native = json.loads((build/'report.json').read_bytes())
    if not native['complete']:
        raise ValueError('complete native checks required')
    EVIDENCE.mkdir(exist_ok=True)
    entries = []

    def add(name, raw):
        packed = gzip.compress(raw, mtime=0)
        target = EVIDENCE/(name+'.gz')
        if target.exists() and target.read_bytes() != packed:
            raise ValueError('refuse to replace different evidence')
        target.write_bytes(packed)
        entries.append(dict(file=target.name, sha256=sha(packed), decoded_sha256=sha(raw), decoded_bytes=len(raw)))

    add('native.json', (build/'report.json').read_bytes())
    for name in (*native['source_sha256_lf'], 'measure_hidden_bootstrap_fuse.py', 'test_hidden_bootstrap.py'):
        add('source-'+name, (ROOT/name).read_bytes())
    for row in native['volumes']:
        stem = f'part{row["part"]:02}'
        image = (build/f'ZX-video-huffman-preview_{stem}.trd').read_bytes()
        if sha(image) != row['trd_sha256']:
            raise ValueError('TRD changed')
        add(stem+'.player.bin', player(image))
        for suffix in ('json', 'trace.txt', 'debugger.txt'):
            add(stem+'.'+suffix, (fuse/(stem+'.'+suffix)).read_bytes())
    (EVIDENCE/'manifest.json').write_text(json.dumps(dict(complete=True, release=False, files=entries), indent=2)+'\n',
        encoding='utf-8', newline='\n')


def audit():
    blobs = read_archive(EVIDENCE, packed_sizes=False)
    native = json.loads(blobs['native.json'])
    for name, digest in native['source_sha256_lf'].items():
        if sha(blobs['source-'+name].replace(b'\r\n', b'\n')) != digest:
            raise ValueError('native source snapshot differs')
    volumes = []
    for row in native['volumes']:
        stem = f'part{row["part"]:02}'
        fuse = json.loads(blobs[stem+'.json'])
        if (not fuse['complete'] or fuse['trd_sha256'] != row['trd_sha256'] or fuse['attributes_checked'] != 768
                or not all(fuse[key] for key in ('attributes_all_black', 'real_rom_preserves_display',
                                                'normal_display_restored', 'trace_nonce_exact'))
                or fuse['full_playback_verified'] or fuse['debugger_memory_writes']
                or fuse['reads_checked'] != row['after']['reads']
                or row['before']['reads'] != row['after']['reads']
                or row['after']['tstates']-row['before']['tstates'] != 16171
                or row['after']['attribute_fill_tstates'] != 16171
                or row['after']['masked_bitmap_writes'] != 6144
                or row['after']['final_page'] != 0x17 or not row['after']['cold_sections_exact']
                or not all(row['prime'][key] for key in ('first_native_screen_exact',
                    'second_compact_frame_exact', 'audio_bank_immutable_exact'))
                or len(blobs[stem+'.player.bin']) != 1024 or row['unchanged_sectors'] != 2556):
            raise ValueError('incomplete native/Fuse startup checks')
        for suffix, key in (('trace.txt', 'trace_sha256'), ('debugger.txt', 'debugger_script_sha256')):
            if sha(blobs[stem+'.'+suffix]) != fuse[key]:
                raise ValueError('Fuse trace changed')
        if sha(blobs['source-measure_hidden_bootstrap_fuse.py'].replace(b'\r\n', b'\n')) != fuse['source_sha256_lf']:
            raise ValueError('Fuse source snapshot differs')
        volumes.append(dict(part=row['part'], trd_sha256=row['trd_sha256'], native_before=row['before'],
            native_after=row['after'], prime=row['prime'], fuse={k: v for k, v in fuse.items() if k != 'events'}))
    if not native['complete'] or not volumes or not all(all(s[k] for k in (
            'prompt_exact', 'wrong_disk_rejected', 'wrong_series_rejected', 'correct_disk_accepted',
            'bootstrap_ram_exact', 'rom_mocked')) for s in native['swaps']):
        raise ValueError('native checks or swaps incomplete')
    return dict(complete=True, release=False, full_playback_verified=False, physical_drive_verified=False,
        runtime_instruction_delta_tstates=0, startup_instruction_delta_tstates=16171,
        additional_bootstrap_code_bytes=20, additional_disk_sectors=0,
        volumes=volumes, swaps=native['swaps'],
        evidence_manifest_sha256=sha((EVIDENCE/'manifest.json').read_bytes()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path)
    parser.add_argument('--fuse', type=Path)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    if bool(args.build) != bool(args.fuse):
        parser.error('--build and --fuse must be supplied together')
    if args.build:
        archive(args.build, args.fuse)
    report = audit()
    if args.write:
        OUTPUT.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')
    elif report != json.loads(OUTPUT.read_bytes()):
        raise ValueError('saved summary differs')
    print(json.dumps(dict(complete=report['complete'], volumes=len(report['volumes']),
        startup_delta_tstates=report['startup_instruction_delta_tstates'],
        runtime_delta_tstates=report['runtime_instruction_delta_tstates'])), flush=True)


if __name__ == '__main__':
    main()
