"""Exhaust every PCM8/feedback cell at the actual static bank-decision sample."""
import argparse
import ast
import gzip
import hashlib
import json
from pathlib import Path

from table_pdm_uniform16_paged import HERE, model, run, save, sha


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--component',type=Path,default=HERE/'evidence/table-pdm-uniform16-paged-component')
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    component=args.component.resolve();out=args.output.resolve()
    if out.exists() and any(out.iterdir()):raise ValueError('Use fresh output')
    out.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((component/'manifest.json').read_text())
    for name,item in manifest['artifact_files'].items():
        data=(component/name).read_bytes()
        assert len(data)==item['bytes'] and sha(data)==item['sha256']
    labels=next(ast.literal_eval(line) for line in (component/'assembler.log').read_text().splitlines()
                if line.startswith('{'))
    blob=(component/'kernel.bin').read_bytes();lookup=(component/'lookup.bin').read_bytes()
    mapping=(component/'pcm-high.bin').read_bytes();words,nxt,states,_,_=model()
    results=[];cells=set()
    for state in states:
        for value in range(256):
            source=bytes([value,(value*73+17)&255,(value*29+state)&255,
                          (value*41+3)&255,(value*7+state)&255,0xA5])
            result=run(blob,labels,lookup,mapping,words,nxt,states,source,
                       initial_state=state,initial_address=0xFFFE)
            assert result['page_events'][0]['after_speaker_outputs']==15
            results.append(dict(pcm8=value,feedback=state,**result))
            cells.add((value>>2,state))
    assert len(cells)==64*len(states)
    save(out/'all-cells.json',results)
    report=dict(complete=True,date='2026-10-20',native_cases=len(results),
        effective_model_cells_at_actual_bank_decision=len(cells),full_model_cells=64*len(states),
        actual_boundary_sample_is_initial_test_cell=True,source_cursor_start=0xFFFE,
        all_page_events_after_speaker_outputs=15,source_banks_per_case=2,
        source_samples_per_case=5,outputs=sum(r['outputs'] for r in results),
        every_speaker_hold_tstates=28,source_sample_tstates=448,
        full_bits_state_source_order_and_memory_checks=True,
        component_manifest_sha256=sha((component/'manifest.json').read_bytes()),
        scope='Supplement to the static two-bank component; all384effective PCM/state cells directly occupy the bank-decision sample. Same limitations as that component.')
    save(out/'report.json',report)
    (out/'producer.py.gz').write_bytes(gzip.compress(Path(__file__).read_bytes(),mtime=0))
    for name in ('table_pdm_uniform16_paged.py','table_pdm_uniform16.py','sdm16_uniform7.py'):
        (out/(name+'.gz')).write_bytes(gzip.compress((HERE/name).read_bytes(),mtime=0))
    artifacts={p.name:dict(bytes=p.stat().st_size,sha256=sha(p.read_bytes()))
               for p in sorted(out.iterdir()) if p.is_file()}
    save(out/'manifest.json',dict(complete=True,artifact_files=artifacts))
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
