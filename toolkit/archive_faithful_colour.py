"""Archive both guarded colour searches and a pixel-exact host comparison GIF."""
import argparse
import gzip
import json
from pathlib import Path

import numpy as np
from PIL import Image,ImageDraw
import five_level_dither as five
from build_zxv_trd import render_spectrum_screen
from prepare_cell_codebook_movie import file_sha,sha


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('strict','selected','tests','evidence','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();args.evidence.mkdir(parents=True,exist_ok=True)
    files=[];reports={}
    def archive(path,key):
        raw=path.read_bytes()
        if path.suffix=='.py':raw=raw.replace(b'\r\n',b'\n')
        compressed=path.suffix not in ('.png','.npz','.gif')
        data=gzip.compress(raw,mtime=0) if compressed else raw
        target=args.evidence/(key+'.gz' if compressed else key);target.write_bytes(data)
        files.append(dict(file=target.name,sha256=sha(data),raw_sha256=sha(raw),bytes=len(data)))
    for name,folder in (('strict',args.strict),('selected',args.selected)):
        report=json.loads((folder/'report.json').read_bytes());reports[name]=report
        assert report['complete']
        for row in report['artifacts']:
            path=folder/row['file'];assert file_sha(path)==row['sha256']
            archive(path,name+'-'+row['file'].replace('/','-'))
        archive(folder/'report.json',name+'-report.json')
        for source,wanted in report['source_sha256_lf'].items():
            path=folder/'source'/source if name=='strict' else Path(__file__).with_name(source)
            assert sha(path.read_bytes().replace(b'\r\n',b'\n'))==wanted
            archive(path,name+'-source-'+source)
    native=json.loads((args.selected/'native.json').read_bytes())
    assert native['complete'] and native['quality_report_sha256']==file_sha(args.selected/'report.json')
    assert args.tests.read_text().strip().endswith('OK')
    archive(args.selected/'native.json','native.json');archive(args.tests,'tests.txt')
    for source in ('archive_faithful_colour.py','profile_cell_palette_quality.py'):
        archive(Path(__file__).with_name(source),'source-'+source)
    pictures=[]
    with np.load(args.selected/'window-4288/input.npz',allow_pickle=False) as data:
        for index in range(2,len(data['joint'])):
            picture=Image.new('RGB',(512,214),'#202020');draw=ImageDraw.Draw(picture)
            for x,(key,title) in enumerate((('baseline','Monochrome'),('joint','Joint colour + grain'))):
                draw.text((x*256+4,4),title,fill='white')
                picture.paste(Image.fromarray(render_spectrum_screen(*five.expand(data[key][index].tobytes()))),(x*256,22))
            pictures.append(picture)
    animation=args.selected/'comparison.gif'
    pictures[0].save(animation,save_all=True,append_images=pictures[1:],duration=100,loop=0,disposal=2)
    with Image.open(animation) as decoded:
        index=0
        for frame in range(decoded.n_frames):
            decoded.seek(frame);duration=decoded.info['duration'];assert duration>0 and duration%100==0
            for _ in range(duration//100):
                np.testing.assert_array_equal(np.asarray(decoded.convert('RGB')),np.asarray(pictures[index]));index+=1
        assert index==32
    archive(animation,'comparison.gif')
    selected=reports['selected'];totals={}
    for name in ('old_colour','baseline','joint'):
        totals[name]={key:float(np.mean([w['metrics'][name][key] for w in selected['windows']]))
                      for key in selected['windows'][0]['metrics'][name]}
        totals[name]['lzsa2_bytes']=sum(w['compression'][name]['lzsa2_bytes'] for w in selected['windows'])
        samples=[f for r in native['results'] if r['variant']==name for f in r['frames']]
        if samples:
            totals[name]['mean_output_tstates']=float(np.mean([f['tstates'] for f in samples]))
            totals[name]['max_output_tstates']=max(f['tstates'] for f in samples)
    result=dict(date='2026-10-01',complete=True,release=False,baseline_commit='756ecd0',frames=128,
        metrics=totals,strict_joint_rgb_mse=float(np.mean([w['metrics']['joint']['rgb_mse'] for w in reports['strict']['windows']])),
        selected_row_counts=[w['compression']['joint']['dictionary_rows'] for w in selected['windows']],
        all_guard_checks_passed=True,luma_guard='cell',rgb_and_physical_rgb_guard='sample',
        guard_reference='monochrome image from the same source, not old colour',
        physical_error_model='source RGB sample held constant over each 2x2 footprint',
        native_frames_checked=sum(len(r['frames']) for r in native['results']),native_instruction_delta_tstates=0,
        full_player_timing_measured=False,default_changed=False,new_trd_generated=False,
        preview_scope='32 host-rendered frames, fixed 100-ms timeline; not emulator publication timing',
        decision='Retain joint colour/coverage with cell luma guard as the preferred bounded prototype; full-volume capacity and playback remain required.',
        artifacts=files)
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(frames=result['frames'],metrics=totals,native_frames=result['native_frames_checked'])))


if __name__=='__main__':main()
