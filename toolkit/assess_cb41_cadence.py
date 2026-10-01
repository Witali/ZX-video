"""Assess saved CB41 frame readiness; this does not replay a faster schedule."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import statistics

FIELD = 70908
ROOT = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def trace_events(script, trace):
    widths, commands = {}, None
    for line in script.splitlines():
        line = line.strip()
        if line.startswith(('commands ', 'com ')):
            commands = []
        elif line == 'end' and commands is not None:
            tag = int(commands[0], 0)
            width = len(commands)-1
            if tag in widths and widths[tag] != width:
                raise ValueError('inconsistent trace event width')
            widths[tag] = width
            commands = None
        elif commands is not None:
            printed = re.match(r'^(?:print|pr)(?:\s+|(?=\[))(.*)$', line)
            if printed:
                commands.append(printed.group(1))
    values = [int(s.strip(), 0) for s in trace.splitlines()
              if re.fullmatch(r'(?:-?\d+|0x[\da-fA-F]+)', s.strip())]
    at, events = 0, []
    while at < len(values):
        tag = values[at]
        count = widths[tag]
        data = values[at+1:at+1+count]
        if len(data) != count:
            raise ValueError('truncated trace')
        events.append((tag, data))
        at += count+1
    return events


def stats(values):
    ordered = sorted(values)
    return dict(min_tstates=min(values), mean_tstates=statistics.mean(values),
                p95_tstates=ordered[int((len(ordered)-1)*.95)], max_tstates=max(values),
                min_ms=min(values)/FIELD*20, mean_ms=statistics.mean(values)/FIELD*20,
                max_ms=max(values)/FIELD*20)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    source = ROOT/'cell_codebook_balanced_profile.json'
    profile = json.loads(source.read_bytes())
    identities = {r['file']:r for r in profile['artifacts']}
    def read(name):
        packed = (ROOT/'cell_codebook_balanced_evidence'/name).read_bytes()
        assert sha(packed) == identities[name]['archive_sha256']
        raw = gzip.decompress(packed)
        assert sha(raw) == identities[name]['raw_sha256']
        return raw
    disks, margins, jobs, slowest = [], [], [], []
    for volume in profile['volumes']:
        part = volume['part']
        assert sha((ROOT.parent/volume['root_file']).read_bytes()) == volume['trd_sha256']
        report = json.loads(read(f'volume-{part}-timing.json.gz'))
        script = read(f'volume-{part}-timing.debugger.txt.gz')
        trace = read(f'volume-{part}-timing.trace.txt.gz')
        assert sha(script) == report['debugger_script_sha256']
        assert sha(trace) == report['trace_sha256']
        events = trace_events(script.decode(), trace.decode())
        ready = [v[0] for tag,v in events if tag in (151,152)]
        pubs = [v[0] for tag,v in events if tag == 150]
        starts = [v for tag,v in events if tag == 100]
        assert len(starts) == 1 and starts[0][1] == report['trace_nonce']
        assert pubs == [r['tstate'] for r in report['publications']]
        assert len(ready) == len(pubs) == volume['frames']
        assert report['complete'] and not report['errors'] and report['nominal_late_frames'] == 0
        assert events[-1][0] == 199
        slack = [pub-done for pub,done in zip(pubs,ready)]
        # The first frame is primed before playback; exclude it from frame-work
        # comparisons. Later ready events may overlap other queued preparation.
        work = [ready[i]-pubs[i-1] for i in range(1,len(pubs))]
        assert min(slack) >= 0 and min(work) >= 0
        margins.extend(slack[1:]); jobs.extend(work)
        slowest.extend(dict(part=part, local_frame=i, movie_frame=volume['frame_start']+i,
                            tstates=cost, ms=cost/FIELD*20) for i,cost in enumerate(work,1))
        runtime_reads = [r for r in report['reads'] if r['start_tstate'] >= pubs[0]]
        disks.append(dict(part=part, frames=len(pubs), readiness_margin=stats(slack[1:]),
            previous_publication_to_ready=stats(work),
            sectors_after_first_publication=len(runtime_reads),
            mean_read_service_ms=statistics.mean(r['tstates'] for r in runtime_reads)/FIELD*20,
            max_read_service_ms=max(r['tstates'] for r in runtime_reads)/FIELD*20,
            trd_sha256=volume['trd_sha256']))
    result = dict(complete=True, release=False, scope=__doc__,
        source_profile_sha256=sha(source.read_bytes()), frames=profile['frames'],
        inspected_intra_disk_intervals=len(jobs), field_tstates=FIELD,
        confirmed_fps=25/3, maximum_sustainable_fps_measured=False,
        readiness_margin=stats(margins), previous_publication_to_ready=stats(jobs),
        slowest_intervals=sorted(slowest, key=lambda r:r['tstates'], reverse=True)[:10],
        disks=disks, candidates=[dict(fields=fields, fps=50/fields,
            period_ms=20*fields, unchanged_trace_ready_intervals_over_budget=sum(j>fields*FIELD for j in jobs))
            for fields in (6,5,4,3,2)],
        caveats=['Readiness is sampled just after native draw, before the ready flag is stored.',
            'This is the six-field run; faster cadence changes queue work, prefetch, IRQ and rotational phases.',
            'Readiness slack is not CPU idle time: next-packet and reservoir work can occupy it.',
            'Zero intervals over a shorter budget would not prove a sustainable higher rate.',
            'Disk read service includes ROM, CPU, IRQ and physical emulation; do not add it to elapsed time twice.',
            'A true higher source fps requires new frame sampling and 50-Hz AY scheduling, not merely accelerating this movie.'])
    a.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k:result[k] for k in ('frames','readiness_margin','previous_publication_to_ready','candidates')}, indent=2))


if __name__ == '__main__':
    main()
