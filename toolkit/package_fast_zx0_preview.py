"""Copy fully measured Fast TRDs into the root as an explicitly named preview.

Require complete independent playback and exact sound/data. The video timing
gates may fail; the preview never claims release status. Git LFS is configured
by .gitattributes before these images are staged.
"""
import argparse
import json
from pathlib import Path

from build_fap3_trd import sha
from summarize_fast_zx0_player import summarize

ROOT = Path(__file__).resolve().parent.parent


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--directory', type=Path, required=True)
    args = p.parse_args(); report = json.loads(json.dumps(summarize()))
    summary = ROOT/'toolkit/fast_zx0_player_summary.json'
    if (report != json.loads(summary.read_bytes()) or not report['complete']
            or not report['totals']['ay_50hz_met'] or not report['all_video_and_audio_bytes_unchanged']):
        raise ValueError('complete saved data/audio verification required')
    entries = []
    for row in report['volumes']:
        part = row['part']; stem = args.directory/f'ZX-video-huffman-preview_part{part:02}'
        data = stem.with_suffix('.trd').read_bytes()
        if sha(data) != row['fast']['trd_sha256']: raise ValueError('unverified image')
        target = ROOT/f'ZX-video-fast-preview_part{part:02}.trd'
        if target.exists() and target.read_bytes() != data:
            raise ValueError(('refuse to overwrite different preview', str(target)))
        entries.append((target, data, dict(part=part, file=target.name, bytes=len(data), sha256=sha(data))))
    for target, data, _ in entries: target.write_bytes(data)
    manifest = dict(complete=True, release=False, variant='adapted Fast ZX0',
        summary_sha256=sha(summary.read_bytes()), disks=[v for _, _, v in entries],
        timing_gates={k: report['totals'][k] for k in ('nominal_schedule_met', 'fallback_met', 'ay_50hz_met')})
    (ROOT/'toolkit/fast_zx0_preview.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(manifest), flush=True)


if __name__ == '__main__': main()
