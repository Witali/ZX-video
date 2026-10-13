"""Check each unique50-Hz experiment stream in the unchanged assembled Z80."""
import argparse
import gzip
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent; CORE = HERE.parents[1]; sys.path.insert(0, str(CORE))
from music_player import build_disk
from verify_preview import extract_player, native_check, expected_registers
from support import sha, save


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); args.output.mkdir(parents=True, exist_ok=True)
    inputs = [(CORE / 'analysis/o_henry/evidence/compact30', 14)]
    for stage in ('stage1', 'stage2', 'stage3'):
        folder = HERE / 'evidence' / stage; report = json.loads((folder / 'report.json').read_bytes())
        inputs += [(folder / t['name'], t['metadata'].get('register_bytes', 11)) for t in report['trials']]
    checked = []; seen = set()
    for folder, width in inputs:
        raw = gzip.decompress((folder / 'registers.gz').read_bytes()); digest = sha(raw)
        if digest in seen: continue
        seen.add(digest); work = args.output / str(len(checked)); work.mkdir()
        packed = gzip.decompress((folder / ('soundtrack.ay12.gz' if width == 14 else 'soundtrack.ay9.gz')).read_bytes())
        assert expected_registers(packed, 12 if width == 14 else 9) == raw
        disk, metadata = build_disk(raw, title='AY TRANSFER PROOF', loop=True, assembly_dir=work / 'assembly', register_bytes=width)
        result = native_check(extract_player(disk), metadata, raw)
        assert result['complete'] and result['ticks'] == 3000 and result['registers_exact']
        checked.append(dict(input=str(folder.relative_to(CORE)), registers_sha256=digest, width=width,
                            native=result, assembler=metadata['assembly']))
        print(json.dumps(dict(input=checked[-1]['input'], fields=result['ticks'], writes=result['register_writes'])), flush=True)
    save(args.output / 'report.json', dict(complete=True, unique_streams=len(checked), streams=checked,
         original_player_source_sha256_lf=sha((CORE / 'ay-player.asm').read_bytes().replace(b'\r\n', b'\n')),
         native_player_hot_path_changed=False, native_instruction_delta_tstates=0,
         scope='Every50-Hz stream in the independent Z80, two complete loops. No ULA/IRQ/disk/Fuse audio qualification; AYE1 subframe commands have no native player.'))


if __name__ == '__main__': main()
