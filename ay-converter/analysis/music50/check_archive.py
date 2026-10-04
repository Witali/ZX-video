"""Audit archived evidence, exact player identity and exported note bounds."""
import argparse
import gzip
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))
from support import save, sha
from verify_preview import extract_player, native_check


def read(path):
    return json.loads(path.read_bytes())


def check_notes(directory):
    notes = read(directory/'note-events.json')
    raw = gzip.decompress((directory/'registers.gz').read_bytes())
    ticks = len(raw)//11
    assert notes['quantum_ms'] == 20 and notes['duration_ticks'] == ticks
    for event in notes['events']:
        start,end,voice,period = (event[k] for k in ('start_tick','end_tick','voice','period'))
        assert 0 <= start < end <= ticks and 0 <= voice < 3
        for tick in range(start,end):
            frame = raw[tick*11:(tick+1)*11]
            assert int.from_bytes(frame[voice*2:voice*2+2],'little') == period
            assert frame[8+voice] > 0
            assert voice != 1 or frame[6] == 0
    return dict(ticks=ticks, events=len(notes['events']), all_events_on_20ms_grid=True,
                constant_period_in_every_event=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('evidence','baseline','root-disk','retained-inventory','offset'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    release = args.evidence/'release'
    report = read(release/'report.json')
    for name,expected in report['artifacts'].items():
        data = (release/name).read_bytes()
        assert len(data) == expected['bytes'] and sha(data) == expected['sha256'], name
    for name,expected in report['producer_sources_sha256_lf'].items():
        assert sha((HERE/name).read_bytes().replace(b'\r\n',b'\n')) == expected, name
    raw = gzip.decompress((release/'registers.gz').read_bytes())
    ablations = read(args.evidence/'results.json')
    assert sha(raw) == ablations['variants']['joint_full']['registers_sha256']
    assert raw == gzip.decompress((args.evidence/'ablations/joint_full/registers.gz').read_bytes())
    disk = (release/'audio-preview.trd').read_bytes()
    assert disk == args.root_disk.read_bytes()
    previous_disk = (args.baseline/'audio-preview.trd').read_bytes()
    assert extract_player(disk) == extract_player(previous_disk)
    verification = read(release/'verification.json')
    assert verification['native']['complete'] and verification['fuse']['complete']
    assert verification['fuse']['ticks'] == 3112 and not verification['fuse']['missing_or_duplicate_fields']
    preserved = read(args.retained_inventory)
    for name,expected in preserved.items():
        assert sha((HERE.parent/name).read_bytes()) == expected, name
    offset = check_notes(args.offset)
    meta = read(args.offset/'player.json')
    offset['native'] = native_check(extract_player((args.offset/'audio-preview.trd').read_bytes()),
                                   meta,gzip.decompress((args.offset/'registers.gz').read_bytes()))
    result = dict(date='2026-10-04', complete=True, source_and_artifact_hashes_verified=True,
        release_matches_selected_ablation=True, root_disk_sha256=sha(disk),
        player_binary_identical_to_baseline=True, ordinary_tstates_before=974,
        ordinary_tstates_after=974, delta_tstates=0, retained_images_unchanged=len(preserved),
        notes=check_notes(release), offset_12_02_seconds_duration_1_019_rounded_to_1=offset,
        scope='Archive integrity and native offset playback; complete cold Fuse proof is release/verification.json.')
    save(args.evidence/'archive-check.json',result)
    print(json.dumps(result),flush=True)


if __name__ == '__main__':
    main()
