"""Keep rejected/soft contour evidence and a host-side comparison animation."""
import argparse
import gzip
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import five_level_dither as five
from build_zxv_trd import render_spectrum_screen
from prepare_cell_codebook_movie import file_sha, sha


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('strong','soft','tests','evidence','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();args.evidence.mkdir(parents=True,exist_ok=True)
    artifacts=[];reports={}
    def archive(path,name):
        raw=path.read_bytes()
        if path.suffix=='.py':raw=raw.replace(b'\r\n',b'\n')
        packed=raw if path.suffix in ('.png','.npz','.gif') else gzip.compress(raw,mtime=0)
        target=args.evidence/(name if path.suffix in ('.png','.npz','.gif') else name+'.gz')
        target.write_bytes(packed)
        artifacts.append(dict(file=target.name,sha256=sha(packed),raw_sha256=sha(raw),bytes=len(packed)))
    for name,folder in (('strong',args.strong),('soft',args.soft)):
        report=json.loads((folder/'report.json').read_bytes());reports[name]=report
        assert report['complete']
        for row in report['artifacts']:
            path=folder/row['file'];assert file_sha(path)==row['sha256']
            archive(path,name+'-'+row['file'].replace('/','-'))
        archive(folder/'report.json',name+'-report.json')
        for source,wanted in report['source_sha256_lf'].items():
            path=folder/'source'/source if name=='strong' else Path(__file__).with_name(source)
            assert sha(path.read_bytes().replace(b'\r\n',b'\n'))==wanted
            archive(path,name+'-source-'+source)
    native_path=args.soft/'native.json';native=json.loads(native_path.read_bytes())
    assert native['complete'] and native['quality_report_sha256']==file_sha(args.soft/'report.json')
    assert args.tests.read_text().strip().endswith('OK')
    archive(native_path,'soft-native.json');archive(args.tests,'tests.txt')
    for name in ('archive_monochrome_contours.py','profile_cell_palette_quality.py'):
        archive(Path(__file__).with_name(name),'source-'+name)
    with np.load(args.soft/'window-160/input.npz',allow_pickle=False) as data:
        frames=[]
        for i in range(2,len(data['baseline'])):
            frame=Image.new('RGB',(512,214),'#202020');draw=ImageDraw.Draw(frame)
            for x,(key,title) in enumerate((('baseline','Monochrome'),('contours','Soft contours'))):
                draw.text((256*x+4,4),title,fill='white')
                frame.paste(Image.fromarray(render_spectrum_screen(*five.expand(data[key][i].tobytes()))),(256*x,22))
            frames.append(frame)
        animation=args.soft/'comparison.gif'
        frames[0].save(animation,save_all=True,append_images=frames[1:],duration=100,loop=0,disposal=2)
        # GIF encoders may combine identical pictures. Check the reconstructed
        # 100-ms timeline, not just the number of stored image records.
        with Image.open(animation) as decoded:
            at=0
            for index in range(decoded.n_frames):
                decoded.seek(index);duration=decoded.info['duration']
                assert duration>0 and duration%100==0
                for _ in range(duration//100):
                    np.testing.assert_array_equal(np.asarray(decoded.convert('RGB')),np.asarray(frames[at]))
                    at+=1
            assert at==len(frames)==32
        archive(animation,'comparison.gif')
    soft=reports['soft'];means={}
    for name in ('baseline','contours'):
        samples=[f for row in native['results'] if row['variant']==name for f in row['frames']]
        means[name]=dict(luma_mse=float(np.mean([w['mean_luma_mse'][name] for w in soft['windows']])),
            lzsa2_bytes=sum(w['compression'][name]['lzsa2_bytes'] for w in soft['windows']),
            mean_output_tstates=float(np.mean([f['tstates'] for f in samples])),
            maximum_output_tstates=max(f['tstates'] for f in samples))
    result=dict(date='2026-10-01',complete=True,release=False,baseline_commit='0cbfa17',frames=96,
        windows=[dict(local_start=w['start'],frames=w['frames']) for w in soft['windows']],
        metrics=means,mean_changed_sample_percent=float(np.mean([w['mean_changed_sample_percent'] for w in soft['windows']])),
        strong_rejected=True,strong_row_counts=[w['compression']['contours']['dictionary_rows'] for w in reports['strong']['windows']],
        soft_row_counts=[w['compression']['contours']['dictionary_rows'] for w in soft['windows']],
        decoder_format_unchanged=True,native_instruction_delta_tstates=0,
        native_frames_checked=sum(len(r['frames']) for r in native['results']),
        full_player_timing_measured=False,new_trd_generated=False,
        default_changed=False,preview='comparison.gif',
        preview_scope='32 host-rendered frames at nominal 10 fps, not measured emulator publication timing',
        decision='Retain soft contours as an optional host prototype; reject strong automatic tracing. No object-recognition or full-playback guarantee.',
        artifacts=artifacts)
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('frames','metrics','mean_changed_sample_percent','native_frames_checked')}))


if __name__=='__main__':main()
