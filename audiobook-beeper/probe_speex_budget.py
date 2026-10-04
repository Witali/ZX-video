"""Measure one favorable exact Speex multiplication strategy on native Z80.

This is neither a full Speex decoder nor a universal lower bound for all
possible algorithms. Prebuilt coefficient tables are deliberately free here;
even this kernel exceeds the startup budget for the ten-tap synthesis alone.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np
from z80 import Z80Machine

from build_lpc_disk import assemble
from verify_pcm import save


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--samples', type=int, default=186880)
    args = p.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    shutil.copy2(Path(__file__).with_name('probe-speex-multiply.asm'), out/'probe.asm')
    labels = assemble(out, 'probe')
    blob = (out/'probe.bin').read_bytes()
    machine = Z80Machine()
    machine.memory[:] = b'\xa5'*65536
    machine.set_memory_block(0x8000, blob)
    machine.set_breakpoint(labels['stop'])
    # Exhaust every input value for representative positive, negative and
    # extreme coefficients; also exhaust every coefficient on boundary inputs.
    coefficients = (-32768, -16385, -4096, -257, -1, 0, 1, 255, 4096, 16383, 32767)
    boundaries = np.array([0, 1, 255, 256, 257, 32767, 32768, 33023, 65280, 65535])
    cases = 0
    for coefficient in range(-32768, 32768):
        values = np.arange(65536) if coefficient in coefficients else boundaries
        low = np.arange(256, dtype=np.int64)*coefficient
        high = np.arange(256, dtype=np.int64)
        high[128:] -= 256
        high *= coefficient*256
        table = b''.join(((low >> shift)&255).astype('u1').tobytes() for shift in (0, 8, 16, 24))
        table += b''.join(((high >> shift)&255).astype('u1').tobytes() for shift in (8, 16, 24))
        machine.set_memory_block(0x9000, table)
        for value in values:
            value = int(value)
            machine.h, machine.l, machine.a = 0x90, value&255, value>>8
            machine.sp, machine.pc, machine.ticks_to_stop = 0x8800, labels['start'], 1000
            while machine.pc != labels['stop']:
                assert not machine.run() & machine._TICKS_LIMIT_HIT
            assert 1000-machine.ticks_to_stop == 128
            actual = (machine.b<<24)|(machine.d<<16)|(machine.e<<8)|machine.c
            expected = (coefficient*(value if value<32768 else value-65536))&0xffffffff
            assert actual == expected, (coefficient, value, actual, expected)
            assert machine.sp == 0x8800
            cases += 1
    assert bytes(machine.memory[0x8000:0x8000+len(blob)]) == blob
    core = 111
    products = args.samples*10
    clock = 3546900
    budget = 39.903992
    report = dict(scope=__doc__, complete=True, samples=args.samples,
        input_pairs_verified=cases, every_coefficient_tested=True,
        exhaustive_input_coefficients=list(coefficients), boundary_inputs=boundaries.tolist(),
        exact_signed_32bit_products=True, instruction_tstates=core, caller_tstates=17,
        every_measured_call_tstates=128, table_bytes_per_coefficient=1792,
        ten_coefficient_table_bytes=17920,
        synthesis_products=products, synthesis_products_only_tstates=products*core,
        synthesis_products_only_cpu_seconds=products*core/clock,
        synthesis_products_with_calls_cpu_seconds=products*(core+17)/clock,
        startup_budget_seconds=budget, total_budget_tstates_per_output_sample=budget*clock/args.samples,
        budget_tstates_per_product_if_all_other_work_free=budget*clock/products,
        excluded=['table generation and refresh', 'argument setup', '32-bit accumulation',
                  'LSP decoding and interpolation', 'LSP to LPC', 'pitch and excitation decoding',
                  'saturation and output handling', 'PCM to IMA', 'disk, ROM, ULA and paging'],
        full_speex_decoder_tested=False, universal_impossibility_claim=False,
        pdm_player_changed=False, ordinary_pdm_tstates_per_sample=423, pdm_hot_path_delta_tstates=0,
        binary_sha256=hashlib.sha256(blob).hexdigest())
    save(out/'report.json', report)
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
