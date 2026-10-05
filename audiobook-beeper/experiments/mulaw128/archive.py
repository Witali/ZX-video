"""Archive complete 128-kHz packet runs and authenticate release artifacts."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def read(p): return json.loads(p.read_bytes())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def copy(a,b):
    b.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(a,b)


def candidate(source,dest):
    report=read(source/'report.json')
    assert report['complete']
    for name in ('native','fuse'):
        proof=read(source/(name+'.json'))
        assert proof['complete'] and proof['cycles_verified']==2
        assert proof['every_pdm_bit_exact'] and proof['every_packet_feedback_exact']
    assert read(source/'fuse.json')['trd_sha256']==sha(source/'audiobook-preview.trd')
    for path in source.iterdir():
        if path.is_file():copy(path,dest/path.name)
    shutil.copytree(source/'assembly',dest/'assembly',dirs_exist_ok=True)
    selected=source/report['selected']
    shutil.copytree(selected/'verification-work',dest/'verification-work',dirs_exist_ok=True)
    calibration=source/'calibration'
    copy(calibration/'calibration.json',dest/'calibration.json')
    for phase in calibration.glob('phase-*'):
        for name in ('phase-probe.json','phase-debugger.txt','phase-trace.txt','phase-stderr.txt','player.json'):
            if (phase/name).exists():copy(phase/name,dest/'phase-probes'/phase.name/name)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--work',type=Path)
    p.add_argument('--verify',action='store_true')
    args=p.parse_args()
    manifest=HERE/'manifest.json'
    if args.verify:
        data=read(manifest)
        for name,digest in data.items():assert sha(ROOT/name)==digest,name
        print(f'Verified {len(data)} artifacts')
        return
    if args.work is None:p.error('--work required')
    work=args.work.resolve();dest=HERE/'evidence';full=work/'speech-full'
    report=read(full/'report.json')
    assert report['complete'] and report['recording']['recording_complete']
    for row in report['candidates']:candidate(full/row['directory'],dest/'speech-full'/row['directory'])
    for path in full.iterdir():
        if path.is_file():copy(path,dest/'speech-full'/path.name)
    for path in (full/'recording').rglob('*'):
        if path.is_file() and path.suffix!='.fmf':copy(path,dest/'speech-full/recording'/path.relative_to(full/'recording'))
    shutil.copytree(full/'producer-source',dest/'producer-source',dirs_exist_ok=True)
    short=work/'speech-short'
    if short.exists():
        candidate(short/'pilot',dest/'speech-short/pilot')
        copy(short/'report.json',dest/'speech-short/report.json')
    micro=work/'micro-all-bytes-v2'
    for name in ('fuse.json','native.json','player.json','soundtrack.mulaw','output-times.u32.gz','audiobook-preview.trd'):
        if (micro/name).exists():copy(micro/name,dest/'micro-all-bytes'/name)
    if micro.exists():
        for folder in ('assembly','verification-work'):
            shutil.copytree(micro/folder,dest/'micro-all-bytes'/folder,dirs_exist_ok=True)
    failed=work/'micro-all-bytes/assembly/assembler.log'
    if failed.exists():copy(failed,dest/'rejected-assembler-spacing.log')
    if (work/'unit-tests.txt').exists():copy(work/'unit-tests.txt',dest/'unit-tests.txt')
    control=work/'control64'
    if control.exists():
        # The exact-accumulator control has its own complete producer and proof.
        control_report=read(control/'report.json')
        assert control_report['complete']
        assert sha(control/'source-preview.wav')==sha(full/'source-preview.wav')
        for row in control_report['candidates']:
            folder=Path(row['directory'])
            assert read(folder/'fuse.json')['complete'] and read(folder/'native.json')['complete']
        for path in control.rglob('*'):
            if path.is_file() and path.suffix!='.fmf':copy(path,dest/'control64'/path.relative_to(control))
        comparison=dict(reference_wav_sha256=sha(full/'source-preview.wav'),
            source_pcm_sha256=report['source']['source_sha256'],
            snr_64khz_db=control_report['quality']['minimum_fixed_clock_snr_db'],
            snr_128khz_db=report['selected']['quality']['minimum_snr_db'],
            scope='Same complete prepared PCM16 reference, filter, precision, edge exclusion and fixed-clock metric')
        comparison['improvement_db']=comparison['snr_128khz_db']-comparison['snr_64khz_db']
        (dest/'comparison.json').write_text(json.dumps(comparison,indent=2)+'\n')
    target=ROOT/'ZX-audiobook-mulaw-128-test.trd'
    copy(full/'audiobook-preview.trd',target)
    assert sha(target)==report['selected']['trd_sha256']==report['recording']['source_trd_sha256']
    copy(full/'report.json',HERE/'results.json')
    files=sorted(p for p in dest.rglob('*') if p.is_file())+[target,HERE/'results.json']
    manifest.write_text(json.dumps({str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in files},indent=2)+'\n')
    print(f'Archived {len(files)} artifacts')


if __name__=='__main__':main()
