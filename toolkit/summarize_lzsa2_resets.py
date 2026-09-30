"""Archive the bounded reset-placement decision with explicit coverage limits."""
import argparse,gzip,json
from pathlib import Path
from build_fap3_trd import sha
from build_five_level_test_trd import save

ROOT=Path(__file__).resolve().parent


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('aligned','shifted','baseline-frames','output','evidence'):
        p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.evidence.mkdir(parents=True,exist_ok=True)
    old=json.loads(a.baseline_frames.read_bytes())
    transport=json.loads(gzip.decompress((ROOT/'lzsa2_stage_evidence/transport.json.gz').read_bytes()))
    retained=json.loads((ROOT/'borrowed_literals_profile.json').read_bytes())
    assert sha((ROOT.parent/'ZX-video-five-level-lzsa2-test.trd').read_bytes())==retained['trd_sha256']
    report=dict(complete=True,release=False,date='2026-09-30',baseline_commit='8b03511',
        scope='Two reset-placement candidates on the last five blocks, touching saved frames 151..191. Exact same full 192-frame input, 21 blocks and LZSA2 format.',
        baseline=dict(stream_bytes=transport['stream_bytes'],sectors=transport['sector_reads'],
            decoder_tstates=transport['decoder_tstates'],producer_tstates=transport['producer_tstates'],
            frame_tstates=old['frame_tstates'],copy_tstates=old['copy']['tstates']),
        variants={},evidence=[],root_trd_unchanged=True,root_trd_sha256=retained['trd_sha256'],
        current_measured_fps=retained['fps'],candidate_playback_measured=False,goal_achieved=False,
        decision='Do not adopt either tested placement. Aligned variant is 2393 component T slower and 51 bytes larger; shifted variant saves 73 bytes with no sector saving but adds 15336 measured decoder/copy T before unmeasured producer/frame effects. No broad claim that all reset placements are inferior.',
        verifier_change='Packet-copy checks now use validated raw_start/raw_end metadata, replacing fixed 15872-byte division. Reproduces every retained baseline case exactly.',
        next='Measure exact coverage and post-LZSA2 byte cost of a 256-entry 4x4 logical-block dictionary on one saved window, with exact fallback. Reconstruct five brightness levels before fixed-phase dithering; no default video-format change without native timing and quality evidence.')
    for name,directory in (('aligned',a.aligned),('shifted',a.shifted)):
        probe=json.loads((directory/'probe.json').read_bytes());copies=json.loads((directory/'copies.json').read_bytes())
        assert probe['complete'] and copies['complete']
        assert probe['input_raw_sha256']==transport['raw_sha256']==copies['raw_sha256']
        assert probe['baseline_stream_sha256']==transport['stream_sha256']
        assert probe['candidate_stream_sha256']==copies['candidate_stream_sha256']==sha((directory/'video.stream').read_bytes())
        assert copies['baseline']==old['copy']
        for filename,digest in probe['source_sha256_lf'].items():
            assert sha((ROOT/filename).read_bytes().replace(b'\r\n',b'\n'))==digest
        row={k:probe[k] for k in ('byte_delta','candidate_stream_bytes','candidate_sectors','candidate_stream_sha256',
            'decoder_delta_tstates','candidate_decoder_tstates','first_slack','cuts','cut_decisions',
            'first_affected_frame','last_affected_frame','changed_raw_bytes','pc_compression_seconds')}
        row.update(copy_tstates=copies['candidate']['tstates'],copy_delta_tstates=copies['copy_delta_tstates'],
            decoder_plus_copy_delta_tstates=copies['decoder_plus_copy_delta_tstates'],
            borrowed_packets=copies['candidate_borrowed_packets'],
            injected_tail_interrupts=sum(r['interrupt_run']['injected_interrupts'] for r in probe['rows']),
            full_banked_transport_verified=False,all_frames_reverified=False)
        names=['probe.json','copies.json','video.stream']
        if name=='aligned':
            cpu=json.loads((directory/'cpu.json').read_bytes());frames=json.loads((directory/'frames.json').read_bytes())
            assert cpu['complete'] and frames['complete'] and cpu['all_instruction_timings_verified']
            assert frames['full_compact_and_both_native_exact'] and frames['all_instruction_timings_verified']
            assert cpu['stream_sha256']==probe['candidate_stream_sha256']
            assert frames['video_sha256']==cpu['raw_sha256']==probe['input_raw_sha256']
            assert cpu['decoder_tstates']==probe['candidate_decoder_tstates']
            assert len(frames['frames'])==192 and len(cpu['blocks'])==21
            assert frames['copy']==copies['candidate']
            for r in probe['rows']:assert r['native']['slices']==cpu['blocks'][r['index']]['slice_tstates']
            row.update(producer_tstates=cpu['producer_tstates'],producer_delta_tstates=cpu['producer_tstates']-transport['producer_tstates'],
                frame_tstates=frames['frame_tstates'],frame_delta_tstates=frames['frame_tstates']-old['frame_tstates'],
                full_banked_transport_verified=True,all_frames_reverified=True,
                total_component_delta_tstates=(cpu['total_tstates']-transport['total_tstates']+
                    frames['frame_tstates']-old['frame_tstates']+copies['copy_delta_tstates']))
            assert row['total_component_delta_tstates']==2393
            names+=['cpu.json','frames.json']
        else:
            row.update(producer_tstates=None,frame_tstates=None,total_component_delta_tstates=None,
                coverage_limit='Independent native, author and per-write host overlap checks cover all five changed blocks; actual bridge copies cover all packets. No full banked transport, frame or playback rerun for this weaker candidate.')
        report['variants'][name]=row
        for filename in names:
            data=(directory/filename).read_bytes();packed=gzip.compress(data,mtime=0)
            target=name+'-'+filename+'.gz';(a.evidence/target).write_bytes(packed)
            report['evidence'].append(dict(file=target,sha256=sha(packed),raw_sha256=sha(data)))
    report['source_sha256_lf']={n:sha((ROOT/n).read_bytes().replace(b'\r\n',b'\n')) for n in (
        'probe_lzsa2_resets.py','check_lzsa2_reset_copies.py','summarize_lzsa2_resets.py',
        'verify_borrowed_literals.py','benchmark_row_lzsa.py','benchmark_inplace_slot.py',
        'verify_lzsa2_dispatch.py','resumable_lzsa2.py','lzsa2_oracle_host.py','lzsa2_stream.py')}
    save(a.output,report)
    print(json.dumps(dict(variants=report['variants'],root_trd_unchanged=True)))


if __name__=='__main__':main()
