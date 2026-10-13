"""Record the matching official Fuse release's PSG model and readback behavior."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import numpy as np

CORE = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(CORE))
import music_profile
from support import sha, save, hidden_startupinfo


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--fuse', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    version = subprocess.run([str(args.fuse), '--version'], capture_output=True, text=True,
                             startupinfo=hidden_startupinfo(), timeout=15)
    commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=args.source, capture_output=True, text=True, check=True).stdout.strip()
    assert commit == 'b72c83e85786f5f84375d42c104952cc5453bbaa'
    sound = (args.source / 'sound.c').read_text()
    ports = (args.source / 'peripherals/sound/ay.c').read_text()
    levels = np.array([int(s, 16) for s in re.search(r'levels\[AY_ENV_STEPS\]\s*=\s*\{(.*?)\}', sound, re.S)[1].replace(',', ' ').split()])
    masks = np.array([int(s, 16) for s in re.search(r'mask\[ AY_REGISTERS \]\s*=\s*\{(.*?)\}', ports, re.S)[1].replace(',', ' ').split()])
    assert len(levels) == 16 and masks[1] == 15 and '#define AY_ENV_STEPS\t\t16' in sound
    result = dict(complete=True, date='2026-10-13', version_stdout=version.stdout, version_stderr=version.stderr,
        source_commit=commit, source_tag='fuse-1.9.0', executable_sha256=sha(args.fuse.read_bytes()),
        source_sha256={p: sha((args.source / p).read_bytes()) for p in ('sound.c', 'peripherals/sound/ay.c', 'settings.dat')},
        upstream='https://git.code.sf.net/p/fuse-emulator/fuse',
        model='AY-3-8912 behavior,16-step envelope and measured16-level DAC', envelope_levels=16,
        dac_integer_levels=levels.tolist(), dac_normalized=(levels / levels[-1]).tolist(),
        register_read_write_masks=masks.tolist(), r1_write31_read=31 & int(masks[1]),
        selectable_ym2149_model=False,
        fuse_dac_vs_ayumi_mae_db={chip: float(np.mean(abs(20 * np.log10(music_profile.chip_levels(chip)[1:] / (levels / levels[-1])[1:])))) for chip in ('AY', 'YM')},
        limitations='Official matching release source and installed version/hash, not proof of identical compiler/build provenance. Fuse uses its own DAC/filter/counter implementation; Ayumi AY/YM is not a bit-exact Fuse audio oracle. Readback identifies behavior, not all clones/FPGA silicon.')
    args.output.parent.mkdir(parents=True, exist_ok=True); save(args.output, result)
    print(json.dumps({k: result[k] for k in ('model', 'r1_write31_read', 'fuse_dac_vs_ayumi_mae_db', 'version_stdout', 'version_stderr')}))


if __name__ == '__main__': main()
