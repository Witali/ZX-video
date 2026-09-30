"""Verify unchanged Z80 renderer opcodes with learned five-level row tables.

Synthetic dense/sparse frames exercise the dictionaries measured in real RGB
windows. Tables are installed before execution; changing books in a running
player, IRQ service and a full five-level packet consumer are not modeled.
"""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

import numpy as np

from audit_dither_phase import sha
import benchmark_cell_screen as render
import cell_screen_z80 as machine
from build_long_video_trd import base
import probe_five_cell_dictionary as probe


def expected_screen(state, tables):
    bitmap = bytearray(6144)
    # Only the twenty existing active source bands are rendered.
    for y in range(8,88):
        for x in range(32):
            index = state[y*32+x]
            for phase in (0,1):
                at = base.spectrum_bitmap_offset(x,y*2+phase)
                bitmap[at] = tables[phase*256+index]
    return bytes(bitmap),bytes(state[3072:])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,default=Path(__file__).with_name('five_row_dictionary_probe.json'))
    p.add_argument('--cache',type=Path,required=True)
    p.add_argument('--zx0',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a = p.parse_args(); source = json.loads(a.input.read_text())
    if not source['complete']: raise ValueError('incomplete source')
    cache = a.cache/sha(a.zx0.read_bytes()); windows = []
    for window in source['windows']:
        blob = probe.read_control(window['dictionary'],cache)
        n = int.from_bytes(blob[:2],'little'); header = blob[:2+2*n]
        if not 1 <= n <= 256 or sha(header) != window['dictionary_sha256']: raise ValueError('dictionary identity differs')
        tables = header[2:2+n]+bytes(256-n)+header[2+n:]+bytes(256-n)
        baseline = render.Harness(fast_mask_dispatch=True,gray_cells=True)
        candidate = render.Harness(fast_mask_dispatch=True,gray_cells=True)
        if baseline.code != candidate.code: raise AssertionError('renderer code changed')
        candidate.cpu.guarding = False
        for i,v in enumerate(tables): candidate.cpu.write8(machine.TABLE+i,v)
        state = np.zeros(3840,dtype=np.uint8)
        state[256:2816] = np.arange(2560,dtype=np.uint16) % n
        state[3072:] = 71
        rows = []
        for index in range(3):
            mask = bytes([255])*80 if index < 2 else bytes([128])+bytes(79)
            if index == 2: state[256] = (int(state[256])+1) % n
            old = baseline.run(state.tobytes(),mask,index)
            with patch.object(render,'expand_compact_screen',side_effect=lambda s:expected_screen(s,tables)):
                new = candidate.run(state.tobytes(),mask,index)
            if old['tstates'] != new['tstates']: raise AssertionError('rendering cost changed')
            rows.append(dict(index=index,target_bank=new['target_bank'],baseline_tstates=old['tstates'],
                             dictionary_tstates=new['tstates'],delta_tstates=new['tstates']-old['tstates'],
                             output_sha256=new['output_sha256'],stages=new['stages']))
        windows.append(dict(start=window['start'],entries=n,table_allocation_bytes=len(tables),
                            code_sha256=sha(candidate.code),frames=rows))
    keys = ('decoder_tstates','producer_tstates','sectors')
    choices = []
    for w in source['windows']:
        old, new = w['hybrid_cpu'],w['dictionary_cpu']
        use = (w['dictionary']['zx0_bytes'] < w['hybrid']['zx0_bytes']
               and new['decoder_tstates']+new['producer_tstates'] <= old['decoder_tstates']+old['producer_tstates'])
        choices.append(dict(start=w['start'],method='row_dictionary' if use else 'hybrid',
                            zx0_bytes=w['dictionary' if use else 'hybrid']['zx0_bytes'],
                            **{k:(new if use else old)[k] for k in keys}))
    totals = {name:dict(zx0_bytes=sum(w[name]['zx0_bytes'] for w in source['windows']),
                       **{k:sum(w[name+'_cpu'][k] for w in source['windows']) for k in keys})
              for name in ('hybrid','dictionary')}
    totals['selected'] = {k:sum(w[k] for w in choices) for k in ('zx0_bytes',)+keys}
    report = dict(complete=True,release=False,scope=__doc__,windows=windows,
                  offline_selection=choices,totals=totals,
                  selection_scope='bounded recommendation only; both ZX0 bytes and decoder+mocked producer CPU must improve; book installation/dispatch/seed recoding remain unmeasured',
                  input_sha256_lf=sha(a.input.read_bytes().replace(b'\r\n',b'\n')),
                  source_sha256_lf={name:sha((Path(__file__).parent/name).read_bytes().replace(b'\r\n',b'\n'))
                      for name in ('audit_five_row_tables.py','benchmark_cell_screen.py','cell_screen_z80.py','probe_five_cell_dictionary.py')})
    a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(frames=sum(len(w['frames']) for w in windows),deltas=[r['delta_tstates'] for w in windows for r in w['frames']],
                          first_window=windows[0]['frames'])))


if __name__ == '__main__': main()
