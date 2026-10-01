"""Preserve full preparation and an oversized selected CB41 movie attempt."""
import argparse
import gzip
import json
from pathlib import Path
from prepare_cell_codebook_movie import file_sha, sha


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('prepared','build','inspection','preview','log','evidence','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.evidence.mkdir(parents=True,exist_ok=True)
    preparation=json.loads(a.prepared.read_bytes());check=json.loads(a.inspection.read_bytes())
    assert check['preparation_sha256']==file_sha(a.prepared)
    assert check['original_audio_prefix_exact'] and check['full_host_screens_exact']
    assert check['preview_sha256']==file_sha(a.preview)
    failed=json.loads((a.build/'conversion.json').read_bytes())
    assert not failed['complete'] and 'needs 2782 sectors' in failed['failure']
    plan=json.loads((a.build/'partition.json').read_bytes())
    meta=json.loads((a.build/'ZX-video-10fps_part01.json').read_bytes())
    assert meta['used_sectors']>2544 and meta['free_sectors']==2544-meta['used_sectors']
    stream=a.build/'work/ZX-video-10fps_part01/codebook.stream'
    assert stream.stat().st_size==meta['video_bytes']
    assert not list(a.build.glob('*.trd')), 'do not archive a failed image as a release'
    artifacts=[]
    def archive(path,key):
        raw=path.read_bytes();packed=gzip.compress(raw,mtime=0);target=a.evidence/(key+'.gz')
        target.write_bytes(packed)
        artifacts.append(dict(file=target.name,raw_bytes=len(raw),raw_sha256=sha(raw),
            archive_bytes=len(packed),archive_sha256=sha(packed)))
    for path,key in ((a.prepared,'preparation.json'),(a.inspection,'inspection.json'),
                     (a.preview,'preview.png'),(a.log,'failed-build.log')):
        archive(path,key)
    for name in ('audio.bin','registers.bin','words.npz','contract.json','decode.json'):
        archive(a.prepared.parent/name,'prepared-'+name)
    for path in sorted(a.build.rglob('*')):
        if not path.is_file():continue
        rel=path.relative_to(a.build)
        if any(s in ('zx0','lzsa') for s in rel.parts):continue
        if path.suffix in ('.json','.bin','.npz','.raw','.stream','.ayh1'):
            archive(path,'build-'+str(rel).replace('\\','-').replace('/','-'))
    sources=('prepare_cell_codebook_movie.py','build_cb41_cadence_movie.py',
        'balance_cb41_cadence.py','convert_cb41.py','inspect_cb41_cadence_movie.py',
        'archive_cb41_cadence_attempt.py')
    for name in sources:archive(Path(__file__).with_name(name),'source-'+name)
    report=dict(complete=True,release=False,full_movie_playback_verified=False,
        requested_fps='10',frames=preparation['frames'],ay_ticks=preparation['ay_ticks'],
        preparation=check,partition=plan['balanced_target'],
        measured_volume=dict(part=1,frames=meta['frames'],video_bytes=meta['video_bytes'],
            video_sectors=meta['video_sectors'],used_sectors=meta['used_sectors'],
            capacity_sectors=2544,overflow_sectors=-meta['free_sectors'],fits=False),
        fully_encoded_selected_volumes=1,other_volumes_encoded=False,
        rejection='Selected three-volume partition exceeds actual capacity; no image emitted.',
        not_a_proof_of_minimum_disk_count=True,root_release_images_replaced=False,
        difficult_window_report='cb41_10fps_window.json',artifacts=artifacts)
    a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report['measured_volume']),flush=True)


if __name__=='__main__':main()
