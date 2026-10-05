"""Audit the O. Henry audition and compare both complete Fuse loops to source."""
import argparse
import gzip
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(HERE))
import ay_fidelity as ay
import quality
import spectrogram
from support import save,sha
from verify_preview import expected_registers


def decode(ffmpeg,path,*,start=0,duration=None):
    command = [str(ffmpeg),'-v','error','-nostdin','-ss',str(start),'-i',str(path)]
    if duration is not None:
        command += ['-t',str(duration)]
    command += ['-ac','1','-ar','22050','-f','f32le','-']
    return np.frombuffer(subprocess.run(command,capture_output=True,check=True).stdout,'<f4').astype(float)


def normalized(samples):
    return samples/max(float(np.sqrt(np.mean(samples**2))),1e-12)*.1


def draw(signals,out,start,end,size):
    count = len(next(iter(signals.values())))//441
    matrices = [ay.spectra(normalized(a),22050,50,count,window_size=size)[0] for a in signals.values()]
    hz = np.fft.rfftfreq(size*2,1/22050)
    useful = (hz >= 70) & (hz <= 8000)
    peak = max(float(matrices[0].max()),1e-12)
    lo,hi = round(start*50),round(end*50)
    fig,axes = plt.subplots(2,1,figsize=(14,7),sharex=True,sharey=True)
    fig.subplots_adjust(left=.075,right=.86,bottom=.1,top=.84,hspace=.27)
    for axis,(name,_),magnitude in zip(axes,signals.items(),matrices):
        db = 20*np.log10(np.maximum(magnitude[lo:hi,useful],peak*.001)/peak)
        picture = axis.pcolormesh((np.arange(lo,hi)+.5)/50,hz[useful],db.T,
            shading='auto',cmap='magma',vmin=-60,vmax=0,rasterized=True)
        axis.set_yscale('log')
        axis.set_yticks([100,250,500,1000,2000,4000,8000],labels=['100','250','500','1k','2k','4k','8k'])
        axis.set_ylabel('Hz'); axis.set_title(name,loc='left',fontsize=11)
        axis.set_xlim(start,end)
    axes[-1].set_xlabel('Seconds from start of the source excerpt; 20-ms hop')
    fig.suptitle(f'O. Henry — original and current AY conversion\n{size/22050*1000:.2f}-ms Hann window; global RMS match, fixed Spectrum clock mapping',fontsize=13)
    bar = fig.add_axes([.89,.16,.016,.64])
    fig.colorbar(picture,cax=bar,label='dB relative to source peak; common -60-dB floor')
    fig.savefig(out,dpi=130); plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('directory','ffmpeg','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    report = json.loads((args.directory/'report.json').read_bytes())
    verification = json.loads((args.directory/'verification.json').read_bytes())
    assert report['disk_timing_verified'] and report['profile'] == 'music'
    assert report['start_seconds'] == 60 and report['ticks'] == 1200
    for name,item in report['artifacts'].items():
        content = (args.directory/name).read_bytes()
        assert sha(content) == item['sha256'] and len(content) == item['bytes'],name
    for name,digest in report['producer_sources_sha256_lf'].items():
        assert sha((HERE/name).read_bytes().replace(b'\r\n',b'\n')) == digest,name
    raw = gzip.decompress((args.directory/'registers.gz').read_bytes())
    packed = gzip.decompress((args.directory/'soundtrack.ay9.gz').read_bytes())
    assert expected_registers(packed) == raw
    states = json.loads(gzip.decompress((args.directory/'channel-states.json.gz').read_bytes()))['states']
    assert len(states) == 1200 and len(raw) == 1200*11
    owners = {}
    for i,state in enumerate(states):
        row = raw[11*i:11*(i+1)]
        assert state['tick'] == i and state['mixer'] == row[7] and state['noise_period'] == row[6]
        assert state['volumes'] == list(row[8:])
        assert state['periods'] == [int.from_bytes(row[c*2:c*2+2],'little') for c in range(3)]
        for c,track in enumerate(state['component_ids']):
            if track:
                assert owners.setdefault(track,c) == c
            if state['tone_volumes'][c]:
                assert not row[7] & (1 << c)
    fuse = verification['fuse']
    assert fuse['complete'] and fuse['cold_boot'] and not fuse['missing_or_duplicate_fields']
    assert fuse['ticks'] == 2400 and fuse['register_writes'] == 26400 and fuse['cycles_verified'] == 2
    original = decode(args.ffmpeg,report['source'],start=60,duration=24)
    assert len(original) == 1200*441
    assert sha(Path(report['source']).read_bytes()) == report['source_sha256']
    audio = decode(args.ffmpeg,args.directory/'fuse-preview.wav')
    ratio = 50*70908/3546900
    assert len(audio) >= len(original)*ratio*2
    reference = spectrogram.features(original)
    loops = []
    for loop in range(2):
        aligned = np.interp((np.arange(len(original))+loop*len(original))*ratio,np.arange(len(audio)),audio)
        loops.append(spectrogram.compare(reference,spectrogram.features(aligned)))
        if loop == 0:
            first_loop = aligned
    # Audition preserves physical Fuse timing; only this spectral plot maps
    # the known clock difference. Neither view fits local gain or time warp.
    physical_first = audio[:round(len(original)*ratio)]
    chunks = [normalized(original),np.zeros(22050),normalized(physical_first)]
    joined = np.concatenate(chunks)
    quality.write_wav(args.output/'original-then-ay.wav',joined*min(1.,.95/max(abs(joined))),22050)
    signals = {'Original recording — source seconds 60..84':original,
               'Current AY music profile — first complete cold Fuse loop':first_loop}
    draw(signals,args.output/'spectrogram-full.png',0,24,2048)
    draw(signals,args.output/'spectrogram-4-8s.png',4,8,2048)
    draw(signals,args.output/'spectrogram-attacks-4-8s.png',4,8,512)
    save(args.output/'comparison.json',dict(date='2026-10-05',complete=True,
        source_sha256=report['source_sha256'],source_interval_seconds=[60,84],
        profile='unchanged music + chip noise fit',update_rate_hz=50,sound_quantum_ms=20,
        ticks=1200,component_count=len(owners),component_channel_migrations=0,
        active_tones_disabled_by_noise=0,all_artifact_and_producer_hashes_match=True,
        every_packed_and_exported_state_verified=True,
        fixed_clock_mapping_ratio=ratio,physical_loop_seconds=24*ratio,
        fuse_loop_stft=loops,
        raw_first_24s_stft=spectrogram.compare(reference,spectrogram.features(audio[:len(original)])),
        audition=dict(file='original-then-ay.wav',original_start_seconds=0,ay_start_seconds=25,
            ay_uses_physical_timing=True,global_rms_match=True),
        limitations='Signal proxies, not speech intelligibility or listening acceptance. Music note selection and pitch holding are unchanged; no speech-specific tuning. No physical hardware test.',
        trd_sha256=sha((args.directory/'audio-preview.trd').read_bytes()),
        analysis_sources_sha256_lf={p.relative_to(HERE).as_posix():sha(p.read_bytes().replace(b'\r\n',b'\n'))
            for p in (Path(__file__),HERE/'spectrogram.py',HERE/'quality.py')}))
    print(json.dumps(dict(complete=True,component_count=len(owners),fuse_loop_stft=loops)),flush=True)


if __name__ == '__main__':
    main()
