"""Compare one soft-contour candidate on cached monochrome preview windows."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import five_level_dither as five
import monochrome_contours as contours
import monochrome_five_level as mono
from build_zxv_trd import render_spectrum_screen
from convert_cb41 import pack_blocks
from generic_cell_codebook import representation, row_sets
from prepare_cell_codebook_movie import file_sha, sha
from probe_adaptive_block_codecs import ExternalCodec


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('baseline','lzsa','output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--preset', choices=tuple(contours.PRESETS), default='soft')
    args = parser.parse_args()
    manifest = json.loads((args.baseline/'conversion.json').read_bytes())
    quality = json.loads((args.baseline/'monochrome-quality.json').read_bytes())
    assert manifest['complete'] and manifest['monochrome']
    with np.load(args.baseline/'work/monochrome-inputs.npz', allow_pickle=False) as f: images=f['images']
    with np.load(args.baseline/'work/five-states.npz', allow_pickle=False) as f: baseline=f['five_states']
    assert sha(images.tobytes()) == quality['input_rgb_sha256']
    assert sha(baseline.tobytes()) == manifest['five_states_sha256']
    assert len(images)==len(baseline)==256
    args.output.mkdir(parents=True, exist_ok=True)
    cache=args.output/'lzsa';cache.mkdir(exist_ok=True)
    codec=ExternalCodec('lzsa2',args.lzsa,args.lzsa,'same author executable as monochrome preview')
    windows=[];panels=[]
    for start in (0,64,160):
        count=32;history=list(range(max(0,start-2),start))
        variants={n:[baseline[i].copy() for i in history] for n in ('baseline','contours')}
        metrics=[];old_mask=None
        for i in range(start,start+count):
            source=images[i];old=baseline[i].tobytes()
            assert mono.encode(source)==old
            new,mask=contours.encode(source,preset=args.preset)
            a,b=five.unpack_levels(old[:3840]),five.unpack_levels(new[:3840])
            qa,qb=mono.quality(source,old),mono.quality(source,new)
            metrics.append(dict(frame=i,prepared_frame=manifest['prepared_range'][0]+i,
                baseline=qa,contours=qb,edge_percent=float(100*np.mean(mask[12:84])),
                changed_sample_percent=float(100*np.mean(a[12:84]!=b[12:84])),
                mask_change_percent=None if old_mask is None else float(100*np.mean(mask[12:84]!=old_mask[12:84]))))
            old_mask=mask
            variants['baseline'].append(baseline[i].copy())
            variants['contours'].append(np.frombuffer(new,dtype=np.uint8).copy())
            if i==start+10:panels.append((manifest['prepared_range'][0]+i,source.copy(),old,new))
        folder=args.output/f'window-{start}';folder.mkdir(exist_ok=True)
        np.savez_compressed(folder/'input.npz',images=images[start:start+count],**{n:np.stack(v) for n,v in variants.items()})
        sizes={}
        for name,values in variants.items():
            states=np.stack(values);n=len(set().union(*row_sets(states)))
            sizes[name]=dict(dictionary_rows=n,native_row_table_fits=n<=256)
            if n>256:continue
            rep=representation(states,len(history),len(states))
            packed,blocks=pack_blocks(rep['raw'],codec,cache)
            (folder/(name+'.raw')).write_bytes(rep['raw'])
            (folder/(name+'.stream')).write_bytes(packed)
            (folder/(name+'-rows.json')).write_text(json.dumps(rep['rows'],indent=2)+'\n',encoding='utf-8')
            sizes[name].update(raw_sha256=rep['raw_sha256'],stream_sha256=sha(packed),
                raw_bytes=len(rep['raw']),lzsa2_bytes=len(packed),blocks=blocks,host_roundtrip_exact=True,
                changed_cells=sum(r['changed_cells'] for r in rep['details']),
                changed_attributes=sum(r['attribute_cells'] for r in rep['details']))
        window=dict(start=start,frames=count,seed_frames=history,frames_metrics=metrics,compression=sizes,
            mean_luma_mse={n:float(np.mean([r[n]['luma_mse'] for r in metrics])) for n in variants},
            mean_changed_sample_percent=float(np.mean([r['changed_sample_percent'] for r in metrics])))
        windows.append(window)
        print(json.dumps({k:v for k,v in window.items() if k not in ('frames_metrics','compression')}),flush=True)
    sheet=Image.new('RGB',(768,218*len(panels)),'#202020');draw=ImageDraw.Draw(sheet)
    for y,(index,source,old,new) in enumerate(panels):
        pictures=[Image.fromarray(source).resize((256,192),Image.Resampling.NEAREST)]
        pictures += [Image.fromarray(render_spectrum_screen(*five.expand(s))) for s in (old,new)]
        for x,(name,picture) in enumerate(zip(('Source','Monochrome','Soft contours'),pictures)):
            draw.text((256*x+4,218*y+4),f'{index}: {name}',fill='white');sheet.paste(picture,(256*x,218*y+22))
    sheet.save(args.output/'preview.png')
    artifacts=[]
    for path in sorted(args.output.rglob('*')):
        if not path.is_file() or 'lzsa' in path.relative_to(args.output).parts or path.name=='report.json':continue
        artifacts.append(dict(file=path.relative_to(args.output).as_posix(),sha256=file_sha(path)))
    report=dict(complete=True,release=False,baseline_commit='0cbfa17',frames=96,
        baseline_manifest_sha256=file_sha(args.baseline/'conversion.json'),preset=args.preset,parameters=contours.PRESETS[args.preset],
        semantic_segmentation=False,default_changed=False,native_instruction_delta_tstates=0,
        actual_playback_measured=False,windows=windows,artifacts=artifacts,
        opencv_version=contours.cv2.__version__,codec=codec.identity,
        metric_limits='Luma MSE is expected to rise with outlines; no semantic recognizability or motion-compensated flicker score.',
        source_sha256_lf={n:sha(Path(__file__).with_name(n).read_bytes().replace(b'\r\n',b'\n')) for n in
            ('monochrome_contours.py','probe_monochrome_contours.py','test_monochrome_contours.py')})
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
