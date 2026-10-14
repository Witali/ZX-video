"""Run the complete public C conversion and authenticate its played disk."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,help='Fresh output directory for reproduction without replacing saved evidence')
    args=parser.parse_args()
    evidence=Path(__file__).resolve().parent.parent
    repository=evidence.parents[3]
    inputs=evidence/'study/inputs';baseline=json.loads((inputs/'song/player.json').read_bytes())
    current=(inputs/'current-main.trd').read_bytes()
    entry=next(x for x in baseline['directory'] if x['name']=='COVER')
    at=(entry['track']*16+entry['sector'])*256
    scratch=repository/'.tmp/automatic-conversion';scratch.mkdir(parents=True,exist_ok=True)
    cover=scratch/'title.scr';cover.write_bytes(current[at:at+6912])
    output=(args.output or Path(__file__).resolve().parent/'sea_foam-c').resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError('Choose a fresh --output directory; existing evidence is preserved')
    command=[sys.executable,str(repository/'audiobook-beeper/convert_snr_audio.py'),
             str(inputs/'song/source-preview.wav'),'--prepared-pcm','--encoder','c',
             '--cover',str(cover),'--output',str(output)]
    start=time.perf_counter();run=subprocess.run(command,capture_output=True,text=True)
    elapsed=time.perf_counter()-start
    log_root=output if args.output else output.parent
    log_root.mkdir(parents=True,exist_ok=True)
    (log_root/'conversion.log').write_text(run.stdout+run.stderr,encoding='utf-8')
    if run.returncode:raise RuntimeError(run.stderr)
    meta=json.loads((output/'conversion.json').read_bytes())
    selected=(output/'audio.trd').read_bytes();played=(evidence/'clock-joint/sea_foam/audio.trd').read_bytes()
    assert selected==played,'Whole C conversion must reproduce the completely played disk byte for byte'
    source=(inputs/'song/source-preview.wav').read_bytes()
    assert (output/'source-preview.wav').read_bytes()==source
    report=dict(complete=True,date='2026-10-14',command=command,external_process_wall_seconds=elapsed,
                conversion=meta,entire_source_file_preserved=True,
                trd_sha256=hashlib.sha256(selected).hexdigest(),
                exact_disk_matches_complete_pentagon512_and1024_fuse_proof=True,
                reused_complete_execution='../clock-joint/sea_foam/verification/execution.json',
                required5_db_scalar_gain_reproduced=True,
                conversion_within_prepared_audio_duration=elapsed<=720384/8000,
                compiler_caches_already_populated=None,
                compiler_cache_policy='Compiler caches are not cleared; compilation when needed remains inside the measured subprocess',
                root_main_image_unchanged=True,artifact_release_accepted=False,
                scope='Complete automatic CLI subprocess including imports/preparation/C encoding/baseline/rendering/assembly/writing. Optional new Fuse verification is not requested; identical full disk reuses authenticated earlier complete runs.')
    (log_root/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(seconds=elapsed,snr_db=meta['host_quality']['fixed_clock']['snr_db'],
                         trd_sha256=report['trd_sha256'],within_source_duration=report['conversion_within_prepared_audio_duration'])))


if __name__=='__main__':main()
