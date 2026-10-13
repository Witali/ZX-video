"""Require byte-exact legacy output and unchanged three-bit packet tables."""
import argparse
import gzip
import hashlib
from pathlib import Path

import numpy as np

from audit import read, BEEPER
from direct_player import build_disk
from ima3_direct_player import MEASURED_MODEL as THREE_BIT
from probe_feedback_packets import model_table, integral_table
from verify_pcm import save


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repository', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    original = a.repository / 'audiobook-beeper/experiments/ima-direct'
    packed = gzip.decompress(read(original/'soundtrack.ima.gz', a.repository))
    disk, meta = build_disk(packed, a.output/'assembly')
    expected = '9ce319e8b9352a96ed965d87ff3d1d8698df7d788221563758d306d23c053013'
    assert hashlib.sha256(disk).hexdigest() == expected
    assert hashlib.sha256(read(a.repository/'ZX-audiobook-IMA-ADPCM-direct-test.trd', a.repository)).hexdigest() == expected
    three = model_table(THREE_BIT)
    old = integral_table(THREE_BIT.get('pcm_bins',64),2,holds=THREE_BIT['holds'],
        beta=THREE_BIT['beta'],extent=THREE_BIT['extent'],q_clip=tuple(THREE_BIT.get('q_clip',(0,15))))
    assert np.array_equal(three[0],old[0]) and np.array_equal(three[1],old[1])
    save(a.output/'report.json', dict(complete=True, reference_trd_sha256=expected,
        preferred_disk_rebuilt_byte_exact=True, ima3_words_and_successors_unchanged=True,
        native_ordinary_tstates=meta['ordinary_tstates'], native_delta_tstates=0,
        original_full_disk_sha256=hashlib.sha256(read(a.repository/'ZX-audiobook-IMA4-full-disk.trd',a.repository)).hexdigest(),
        scope='Deterministic assembly/table check; authenticated older execution evidence reused for identical disk bytes'))


if __name__ == '__main__':
    main()
