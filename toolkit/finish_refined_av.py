"""Verify continuation, archive evidence and publish a complete refined TRD set."""
import argparse
import gzip
import json
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw

import faithful_colour as colour
import five_level_dither as five
from build_zxv_trd import render_spectrum_screen
from convert_video import write_json
from prepare_cell_codebook_movie import file_sha, sha


def preview(prepared, output):
    meta = json.loads(prepared.read_bytes())
    worst = sorted(meta['quality'], key=lambda q:q['rgb_mse'], reverse=True)[:2]
    indices = sorted({0,704,3392,4288,meta['frames']-1,
        *(q['frame'] for q in worst), *(q['output_frame'] for q in meta['joins'])})
    sheet = Image.new('RGB',(768,216*len(indices)), '#202020')
    draw = ImageDraw.Draw(sheet)
    samples = []
    for row, index in enumerate(indices):
        chunk = next(c for c in meta['chunks'] if c['start'] <= index < c['end'])
        path = prepared.parent/chunk['file']
        assert file_sha(path) == chunk['sha256']
        with np.load(path,allow_pickle=False) as saved:
            image = saved['images'][index-chunk['start']]
            state = saved['five_states'][index-chunk['start']].tobytes()
        pictures = [Image.fromarray(image).resize((256,192),Image.Resampling.NEAREST),
                    Image.fromarray(np.rint(colour.averaged(state)).astype(np.uint8)).resize((256,192),Image.Resampling.NEAREST),
                    Image.fromarray(render_spectrum_screen(*five.expand(state)))]
        for column, (title, picture) in enumerate(zip(('Scaled source','Average reconstructed colour','Actual fixed dither'),pictures)):
            draw.text((column*256+4,row*216+3),f'{index}: {title}',fill='white')
            sheet.paste(picture,(column*256,row*216+22))
        samples.append(meta['quality'][index])
    sheet.save(output)
    return samples


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('build','prepared','fuse','evidence','output','root'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--continuation-only', action='store_true')
    p.add_argument('--allow-fallback', action='store_true')
    args = p.parse_args()
    manifest = json.loads((args.build/'conversion.json').read_bytes())
    assert manifest['complete'] and manifest['whole_movie'] and manifest['frame_fields'] == 5
    prepared = json.loads(args.prepared.read_bytes())
    assert manifest['preparation_sha256'] == file_sha(args.prepared)
    assert manifest['frames'] == prepared['frames'] and manifest['ay_ticks'] == prepared['ay_ticks']
    continuation = args.build/'continuation'
    compatibility = args.build/'continuation-input'
    compatibility.mkdir(exist_ok=True)
    rows = []
    for number, record in enumerate(manifest['volumes'],1):
        assert file_sha(args.build/record['file']) == record['sha256']
        folder = compatibility/f'volume-{number}'
        folder.mkdir(exist_ok=True)
        for source, name in ((args.build/record['file'],'candidate.trd'),
                             (args.build/record['metadata'],'metadata.json'),
                             (args.build/record['states'],'states.npz')):
            shutil.copyfile(source,folder/name)
        rows.append(dict(volume=number,trd_sha256=record['sha256'],frames=record['frames']))
    write_json(compatibility/'capacity.json',dict(all_volumes_fit=True,volumes=rows))
    cached = continuation/'continuation.json'
    if not cached.exists() or not json.loads(cached.read_bytes())['complete']:
        subprocess.run([sys.executable,str(Path(__file__).with_name('verify_cell_codebook_continuation.py')),
            '--build',str(compatibility),'--fuse',str(args.fuse),'--raw',str(args.build/'work/stream.raw'),
            '--output',str(continuation),'--mode','fuse'],check=True)
    resumed = json.loads((continuation/'continuation.json').read_bytes())
    assert resumed['complete'] and len(resumed['volumes']) == len(rows)
    for row, check in zip(rows,resumed['volumes'],strict=True):
        assert row['trd_sha256'] == check['trd_sha256'] and check['complete']
        assert check['ay_records_exact'] and not (check['audio_underruns'] or check['ay_gaps'] or check['ay_duplicates'])
    if args.continuation_only: return
    assert (args.prepared.parent/'tests.txt').read_text().strip().endswith('OK')
    args.evidence.mkdir(parents=True,exist_ok=True)
    subprocess.run([sys.executable,str(Path(__file__).with_name('summarize_cb41_cadence.py')),
        '--run',str(args.build),'--evidence',str(args.evidence),'--output',str(args.output)],check=True)
    result = json.loads(args.output.read_bytes())
    disks = result['runs'][0]['disks']
    fallback = all(d['timing']['fallback_one_field_met'] for d in disks)
    # Apply the same nominal/fallback gate to actual predecessor-EOF resumes.
    from profile_fap3 import summarize_fuse
    resumed_timing = [summarize_fuse(json.loads((continuation/f'part-{i}.json').read_bytes()))
                      for i in range(1,len(disks)+1)]
    nominal = result['all_nominal_deadlines_met'] and all(r['nominal_deadlines_met'] for r in resumed_timing)
    fallback = fallback and all(r['fallback_one_field_met'] for r in resumed_timing)
    image_path = args.evidence/'preview.png'
    samples = preview(args.prepared,image_path)
    result.update(date='2026-10-01', whole_movie=True, video_fps=10, ay_hz=50,
        new_colour_and_audio=True, additional_disks_authorized=True,
        nominal_deadlines_met=nominal, fallback_one_field_met=fallback,
        continuation_complete=True, continuation=resumed_timing, quality_samples=samples,
        preparation_sha256=file_sha(args.prepared), root_images=[])
    result['source_sha256_lf'].update({name:sha(Path(__file__).with_name(name).read_bytes().replace(b'\r\n',b'\n'))
        for name in ('prepare_refined_av.py','finish_refined_av.py','faithful_colour.py',
                     'ay_fidelity.py','ay_square_fit.py','verify_cell_codebook_continuation.py')})
    extras = [args.prepared,args.prepared.parent/'video.json',args.prepared.parent/'audio.json',
              args.prepared.parent/'contract.json',args.prepared.parent/'tests.txt',
              args.prepared.parent/'audio.bin',image_path]
    for path in extras:
        raw = path.read_bytes()
        target = image_path if path==image_path else args.evidence/('prepared-'+path.name+'.gz')
        if path != image_path: target.write_bytes(gzip.compress(raw,mtime=0))
        result['artifacts'].append(dict(file=target.name,raw_sha256=sha(raw),
            archive_sha256=file_sha(target),raw_bytes=len(raw),archive_bytes=target.stat().st_size))
    write_json(args.output,result)
    if not (nominal or args.allow_fallback and fallback):
        raise ValueError('complete measured output fails the selected timing gate; report retained')
    for record in manifest['volumes']:
        target = args.root/record['file']
        if target.exists() and file_sha(target) != record['sha256']:
            raise ValueError('refusing to replace a different existing image')
        shutil.copyfile(args.build/record['file'],target)
        result['root_images'].append(dict(file=target.name,sha256=file_sha(target)))
    result['release'] = nominal
    result['preview_only'] = not nominal
    write_json(args.output,result)
    print(json.dumps(dict(disks=len(disks),frames=manifest['frames'],nominal=nominal,fallback=fallback)),flush=True)


if __name__ == '__main__': main()
