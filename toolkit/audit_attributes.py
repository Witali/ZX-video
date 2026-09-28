"""Count attribute changes and actual raw-attribute flags without rendering."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from bulk_frame_stream import read_packet
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header


def audit(states, raw):
    if states.dtype != np.uint8 or states.ndim != 2 or states.shape[1] != 3840:
        raise ValueError('expected compact uint8 frames')
    reader = Reader(raw)
    _, _, count, _, _ = read_header(reader, magic=b'FAP3')
    if count != len(states): raise ValueError('stream/state frame counts differ')
    raw_frames = []
    for frame in range(count):
        _, packet = read_packet(reader, stored_guards=False)
        if packet['flags'] & 64: raw_frames.append(frame)
    reader.end()
    attrs = states[:, 3072:]
    delta = attrs.copy()
    delta[1:] ^= attrs[:-1]
    changes = np.count_nonzero(delta, axis=1)
    active = delta[:, 96:672]
    return dict(frames=count, states_sha256=hashlib.sha256(states.tobytes()).hexdigest(),
        raw_sha256=hashlib.sha256(raw).hexdigest(), flash_cells=int(np.count_nonzero(attrs & 128)),
        bright_cells=int(np.count_nonzero(attrs & 64)),
        colour_bits=7, hardware_attribute_bytes=768, active_attribute_cells=576,
        changed_attributes=int(changes.sum()), unchanged_attribute_frames=int(np.count_nonzero(changes == 0)),
        changed_after_first_frame=int(changes[1:].sum()),
        unchanged_fraction_after_first_frame=float(1-np.count_nonzero(delta[1:])/delta[1:].size),
        active_unchanged_fraction_after_first_frame=float(1-np.count_nonzero(active[1:])/active[1:].size),
        raw_attribute_frames=len(raw_frames), raw_attribute_frame_indices=raw_frames,
        scope='Frame-to-frame attribute statistics and FAP3 flags; no isolated compressed-byte or CPU saving claim.',
        stream_state_equivalence_rechecked=False, release=False)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('states', 'raw', 'output'): p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args()
    with np.load(a.states, allow_pickle=False) as saved: states = saved['states']
    report = audit(states, a.raw.read_bytes())
    a.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k != 'raw_attribute_frame_indices'}))


if __name__ == '__main__': main()
