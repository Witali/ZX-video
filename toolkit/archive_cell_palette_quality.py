"""Archive a completed bounded palette experiment without its codec cache."""
import argparse
import gzip
import json
from pathlib import Path

from prepare_cell_codebook_movie import file_sha, sha


def aggregate(report, name):
    windows = report['windows']
    total = sum(w['frames'] for w in windows)
    metrics = {key: sum(w['metrics'][name][key]*w['frames'] for w in windows)/total
               for key in windows[0]['metrics'][name]}
    if name != 'four':
        metrics['lzsa2_bytes'] = sum(w['compression'][name]['lzsa2_bytes'] for w in windows)
        metrics['changed_cells'] = sum(w['compression'][name]['changed_cells'] for w in windows)
        metrics['changed_attributes'] = sum(w['compression'][name]['changed_attributes'] for w in windows)
    return metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--tests', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--summary', type=Path, required=True)
    args = parser.parse_args()
    report = json.loads((args.work/'report.json').read_bytes())
    native = json.loads((args.work/'native.json').read_bytes())
    assert report['complete'] and native['complete']
    assert native['quality_report_sha256'] == file_sha(args.work/'report.json')
    assert args.tests.read_text().strip().endswith('OK')
    for row in report['artifacts']:
        assert file_sha(args.work/row['file']) == row['sha256']
    for name, wanted in report['source_sha256_lf'].items():
        assert sha(Path(__file__).with_name(name).read_bytes().replace(b'\r\n', b'\n')) == wanted
    args.output.mkdir(parents=True, exist_ok=True)
    files = []
    paths = [(args.work/row['file'], row['file'].replace('/', '-')) for row in report['artifacts']]
    paths += [(args.work/name, name) for name in ('report.json', 'native.json')]
    paths += [(args.tests, 'tests.txt')]
    sources = ('cell_palette_quality.py', 'probe_cell_palette_quality.py',
               'profile_cell_palette_quality.py', 'test_cell_palette_quality.py',
               'archive_cell_palette_quality.py')
    paths += [(Path(__file__).with_name(name), 'source-'+name) for name in sources]
    for path, name in paths:
        data = path.read_bytes()
        if path.suffix == '.py': data = data.replace(b'\r\n', b'\n')
        packed = data if path.suffix in ('.png', '.npz') else gzip.compress(data, mtime=0)
        archived = name if path.suffix in ('.png', '.npz') else name+'.gz'
        destination = args.output/archived
        destination.write_bytes(packed)
        assert destination.read_bytes() == packed
        files.append(dict(file=archived, bytes=len(packed), sha256=sha(packed),
                          original_bytes=len(data), original_sha256=sha(data)))
    totals = {name: aggregate(report, name) for name in ('four', 'baseline', 'candidate', 'endpoints', 'contrast')}
    cpu = {}
    for name in ('baseline', 'endpoints'):
        frames = [f for r in native['results'] if r['variant']==name for f in r['frames']]
        cpu[name] = dict(frames=len(frames), mean_tstates=sum(f['tstates'] for f in frames)/len(frames),
                         maximum_tstates=max(f['tstates'] for f in frames))
    result = dict(date='2026-10-01', complete=True, release=False, baseline_commit=report['baseline_commit'],
        windows=[dict(start=w['start'], frames=w['frames']) for w in report['windows']],
        frames=report['frames'], metrics=totals, native_output_only=cpu,
        native_instruction_delta_tstates=0, native_loader_tstates=54028,
        decisions=dict(palette_repair='Defer default adoption: increased size and dark-scene boundary error.',
                       endpoint_bias='Keep opt-in research only: larger solid extremes trade accuracy, size and output work.',
                       combined='Defer: highest stream cost; full-movie native row capacity and timing unverified.'),
        limitations=report['metric_limits']+'; window sizes are not full-volume capacity; output CPU excludes LZSA2 and I/O',
        artifacts=files)
    args.summary.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(files=len(files), archived_bytes=sum(f['bytes'] for f in files), summary=str(args.summary))))


if __name__ == '__main__':
    main()
