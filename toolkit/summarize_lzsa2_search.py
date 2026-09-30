"""Archive the bounded standard-format LZSA2 search experiments and decisions."""
import argparse,gzip,json,struct
from pathlib import Path
from build_fap3_trd import sha
from build_five_level_test_trd import save
import resumable_lzsa2

ROOT=Path(__file__).resolve().parent


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('wide','deep','output','evidence'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    base=json.loads(gzip.decompress((ROOT/'lzsa2_stage_evidence/transport.json.gz').read_bytes()))
    retained=json.loads((ROOT/'borrowed_literals_profile.json').read_bytes())
    regions,_,native=resumable_lzsa2.build()
    assert native==base['native']
    assert sha((ROOT.parent/'ZX-video-five-level-lzsa2-test.trd').read_bytes())==retained['trd_sha256']
    result=dict(complete=True,release=False,date='2026-09-30',baseline_commit='c3d1125',
        scope='Fixed 21 independent raw blocks / 323940 bytes from the 192-frame five-level fixture. Host compressor changes only. No player/disk release.',
        baseline={k:base[k] for k in ('raw_sha256','stream_sha256','decoded_bytes','stream_bytes','sector_reads','decoder_tstates','producer_tstates','total_tstates','max_slice_tstates')},
        variants={},native_machine_code_sha256=sha(b''.join(blob for _,blob in regions)),
        native_code_unchanged=True,format_unchanged=True,decoded_bytes_unchanged=True,root_trd_unchanged=True,
        root_trd_sha256=retained['trd_sha256'],candidate_fps=None,
        table_allocation_estimate=dict(arrival_struct_bytes=24,allocated_positions=65537,
            baseline_arrival_bytes=65537*64*24,candidate_arrival_bytes=65537*256*24,
            baseline_match_bytes=65536*64*4,candidate_match_bytes=65536*128*4,
            scope='Allocation requests derived from the pinned C structures and constants on MSVC x64; excludes other tables/runtime and is not measured peak working set.'),
        decision='Reject table enlargement and this supplemental-search expansion as production defaults: 2/12 bytes saved, no sector saved, slightly more Z80 work. Keep reproducible prototypes and design a stronger state-aware parser.',
        next='Compare a bounded exact parser on small adversarial inputs to expose pruning losses, then test an extended parser only on a saved difficult window. Retain baseline payloads whenever a candidate loses the required byte/time objective.',
        evidence=[])
    a.evidence.mkdir(parents=True,exist_ok=True)
    probes={}
    for name,directory in (('wide',a.wide),('deep',a.deep)):
        probe=json.loads((directory/'probe.json').read_bytes());cpu=json.loads((directory/'cpu.json').read_bytes())
        verify=json.loads((directory/'verification.json').read_bytes());stream=(directory/'wide.stream').read_bytes()
        assert probe['complete'] and cpu['complete'] and verify['complete']
        assert probe['raw_sha256']==cpu['raw_sha256']==verify['raw_sha256']==base['raw_sha256']
        assert probe['baseline_stream_sha256']==base['stream_sha256']
        assert probe['stream_sha256']['wide']==cpu['stream_sha256']==verify['stream_sha256']==sha(stream)
        assert native==cpu['native'] and cpu['all_instruction_timings_verified']
        assert verify['decoder_tstates']==cpu['decoder_tstates']
        assert len(probe['rows'])==len(cpu['blocks'])==len(verify['rows'])==21
        for old,new in zip(base['blocks'],cpu['blocks']):assert old['raw_sha256']==new['raw_sha256']
        probes[name]=probe
        result['variants'][name]=dict(
            **{k:cpu[k] for k in ('stream_bytes','sector_reads','decoder_tstates','producer_tstates','total_tstates','max_slice_tstates','stream_sha256')},
            byte_delta=cpu['stream_bytes']-base['stream_bytes'],decoder_delta_tstates=cpu['decoder_tstates']-base['decoder_tstates'],
            saved_percent=100*(base['stream_bytes']-cpu['stream_bytes'])/base['stream_bytes'],
            pc_seconds=probe['pc_seconds'],pc_time_ratio=probe['pc_seconds']['wide']/probe['pc_seconds']['baseline'],
            pc_timing_scope=probe['pc_timing_scope'],improved_blocks=probe['improved_blocks'],regressed_blocks=probe['regressed_blocks'],
            independent_slices_exact=True,injected_interrupts=verify['injected_interrupts'])
        if name=='deep':
            edges=json.loads((directory/'edges/edges.json').read_bytes())
            assert edges['complete'];result['deep_native_edge_cases']=len(edges['cases'])
        for filename in ('probe.json','build.json','build.log','cpu.json','verification.json','wide.stream'):
            content=(directory/filename).read_bytes()
            if filename in ('probe.json','build.json'):
                record=json.loads(content)
                manifest=record['build'] if filename=='probe.json' else record
                # Correct an early descriptive note; experimental source hashes
                # and measurements remain unchanged. The wide build predated
                # the optional deep flag and therefore means deep=False.
                manifest.setdefault('deep_supplements',name=='deep')
                manifest['note']='Standard format and unchanged writer/decoder. The optional deep variant widens specified supplement limits; both variants still use bounded heuristic search.'
                content=(json.dumps(record,indent=2)+'\n').encode()
            dest=name+'-'+filename+'.gz';packed=gzip.compress(content,mtime=0)
            (a.evidence/dest).write_bytes(packed)
            result['evidence'].append(dict(file=dest,sha256=sha(packed),raw_sha256=sha(content)))
    content=(a.deep/'edges/edges.json').read_bytes();packed=gzip.compress(content,mtime=0)
    (a.evidence/'deep-edges.json.gz').write_bytes(packed)
    result['evidence'].append(dict(file='deep-edges.json.gz',sha256=sha(packed),raw_sha256=sha(content)))
    result['size_only_best_of_estimate_bytes']=sum(4+min(r['baseline']['payload_bytes'],r['wide']['payload_bytes'],s['wide']['payload_bytes'])
        for r,s in zip(probes['wide']['rows'],probes['deep']['rows']))
    result['best_of_scope']='Byte-count estimate only from independent saved payloads, not a newly built stream or disk. At equal size production selection must consider measured Z80 work.'
    result['source_sha256_lf']={n:sha((ROOT/n).read_bytes().replace(b'\r\n',b'\n')) for n in (
        'probe_lzsa2_search.py','verify_lzsa2_search.py','summarize_lzsa2_search.py','benchmark_row_lzsa.py',
        'resumable_lzsa2.py','lzsa2_stream.py','test_row_lzsa.py','verify_lzsa2_dispatch.py','build_lzsa_windows.cmd')}
    save(a.output,result)
    print(json.dumps({k:result[k] for k in ('variants','deep_native_edge_cases','size_only_best_of_estimate_bytes','root_trd_unchanged')}))


if __name__=='__main__':main()
