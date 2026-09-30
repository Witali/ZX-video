"""Archive the exact cell-codebook feasibility probe without claiming playback."""
import argparse,gzip,json
from pathlib import Path
from build_fap3_trd import sha
from build_five_level_test_trd import save

ROOT=Path(__file__).resolve().parent


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('work','output','evidence'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();probe=json.loads((a.work/'probe.json').read_bytes());edges=json.loads((a.work/'tests.json').read_bytes())
    assert probe['complete'] and edges['complete'] and probe['full_native_screens_host_exact']
    assert edges['full_host_screens_exact'] and edges['every_dictionary_index_used']
    for name,digest in probe['source_sha256_lf'].items():
        assert sha((ROOT/name).read_bytes().replace(b'\r\n',b'\n'))==digest,name
    report={k:v for k,v in probe.items() if k not in ('variants','frames','screen_sha256','dictionary_row_keys')}
    retained=json.loads((ROOT/'borrowed_literals_profile.json').read_bytes())
    assert sha((ROOT.parent/'ZX-video-five-level-lzsa2-test.trd').read_bytes())==retained['trd_sha256']
    report.update(date='2026-09-30',variants={},coverage_percent=100*probe['book_cells']/probe['changed_cells'],
        host_boundary_cases=edges['cases'],maximum_synthetic_packet_bytes=edges['maximum_packet_bytes'],
        maximum_window_packet_bytes=max(r['packet_bytes'] for r in probe['frames']),
        root_trd_unchanged=True,root_trd_sha256=retained['trd_sha256'],
        current_measured_fps=retained['fps'],goal_achieved=False,
        decision='Promote this exact separate inner-format candidate to a native-renderer prototype. Most compressed-size saving comes from direct cell deltas; the dictionary substantially reduces decoded volume and LZSA2 CPU beyond that control. No production/player/disk adoption yet.',
        next='Implement and verify native cell output including both masks, dictionary/literal modes, all attributes, source cursors, stack and bank safety. Keep brightness-before-dither semantics and account for dictionary RAM/loading, packet transport and real schedule before integration.',evidence=[])
    names=['probe.json','tests.json','initial-screens.bin']
    for name,source in probe['variants'].items():
        cpu=json.loads((a.work/(name+'-cpu.json')).read_bytes())
        independent=json.loads((a.work/(name+'-verification.json')).read_bytes())
        assert cpu['complete'] and independent['complete'] and cpu['all_instruction_timings_verified']
        assert cpu['sectors_exact_once']
        assert cpu['raw_sha256']==source['raw_sha256']==independent['raw_sha256']
        assert cpu['stream_sha256']==source['stream_sha256']==independent['stream_sha256']
        assert cpu['decoder_tstates']==independent['decoder_tstates']
        assert cpu['sector_reads']==source['sectors'] and cpu['stream_bytes']==source['compressed_bytes']
        assert sha((a.work/(name+'.raw')).read_bytes())==source['raw_sha256']
        assert sha((a.work/(name+'.stream')).read_bytes())==source['stream_sha256']
        report['variants'][name]={k:v for k,v in source.items() if k!='blocks'}
        report['variants'][name].update(block_count=len(cpu['blocks']),injected_interrupts=independent['injected_interrupts'],
            **{k:cpu[k] for k in ('decoder_tstates','producer_tstates','total_tstates','max_slice_tstates','carry_copy_bytes')})
        names += [name+suffix for suffix in ('.raw','.stream','-cpu.json','-verification.json')]
    base=report['variants']['current'];control=report['variants']['direct_rows'];new=report['variants']['codebook']
    report['deltas']=dict(bytes_vs_current=new['compressed_bytes']-base['compressed_bytes'],
        bytes_vs_control=new['compressed_bytes']-control['compressed_bytes'],
        byte_saving_percent=100*(base['compressed_bytes']-new['compressed_bytes'])/base['compressed_bytes'],
        decoder_vs_current=new['decoder_tstates']-base['decoder_tstates'],
        decoder_saving_percent=100*(base['decoder_tstates']-new['decoder_tstates'])/base['decoder_tstates'],
        transport_component_vs_current=new['total_tstates']-base['total_tstates'])
    a.evidence.mkdir(parents=True,exist_ok=True)
    for name in names:
        data=(a.work/name).read_bytes();packed=gzip.compress(data,mtime=0)
        (a.evidence/(name+'.gz')).write_bytes(packed)
        report['evidence'].append(dict(file=name+'.gz',sha256=sha(packed),raw_sha256=sha(data)))
    report['source_sha256_lf'].update({name:sha((ROOT/name).read_bytes().replace(b'\r\n',b'\n')) for name in (
        'test_cell_codebook.py','summarize_cell_codebook.py','benchmark_row_lzsa.py','verify_lzsa2_search.py',
        'verify_lzsa2_dispatch.py','resumable_lzsa2.py')})
    save(a.output,report)
    print(json.dumps({k:report[k] for k in ('coverage_percent','host_boundary_cases','maximum_window_packet_bytes','deltas','root_trd_unchanged')}))


if __name__=='__main__':main()
