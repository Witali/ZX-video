"""Reproduce the old controls, audit Fuse counter debt and compare DAC steps.

The instantaneous-DAC diagnostic excludes normal oscillator edges by measuring
each command before/after at the same chip phase. It is a bounded artifact
proxy, not a count of audible clicks or a perceptual quality score.
"""
import argparse
import gzip
import json
from pathlib import Path
import struct
import subprocess

from build import HERE, ROOT, CONTROL_HZ, CPU_HZ, REGISTER_ORDER, control_frames, sha
from verify import decode_records, unpack


def serial_probe(data, order, frames):
    records,_ = decode_records(data)
    events = []
    last = -1
    # Reproduce the measured decoder path, including skipped-mask slot costs.
    write_cost = 241 if order==REGISTER_ORDER else 219
    before_out = 192 if order==REGISTER_ORDER else 170
    for record in records:
        if record['tick']>=frames:
            break
        values = dict(record['writes'])
        cpu = record['tick']*CPU_HZ/CONTROL_HZ+41+365
        for reg in order:
            if reg in values:
                sample = max(last+1,round((cpu+before_out)*44100/CPU_HZ))
                events.append((sample,reg,values[reg]))
                last = sample
                cpu += write_cost
            else:
                cpu += 77
    count = round(frames*44100/CONTROL_HZ)
    blob = b'AYE1'+struct.pack('<III',44100,count,14)
    blob += b''.join(struct.pack('<IBB',*event) for event in events)
    return blob,events


def fuse_counter_probe(events):
    """The published Fuse loop: zero period breaks without subtracting debt.

    Aggregate intervals of equal period analytically. Each renderer step is
    about32 Spectrum T. A later nonzero period consumes the whole accumulated
    counter before the subsequent R13 action can reset it. Counts are source-
    algorithm predictions, not wall-clock timings of a particular machine.
    """
    state = [0]*14
    counter = 0
    step = 0
    maximum_burst = 0
    restores = 0
    pending_restore = False
    for sample,reg,value in events:
        next_step = round(sample/44100*CPU_HZ/32)
        elapsed = next_step-step
        period = state[11]+256*state[12]
        if elapsed>0:
            if period:
                burst = (counter+1)//period
                maximum_burst = max(maximum_burst,burst)
                if pending_restore and burst>1:
                    restores += 1
                counter = (counter+elapsed)%period
            else:
                counter += elapsed
            step = next_step
            pending_restore = False
        old_period = period
        state[reg] = value
        if reg==13:
            counter = 0
        if reg in (11,12) and old_period==0 and state[11]+256*state[12]>0:
            pending_restore = True
    return dict(predicted_max_envelope_iterations_in_one_renderer_step=maximum_burst,
                restores_with_accumulated_counter=restores,
                scope='Published Fuse AY-loop counter model;32-T step approximation; not measured host stalls.')


def analyze(output, node, seconds=16):
    output = Path(output).resolve()
    output.mkdir(parents=True,exist_ok=True)
    old = json.loads((HERE/'reports/ay-only/build.json').read_text())
    results = []
    for name in ('lumiere','alicia'):
        score = json.loads((HERE/'scores'/f'{name}.json').read_text(encoding='utf-8'))
        comparisons = {}
        for label,safe in (('baseline',False),('fixed',True)):
            packed,meta = control_frames(score,click_safe=safe)
            if not safe:
                expected = next(s for s in old['songs'] if s['song']==name)
                assert meta['frames_sha256']==expected['frames_sha256']
            frames = unpack(packed)
            width = min(len(frames),round(seconds*CONTROL_HZ))
            order = REGISTER_ORDER if safe else tuple(range(14))
            probe,events = serial_probe(packed,order,width)
            path = output/f'{name}-{label}.aye.gz'
            path.write_bytes(gzip.compress(probe,mtime=0))
            diagnostic = path.with_suffix('.json')
            subprocess.run([str(node),str(ROOT/'ay-converter/render_timed_ay.js'),
                str(path),str(path.with_suffix('.f32')),str(diagnostic)],check=True)
            register_periods = [row[11]+256*row[12] for row in frames]
            mode_edges = sum(bool(a[10]&16)!=bool(b[10]&16) for a,b in zip(frames,frames[1:]))
            measured = json.loads(diagnostic.read_text())
            measured['limitations'] = 'Same-phase DAC changes exclude ordinary oscillator edges. Serial events use measured219/241-T write paths, rounded to44.1kHz samples. Not perceptual click audibility or full Z80/Fuse qualification.'
            comparisons[label] = dict(full_fields=len(frames),
                zero_envelope_period_fields=register_periods.count(0),
                envelope_restarts=sum(row[13]!=255 for row in frames),
                bass_mode_edges=mode_edges,packed_bytes=len(packed),
                logical_frames_sha256=meta['frames_sha256'],
                bounded_probe_fields=width,probe_sha256=sha(probe),
                dac_steps=measured,
                fuse_counter=fuse_counter_probe(events))
        results.append(dict(song=name,comparisons=comparisons))
    report = dict(date='2026-10-26',baseline_commit='c7b3c794',
        fuse_source='https://raw.githubusercontent.com/speccytools/fuse/master/sound.c',
        hypothesis='Zero unused envelope periods accumulate counter work in Fuse; repeated gates/restarts and early ENV enables cause control discontinuities.',
        limitations='Counter-work prediction and16-second DAC-step probes do not establish physical audibility or sound-card underruns. Full native/Fuse delivery checks are separate.',
        songs=results)
    (output/'analysis.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(report,indent=2))
    return report


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'build/music-menu-click-fix/analysis')
    parser.add_argument('--node',type=Path,required=True)
    args = parser.parse_args()
    analyze(args.output,args.node)
