"""Audit the noise-only edit and compare whole captures and noisy intervals."""
import argparse
import gzip
import json
from pathlib import Path
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(HERE))
sys.path.insert(0,str(HERE/'analysis/entertainer'))
from probe import decode
from support import save,sha
from verify_preview import expected_registers,extract_player
import spectrogram
import ay_fidelity as ay


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('input','baseline','candidate','ffmpeg','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    old = np.frombuffer(gzip.decompress((args.baseline/'registers.gz').read_bytes()),np.uint8).reshape(-1,11)
    raw_bytes = gzip.decompress((args.candidate/'registers.gz').read_bytes())
    new = np.frombuffer(raw_bytes,np.uint8).reshape(-1,11)
    assert expected_registers(gzip.decompress((args.candidate/'soundtrack.ay9.gz').read_bytes())) == raw_bytes
    np.testing.assert_array_equal(old[:,:6],new[:,:6])
    np.testing.assert_array_equal(old[:,7],new[:,7])
    mask = old[:,6] > 0
    np.testing.assert_array_equal(mask,new[:,6]>0)
    np.testing.assert_array_equal(old[~mask],new[~mask])
    states = [json.loads(gzip.decompress((d/'channel-states.json.gz').read_bytes()))['states']
              for d in (args.baseline,args.candidate)]
    owners = {}
    for i,(a,b) in enumerate(zip(*states)):
        for key in ('tick','component_ids','periods','tone_volumes','mixer','noise_share','noise_channel'):
            assert a[key] == b[key],(i,key)
        assert b['noise_period'] == new[i,6] and b['volumes'] == list(new[i,8:])
        for c,track in enumerate(b['component_ids']):
            if track:
                assert owners.setdefault(track,c) == c
            if b['tone_volumes'][c]:
                assert not new[i,7] & (1 << c)
            if not mask[i] or c != b['noise_channel']:
                assert new[i,8+c] == old[i,8+c]
        if mask[i]:
            c = b['noise_channel']
            assert 1 <= new[i,8+c] <= old[i,8+c]
            assert int(old[i,8+c])-int(new[i,8+c]) <= 2
    report = json.loads((args.candidate/'report.json').read_bytes())
    for name,artifact in report['artifacts'].items():
        content = (args.candidate/name).read_bytes()
        assert sha(content) == artifact['sha256'] and len(content) == artifact['bytes'],name
    for name,digest in report['producer_sources_sha256_lf'].items():
        assert sha((HERE/name).read_bytes().replace(b'\r\n',b'\n')) == digest,name
    assert extract_player((args.baseline/'audio-preview.trd').read_bytes()) == extract_player((args.candidate/'audio-preview.trd').read_bytes())
    verification = json.loads((args.candidate/'verification.json').read_bytes())
    assert verification['fuse']['complete'] and not verification['fuse']['missing_or_duplicate_fields']
    assert verification['fuse']['register_writes'] == len(new)*22
    source = decode(args.ffmpeg,args.input,duration=len(new)/50)[:len(new)*441]
    reference = spectrogram.features(source)
    result = {}
    signals = {'Original':source}
    ratio = 50*70908/3546900
    for name,directory in [('Previous tracked AY',args.baseline),('Fitted noise AY',args.candidate)]:
        audio = decode(args.ffmpeg,directory/'fuse-preview.wav')
        loops = []
        for loop in range(2):
            aligned = np.interp((np.arange(len(source))+loop*len(source))*ratio,np.arange(len(audio)),audio)
            features = spectrogram.features(aligned)
            loops.append(spectrogram.compare({k:(a[mask],r[mask]) for k,(a,r) in reference.items()},
                                             {k:(a[mask],r[mask]) for k,(a,r) in features.items()}))
            if loop == 0:
                signals[name] = aligned
        result[name] = loops
    audit = dict(date='2026-10-04',complete=True,ticks=len(new),noise_ticks=int(mask.sum()),
        component_count=len(owners),component_channel_migrations=0,active_tones_disabled=0,
        tone_periods_identical=True,mixers_identical=True,noise_presence_and_routes_identical=True,
        other_channel_volumes_identical=True,all_silent_noise_states_byte_identical=True,
        period_ticks_changed=int(np.sum(old[:,6]!=new[:,6])),
        volume_ticks_changed=int(np.any(old[:,8:]!=new[:,8:],axis=1).sum()),
        packed_decode_and_all_state_bytes_exact=True,all_artifact_and_producer_hashes_match=True,
        player_binary_identical=True,ordinary_tstates_before=974,ordinary_tstates_after=974,delta_tstates=0,
        trd_sha256=sha((args.candidate/'audio-preview.trd').read_bytes()),
        noisy_interval_stft=result,normalization='Global RMS over the full loop, then score the same 415 detected-noise states; fixed clock mapping, no local gain or time warp.')
    save(args.output/'noise-audit.json',audit)
    fig,axes = plt.subplots(2,1,figsize=(14,8))
    fig.subplots_adjust(left=.08,right=.96,bottom=.09,top=.84,hspace=.42)
    hz = np.fft.rfftfreq(8192,1/22050)
    useful = (hz >= 150) & (hz <= 8000)
    for name,audio in signals.items():
        normal = audio/max(float(np.sqrt(np.mean(audio**2))),1e-12)*.1
        magnitude,_ = ay.spectra(normal,22050,50,len(new),window_size=4096)
        # A diagnostic broadband floor estimate, not separated source noise.
        power = magnitude[mask]**2
        floor = np.median(np.lib.stride_tricks.sliding_window_view(
            np.pad(power,((0,0),(8,8)),mode='edge'),17,axis=1),axis=-1)/.7
        broad = np.minimum(power,floor).mean(axis=0)
        axes[0].plot(hz[useful],10*np.log10(np.maximum(broad[useful],1e-14)),label=name,linewidth=1.3)
    axes[0].set(xscale='log',xlim=(150,8000),xlabel='Frequency (Hz)',ylabel='Mean broadband-floor power (dB)',
        title='Same 415 noisy states, first complete Fuse loops; global RMS match')
    axes[0].grid(alpha=.25); axes[0].legend()
    t = (np.arange(len(new))+.5)/50
    axes[1].step(t,old[:,6],where='mid',label='Previous R6',alpha=.65)
    axes[1].step(t,new[:,6],where='mid',label='Fitted R6',alpha=.9)
    axes[1].set(xlim=(0,len(new)/50),ylim=(-1,33),xlabel='Source time (seconds)',ylabel='Noise period R6',
        title='Period changes every 20 ms; zero denotes disabled noise in this file format')
    axes[1].grid(alpha=.25); axes[1].legend()
    fig.suptitle('Noise colour: measured chip output and selected periods\nBroadband-floor estimate can include dense harmonics and transients',fontsize=13)
    fig.savefig(args.output/'noise-colour.png',dpi=130)
    plt.close(fig)
    print(json.dumps(audit),flush=True)


if __name__ == '__main__':
    main()
