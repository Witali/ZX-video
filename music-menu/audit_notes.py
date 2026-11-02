"""Audit the actual register frames around repeats, noise slots and AY ENV."""
import argparse
import json
from pathlib import Path

from arrangement import timeline
from build import HERE, ROOT, CONTROL_HZ, REPEAT_GAP_FIELDS, control_frames, sha
from verify import unpack


def audit(output):
    output = Path(output)
    baseline = json.loads((HERE/'reports/click-fix/final/build.json').read_text())
    release = json.loads((output/'build.json').read_text())
    assert sha((output/'ZX-Music-Menu.trd').read_bytes())==release['trd_sha256']
    report = dict(baseline_trd_sha256=baseline['trd_sha256'],trd_sha256=release['trd_sha256'],songs=[],
                  scope='Register-frame/note-envelope audit; actual Fuse traces and recordings are separate')
    for name in ('lumiere','alicia'):
        score = json.loads((HERE/'scores'/f'{name}.json').read_text())
        before,before_meta = control_frames(score,articulation=False,percussion=False)
        after,meta = control_frames(score)
        saved = next(s for s in release['songs'] if s['song']==name)
        assert after==(output/f'{name}.rows').read_bytes()
        assert meta['frames_sha256']==saved['frames_sha256']
        original = next(s for s in baseline['songs'] if s['song']==name)
        assert before_meta['frames_sha256']==original['frames_sha256']
        old,new = unpack(before),unpack(after)
        assert len(old)==len(new)==meta['ticks']
        assert all(all(a[r]==b[r] for r in (4,5,10,11,12,13)) for a,b in zip(old,new))
        noise_fields = [t for t,row in enumerate(new) if not row[7]&16]
        assert len(noise_fields)==meta['noise_fields']
        assert all(old[t][9]==0 and new[t][7]&2 for t in noise_fields)
        boundaries = []
        notes = timeline(score)[0][0]
        for left,right in zip(notes,notes[1:]):
            start = round(right[0]*CONTROL_HZ)
            old_end = round((left[0]+left[1])*CONTROL_HZ)
            if left[2]!=right[2] or not 0<=start-old_end<REPEAT_GAP_FIELDS:
                continue
            assert all(row[8]==0 for row in new[start-REPEAT_GAP_FIELDS:start])
            assert new[start][8]>0
            boundaries.append(dict(seconds=right[0],pitch=right[2],onset_field=start,
                silence_fields=REPEAT_GAP_FIELDS,
                before_levels=[r[8] for r in old[start-6:start+6]],
                after_levels=[r[8] for r in new[start-6:start+6]]))
        assert len(boundaries)==len(meta['repeated_note_articulation'])
        report['songs'].append(dict(song=name,ticks=len(new),
            score_onset_grid_unchanged=True,source_note_counts=meta['source_notes'],
            repeated_boundaries=len(boundaries),boundaries=boundaries,
            minimum_repeat_gap_seconds=REPEAT_GAP_FIELDS/CONTROL_HZ,
            hardware_bass_envelope_frames_unchanged=True,
            hardware_envelope_restarts=meta['envelope_restarts'],
            zero_hardware_envelope_period_fields=sum(r[11]+256*r[12]==0 for r in new),
            noise_hits=meta['noise_fields'],noise_channel=meta['percussion_channel'],
            max_percussion_advance_seconds=meta['max_percussion_advance_seconds'],
            all_noise_uses_literal_accompaniment_rests=True))
    output.mkdir(parents=True,exist_ok=True)
    (output/'note-envelope-audit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps([dict(song=s['song'],repeats=s['repeated_boundaries'],noise_hits=s['noise_hits'],
        gap_seconds=s['minimum_repeat_gap_seconds'],hardware_bass_unchanged=s['hardware_bass_envelope_frames_unchanged'])
        for s in report['songs']],indent=2))
    return report


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'build/music-menu-autoplay')
    audit(parser.parse_args().output)
