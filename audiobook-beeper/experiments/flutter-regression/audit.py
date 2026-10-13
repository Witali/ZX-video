"""Compare periodic timing/noise on authenticated, identical-source checkpoints."""
import argparse
from functools import partial
import gzip
import hashlib
import io
import json
from pathlib import Path
import sys
import wave

import numpy as np

HERE = Path(__file__).resolve().parent
BEEPER = HERE.parents[1]
sys.path[:0] = [str(BEEPER), str(BEEPER.parent/'toolkit')]
from audit_direct_regression import fixed_reference
from convert_mulaw_audio import filter_signal, STABLE_FILTER
from verify_direct import reference, sample_positions, expand_samples
from build_pdm import write_wav
from direct_player import HOLDS

CPU, FIELD = 3546900, 70908
STAGES = [('original', 'b359f532', 'ima-direct'),
          ('weighted', '83abfc59', 'ima-direct-weighted'),
          ('compensated_locked', '4a819dff', 'ima-direct-locked'),
          ('waveform', '5d28485e', 'ima-waveform'),
          ('current', 'b87ac68f', 'quality-max/evidence/ima4/selected')]


def read(path, root):
    data = path.read_bytes()
    if data.startswith(b'version https://git-lfs.github.com/spec/v1'):
        lines = data.decode().splitlines()
        oid = next(x.split(':', 1)[1] for x in lines if x.startswith('oid sha256:'))
        data = (root/'.git/lfs/objects'/oid[:2]/oid[2:4]/oid).read_bytes()
        assert hashlib.sha256(data).hexdigest() == oid
    return data


def metrics(x, y, rate=44100):
    """Field-folded error and source power with one anchored clock, no fits."""
    count = min(len(x), len(y))
    select = np.arange(4410, count-4410)
    ref = x[select]
    error = y[select]-ref
    phase = np.floor(select*CPU/rate % FIELD*128/FIELD).astype(int)
    def fold(values, bins):
        return np.bincount(bins, weights=values*values, minlength=128)/np.maximum(1,np.bincount(bins,minlength=128))
    power = fold(error, phase)
    source = fold(ref, phase)
    split = len(error)//2
    early = fold(error[:split], phase[:split])
    late = fold(error[split:], phase[split:])
    ratio = power/np.maximum(1e-20, source)
    signal_power,noise_power=float(np.mean(ref*ref)),float(np.mean(error*error))
    return dict(total_snr_db=(float(10*np.log10(signal_power/noise_power)) if signal_power>1e-24 and noise_power>0 else None),
                source_rms=float(np.sqrt(np.mean(ref*ref))),
                error_rms=float(np.sqrt(np.mean(error*error))),
                field_error_power_peak=float(power.max()),
                field_error_power_std=float(np.std(power)),
                field_error_power_max_min=float(power.max()/power.min()),
                field_relative_error_max_min=(float(ratio.max()/ratio.min()) if signal_power>1e-24 else None),
                early_late_profile_correlation=float(np.corrcoef(early,late)[0,1]),
                field_error_power=power.tolist())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--ffmpeg', required=True)
    args = parser.parse_args()
    root = args.repository.resolve()
    out = args.output.resolve()
    assert not out.exists()
    out.mkdir(parents=True)
    report = dict(complete=False, filter=STABLE_FILTER, field_hz=CPU/FIELD,
                  unchanged_source=True, physical_hardware_tested=False, stages=[])
    common = None
    for label, commit, relative in STAGES:
        path = root/'audiobook-beeper/experiments'/relative
        if (path/'artifacts.json').exists():
            saved = json.loads(read(path/'artifacts.json',root))
            expected = {k:v['sha256'] for k,v in saved.items()}
        else:
            saved = json.loads(read(root/'audiobook-beeper/experiments/quality-max/manifest.json',root))
            prefix = path.relative_to(root).as_posix()+'/'
            expected = {k[len(prefix):]:v for k,v in saved.items() if k.startswith(prefix)}
        def authenticated(name):
            data = read(path/name,root)
            assert hashlib.sha256(data).hexdigest()==expected[name], (label,name)
            return data
        meta = json.loads(authenticated('player.json'))
        proof = json.loads(authenticated('fuse.json'))
        native = json.loads(authenticated('native.json'))
        meta.setdefault('model',dict(holds=HOLDS,beta=.5,extent=1.))
        meta.setdefault('loop_idle_pairs',0)
        meta.setdefault('outputs_per_cycle',meta['pcm_samples']*16)
        assert proof['complete'] and native['complete'] and proof['cycles_verified']==2
        assert proof['every_pdm_bit_exact'] and proof['every_predictor_and_index_exact']
        raw = authenticated('source-preview.wav')
        with wave.open(io.BytesIO(raw),'rb') as wav:
            assert wav.getparams()[:3] == (1,1,8000)
            source = np.frombuffer(wav.readframes(wav.getnframes()),'u1').copy()
        if common is None:
            common = source
        else:
            assert np.array_equal(source,common),label
        packed = gzip.decompress(authenticated('soundtrack.ima.gz'))
        timeline = np.frombuffer(gzip.decompress(authenticated('output-times.u32.gz')),'<u4').astype(np.int64)
        pcm, _, levels, bits = reference(packed, cycles=2, model=meta['model'], idle_pairs=meta['loop_idle_pairs'])
        count = meta['outputs_per_cycle']
        assert len(timeline)==2*count+1 and len(source)==len(pcm)
        row = dict(stage=label,checkpoint=commit,source_sha256=hashlib.sha256(source.tobytes()).hexdigest(),
                   packed_sha256=hashlib.sha256(packed).hexdigest(),model=meta['model'],loops=[])
        for loop in range(2):
            times = timeline[loop*count:(loop+1)*count+1].copy()
            times -= times[0]
            output = filter_signal(bits[loop*count:(loop+1)*count],times,args.ffmpeg,768000)
            rate = meta.get('compensated_reference_rate_hz') or len(source)*CPU/times[-1]
            fixed = fixed_reference(source,times[-1],rate,args.ffmpeg)
            result = metrics(fixed,output)
            held = filter_signal(expand_samples(meta,levels)/256.,times,args.ffmpeg,768000)
            result['pdm_only'] = metrics(held,output)
            positions = times[sample_positions(meta)]
            # Ignore only the already silent guard in the timing diagnosis.
            active = positions[:len(source)-128]
            mean = (active[-1]-active[0])/(len(active)-1)
            residual = active-(active[0]+np.arange(len(active))*mean)
            duration = np.diff(active)
            rates = 40*CPU/(active[40:]-active[:-40])
            result.update(loop=loop+1,reference_rate=rate,
                sample_tstates=[int(duration.min()),int(duration.max())],
                five_ms_speed_error_percent=[float((rates.min()/8000-1)*100),float((rates.max()/8000-1)*100)],
                clock_residual_peak_to_peak_us=float(np.ptp(residual)/CPU*1e6),
                exact_field_delay_amplitude_us=float(2*abs(np.mean((residual-residual.mean())*np.exp(-2j*np.pi*active/FIELD)))/CPU*1e6))
            row['loops'].append(result)
            if loop==0:
                write_wav(out/(label+'-output.wav'),output*.8)
        report['stages'].append(row)
        print(json.dumps(dict(stage=label,summary=[{k:({kk:vv for kk,vv in v.items() if kk!='field_error_power'} if k=='pdm_only' else v)
            for k,v in x.items() if k!='field_error_power'} for x in row['loops']])),flush=True)
        (out/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    report['complete']=True
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':
    main()
