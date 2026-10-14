"""Reproduce/check complete default output and version1 workset identity.

No original or historical producer is edited. The existing full benchmark
executes the new default C DLL/standalone against saved complete Python bytes.
This separate checker also compares every serialized workset to the archived
version1 bytes and authenticates unchanged Python originals against Git.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


sha=lambda data:hashlib.sha256(data).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scratch',type=Path,default=Path('.tmp/centered-default-check'))
    parser.add_argument('--captured',action='store_true')
    args=parser.parse_args();scratch=args.scratch.resolve()
    evidence=Path('audiobook-beeper/experiments/song-snr/evidence')
    if not args.captured:
        subprocess.run([sys.executable,str(evidence/'native-encoder/benchmark.py'),
                        '--scratch',str(scratch)],check=True)
    current=json.loads((scratch/'report.json').read_bytes())
    archived=json.loads((evidence/'native-encoder/report.json').read_bytes())
    assert current['complete'] and len(current['rows'])==9
    before={row['source']:row for row in archived['rows']};rows=[]
    for row in current['rows']:
        previous=before[row['source']]
        assert row['all_bytes_identical']
        assert row['packed_sha256']==previous['packed_sha256']
        assert row['workset_sha256']==previous['workset_sha256']
        assert 'pcm_quantization_bias' not in row['statistics']
        assert 'pcm_quantization_bias' not in row['standalone_statistics']
        rows.append(dict(source=row['source'],samples=row['samples'],
                         packed_sha256=row['packed_sha256'],
                         version1_workset_sha256=row['workset_sha256'],
                         every_output_byte_unchanged=True,every_workset_byte_unchanged=True,
                         default_statistics_bias_key_absent=True,
                         native_seconds=row['complete_c_seconds'],standalone_seconds=row['standalone_seconds']))
    original={}
    for revision,names in (('13819086',('ima_waveform_encoder.py','ima_beam.py')),
                           ('7938cbe6',('experiments/song-snr/clock_control.py','experiments/song-snr/general.py'))):
        for name in names:
            path='audiobook-beeper/'+name
            old=subprocess.check_output(['git','show',revision+':'+path]).replace(b'\r\n',b'\n')
            new=Path(path).read_bytes().replace(b'\r\n',b'\n')
            assert old==new,path+' original changed'
            original[path]=dict(git_reference=revision,normalized_lf_sha256=sha(new),unchanged=True)
    sources=('audiobook-beeper/native_waveform_encoder.c','audiobook-beeper/native_waveform_encoder.py',
             'audiobook-beeper/centered_waveform_reference.py','audiobook-beeper/test_centered_waveform_encoder.py')
    report=dict(date='2026-10-14',complete=True,scope='Complete all9 default C/standalone output and version1 serialization compatibility. Original Python unchanged; no new player execution or quality qualification.',rows=rows,original_python=original,
                producer_sha256={name:sha(Path(name).read_bytes()) for name in sources},
                archived_full_benchmark_sha256=sha((evidence/'native-encoder/report.json').read_bytes()),
                current_full_benchmark_sha256=sha((scratch/'report.json').read_bytes()))
    (scratch/'compatibility.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(complete=True,sources=len(rows),unchanged_version1_worksets=True,original_python_unchanged=True)))


if __name__=='__main__':main()
