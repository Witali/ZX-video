"""Archive native cell-output evidence, keeping integration costs explicit."""
import argparse,gzip,json
from collections import Counter
from pathlib import Path
from build_fap3_trd import sha
from build_five_level_test_trd import save

ROOT=Path(__file__).resolve().parent


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('input','output','evidence'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();raw=a.input.read_bytes();native=json.loads(raw)
    host=json.loads((ROOT/'cell_codebook_profile.json').read_bytes());old=json.loads((ROOT/'borrowed_literals_profile.json').read_bytes())
    assert native['complete'] and native['source_raw_sha256']==host['variants']['codebook']['raw_sha256']
    assert native['states_sha256']==host['states_sha256'] and len(native['edges'])==22
    for name,digest in native['source_sha256_lf'].items():
        assert sha((ROOT/name).read_bytes().replace(b'\r\n',b'\n'))==digest,name
    assert sha((ROOT.parent/'ZX-video-five-level-lzsa2-test.trd').read_bytes())==old['trd_sha256']
    report=dict(complete=True,release=False,date='2026-09-30',baseline_commit='d1f32d3',
        scope='64 saved frames (128..191), native CB41 draw only with caller-supplied packets/mapped target. Exact unchanged video and LZSA2 bytes.',
        states_sha256=native['states_sha256'],variants={},baseline_frame_tstates=native['baseline_frame_tstates'],
        baseline_scope='Existing frame reconstruction/metadata/output on these frames in the full borrowed-literal fixture. Ownership and paging differ from the new standalone draw ABI; not an integrated delivery comparison.',
        edges=len(native['edges']),maximum_synthetic_frame_tstates=max(r['frames'][0]['tstates'] for r in native['edges']),
        edge_interrupts=sum(r['injected_interrupts'] for r in native['edges']),
        root_trd_unchanged=True,root_trd_sha256=old['trd_sha256'],current_measured_fps=old['fps'],
        actual_playback_measured=False,goal_achieved=False,
        excluded_costs=['Packet acquisition/copying','Caller paging and screen publication','Real AY/IRQ and ULA contention',
            'TR-DOS ROM and physical latency','Cold-boot/start-state integration'],
        decision='Retain verified native CB41 output and proceed to one integrated timing-test disk. Both dictionary and row-literal paths are exact; the book renderer is slower than literal-only but its previously measured decoder savings outweigh that component difference.',
        next='Integrate the verified CB41 path with packet delivery, existing 50-Hz AY and exact six-field publication, with a complete RAM map and independent cold boot. Run the selected window through actual EOF/AY/pixel/deadline checks before expanding to the full edited movie.')
    for name,v in native['variants'].items():
        assert v['complete'] and v['all_screens_exact'] and v['all_instruction_timings_exact']
        assert len(v['frames'])==64
        stages=Counter()
        for f in v['frames']:stages.update(f['stages']);assert f['independent']['tstates']==f['tstates']
        report['variants'][name]=dict(frame_tstates=v['frame_tstates'],mean_frame_tstates=v['frame_tstates']/64,
            min_frame_tstates=min(f['tstates'] for f in v['frames']),max_frame_tstates=max(f['tstates'] for f in v['frames']),
            delta_vs_old_frame_component=v['frame_tstates']-native['baseline_frame_tstates'],stages=dict(stages),
            code_bytes=v['native']['code_bytes'],state_bytes=v['native']['state_bytes'],
            book_loader_tstates=v['loader']['tstates'] if v['loader'] else 0,
            injected_interrupts=v['injected_interrupts'],
            hypothetical_component_sum=v['frame_tstates']+host['variants'][name]['total_tstates'])
    candidate=report['variants']['codebook'];control=report['variants']['direct_rows']
    report['frame_component_saving_percent']=100*(native['baseline_frame_tstates']-candidate['frame_tstates'])/native['baseline_frame_tstates']
    report['dictionary_vs_literal_render_delta']=candidate['frame_tstates']-control['frame_tstates']
    report['dictionary_vs_literal_combined_delta']=candidate['hypothetical_component_sum']-control['hypothetical_component_sum']
    report['component_sum_caveat']='Sums use separate fixed-demand transport and supplied-packet render tests. They exclude the costs above and are not measured frame-delivery time or a cadence guarantee.'
    a.evidence.mkdir(parents=True,exist_ok=True);packed=gzip.compress(raw,mtime=0)
    (a.evidence/'native.json.gz').write_bytes(packed)
    report['evidence']=dict(file='native.json.gz',sha256=sha(packed),raw_sha256=sha(raw))
    report['source_sha256_lf']=dict(native['source_sha256_lf'])
    report['source_sha256_lf']['summarize_cell_codebook_native.py']=sha(Path(__file__).read_bytes().replace(b'\r\n',b'\n'))
    save(a.output,report)
    print(json.dumps({k:report[k] for k in ('baseline_frame_tstates','frame_component_saving_percent',
        'dictionary_vs_literal_render_delta','dictionary_vs_literal_combined_delta','edges','root_trd_unchanged')}))


if __name__=='__main__':main()
