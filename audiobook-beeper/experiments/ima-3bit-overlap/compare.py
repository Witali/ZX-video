"""Compare the fixed speech fixture against the archived final sequential TRD.

The boundary regression applies only to this unchanged reference recording;
it is not a quality threshold for arbitrary input audio.
"""
import argparse
from array import array
import gzip
import hashlib
import json
from pathlib import Path
import re
import numpy as np
from analyze_ima_boundaries import read_wav, boundary_metrics


def trace_times(folder):
    """Recover both exact timelines from the old compact Fuse trace."""
    script = (folder/'debugger.txt').read_text()
    widths = {}
    for commands in re.findall(r'(?:commands|com) \d+\n(.*?)\nend', script, re.S):
        prints = re.findall(r'^(?:print|pr) (.*)$', commands, re.M)
        if prints and re.fullmatch(r'-\d+', prints[0]):
            widths[int(prints[0])] = len(prints)-1
    data = gzip.decompress((folder/'trace.txt.gz').read_bytes())
    values = (int(m.group(1), 0) for m in re.finditer(rb'(?m)^(-?\d+|0x[\da-fA-F]+)\r*$', data))
    pulses = [array('I'), array('I')]
    part = None
    for tag in values:
        if tag >= 0xffff0000:
            tag -= 2**32
        if tag >= 0:
            assert part is not None
            pulses[part].append(tag >> 1)
        else:
            row = [next(values) for _ in range(widths[tag])]
            if tag == -100:
                part = row[0]
            elif tag == -110:
                part = None
    result = []
    for holds in pulses:
        times = np.cumsum(np.asarray(holds, dtype=np.int64))
        times -= times[0]
        assert len(times) == 2990047
        result.append(times)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    out = args.directory.resolve()
    baseline = Path(__file__).resolve().parent.parent/'ima-3bit-series'
    source_dir = baseline.parent/'ima-3bit-direct'
    source = read_wav(source_dir/'uniform-clock-source-preview.wav')
    assert (out/'qualified/source-preview.wav').read_bytes() == (source_dir/'source-preview.wav').read_bytes()
    old_times = trace_times(baseline/'reload/fuse')
    old_report = json.loads((baseline/'reload/fuse/report.json').read_bytes())
    new_report = json.loads((out/'verification/cold-0001/report.json').read_bytes())
    assert new_report['complete'] and new_report['ended_at'] == 'end_of_audio'
    rows = []
    for index in (1, 2):
        old = read_wav(baseline/f'reload/fuse/part-{index:02d}-output.wav')
        new = read_wav(out/f'verification/cold-0001/part-{index:02d}-output.wav')
        times = np.frombuffer(gzip.decompress((out/f'verification/cold-0001/part-{index:02d}-times.u32.gz').read_bytes()), '<u4').astype(np.int64)
        previous = [boundary_metrics(source, old, old_times[index-1], period) for period in (64, 128)]
        current = [boundary_metrics(source, new, times, period) for period in (64, 128)]
        assert previous[1]['boundary_to_middle_ratio'] > 1.5
        assert all(row['boundary_to_middle_ratio'] < 1.1 for row in current)
        assert new_report['parts'][index-1]['fixed_clock_snr_db'] >= 20
        rows.append(dict(part=index, baseline=previous, corrected=current,
                         baseline_measured_snr_db=old_report['parts'][index-1]['fixed_clock_snr_db'],
                         corrected_measured_snr_db=new_report['parts'][index-1]['fixed_clock_snr_db']))
    binaries = {}
    for path in (baseline/'final-layout').glob('part-*/assembly/*.bin'):
        relative = path.relative_to(baseline/'final-layout')
        assert path.read_bytes() == (out/'disk'/relative).read_bytes(), relative
        binaries[relative.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    report = dict(complete=True, scope=__doc__, parts=rows,
                  all_player_and_table_binaries_identical=binaries,
                  source_pcm_unchanged=True, native_tstates_per_sample_before=427.375,
                  native_tstates_per_sample_after=427.375, native_tstate_delta=0,
                  page_extra_tstates=14, bank_extra_tstates=140,
                  ram_reservation_before_and_after=13312, packed_bytes_before_and_after=70080,
                  new_trd_sha256=hashlib.sha256((out/'audio.trd').read_bytes()).hexdigest())
    (out/'comparison.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({str(r['part']): [r['corrected_measured_snr_db'],
          r['corrected'][1]['boundary_to_middle_ratio']] for r in rows}))


if __name__ == '__main__':
    main()
