"""Extend the pinned default DHA trial without changing its first-song evidence."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

from dha_host_probe import HERE, run_source, save, sha


NAMES=('silence','quiet440','loud3000','steps','quiet997','multitone','speech','entertainer')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence',type=Path,default=HERE/'evidence')
    parser.add_argument('--output',type=Path,default=HERE/'evidence/dha-host-corpus')
    parser.add_argument('--build',type=Path,required=True)
    parser.add_argument('--scratch',type=Path,required=True)
    args=parser.parse_args();evidence=args.evidence.resolve();out=args.output.resolve()
    if out.exists() and any(out.iterdir()):raise ValueError('Use an empty corpus directory')
    out.mkdir(parents=True,exist_ok=True);args.scratch.mkdir(parents=True,exist_ok=True)
    first=evidence/'dha-host';build=json.loads((first/'build.json').read_bytes())
    cli,dll=args.build.resolve()/'dha.exe',args.build.resolve()/'dha_codec.dll'
    for path in (cli,dll):assert sha(path.read_bytes())==build['builds'][path.name]['sha256']
    original_manifest=(first/'manifest.json').read_bytes()
    frozen=dict(first_song_manifest_sha256=sha(original_manifest),
        first_song_report_sha256=sha((first/'sea_foam/report.json').read_bytes()),
        pinned_source_snapshot_sha256=sha((first/'source-snapshot.json').read_bytes()),
        CLI_sha256=sha(cli.read_bytes()),DLL_sha256=sha(dll.read_bytes()),
        integration_harness_sha256=sha(Path(__file__).with_name('dha_host_probe.py').read_bytes()),
        defaults_unchanged=True,no_resampling_filter_gain_or_SNR_measurement=True)
    save(out/'configuration.json',frozen)
    rows=[dict(source='sea_foam',external_report='../dha-host/sea_foam/report.json',
               report=json.loads((first/'sea_foam/report.json').read_bytes()))]
    for name in NAMES:
        report=run_source(name,evidence,out,args.scratch.resolve(),cli,dll)
        rows.append(dict(source=name,report=report))
        save(out/'partial.json',dict(complete=False,rows=rows))
        assert sha(cli.read_bytes())==frozen['CLI_sha256'] and sha(dll.read_bytes())==frozen['DLL_sha256']
        assert (first/'manifest.json').read_bytes()==original_manifest
    save(out/'report.json',dict(complete=True,date='2026-10-19',whole9_source_corpus=True,rows=rows,
        same_unmodified_library_and_defaults=True,first_song_evidence_unchanged=True,
        host_container_not_Z80_wire=True,no_SNR_measurement=True,
        source_independent_quality_claim=False,model_training_on_same_song_family_disclosed=True,
        physical_hardware_tested=False,release_accepted=False))
    (out/'harness.py.gz').write_bytes(gzip.compress(Path(__file__).read_bytes(),mtime=0))
    artifacts=[]
    for path in sorted(out.rglob('*')):
        if path.is_file() and path.name!='manifest.json' and '__pycache__' not in path.parts:
            raw=path.read_bytes();artifacts.append(dict(path=path.relative_to(out).as_posix(),bytes=len(raw),sha256=sha(raw)))
    save(out/'manifest.json',dict(files=len(artifacts),artifacts=artifacts))
    print(json.dumps(dict(complete=True,sources=9,files=len(artifacts))),flush=True)


if __name__=='__main__':main()
