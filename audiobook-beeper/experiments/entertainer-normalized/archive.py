"""Archive and authenticate the two completed normalized music conversions."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import wave

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
NAMES = {c: f'ZX-music-Entertainer-normalized-{c.upper()}.trd' for c in ('ima3', 'ima4')}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def save(path, value):
    path.write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8')


def copy(source, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and source.read_bytes() != dest.read_bytes():
        raise ValueError(f'Refusing to overwrite a different artifact: {dest}')
    shutil.copyfile(source, dest)


def archive(work):
    assert read(work/'build-status.json')['complete']
    for name in ('normalization.json', 'normalized-source.wav', 'build-status.json',
                 'pass1.log', 'pass2.log', 'final-pcm8.log', 'ima3.log', 'ima4.log'):
        copy(work/name, HERE/name)
    if (work/'previous-preparation-loudness.log').exists():
        copy(work/'previous-preparation-loudness.log', HERE/'previous-preparation-loudness.log')
    for codec in NAMES:
        source = work/codec
        dest = HERE/codec
        for path in source.iterdir():
            if path.is_file() and path.suffix in ('.json', '.gz', '.wav', '.trd'):
                copy(path, dest/path.name)
        for folder in ('assembly', 'sound-128', 'producer-source'):
            for path in (source/folder).rglob('*'):
                if path.is_file():copy(path, dest/path.relative_to(source))
        report = read(source/'report.json')
        if codec == 'ima3':
            selected = source/report['selected']['directory']
            trace = selected/read(selected/'report.json')['selected']/'verification-work'
            for path in source.glob('encode-*/report.json'):
                copy(path, dest/'attempts'/path.relative_to(source))
            for path in source.glob('encode-*/soundtrack.ima.gz'):
                copy(path, dest/'attempts'/path.relative_to(source))
            for name in ('quality.json', 'report.json', 'phase-probe.json'):
                copy(source/'pilot'/name, dest/'pilot'/name)
            # Preserve exact producer bytes authenticated by this run's identity.
            for name, expected in read(source/'run.json')['producer_sha256'].items():
                path = ROOT/'audiobook-beeper'/name
                assert digest(path) == expected, name
                archived = dest/'producer-source'/(name+'.gz')
                archived.parent.mkdir(parents=True, exist_ok=True)
                archived.write_bytes(gzip.compress(path.read_bytes(), mtime=0))
        else:
            trace = source/report['selected_variant']['directory']/'verification-work'
            for path in source.glob('*/calibration.json'):
                copy(path, dest/'attempts'/path.relative_to(source))
        for path in trace.iterdir():
            if path.is_file():copy(path, dest/'verification-work'/path.name)
        copy(source/'audiobook-preview.trd', ROOT/NAMES[codec])


def verify():
    normalization = read(HERE/'normalization.json')
    assert digest(HERE/'build.py') == normalization['builder_sha256']
    assert digest(ROOT/normalization['source']) == normalization['source_sha256']
    assert digest(HERE/'normalized-source.wav') == normalization['prepared_wav_sha256']
    assert read(HERE/'build-status.json')['complete']
    rows = {}
    for codec, name in NAMES.items():
        folder = HERE/codec
        quality = read(folder/'quality.json')
        native, fuse = read(folder/'native.json'), read(folder/'fuse.json')
        recording = read(folder/'sound-128/report.json')
        assert native['complete'] and fuse['complete']
        assert native['cycles_verified'] == fuse['cycles_verified'] == 2
        assert fuse['cold_boot'] and fuse['runtime_disk_reads'] == 0
        assert native['memory_guards_passed'] and native['every_output_port_uncontended']
        for evidence in (native, fuse):
            assert evidence['every_pdm_bit_exact'] and evidence['every_predictor_and_index_exact']
        assert recording['recording_complete'] and recording['paging_latches_match']
        assert recording['secondary_paging_unchanged']
        assert quality['speed_within_two_percent']
        assert abs(quality['mean_speed_error_percent']) <= 2
        with wave.open(str(folder/'source-preview.wav'), 'rb') as wav:
            assert (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) == (1, 1, 8000)
            raw = wav.readframes(wav.getnframes())
        assert native['pcm16_samples_verified'] == fuse['pcm16_samples_verified'] == 2*len(raw)
        assert hashlib.sha256(raw).hexdigest() == normalization['pcm_sha256']
        assert read(folder/'input.json')['prepared_pcm_unchanged']
        assert (ROOT/name).read_bytes() == (folder/'audiobook-preview.trd').read_bytes()
        assert recording['source_trd_sha256'] == digest(ROOT/name)
        rows[codec] = dict(trd=name, trd_sha256=digest(ROOT/name), same_normalized_reference=True,
                           quality=quality, native_complete=True, fuse_complete=True,
                           normal_recording_complete=True, physical_hardware_tested=False)
    return dict(complete=True, normalization=normalization, codecs=rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--write-manifest', action='store_true')
    args = parser.parse_args()
    if args.archive:
        archive(args.archive.resolve())
        save(HERE/'comparison.json', verify())
    manifest = HERE/'artifact-hashes.json'
    if args.write_manifest:
        files = sorted(p for p in HERE.rglob('*') if p.is_file() and p != manifest
                       and '__pycache__' not in p.parts)
        save(manifest, {p.relative_to(HERE).as_posix(): digest(p) for p in files})
    for name, expected in read(manifest).items():
        assert digest(HERE/name) == expected, name
    result = verify()
    assert result == read(HERE/'comparison.json')
    print(json.dumps(dict(complete=True, artifacts=len(read(manifest)),
                          disks={c:r['trd'] for c,r in result['codecs'].items()},
                          minimum_snr_db={c:r['quality']['minimum_snr_db'] for c,r in result['codecs'].items()})))


if __name__ == '__main__':main()
