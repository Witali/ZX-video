"""Compare attribute artifacts and contrast on authenticated short movie windows."""
import argparse
import json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
import build_long_video_trd as video
import five_level_dither as five
import hybrid_five_level as hybrid
from cell_palette_quality import averaged,encode,restore_endpoints
from convert_cb41 import pack_blocks
from generic_cell_codebook import representation,row_sets
from prepare_cell_codebook_movie import file_sha,sha
from probe_adaptive_block_codecs import ExternalCodec


def metrics(state,image):
    actual=averaged(state)[12:84];source=image[12:84].astype(float);residual=actual-source
    luma=np.array([.2126,.7152,.0722])
    ay,sy=actual@luma,source@luma
    ac=actual.reshape(18,4,32,4,3).transpose(0,2,1,3,4).reshape(576,16,3).mean(axis=1)
    sc=source.reshape(18,4,32,4,3).transpose(0,2,1,3,4).reshape(576,16,3).mean(axis=1)
    colour=(ac-ac.mean(axis=1,keepdims=True))-(sc-sc.mean(axis=1,keepdims=True))
    dx=np.diff(residual,axis=1)[:,3::4];dy=np.diff(residual,axis=0)[3::4]
    boundary=np.concatenate([dx.reshape(-1,3),dy.reshape(-1,3)])
    return dict(rgb_mse=float(np.mean(residual**2)),luma_mse=float(np.mean((ay-sy)**2)),
        luma_span_p95_p5=float(np.percentile(ay,95)-np.percentile(ay,5)),
        source_luma_span_p95_p5=float(np.percentile(sy,95)-np.percentile(sy,5)),
        luma_std=float(ay.std()),source_luma_std=float(sy.std()),
        cell_chroma_bias_rms=float(np.sqrt(np.mean(colour**2))),
        cells_chroma_bias_over_20=int(np.count_nonzero(np.sqrt(np.mean(colour**2,axis=1))>20)),
        cell_boundary_residual_mse=float(np.mean(boundary**2)),
        solid_black_percent=float(100*np.mean(np.all(actual==0,axis=2))),
        solid_bright_white_percent=float(100*np.mean(np.all(actual==255,axis=2))),
        solid_normal_white_percent=float(100*np.mean(np.all(actual==205,axis=2))),
        source_near_black_percent=float(100*np.mean(np.max(source,axis=2)<=12)),
        source_near_white_percent=float(100*np.mean(np.min(source,axis=2)>=243)))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('prepared','lzsa','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--starts',type=int,nargs='+',default=[0,704,3392,4288])
    p.add_argument('--count',type=int,default=32)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    meta=json.loads(a.prepared.read_bytes());by_start={c['start']:c for c in meta['chunks']}
    loaded={};archives=[]
    def chunk(first):
        if first not in loaded:
            desc=by_start[first];path=a.prepared.parent/desc['file'];assert file_sha(path)==desc['sha256']
            with np.load(path,allow_pickle=False) as f:loaded[first]={k:f[k].copy() for k in f.files}
        return loaded[first]
    def state(i):return chunk(i//64*64)['five_states'][i%64].copy()
    codec=ExternalCodec('lzsa2',a.lzsa,a.lzsa,'same executable as current CB41 build')
    cache=a.output/'lzsa';cache.mkdir(exist_ok=True)
    windows=[];panels=[]
    for start in a.starts:
        if start%64 or not 1<=a.count<=64:raise ValueError('use cached chunk starts and at most 64 frames')
        saved=chunk(start);previous=chunk(start-64)['last_attrs'] if start else None
        old_hist=[state(i) for i in range(max(0,start-2),start)]
        candidate_previous=state(start-1)[3840:] if start else None
        variants={name:list(old_hist) for name in ('baseline','candidate','endpoints','contrast')};rows=[];pictures=[]
        for i in range(a.count):
            image=saved['images'][i]
            compact,previous=video.encode_compact_frame(image,previous,100000,'ordered4')
            baseline=bytearray(hybrid.refine_compact(compact,image));baseline[3840:3936]=bytes([1])*96;baseline[4512:]=bytes([1])*96
            assert bytes(baseline)==saved['five_states'][i].tobytes(),('baseline history differs',start+i)
            fixed=encode(image,baseline,candidate_previous)
            endpoints=restore_endpoints(image,baseline)
            contrast=restore_endpoints(image,fixed)
            candidate_previous=np.frombuffer(fixed[3840:],dtype=np.uint8).copy()
            four=five.from_compact(compact)
            row=dict(frame=start+i,four=metrics(four,image),baseline=metrics(baseline,image),candidate=metrics(fixed,image),endpoints=metrics(endpoints,image),contrast=metrics(contrast,image))
            rows.append(row);pictures.append((image.copy(),four,bytes(baseline),fixed,endpoints,contrast))
            variants['baseline'].append(np.frombuffer(baseline,dtype=np.uint8).copy())
            variants['candidate'].append(np.frombuffer(fixed,dtype=np.uint8).copy())
            variants['endpoints'].append(np.frombuffer(endpoints,dtype=np.uint8).copy())
            variants['contrast'].append(np.frombuffer(contrast,dtype=np.uint8).copy())
        folder=a.output/f'window-{start}';folder.mkdir(exist_ok=True)
        np.savez_compressed(folder/'input.npz',images=saved['images'][:a.count],
                            **{n:np.stack(v) for n,v in variants.items()})
        sizes={}
        for name,frames in variants.items():
            frames=np.stack(frames);sets=row_sets(frames)
            n=len(set().union(*sets));sizes[name]=dict(dictionary_rows=n,native_row_table_fits=n<=256)
            if n>256:continue
            rep=representation(frames,len(old_hist),len(frames));packed,blocks=pack_blocks(rep['raw'],codec,cache)
            (folder/(name+'.raw')).write_bytes(rep['raw']);(folder/(name+'.stream')).write_bytes(packed)
            (folder/(name+'-rows.json')).write_text(json.dumps(rep['rows'],indent=2)+'\n',encoding='utf-8')
            sizes[name].update(raw_bytes=len(rep['raw']),lzsa2_bytes=len(packed),
                raw_sha256=rep['raw_sha256'],stream_sha256=sha(packed),blocks=blocks,host_roundtrip_exact=True,
                changed_cells=sum(r['changed_cells'] for r in rep['details']),
                changed_attributes=sum(r['attribute_cells'] for r in rep['details']))
        selected=max(range(len(rows)),key=lambda i:rows[i]['baseline']['rgb_mse']-rows[i]['candidate']['rgb_mse'])
        panels.append((rows[selected]['frame'],pictures[selected]))
        summary={name:{k:float(np.mean([r[name][k] for r in rows])) for k in rows[0][name]} for name in ('four','baseline','candidate','endpoints','contrast')}
        window=dict(start=start,frames=a.count,seed_frames=list(range(max(0,start-2),start)),
            candidate_history='same two baseline screens at window entry; candidate palette then carried across all frames',
            baseline_reproduced_exact=True,metrics=summary,frames_metrics=rows,compression=sizes,
            worse_rgb_frames={n:sum(r[n]['rgb_mse']>r['baseline']['rgb_mse']+1e-8 for r in rows) for n in ('candidate','endpoints','contrast')})
        windows.append(window)
        print(json.dumps(dict(start=start,metrics=summary,
            bytes={n:s.get('lzsa2_bytes') for n,s in sizes.items()},rows={n:s['dictionary_rows'] for n,s in sizes.items()})),flush=True)
    sheet=Image.new('RGB',(1536,218*len(panels)),'#202020');draw=ImageDraw.Draw(sheet)
    endpoint_sheet=Image.new('RGB',(768,218*len(panels)),'#202020');endpoint_draw=ImageDraw.Draw(endpoint_sheet)
    for y,(index,(source,*states)) in enumerate(panels):
        images=[Image.fromarray(source).resize((256,192),Image.Resampling.NEAREST)]
        images += [Image.fromarray(video.base.render_spectrum_screen(*five.expand(s))) for s in states]
        for x,(name,img) in enumerate(zip(('Source','Four levels','Current five','Palette repair','Endpoints only','Repair + endpoints'),images)):
            draw.text((256*x+4,218*y+4),f'{index}: {name}',fill='white');sheet.paste(img,(256*x,218*y+22))
        for x,(name,slot) in enumerate((('Source',0),('Current five',2),('Endpoint bias',4))):
            endpoint_draw.text((256*x+4,218*y+4),f'{index}: {name}',fill='white')
            endpoint_sheet.paste(images[slot],(256*x,218*y+22))
    sheet.save(a.output/'preview.png')
    endpoint_sheet.save(a.output/'endpoints.png')
    for path in sorted(a.output.rglob('*')):
        if not path.is_file() or 'lzsa' in path.relative_to(a.output).parts or path.name in ('report.json',):continue
        archives.append(dict(file=str(path.relative_to(a.output)).replace('\\','/'),bytes=path.stat().st_size,sha256=file_sha(path)))
    report=dict(complete=True,release=False,scope=__doc__,baseline_commit='7124c9f',
        preparation_sha256=file_sha(a.prepared),frames=sum(w['frames'] for w in windows),
        keep_mse_per_component=64,legacy_attribute_penalty=100000,
        normal_white_allowed=True,all_five_levels_searched=True,
        palette_repair_per_cell_average_rgb_never_worse=True,
        contrast_margin=12,contrast_may_increase_rgb_error=True,
        fixed_phase=True,flash=False,player_code_changed=False,native_instruction_delta_tstates=0,
        actual_playback_measured=False,decoder_work_can_change_with_data=True,
        metric_limits='sRGB averages and luma/chroma/seam proxies; not perceptual scores, optical blending or a full-movie timing gate',
        windows=windows,artifacts=archives,preview_frames=[i for i,_ in panels],
        source_sha256_lf={n:sha(Path(__file__).with_name(n).read_bytes().replace(b'\r\n',b'\n'))
            for n in ('cell_palette_quality.py','probe_cell_palette_quality.py')})
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
