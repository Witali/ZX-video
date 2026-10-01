"""Freeze audio probe evidence, rejected measurements and native timing hashes."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe', type=Path, required=True)
    parser.add_argument('--unconstrained', type=Path, required=True)
    parser.add_argument('--fixed-pitches', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--converter', type=Path, help='completed generic converter smoke build')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    report = json.loads((args.probe/'report.json').read_text())
    index = dict(baseline_commit='c4a28ec', files={}, source_code_sha256={},
                 source_code_hash_normalization='CRLF to LF')
    for name in ('ay_fidelity.py', 'ay_square_fit.py', 'convert_video.py', 'probe_ay_square_fit.py',
                 'profile_ay_square_fit.py', 'resident_audio_z80.py', 'ay_interrupt.py'):
        source = Path(__file__).with_name(name).read_bytes().replace(b'\r\n', b'\n')
        index['source_code_sha256'][name] = hashlib.sha256(source).hexdigest()
    with Path(report['source']).open('rb') as source:
        index['source_video_sha256'] = hashlib.file_digest(source, 'sha256').hexdigest()
    for source, target in ((args.unconstrained/'report.json', 'rejected-unconstrained.json'),
                           (args.fixed_pitches/'report.json', 'superseded-fixed-pitches.json'),
                           (args.probe/'report.json', 'comparison.json'),
                           (args.probe/'native.json', 'native.json')):
        (args.output/target).write_bytes(source.read_bytes().replace(b'\r\n', b'\n'))
    for window in report['windows']:
        name = f'{window["start_seconds"]:g}s'
        for source in sorted((args.probe/name).iterdir()):
            if source.name not in window['artifacts']:
                continue
            if sha(source) != window['artifacts'][source.name]:
                raise ValueError(f'changed probe artifact: {source}')
            target = args.output/name/source.name
            target.parent.mkdir(parents=True, exist_ok=True)
            # Keep one directly playable A/B/source trio; gzip other previews.
            if source.suffix == '.wav' and not (name == '60s' and source.stem in ('original', 'before', 'after')):
                target = target.with_suffix('.wav.gz')
                target.write_bytes(gzip.compress(source.read_bytes(), mtime=0))
            else:
                shutil.copyfile(source, target)
    if args.converter:
        for name in ('conversion.json', 'audio-quality.json', 'codec.json', 'timing.json',
                     'timing/ZX-video_part01.cpu.json'):
            target = args.output/'converter'/name
            target.parent.mkdir(parents=True, exist_ok=True)
            data = (args.converter/name).read_bytes().replace(b'\r\n', b'\n')
            if name.endswith('.cpu.json'):
                target = target.with_suffix('.json.gz')
                data = gzip.compress(data, mtime=0)
            target.write_bytes(data)
    for path in sorted(args.output.rglob('*')):
        if path.is_file() and path.name != 'index.json':
            index['files'][path.relative_to(args.output).as_posix()] = dict(bytes=path.stat().st_size, sha256=sha(path))
    (args.output/'index.json').write_text(json.dumps(index, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(dict(files=len(index['files']), bytes=sum(v['bytes'] for v in index['files'].values()))))


if __name__ == '__main__':
    main()
