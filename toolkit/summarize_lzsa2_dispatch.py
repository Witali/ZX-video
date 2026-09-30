"""Archive the one-candidate LZSA2 dispatch comparison and full Fuse captures."""
import argparse
import gzip
import json
from pathlib import Path
import shutil

import numpy as np
from build_fap3_trd import sha
from capture_five_level_fuse import capture
from disk_progress_z80 import reference_screen
from five_level_dither import expand

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('work','fuse','states','evidence','output','trd'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.evidence.mkdir(parents=True,exist_ok=True)
    old=ROOT/'toolkit/row_lzsa_evidence'
    def archived(name):return json.loads(gzip.decompress((old/(name+'.gz')).read_bytes()))
    load=lambda name:json.loads((a.work/name).read_text())
    baseline=[archived('lzsa2-'+name) for name in ('metadata.json','cpu.json','timing.json')]
    candidate=[load(name) for name in ('metadata.json','cpu.json','timing.json')]
    variants=[]
    for name,(m,c,t) in zip(('baseline','candidate'),(baseline,candidate)):
        assert c['complete'] and t['complete'] and not t['errors']
        assert t['trd_sha256']==m['trd_sha256']
        pubs=t['publications']
        assert len(pubs)==m['frames']==192 and t['ay_ticks']==1152
        sound=t['ay_records_exact'] and not any(t[k] for k in ('audio_underruns','ay_record_field_gaps','ay_record_field_duplicates'))
        assert sound
        variants.append(dict(variant=name,decoder_tstates=c['decoder_tstates'],producer_tstates=c['producer_tstates'],
            total_transport_tstates=c['total_tstates'],code_bytes=c['native']['code_bytes'],max_slice_tstates=c['max_slice_tstates'],
            video_bytes=m['video_bytes'],video_sectors=m['video_sectors'],used_sectors=m['used_sectors'],
            trd_sha256=m['trd_sha256'],frames=len(pubs),ay_ticks=t['ay_ticks'],ay_exact=sound,
            checked_sectors=t['runtime_sectors_checked'],pixel_samples_per_frame=t['pixel_samples_per_frame'],
            fps=(len(pubs)-1)*70908*50/(pubs[-1]['tstate']-pubs[0]['tstate']),
            publication_span_tstates=pubs[-1]['tstate']-pubs[0]['tstate'],
            disk_windows_elapsed_tstates=sum(r['tstates'] for r in t['reads']),
            seek_windows_elapsed_tstates=sum(r['tstates'] for r in t['seek_calls']),
            missed_nominal_deadlines=t['nominal_late_frames'],max_late_fields=t['max_late_fields'],
            late_runs=t['late_runs'],bad_actual_intervals=t['bad_actual_intervals'],
            nominal_pass=bool(not t['nominal_late_frames'] and max(map(abs,t['actual_phase_tstates']))<=64),
            fallback_pass=bool(t['max_late_fields']<=1 and not t['actual_out_over_one_field']
                and not t['bad_actual_intervals'] and all(r['recovered_at'] is not None for r in t['late_runs']))))
    assert baseline[1]['stream_sha256']==candidate[1]['stream_sha256']
    assert baseline[1]['raw_sha256']==candidate[1]['raw_sha256']
    assert baseline[0]['row_dictionary']==candidate[0]['row_dictionary']
    before,after=variants
    assert after['publication_span_tstates']<before['publication_span_tstates']
    assert all(after[k]==before[k] for k in ('video_bytes','video_sectors','used_sectors','producer_tstates'))
    # Calculate dispatch savings from baseline instruction-entry counts.
    labels=baseline[0]['decoder_labels'];counts={}
    for row in baseline[1]['decoder_histogram']:
        counts[row['pc']]=counts.get(row['pc'],0)+row['count']
    many=counts[labels['MoreLiterals']];none=counts[labels['NoLiterals']]
    short=counts[labels['Token']]-many-none
    prediction=20*short+8*many
    assert prediction==before['decoder_tstates']-after['decoder_tstates']==432620
    archives=[]
    def archive(path,name):
        raw=path.read_bytes();blob=gzip.compress(raw,mtime=0)
        dest=a.evidence/(name+'.gz');dest.write_bytes(blob)
        archives.append(dict(file=dest.name,sha256=sha(blob),raw_sha256=sha(raw)))
    with np.load(a.states,allow_pickle=False) as data:states=data['five_states']
    captures=[];work=a.work/'captures';work.mkdir(exist_ok=True)
    for index in (0,1,63,64,128,191):
        screen,row=capture(a.fuse,a.work/'candidate.trd',candidate[0],index,work)
        expected=reference_screen(b''.join(expand(states[index].tobytes())),index,192)
        assert screen==expected,('full screen',index)
        (work/f'frame-{index}.scr').write_bytes(screen)
        captures.append(dict(row,compared_bytes=len(screen),mismatches=0))
        for ext in ('scr','trace.txt','debugger.txt'):archive(work/f'frame-{index}.{ext}',f'frame-{index}.{ext}')
    for name in ('metadata.json','cpu.json','native.json','build.json','timing.json','timing.trace.txt','timing.debugger.txt','edges/edges.json'):
        archive(a.work/name,name.replace('/','-'))
    # Retain the rejected stale temporary-fixture build as a separate record.
    wrong=a.work/'wrong-fixture-build.json.gz'
    if wrong.exists():
        blob=wrong.read_bytes();(a.evidence/wrong.name).write_bytes(blob)
        archives.append(dict(file=wrong.name,sha256=sha(blob),raw_sha256=sha(gzip.decompress(blob))))
    shutil.copyfile(a.work/'candidate.trd',a.trd)
    report=dict(complete=True,release=False,baseline_commit='afc18fc',variants=variants,captures=captures,
        predicted_and_measured_saving_tstates=prediction,
        token_counts=dict(no_literals=none,one_or_two_literals=short,extended_literals=many),
        unchanged_stream_sha256=candidate[1]['stream_sha256'],selected_image=a.trd.name,
        selected_trd_sha256=sha(a.trd.read_bytes()),archives=archives,
        native_verification=load('native.json')['variants'],
        decision='Adopt flag dispatch: identical stream, lower CPU and shorter full Fuse publication span. Both release timing gates still fail.',
        source_sha256_lf={n:sha((ROOT/'toolkit'/n).read_text().encode()) for n in
            ('resumable_lzsa2.py','lzsa2_test_cpu.py','benchmark_row_lzsa.py','build_row_lzsa.py','verify_lzsa2_dispatch.py','summarize_lzsa2_dispatch.py')})
    # Detailed per-slice native results are already archived separately.
    report['native_verification']={k:{f:v[f] for f in ('total_tstates','injected_interrupts')} for k,v in report['native_verification'].items()}
    a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(complete=True,saving_tstates=prediction,fps=after['fps'],captures=len(captures),release=False)))


if __name__=='__main__':main()
