"""Generate the requested UI disk through the complete public C converter.

Existing achieved-disk evidence is immutable. This program writes only a new
output directory and verifies that the PLAYER file is the sole disk change.
Complete execution and delivery are separate, subsequent checks.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time


HERE=Path(__file__).resolve().parent
REPO=HERE.parents[4]
BEFORE=HERE.parent/'achieved-disk/generated'


def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=HERE/'generated')
    args=parser.parse_args()
    output=args.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError('Choose a fresh output directory; saved evidence is preserved')
    command=[sys.executable,str(REPO/'audiobook-beeper/convert_snr_audio.py'),
             str(HERE.parent/'study/inputs/song/source-preview.wav'),
             '--prepared-pcm','--encoder','c','--audio-progress-ui',
             '--cover',str(BEFORE/'cover.scr'),'--output',str(output)]
    started=time.perf_counter()
    result=subprocess.run(command,capture_output=True,text=True)
    elapsed=time.perf_counter()-started
    output.mkdir(parents=True,exist_ok=True)
    (output/'conversion.log').write_text(result.stdout+result.stderr,encoding='utf-8',newline='\n')
    if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    old=(BEFORE/'audio.trd').read_bytes();new=(output/'audio.trd').read_bytes()
    assert sha(old)=='ccab87249b9ce148f3b84cc317d64078a05f51c1e7d5ca7aa9f14958e8fc9074'
    before=json.loads((BEFORE/'player.json').read_bytes())
    meta=json.loads((output/'player.json').read_bytes())
    model=dict(meta['model']);assert model.pop('audio_progress_ui') is True
    assert model==before['model']
    assert gzip.decompress((output/'soundtrack.ima.gz').read_bytes())==gzip.decompress((BEFORE/'soundtrack.ima.gz').read_bytes())
    assert (output/'source-preview.wav').read_bytes()==(BEFORE/'source-preview.wav').read_bytes()
    assert (output/'cover.scr').read_bytes()==(BEFORE/'cover.scr').read_bytes()
    entry=next(x for x in before['directory'] if x['name']=='PLAYER')
    begin=(entry['track']*16+entry['sector'])*256;end=begin+16384
    assert old[:begin]==new[:begin] and old[end:]==new[end:]
    assert len(new)==655360
    conversion=json.loads((output/'conversion.json').read_bytes())
    report=dict(date='2026-10-14',complete_conversion=True,command=command,
                external_process_wall_seconds=elapsed,trd_sha256=sha(new),
                baseline_trd_sha256=sha(old),only_player_file_changes=True,
                source_cover_packed_audio_exact=True,player_disk_byte_range=[begin,end],
                encoder='c',host_snr_db=conversion['host_quality']['fixed_clock']['snr_db'],
                full_new_emulator_execution_required=True,
                scope='Complete public automatic conversion, unchanged source/cover/payload/decoder tables. This generation report does not substitute for complete own-clock playback.')
    (output/'generation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':main()
