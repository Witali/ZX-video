"""Aligned, common-scale spectrograms and unpooled six-voice error diagnostics."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import wave
import numpy as np

CORE=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(CORE))
import noise_colour
from simulation_refine import Objective, spectra
import spectrogram


def read(path):
    with wave.open(str(path),'rb') as stream:
        assert stream.getnchannels()==1 and stream.getsampwidth()==2
        data=np.frombuffer(stream.readframes(stream.getnframes()),'<i2').astype(float)/32768
        rate=stream.getframerate()
    if rate==44100:return noise_colour.downsample(data)
    if rate!=22050:raise ValueError('expected 22050 or 44100 Hz')
    return data


def diagnostic(reference,audio):
    objective=Objective(reference)
    metrics,local=objective.measure(audio,per_tick=True)
    features={size:(value,objective.rms) for size,value in objective.reference.items()}
    observed={size:(spectra(audio,np.arange(objective.count),size)[:,objective.useful[size]],objective.rms)
              for size in objective.reference}
    unpooled=spectrogram.compare(features,observed)
    a,b=features[2048][0],observed[2048][0]
    hz=np.fft.rfftfreq(4096,1/22050)[objective.useful[2048]]
    bands={}
    full_power=abs(np.fft.rfft(audio))**2
    full_hz=np.fft.rfftfreq(len(audio),1/22050)
    for low,high in ((50,300),(300,1000),(1000,2000),(2000,4000),(4000,8000)):
        mask=(hz>=low)&(hz<high)
        wanted,actual=a[:,mask]**2,b[:,mask]**2
        denom=max(float(wanted.sum()),1e-20)
        bands[f'{low}-{high}']=dict(power_ratio=float(actual.sum()/denom),
                                  missing_power_fraction=float(np.maximum(wanted-actual,0).sum()/denom),
                                  extra_power_fraction=float(np.maximum(actual-wanted,0).sum()/denom))
    # Choose a source-active three-second interval with the largest average
    # full multiresolution error. This selection does not move the timeline.
    valid=objective.rms>objective.level_floor
    numerator=np.convolve(local*valid,np.ones(150),'valid')
    denominator=np.convolve(valid.astype(float),np.ones(150),'valid')
    score=numerator/np.maximum(denominator,1)
    score[denominator<100]=-1
    start=int(score.argmax())/50
    return dict(metrics=metrics,unpooled=unpooled,bands_2048=bands,
                sub_50hz_power_fraction=float(full_power[full_hz<50].sum()/max(full_power.sum(),1e-20)),
                worst_interval_seconds=[start,start+3])


def plot(reference,versions,path,interval=None):
    # Pillow renders the measured STFT cells directly; no artist redraws,
    # per-panel auto-contrast or image generation alters the numerical plot.
    from PIL import Image, ImageDraw, ImageFont
    count=len(reference)//441
    ticks=np.arange(count)
    selected=np.ones(count,bool) if interval is None else ((ticks/50>=interval[0])&(ticks/50<interval[1]))
    magnitude=spectra(reference,ticks[selected],1024)
    hz=np.fft.rfftfreq(2048,1/22050)
    useful=hz<=8000
    peak=max(float(spectra(reference,ticks,1024).max()),1e-12)
    floor=peak*.001
    reference_db=20*np.log10(np.maximum(magnitude[:,useful],floor)/peak)
    total=1+2*len(versions)
    panels=[('Prepared source',reference_db,False)]
    for index,(name,audio) in enumerate(versions,1):
        observed=spectra(audio,ticks[selected],1024)[:,useful]
        db=20*np.log10(np.maximum(observed,floor)/peak)
        panels.extend([(name,db,False),(name+' minus source',(db-reference_db),True)])
    width,height,left,top,right=1550,225,80,42,230
    image=Image.new('RGB',(width,total*(height+top+38)+35),'white')
    draw=ImageDraw.Draw(image)
    try:font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
    except OSError:font=ImageFont.load_default(size=18)
    palette=np.array([[2,0,5],[31,12,72],[90,24,107],[151,42,99],[213,72,66],[250,143,65],[252,232,159]],float)
    diverging=np.array([[33,80,170],[145,190,234],[246,246,246],[239,153,122],[170,30,46]],float)
    def colours(data,error):
        value=np.clip((data+20)/40 if error else (data+60)/60,0,1)
        table=diverging if error else palette
        position=value*(len(table)-1)
        lower=np.minimum(position.astype(int),len(table)-2)
        fraction=position-lower
        return np.rint(table[lower]*(1-fraction[...,None])+table[lower+1]*fraction[...,None]).astype(np.uint8)
    start,end=float(ticks[selected][0]/50),float((ticks[selected][-1]+1)/50)
    plot_width=width-left-right
    for index,(title,data,error) in enumerate(panels):
        y=index*(height+top+38)+top
        heat=Image.fromarray(colours(data.T[::-1],error)).resize((plot_width,height),Image.Resampling.BOX)
        image.paste(heat,(left,y))
        draw.text((left,y-29),title,font=font,fill='black')
        for khz in (0,2,4,6,8):
            yy=y+height-round(khz/8*height)
            draw.text((8,yy-9),str(khz)+' kHz',font=font,fill='black')
        for seconds in np.linspace(start,end,7):
            xx=left+round((seconds-start)/(end-start)*plot_width)
            draw.line((xx,y+height,xx,y+height+4),fill='black')
            draw.text((xx-16,y+height+7),f'{seconds:.1f}',font=font,fill='black')
        bar=left+plot_width+20
        gradient=np.linspace(20 if error else 0,-20 if error else -60,height)[:,None]
        strip=Image.fromarray(colours(gradient,error)).resize((22,height))
        image.paste(strip,(bar,y))
        draw.text((bar+32,y),'Extra +20 dB' if error else 'Source peak 0 dB',font=font,fill='black')
        draw.text((bar+32,y+height//2-9),'Equal 0 dB' if error else '-30 dB',font=font,fill='black')
        draw.text((bar+32,y+height-22),'Missing -20 dB' if error else '-60 dB',font=font,fill='black')
    draw.text((left,image.height-30),'Time, seconds; same gain and STFT grid, no time/frequency alignment',font=font,fill='black')
    image.save(path)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--candidate',type=Path)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    old=CORE/'analysis/six_voice_clicks/evidence'
    reference=read(old/'reference.wav')
    baseline=read(old/'six-voice-preview.wav')
    versions=[('Previous smooth six-voice output',baseline)]
    result=dict(date='2026-10-13',seconds=30,reference_sha256=hashlib.sha256((old/'reference.wav').read_bytes()).hexdigest(),
                common_time_grid=True,time_or_pitch_warp=False,per_image_normalization=False,
                source_interval_seconds=[60,90],baseline=diagnostic(reference,baseline))
    if args.candidate:
        candidate=read(args.candidate)
        assert len(candidate)==len(reference)
        versions.append(('Refined six-voice output',candidate))
        result['candidate']=diagnostic(reference,candidate)
        result['candidate_wav_sha256']=hashlib.sha256(args.candidate.read_bytes()).hexdigest()
    plot(reference,versions,args.output/'spectrogram-full.png')
    plot(reference,versions,args.output/'spectrogram-detail.png',result['baseline']['worst_interval_seconds'])
    if args.candidate:
        plot(reference,versions[1:],args.output/'source-result-full.png')
        plot(reference,versions[1:],args.output/'source-result-detail.png',result['baseline']['worst_interval_seconds'])
    (args.output/'spectral-report.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
