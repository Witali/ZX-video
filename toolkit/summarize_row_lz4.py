"""Save reproducible LZ4 analysis, separating CPU evidence from disk estimates."""
import argparse,gzip,json,struct
from collections import Counter
from pathlib import Path
from build_fap3_trd import sha
from build_five_level_test_trd import save
import lz4_stream

ROOT=Path(__file__).resolve().parent


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('baseline','candidate','verification','metadata','raw','evidence','output'):
        p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    old=json.loads(a.baseline.read_bytes());new=json.loads(a.candidate.read_bytes());v=json.loads(a.verification.read_bytes())
    lzsa=json.loads(gzip.decompress((ROOT/'lzsa2_stage_evidence/transport.json.gz').read_bytes()))
    stream=gzip.decompress((ROOT/'modern_codec_evidence/lz4_hc12.stream.gz').read_bytes());raw=a.raw.read_bytes()
    assert old['complete'] and new['complete'] and v['complete'] and lzsa['complete']
    assert old['stream_sha256']==new['stream_sha256']==v['stream_sha256']==sha(stream)
    assert old['raw_sha256']==new['raw_sha256']==v['raw_sha256']==lzsa['raw_sha256']==sha(raw)
    assert old['all_instruction_timings_verified'] and new['all_instruction_timings_verified']
    assert old['native']['fast_short'] is False and new['native']['fast_short'] is True
    literals=Counter();matches=Counter();offsets=Counter();repeats=0;at=0;out=0;per_block=[]
    for i in range(len(new['blocks'])):
        n,size=struct.unpack_from('<HH',stream,at);at+=4
        decoded,proof=lz4_stream.trace(stream[at:at+size],limit=n)
        assert decoded==raw[out:out+n];at+=size;out+=n
        literals.update(proof['literal_runs']);matches.update(proof['match_runs']);offsets.update(proof['match_offsets'])
        repeats+=sum(x==y for x,y in zip(proof['match_offsets'],proof['match_offsets'][1:]))
        for report in (old,new,lzsa):
            assert report['blocks'][i]['raw_sha256']==sha(decoded)
        ob,nb,lb=(r['blocks'][i] for r in (old,new,lzsa))
        per_block.append(dict(index=i,lz4_payload_bytes=size,lzsa2_payload_bytes=lb['payload_bytes'],
            added_bytes=size-lb['payload_bytes'],lz4_baseline_tstates=ob['decoder_tstates'],
            lz4_candidate_tstates=nb['decoder_tstates'],lzsa2_tstates=lb['decoder_tstates'],
            decoder_saving_vs_lzsa2=lb['decoder_tstates']-nb['decoder_tstates']))
    assert at==len(stream) and out==len(raw)
    counts=dict(zero_literals=literals[0],short_literals=sum(v for k,v in literals.items() if 1<=k<=14),
        extended_literals=sum(v for k,v in literals.items() if k>=15),
        short_matches=sum(v for k,v in matches.items() if k<=18),
        extended_matches=sum(v for k,v in matches.items() if k>=19))
    predicted=58*counts['short_literals']+101*counts['short_matches']-19*counts['extended_literals']-22*counts['extended_matches']
    assert predicted==old['decoder_tstates']-new['decoder_tstates']
    assert old['producer_tstates']==new['producer_tstates']
    small=sum(v for k,v in offsets.items() if k<=255);large=sum(offsets.values())-small
    hotspots={}
    for name,r in (('baseline',old),('candidate',new)):
        rows={x['address']:x['instruction'] for x in r['native']['instruction_listing']};c=Counter()
        for h in r['decoder_histogram']:c[rows[h['pc']]]+=h['tstates']*h['count']
        assert sum(c.values())==r['decoder_tstates']
        hotspots[name]=dict(c.most_common())
    extra_sectors=new['sector_reads']-lzsa['sector_reads'];saving=lzsa['total_tstates']-new['total_tstates']
    retained=json.loads((ROOT/'borrowed_literals_profile.json').read_bytes())
    assert sha((ROOT.parent/'ZX-video-five-level-lzsa2-test.trd').read_bytes())==retained['trd_sha256']
    result=dict(complete=True,release=False,date='2026-09-30',baseline_commit='e681055',
        scope='21 saved blocks of the exact 192-frame five-level fixture; same decoded bytes and block boundaries. No new TRD or elapsed playback measurement.',
        raw_sha256=sha(raw),stream_sha256=sha(stream),decoded_bytes=len(raw),blocks=len(per_block),
        metrics={name:{k:r[k] for k in ('decoder_tstates','producer_tstates','total_tstates','stream_bytes','sector_reads','max_slice_tstates')}
            for name,r in (('lzsa2',lzsa),('lz4_baseline',old),('lz4_candidate',new))},
        native_bytes=dict(baseline=old['native']['code_bytes'],candidate=new['native']['code_bytes']),
        counts=counts,instruction_cycle_saving=predicted,
        decoder_reduction_percent=100*predicted/old['decoder_tstates'],
        decoder_reduction_vs_lzsa2_percent=100*(lzsa['decoder_tstates']-new['decoder_tstates'])/lzsa['decoder_tstates'],
        stream_growth_vs_lzsa2_percent=100*(len(stream)-lzsa['stream_bytes'])/lzsa['stream_bytes'],
        component_saving_vs_lzsa2_tstates=saving,extra_sectors=extra_sectors,
        additive_disk_break_even_tstates_per_extra_sector=saving/extra_sectors,
        disk_estimate_limits='Break-even only in a serial additive model. It excludes ROM, physical latency, ULA, IRQ, actual demand queues, packet borrowing changes, and mixed-codec dispatch. Sector interleave, seeking and overlap require a Fuse run.',
        ldir_repeat_removal_upper_bound_tstates=hotspots['candidate']['LDIR']-16*len(raw),
        hotspots=hotspots,per_block=per_block,
        offsets=dict(total=sum(offsets.values()),one_byte_possible=small,larger_than_255=large,
            repeated_previous=repeats,distance_one=offsets[1],
            custom_1_or_3_byte_offset_size_delta=large-small,
            custom_offset_estimate_only='Same token parse, hypothetical offsets 1..255 in one byte, other offsets as 0 + uint16. Not standard LZ4; no decoder or CPU measurement. Does not include format signalling or altered block fit.'),
        verification=dict(video_blocks_per_variant=len(per_block),edges_per_variant=v['edge_cases_per_variant'],
            invalid_host_inputs_rejected=v['invalid_host_inputs_rejected'],
            author_decoder_version=v['author_decoder_version'],independent_slices_exact=True,
            injected_video_interrupts={k:r['injected_interrupts'] for k,r in v['variants'].items()},
            unavailable_video_interrupt_events={k:sum(x['interrupt_run']['unavailable_interrupt_events'] for x in r['blocks']) for k,r in v['variants'].items()},
            worst_edge_slice_tstates={k:r['max_slice_tstates'] for k,r in v['edges'].items()},
            minimum_edge_decoder_sp={k:r['minimum_decoder_sp'] for k,r in v['edges'].items()}),
        root_trd_unchanged=True,root_trd_sha256=retained['trd_sha256'],
        decision='Retain the verified fast LZ4 component as an experiment; do not replace LZSA2 on decoder CPU alone. Prioritize measured block selection and actual delivery timing.',
        next='Use a bounded difficult-frame window to choose between codecs using bytes and native cycles; account for dispatch/code placement and measure real disk/publication deadlines before adoption.')
    a.evidence.mkdir(parents=True,exist_ok=True);result['evidence']=[]
    for name,path in (('baseline.json',a.baseline),('candidate.json',a.candidate),('verification.json',a.verification),
                      ('metadata.json',a.metadata),('video.raw',a.raw)):
        content=path.read_bytes();packed=gzip.compress(content,mtime=0);(a.evidence/(name+'.gz')).write_bytes(packed)
        result['evidence'].append(dict(file=name+'.gz',sha256=sha(packed),raw_sha256=sha(content)))
    result['source_sha256_lf']={n:sha((ROOT/n).read_bytes().replace(b'\r\n',b'\n')) for n in (
        'resumable_lz4.py','lz4_stream.py','benchmark_row_lz4.py','verify_row_lz4.py','summarize_row_lz4.py',
        'resumable_lzsa2.py','verify_lzsa2_dispatch.py','benchmark_inplace_slot.py','benchmark_inplace_streaming.py')}
    save(a.output,result)
    print(json.dumps({k:result[k] for k in ('instruction_cycle_saving','decoder_reduction_vs_lzsa2_percent',
        'component_saving_vs_lzsa2_tstates','extra_sectors','offsets','root_trd_unchanged')}))


if __name__=='__main__':main()
