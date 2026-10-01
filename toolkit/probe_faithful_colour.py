"""Bounded colour/coverage comparison with per-sample monochrome guards."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image,ImageDraw

import faithful_colour as colour
import monochrome_five_level as mono
import five_level_dither as five
from build_zxv_trd import render_spectrum_screen
from convert_cb41 import pack_blocks
from generic_cell_codebook import representation,row_sets
from prepare_cell_codebook_movie import file_sha,sha
from probe_adaptive_block_codecs import ExternalCodec
from probe_cell_palette_quality import metrics


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('prepared','lzsa','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--luma-guard',choices=('sample','cell'),default='cell')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    meta=json.loads(args.prepared.read_bytes());chunks={c['start']:c for c in meta['chunks']};loaded={}
    def frame(i):
        start=i//64*64
        if start not in loaded:
            desc=chunks[start];path=args.prepared.parent/desc['file'];assert file_sha(path)==desc['sha256']
            with np.load(path,allow_pickle=False) as data:loaded[start]={k:data[k].copy() for k in ('images','five_states')}
        return loaded[start]['images'][i-start],loaded[start]['five_states'][i-start]
    codec=ExternalCodec('lzsa2',args.lzsa,args.lzsa,'same author LZSA2 executable as current player')
    cache=args.output/'lzsa';cache.mkdir(exist_ok=True)
    windows=[];panels=[]
    for start in (0,704,3392,4288):
        history=list(range(max(0,start-2),start));previous=None
        variants={n:[] for n in ('old_colour','baseline','joint')};images=[];rows=[]
        for i in range(max(0,start-2),start+32):
            image,old=frame(i)
            gray=mono.encode(image);joint=colour.encode(image,previous,luma_guard=args.luma_guard)
            previous=np.frombuffer(joint[3840:],dtype=np.uint8).copy()
            for name,state in (('old_colour',old.tobytes()),('baseline',gray),('joint',joint)):
                variants[name].append(np.frombuffer(state,dtype=np.uint8).copy())
            if i<start:continue
            images.append(image.copy())
            values={n:metrics(s,image) for n,s in (('old_colour',old),('baseline',gray),('joint',joint))}
            for name,state in (('old_colour',old),('baseline',gray),('joint',joint)):
                e=colour.errors(image,state)
                values[name]['physical_rgb_mse']=float(e['physical_rgb'][12:84].mean())
                values[name]['grain_variance']=float(e['grain'][12:84].mean())
                avg=colour.averaged(state)[12:84]
                values[name]['coloured_samples_percent']=float(100*np.mean(np.ptp(avg,axis=2)>1e-6))
            rows.append(dict(frame=i,**values))
            if i==start+10:panels.append((i,image.copy(),gray,old.tobytes(),joint))
        folder=args.output/f'window-{start}';folder.mkdir(exist_ok=True)
        np.savez_compressed(folder/'input.npz',images=np.stack(images),**{n:np.stack(v) for n,v in variants.items()})
        sizes={}
        for name,values in variants.items():
            frames=np.stack(values);n=len(set().union(*row_sets(frames)))
            sizes[name]=dict(dictionary_rows=n,native_row_table_fits=n<=256)
            if n>256:continue
            rep=representation(frames,len(history),len(frames));packed,blocks=pack_blocks(rep['raw'],codec,cache)
            (folder/(name+'.raw')).write_bytes(rep['raw']);(folder/(name+'.stream')).write_bytes(packed)
            (folder/(name+'-rows.json')).write_text(json.dumps(rep['rows'],indent=2)+'\n',encoding='utf-8')
            sizes[name].update(raw_sha256=rep['raw_sha256'],stream_sha256=sha(packed),
                raw_bytes=len(rep['raw']),lzsa2_bytes=len(packed),blocks=blocks,host_roundtrip_exact=True,
                changed_cells=sum(r['changed_cells'] for r in rep['details']),
                changed_attributes=sum(r['attribute_cells'] for r in rep['details']))
        summary={name:{k:float(np.mean([r[name][k] for r in rows])) for k in rows[0][name]} for name in variants}
        window=dict(start=start,frames=32,seed_frames=history,metrics=summary,frames_metrics=rows,
            history_scope='Two source-derived histories per method; joint palette hysteresis starts at first history, not full movie.',
            compression=sizes,all_guards_passed=True)
        windows.append(window)
        print(json.dumps(dict(start=start,rgb={n:m['rgb_mse'] for n,m in summary.items()},
            colour=summary['joint']['coloured_samples_percent'],
            bytes={n:s.get('lzsa2_bytes') for n,s in sizes.items()},rows={n:s['dictionary_rows'] for n,s in sizes.items()})),flush=True)
    sheet=Image.new('RGB',(1024,len(panels)*218),'#202020');draw=ImageDraw.Draw(sheet)
    for row,(index,source,*states) in enumerate(panels):
        pictures=[Image.fromarray(source).resize((256,192),Image.Resampling.NEAREST)]
        pictures += [Image.fromarray(render_spectrum_screen(*five.expand(s))) for s in states]
        for column,(title,picture) in enumerate(zip(('Source','Monochrome','Old colour','Joint colour + grain'),pictures)):
            draw.text((column*256+4,row*218+4),f'{index}: {title}',fill='white');sheet.paste(picture,(column*256,row*218+22))
    sheet.save(args.output/'preview.png')
    artifacts=[dict(file=p.relative_to(args.output).as_posix(),sha256=file_sha(p)) for p in sorted(args.output.rglob('*'))
               if p.is_file() and 'lzsa' not in p.relative_to(args.output).parts and p.name!='report.json']
    report=dict(complete=True,release=False,baseline_commit='756ecd0',frames=128,parameters=colour.PARAMETERS,luma_guard=args.luma_guard,
        preparation_sha256=file_sha(args.prepared),windows=windows,artifacts=artifacts,codec=codec.identity,
        player_code_changed=False,native_instruction_delta_tstates=0,full_player_timing_measured=False,
        all_guards_passed=True,contours_applied=False,phase_randomized=False,
        metric_limits=colour.__doc__,
        source_sha256_lf={n:sha(Path(__file__).with_name(n).read_bytes().replace(b'\r\n',b'\n')) for n in
            ('faithful_colour.py','test_faithful_colour.py','probe_faithful_colour.py')})
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
