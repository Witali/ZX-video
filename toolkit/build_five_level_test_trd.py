"""Build one short independent TRD from three real five-level 2x2 windows.

Uses the existing AY register states, fixed full-volume row dictionary,
FAP3 motion/Huffman and adapted Fast ZX0. No runtime dictionary changes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
import ay_interrupt
import build_long_video_trd as video
import five_level_dither as five
import hybrid_five_level as hybrid
from probe_hybrid_five_level import error
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header
from bulk_frame_stream import read_packet
from encode_fap3 import encode
from build_fap3_trd import sha
from row_dictionary_video import Builder, encode_states, reference_tables
from build_integrated_bootstrap import check_cold
from build_inplace_keepalive import prime


def save(path,value):
    path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')


def source_audio(raw):
    r=Reader(raw); _,_,count,_,_=read_header(r,magic=b'FAP3')
    registers=bytearray(11); result=[]
    for _ in range(count):
        _,packet=read_packet(r,stored_guards=False)
        for tick in packet['ticks']:
            for at in range(1,len(tick),2): registers[tick[at]]=tick[at+1]
            frame=video.AyFrame(tuple(registers[i]+256*registers[i+1] for i in (0,2,4)),tuple(registers[8:11]),registers[6])
            if ay_interrupt.registers(frame)!=registers: raise ValueError('AY state not representable exactly')
            result.append(frame)
    r.end(); return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('source','ffmpeg','zx0','audio-raw','baseline-build','work','trd','report'):
        p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--starts',type=int,nargs='+',default=[629,2857,3855])
    p.add_argument('--window',type=int,default=64)
    a=p.parse_args(); a.work.mkdir(parents=True,exist_ok=True)
    if a.window<2 or any(s<0 or s+a.window>4086 for s in a.starts):
        raise ValueError('this fixture selects windows before the credits edit')
    with a.source.open('rb') as f: source_hash=hashlib.file_digest(f,'sha256').hexdigest()
    quantizers=('build_long_video_trd.py','build_zxv_trd.py','hybrid_five_level.py',
                'five_level_dither.py','dither_phase.py','row_dictionary_video.py',
                'build_five_level_test_trd.py')
    contract=dict(source_sha256=source_hash,starts=a.starts,window=a.window,zoom=1.25,
                  ffmpeg_sha256=sha(a.ffmpeg.read_bytes()),
                  quantizer_sha256_lf={name:sha(Path(__file__).with_name(name).read_bytes().replace(b'\r\n',b'\n'))
                                       for name in quantizers})
    cache=a.work/'prepared.npz'; cached=a.work/'prepared.json'
    if cache.exists() and cached.exists() and json.loads(cached.read_text())['contract']==contract:
        prepared=json.loads(cached.read_text())
        with np.load(cache,allow_pickle=False) as data:
            states=data['states']; five_states=data['five_states']
    else:
        five_frames=[]; four_frames=[]; rgb_frames=[]; rows=[]
        for start in a.starts:
            command=[str(a.ffmpeg.resolve()),'-v','error','-nostdin','-ss',str(start*3/25),'-i',str(a.source.resolve()),
                     '-an','-vf','fps=25/3,scale=256:144:flags=area','-pix_fmt','rgb24','-frames:v',str(a.window),'-f','rawvideo','-']
            rgb=subprocess.run(command,check=True,capture_output=True).stdout
            images=np.frombuffer(rgb,dtype=np.uint8).reshape(a.window,144,256,3)
            attrs=None
            for local,analysis in enumerate(images):
                image=video.apply_reframe(analysis,video.ReframeWindow(.5,.5,1.25))
                compact,attrs=video.encode_compact_frame(image,attrs,100000,'ordered4')
                candidate=bytearray(hybrid.refine_compact(compact,image))
                # Zero-index dictionary row and fixed black-border attributes.
                candidate[3840:3936]=bytes([1])*96; candidate[4512:]=bytes([1])*96
                candidate=bytes(candidate)
                before=error(hybrid.from_compact(compact),image)
                after=error(hybrid.from_five(candidate,adaptive=False),image)
                if after>before+1e-9: raise AssertionError('five-level refinement worsened RGB error')
                rows.append(dict(frame=len(rows),source_frame=start+local,four_mse=before,five_mse=after))
                five_frames.append(candidate); four_frames.append(compact); rgb_frames.append(image)
                if local%16==15: print(f'Quantized {start}: {local+1}/{a.window}',flush=True)
        states,book=encode_states(five_frames)
        five_states=np.stack([np.frombuffer(f,dtype=np.uint8) for f in five_frames])
        np.savez_compressed(cache,states=states,five_states=five_states,
                            four_states=np.stack([np.frombuffer(f,dtype=np.uint8) for f in four_frames]),images=np.stack(rgb_frames))
        prepared=dict(contract=contract,row_dictionary=book,frames=rows,
                      exact_full_native_reference=True,states_sha256=sha(states.tobytes()))
        save(cached,prepared)
    print(f'Dictionary: {prepared["row_dictionary"]["entries"]} rows; {len(states)} frames',flush=True)
    original=a.audio_raw.read_bytes(); audio=source_audio(original)
    selected=[t for s in a.starts for t in audio[s*6:(s+a.window)*6]]
    raw,codec=encode(states,selected); (a.work/'video.raw').write_bytes(raw)
    options=json.loads(a.baseline_build.read_text())['contract']['options']; options['startup_delta']=False
    with reference_tables(prepared['row_dictionary']):
        fingerprint=b'AYH1R5T1'+bytes.fromhex(sha(raw))[:6]
        b=Builder(raw,states,a.zx0.resolve(),a.work/'zx0',row_dictionary=prepared['row_dictionary'],
                  series_fingerprint=fingerprint,**options)
        b.ends=[len(states)]; image,m=b.volume(0,len(states),1)
        if image is None: raise ValueError('test does not fit one TRD')
        a.trd.write_bytes(image); save(a.work/'metadata.json',m)
        checks=check_cold(image,m,b.expected_banks); checks.update(prime(image,m,states))
    report=dict(complete=True,release=False,scope=__doc__,contract=contract,
        frames=len(states),duration_seconds=len(states)*3/25,frame_rate=[25,3],ay_rate_hz=50,
        native_size=[256,192],active_native_size=[256,144],logical_size=[128,96],active_logical_size=[128,72],
        dither='five levels, fixed 2x2 phase',row_dictionary=prepared['row_dictionary'],
        trd_sha256=sha(image),trd_bytes=len(image),states_sha256=sha(states.tobytes()),raw_sha256=sha(raw),
        original_ay_raw_sha256=sha(original),selected_ay_states_sha256=sha(b''.join(map(ay_interrupt.registers,selected))),
        codec=codec,checks=checks,quality=prepared['frames'],
        metadata_sha256=sha((a.work/'metadata.json').read_bytes()),
        **{k:m[k] for k in ('used_sectors','free_sectors','video_bytes','video_sectors','independently_bootable')})
    save(a.report,report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('row_dictionary','codec','checks','quality','scope','contract')}),flush=True)


if __name__=='__main__': main()
