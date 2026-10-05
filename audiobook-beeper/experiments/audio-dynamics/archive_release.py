"""Archive a completed conditioned IMA4 disk and its full execution evidence.

Retain selected native/Fuse traces, final volume traces, producer snapshots,
and every candidate's metadata. Intermediate payloads, duplicate disks and
rejected candidates' large traces stay in the generated build directory.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build', type=Path)
    args = parser.parse_args()
    source = args.build.resolve()
    here = Path(__file__).resolve().parent
    report = json.loads((source/'report.json').read_bytes())
    assert report['complete'] and report['verification']['complete']
    assert report['dynamics']['mode'] == 'gentle'
    assert report['part_count'] == 5 and report['retained_source_samples'] == 909696
    volumes = json.loads((source/'volumes.json').read_bytes())
    assert len(volumes) == 1 and volumes[0]['used_sectors'] == 2560
    assert digest(source/'audio.trd') == volumes[0]['trd_sha256']
    copied = {}

    def copy(src, dst):
        assert not dst.exists(), str(dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        assert digest(src) == digest(dst)
        copied[dst.relative_to(here).as_posix()] = digest(dst)

    def tree(src, dst):
        for file in sorted(src.rglob('*')):
            if file.is_file():
                copy(file, dst/file.relative_to(src))

    for file in sorted(source.glob('*.json')):
        copy(file, here/'release'/file.name)
    copy(source/'audio.trd', here/'release/audio.trd')
    tree(source/'verification', here/'release/verification')
    tree(source/'work/volume-0001', here/'build-work/volume-0001')
    for number in range(1, 6):
        part = source/'work'/f'part-{number:05d}'
        part_report = json.loads((part/'report.json').read_bytes())
        assert part_report['complete']
        target = here/'selected'/part.name
        for file in sorted(part.iterdir()):
            if file.is_file():
                copy(file, target/file.name)
        tree(part/'assembly', target/'assembly')
        tree(part/'producer-source', target/'producer-source')
        chosen = part/part_report['selected_variant']['directory']
        tree(chosen/'verification-work', target/'verification-work')
        for file in sorted(part.rglob('*')):
            relative = file.relative_to(part)
            if len(relative.parts) < 2 or relative.parts[0] in ('assembly', 'producer-source'):
                continue
            if file.is_file() and (file.suffix == '.json'
                                   or file.name in ('phase-trace.txt', 'phase-debugger.txt', 'phase-stderr.txt')):
                copy(file, here/'searches'/part.name/relative)
    for name in ('ima4-normalized-convert.log', 'ima4-normalized-part-3.log',
                 'ima4-normalized-part-4.log', 'ima4-normalized-part-5.log'):
        copy(source.parent.parent/'.tmp'/name, here/'logs'/name)
    (here/'artifact-hashes.json').write_text(json.dumps(copied, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(files=len(copied), bytes=sum((here/p).stat().st_size for p in copied),
                          disk_sha256=volumes[0]['trd_sha256'])))


if __name__ == '__main__':
    main()
