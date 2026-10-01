"""Archive generic CLI profile checks separately from sustained movie delivery."""
import argparse
import gzip
import json
from pathlib import Path

from build_fap3_trd import sha
from convert_video import write_json


def read(path):return json.loads(path.read_bytes())


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('root','output','evidence'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();tmp=a.root/'.tmp';a.evidence.mkdir(parents=True,exist_ok=True)
    artifacts=[];checks=[]
    def archive(path,name):
        raw=path.read_bytes();packed=raw if path.suffix=='.trd' else gzip.compress(raw,mtime=0)
        filename=name+('' if path.suffix=='.trd' else '.gz')
        (a.evidence/filename).write_bytes(packed)
        artifacts.append(dict(file=filename,raw_bytes=len(raw),raw_sha256=sha(raw),
            archive_bytes=len(packed),archive_sha256=sha(packed)))
    baseline=read(tmp/'direct-lzsa2-header-part04/part04.json')
    decoder={r['address']:r['code_hex'] for r in baseline['lzsa2']['regions'] if r['address'] in (0x7c00,0x8d74)}
    assert len(decoder)==2
    for suite,reportfile in (('generic-guarded-colour-fixed','generic-guarded-colour-fixed-report.json'),
                            ('generic-guarded-edge-cases','generic-guarded-edge-cases-report.json')):
        report=read(tmp/reportfile);assert report['complete']
        archive(tmp/reportfile,reportfile)
        for case in report['cases']:
            name=case['name'];folder=tmp/suite/(name+'-out');conversion=read(folder/'conversion.json')
            assert conversion['profile']=='cb46-guarded-v1' and conversion['wire']=='CB46'
            assert conversion['complete'] and conversion['timing_verified']
            timing=read(folder/'timing.json');assert timing['all_nominal_deadlines_met']
            for v in conversion['volumes']:
                m=read(folder/v['metadata']);work=folder/'work'/Path(v['file']).stem
                selection=read(work/'compression-selection.json')
                cpu=read(work/'cpu.json');fuse=read(work/'timing.json');screens=read(work/'screens.json')
                assert sha((folder/v['file']).read_bytes())==m['trd_sha256']==v['sha256']
                assert sha((work/'codebook.raw').read_bytes())==selection['raw_sha256']==m['cell_codebook']['raw_sha256']
                assert sha((work/'codebook.stream').read_bytes())==selection['stream_sha256']
                assert sha((work/'timing.trace.txt').read_bytes())==fuse['trace_sha256']
                assert fuse['trd_sha256']==screens['trd_sha256']==m['trd_sha256']
                assert sha((folder/v['metadata']).read_bytes())==fuse['integrated_bootstrap_metadata_sha256']
                assert cpu['complete'] and cpu['all_native_screens_exact']
                assert cpu['retired_runtime_reads_writes_or_fetches']==0
                assert cpu['streaming_lzsa2_input_frontier_guarded'] and cpu['sector_cache_fifo_bounds_guarded']
                assert fuse['complete'] and fuse['ay_records_exact'] and not fuse['errors'] and not fuse['failure']
                assert fuse['nominal_late_frames']==0 and not fuse['bad_actual_intervals']
                assert screens['full_screens_exact'] and screens['compared_bytes']==m['frames']*6912
                assert selection['complete'] and selection['every_selected_block_no_larger_or_slower']
                assert selection['bytes_after']<=selection['bytes_before']
                assert selection['decoder_tstates_after']<=selection['decoder_tstates_before']
                assert selection['rgb_proof']['visible_pixel_changes']==0
                assert selection['states_sha256']==m['states_sha256']
                assert m['cell_codebook']['native']==baseline['cell_codebook']['native']
                actual={r['address']:r['code_hex'] for r in m['lzsa2']['regions'] if r['address'] in decoder}
                assert actual==decoder
                relocated=m.get('cell_core_relocation')
                if relocated:
                    assert relocated['instruction_tstates_before']==relocated['instruction_tstates_after']
                    assert relocated['instruction_delta_tstates']==0
                checks.append(dict(case=name,frames=m['frames'],trd_sha256=m['trd_sha256'],
                    used_sectors=m['used_sectors'],nominal_late_frames=0,
                    decoder_code_identical=True,renderer_code_identical=True,
                    compression_selected=selection['selected'],core_relocation=relocated))
            if len(conversion['volumes'])>1:
                swaps=read(folder/'disk-swaps.json')
                assert len(swaps)==len(conversion['volumes'])-1 and all(x['bootstrap_ram_exact'] for x in swaps)
            for path in sorted(folder.rglob('*')):
                if not path.is_file() or any(x in ('lzsa','zx0') for x in path.relative_to(folder).parts):continue
                if path.suffix in ('.json','.raw','.stream','.npz','.ayh1','.txt','.trd'):
                    archive(path,name+'-'+path.relative_to(folder).as_posix().replace('/','-'))
            archive(tmp/suite/(name+'.mkv'),name+'-source.mkv')
    assert {x['case'] for x in checks}=={'single','portrait','colour','anamorphic','audio-tail'}
    window=read(tmp/'generic-guarded-window/report.json')
    assert window['complete'] and window['generic_representation_exact'] and window['archived_candidate_exact']
    assert window['selected'] and window['every_selected_block_no_larger_or_slower']
    for name in ('report.json','video.raw','video.stream'):
        archive(tmp/'generic-guarded-window'/name,'window-'+name)
    log=tmp/'generic-guarded-tests.log';assert log.read_text().strip().endswith('OK');archive(log,log.name)
    failed=tmp/'generic-guarded-colour/colour.log'
    assert 'unrolled cell renderer overlaps the LZSA2 core' in failed.read_text()
    archive(failed,'initial-core-overlap.log')
    archive(tmp/'generic-guarded-colour/colour-out/conversion.json','initial-core-overlap-conversion.json')
    archive(tmp/'direct-lzsa2-header-part04/part04.json','decoder-baseline-part04.json')
    sources=('guarded_cb46.py','fixed_cell_decoder.py','test_guarded_cb46.py','check_guarded_cb46.py',
        'verify_guarded_cb46.py','check_generic_cb41.py','convert_cb41.py','convert_video.py',
        'cell_codebook_player.py','fit_lzsa2_cpu_budget.py','invisible_attribute_writes.py')
    result=dict(complete=True,release=False,date='2026-10-01',baseline_commit='7cfbacf',scope=__doc__,
        profile='cb46-guarded-v1',unit_tests=21,fixture_volumes=checks,
        fixture_frames=sum(x['frames'] for x in checks),fixture_ay_ticks=sum(x['frames'] for x in checks)*5,
        fixture_screen_bytes=sum(x['frames'] for x in checks)*6912,
        window={k:window[k] for k in ('bytes_before','bytes_after','decoder_tstates_before','decoder_tstates_after',
            'distinct_blocks_recompressed','generic_representation_exact','archived_candidate_exact')},
        instruction_delta_tstates=0,root_images_changed=False,
        limitations=['Short generic fixtures do not prove sustained movie deadlines.',
            'Two fixture disk transitions use the existing modeled-ROM bootstrap checks, not full preceding-EOF Fuse continuation.',
            'The four-volume movie timing and continuation gates remain open. Defaults are unchanged.'],
        artifacts=artifacts,source_sha256_lf={n:sha(Path(__file__).with_name(n).read_bytes().replace(b'\r\n',b'\n')) for n in sources})
    write_json(a.output,result)
    print(json.dumps(dict(complete=True,volumes=len(checks),frames=result['fixture_frames'],artifacts=len(artifacts))))


if __name__=='__main__':main()
