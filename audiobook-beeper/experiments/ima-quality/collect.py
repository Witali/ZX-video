"""Preserve diagnostics and source provenance after the bounded quality study."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

from archive import HERE, ROOT, copy, read
from verify_pcm import save


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work',type=Path,required=True)
    args=parser.parse_args(); work=args.work.resolve()
    for name in ('probe','probe-speech4'):
        for path in (work/name).iterdir():
            if path.is_file():copy(path,HERE/'diagnostics'/name/path.name)
    copy(work/'guard-probe.json',HERE/'diagnostics/guard-probe.json')
    copy(work/'cli-source.wav',HERE/'cli/source.wav')
    for name in ('cli-ima3-series','cli-ima4-verified','cli-ima4-refined'):
        source=work/name; dest=HERE/'cli'/name
        for path in source.rglob('*'):
            if path.is_file() and path.suffix in ('.json','.trd'):
                copy(path,dest/path.relative_to(source))
        if name!='cli-ima3-series':
            selected=source/read(source/'report.json')['selected_variant']['directory']
            for path in selected.rglob('*'):
                if path.is_file() and path.suffix not in ('.lst','.fmf'):
                    copy(path,dest/'selected'/path.relative_to(selected))
            for folder in source.glob('encode-*'):
                for path in folder.iterdir():
                    if path.is_file():copy(path,dest/folder.name/path.name)
            for path in (source/'producer-source').iterdir():
                if path.is_file():copy(path,dest/'producer-source'/path.name)
    for path in (work/'program-files-probe').iterdir():
        if path.is_file():copy(path,HERE/'diagnostics/program-files-control'/path.name)
    for path in ROOT.glob('build-quality-*.log'):
        copy(path,HERE/'diagnostics/logs'/path.name)
    for name in ('music3','music4','speech3','speech4','cli-ima4'):
        source=work/name
        for path in source.rglob('phase-*.txt'):
            copy(path,HERE/'diagnostics/sdl-failures'/name/path.relative_to(source))
        for filename in ('identity.json','failure.json','input.json'):
            if (source/filename).exists():copy(source/filename,HERE/'diagnostics/sdl-failures'/name/filename)
    # This is a final reproducible source snapshot. Earlier invocation identities
    # remain separate: orchestration evolved while independent searches ran.
    snapshots=HERE/'final-producer-source';snapshots.mkdir(exist_ok=True)
    hashes={}
    for path in sorted((ROOT/'audiobook-beeper').iterdir()):
        if path.suffix not in ('.py','.asm'):continue
        data=path.read_bytes().replace(b'\r\n',b'\n')
        hashes[path.name]=hashlib.sha256(data).hexdigest()
        (snapshots/(path.name+'.gz')).write_bytes(gzip.compress(data,mtime=0))
    save(snapshots/'hashes.json',hashes)
    save(snapshots/'scope.json',dict(
        scope='Final source snapshot; original invocation identities and per-candidate snapshots are retained separately.',
        core_encoder_and_player_changed_during_runs=False,
        changes_during_runs='CLI orchestration, tests, and experiment/archive helpers only.'))
    print(json.dumps(dict(snapshotted_sources=len(hashes),diagnostics_collected=True)))


if __name__=='__main__':main()
