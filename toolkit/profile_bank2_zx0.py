"""Compare all frame stages after relocating ZX0, with identical packet bytes.

Elapsed timings include interrupts/contention and physical controller service
in Fuse. The baseline run has a different initial disk/IRQ phase.
"""
import json
from pathlib import Path

from build_fap3_trd import sha
from profile_integrated_timing import analyze


def main():
    root=Path(__file__).parent
    model_path=root/'inline_huffman_patches_cpu.json';model=json.loads(model_path.read_bytes())
    baseline_path=root/'integrated_timing_profile.json';baseline=json.loads(baseline_path.read_bytes())
    result=dict(complete=False,release=False,scope=__doc__,volumes=[],
        baseline_profile_sha256=sha(baseline_path.read_bytes()),cpu_model_sha256=sha(model_path.read_bytes()),
        source_sha256=sha(Path(__file__).read_bytes()),initial_disk_and_irq_phases_not_matched=True)
    for part in (1,2,3):
        report_path=root/'bank2_zx0_evidence'/f'part{part:02}.json'
        meta_path=report_path.with_name(f'part{part:02}.metadata.json')
        r=json.loads(report_path.read_bytes());m=json.loads(meta_path.read_bytes());cpu=model['volumes'][part-1]
        if (r['integrated_bootstrap_metadata_sha256']!=sha(meta_path.read_bytes()) or
            m['raw_sha256']!=cpu['raw_sha256'] or m['frames']!=cpu['checked_frames'] or
            not m['bank2_zx0']['enabled']):raise ValueError('different input')
        v=analyze(r,m,cpu);old=baseline['volumes'][part-1]
        if len(v['frames'])!=len(old['frames']):raise ValueError('baseline frame count differs')
        v.update(report_sha256=sha(report_path.read_bytes()),metadata_sha256=sha(meta_path.read_bytes()),
            baseline_stages=old['stages'],baseline_work_elapsed=old['work_elapsed'],
            stage_elapsed_delta={name:stage['elapsed']['total']-old['stages'][name]['elapsed']['total']
                                 for name,stage in v['stages'].items()})
        result['volumes'].append(v)
        print(json.dumps(dict(part=part,mean_stage_tstates={n:s['elapsed']['mean'] for n,s in v['stages'].items()},
            stage_elapsed_delta=v['stage_elapsed_delta'],mean_work_tstates=v['work_elapsed']['mean'],
            queue_at_packet=v['queue_at_packet'],late_despite_native_ready_1000T_early=v['late_despite_native_ready_1000T_early'])),flush=True)
    result.update(complete=True,frames=sum(len(v['frames']) for v in result['volumes']))
    (root/'bank2_zx0_profile.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
