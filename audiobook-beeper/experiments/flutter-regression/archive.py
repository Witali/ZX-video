"""Preserve completed comparisons, selected full proofs and rejected-stage reports."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil

from audit import BEEPER


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()


def candidate(source, target):
    report=json.loads((source/'report.json').read_bytes())
    assert report['complete']
    selected=source/report['selected_variant']['directory']
    target.mkdir(parents=True)
    for file in source.iterdir():
        if file.is_file():
            shutil.copy2(file,target/file.name)
    for name in ('assembly','producer-source'):
        shutil.copytree(source/name,target/name)
    shutil.copytree(selected/'verification-work',target/'verification-work')
    stages=target/'stages'
    for file in source.rglob('*.json'):
        if not any(parent in ('assembly','producer-source') for parent in file.relative_to(source).parts):
            destination=stages/file.relative_to(source)
            destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(file,destination)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--temporary-root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--ffmpeg',type=Path,required=True)
    p.add_argument('--fuse',type=Path,required=True)
    a=p.parse_args()
    out=a.output
    out.mkdir(parents=True,exist_ok=False)
    tmp=a.temporary_root
    for label,folder in [('loud-fixed','flutter-zero-public'),
                         ('quiet-midpoint','flutter-bad-disk-ab/midpoint'),
                         ('quiet-fixed','flutter-bad-disk-ab/zero-floor')]:
        candidate(tmp/folder,out/label)
    for label,folder in [('history','flutter-regression-history-modulation'),
                         ('host-probe','flutter-zero-host-corrected'),
                         ('loud-comparison','flutter-loud-comparison'),
                         ('quiet-comparison','flutter-quiet-comparison'),
                         ('silence','flutter-silence-corrected'),
                         ('series','flutter-series'),('legacy','flutter-legacy-check')]:
        status=tmp/folder/('verification/report.json' if label=='series' else 'report.json')
        assert json.loads(status.read_bytes()).get('complete',True)
        shutil.copytree(tmp/folder,out/label)
    diagnostics=out/'diagnostics'
    diagnostics.mkdir()
    for pattern in ('flutter*.log',):
        for path in tmp.glob(pattern):
            shutil.copy2(path,diagnostics/path.name)
    # Retain the superseded host estimate that omitted the pointer page.
    shutil.copy2(tmp/'flutter-zero-origin/report.json',diagnostics/'superseded-host-layout-estimate.json')
    producers=out/'integrated-source'
    producers.mkdir()
    hashes={}
    for path in BEEPER.iterdir():
        if path.suffix in ('.py','.asm'):
            data=path.read_bytes().replace(b'\r\n',b'\n')
            hashes[path.name]=hashlib.sha256(data).hexdigest()
            (producers/(path.name+'.gz')).write_bytes(gzip.compress(data,mtime=0))
    (producers/'hashes.json').write_text(json.dumps(hashes,indent=2)+'\n',encoding='utf-8',newline='\n')
    quiet=json.loads((out/'quiet-comparison/report.json').read_bytes())['candidates']
    before,after=(quiet[i]['loops'][0] for i in (1,2))
    source_hashes={x['source_sha256'] for x in quiet}
    assert len(source_hashes)==1
    fixed=json.loads((out/'quiet-fixed/report.json').read_bytes())
    series=json.loads((out/'series/verification/report.json').read_bytes())
    assert series['complete'] and series['volumes'][0]['ended_at']=='end_of_audio'
    report=dict(date='2026-10-13',complete=True,source_sha256=source_hashes.pop(),
        audition_trd_sha256=fixed['trd_sha256'],audition_prepared_samples=186880,
        quality_gate_passed=fixed['quality_gate_passed'],preview_only=fixed['preview_only'],
        quiet_peak_field_noise_power_reduction_percent=100*(1-after['field_error_power_peak']/before['field_error_power_peak']),
        quiet_field_noise_power_std_reduction_percent=100*(1-after['field_error_power_std']/before['field_error_power_std']),
        quiet_total_error_power_reduction_percent=100*(1-(after['error_rms']/before['error_rms'])**2),
        physical_sample_clock_constant=False,subjective_symptom_eliminated=False,
        native_tstates=dict(first_half=215,second_half=208,ordinary=423,page_extra=14,bank_extra=140,delta=0),
        complete_series_verified=True,physical_hardware_tested=False,
        fresh_normal_speed_endpoint_capture=False,
        tools=dict(ffmpeg_sha256=sha(a.ffmpeg),fuse_sha256=sha(a.fuse)),
        limits=['The quiet excerpt still fails the existing20-dB gate.',
                'A smaller field-power peak is not proof of subjective flutter elimination.',
                'No constant-clock or faster-than-real-time architecture is implemented.'])
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    files={str(path.relative_to(out).as_posix()):dict(sha256=sha(path),bytes=path.stat().st_size)
           for path in sorted(out.rglob('*')) if path.is_file()}
    (out/'manifest.json').write_text(json.dumps(dict(schema=1,files=files),indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(complete=True,files=len(files),bytes=sum(x['bytes'] for x in files.values()),report=report)))


if __name__=='__main__':
    main()
