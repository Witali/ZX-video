"""Generic, opt-in CB46 profile and encoder-only byte/CPU budget selection.

No movie paths, frame cuts or cached metadata are needed. Playback opcodes
reuse the measured four-slot/direct-header implementation unchanged.
"""
import struct

import numpy as np

from build_fap3_trd import sha
from dynamic_row_dictionary import decode_check
from inplace_zx0 import layout
from invisible_attribute_writes import transform_states,transform_stream,verify_rgb
import lzsa2_stream

CORE=0x8d74
PLAYER_OPTIONS=dict(shared_audio=True,four_slots=True,inline_cells=True,
    sector_cache=True,streaming_lzsa2=True,direct_lzsa2_header=True,fixed_cell_decoder=True,
    side_only_seek=True)


def representation(frames,start,end):
    from front_cell_reuse import representation as front
    from partial_row_cells import encode
    base=front(frames,start,end)
    result=encode(base,frames,start,end)
    return dict(base,raw=result['raw'],raw_sha256=result['raw_sha256'],
        details=[dict(old,**new) for old,new in zip(base['details'],result['details'])],
        dynamic_proof=result['proof'])


def audio_fits(data,labels):
    """Check the actual fixed AY forest/tail and compressed-cache helper gap."""
    from fixed_resident_audio import build
    try:
        result=build(data,labels,core_limit=CORE,single_bank=6,fixed_tail=True)
    except ValueError as error:
        return dict(resident_fits=False,reason=str(error))
    if any(s['bank']==2 and s['address']+s['bytes']>0xb900 for s in result['payload_segments']):
        return dict(resident_fits=False,reason='fixed AY tail overlaps sector-cache helper at B900h')
    return dict(resident_fits=True,payload_bytes=result['payload_bytes'],
        fixed_bytes=result['fixed_bytes'],fixed_payload_range=result.get('fixed_payload_range'),
        ayh1_sha256=result['ayh1_sha256'],banks=result['banks'])


def select(raw,stream,blocks,rows,frames,start,end,codec,cache):
    """Measure once per distinct block candidate; restore failures monotonically."""
    from fit_lzsa2_cpu_budget import fit
    from lzsa2_distance_cost import Costs
    from verify_lzsa2_dispatch import execute
    import resumable_lzsa2
    regions,z,native=resumable_lzsa2.build(core=CORE,core_limit=0x8e80)
    # A flat test-core input address, not a player RAM allocation. 2000h leaves
    # space for near-incompressible blocks without overlapping the 7C00h core.
    source=0x2000
    costs=Costs();baseline=[];at=out=0
    for b in blocks:
        n,size=struct.unpack_from('<HH',stream,at);at+=4
        coded=stream[at:at+size];at+=size
        assert (out,out+n,n,size)==(b['raw_start'],b['raw_end'],b['decoded_bytes'],b['compressed_bytes'])
        part=raw[out:out+n];out+=n
        assert sha(part)==b['sha256']
        cpu=execute(regions,z,native,coded,part,source=source)
        baseline.append((part,coded,cpu))
    assert at==len(stream) and out==len(raw)
    frozen=set();rounds=[];measured={};final=None
    for iteration in range(end-start+1):
        states=transform_states(frames,start,end,frozen)
        data,mapping,details=transform_stream(raw,frames,states,start,end,frozen)
        coded_stream=bytearray();result_blocks=[];failed=[]
        for i,(old_part,old_coded,old_cpu) in enumerate(baseline):
            lo,hi=int(mapping[blocks[i]['raw_start']]),int(mapping[blocks[i]['raw_end']])
            part=data[lo:hi];key=i,sha(part)
            if part==old_part:
                coded,cpu,fitting=old_coded,old_cpu,None
            elif key in measured:
                coded,cpu,fitting=measured[key]
            else:
                coded=codec.encode_verified(part,None,cache)
                coded,cpu,fitting=fit(coded,part,len(old_coded),old_cpu['tstates'],costs,regions,z,native,source=source)
                measured[key]=(coded,cpu,fitting)
            exact,proof=lzsa2_stream.trace(coded,limit=len(part));assert exact==part
            space=layout(len(coded),len(part),proof['minimum_input_start'],len(coded_stream))
            fits=space['sector_aligned_fits']
            if fits:lzsa2_stream.trace(coded,limit=len(part),input_start=space['input_start'])
            passed=fits and len(coded)<=len(old_coded) and cpu['tstates']<=old_cpu['tstates']
            if not passed:failed.append(i)
            result_blocks.append(dict(raw_start=lo,raw_end=hi,decoded_bytes=len(part),
                compressed_bytes=len(coded),codec='lzsa2',sha256=sha(part),inplace_proof=proof,
                inplace_layout=space,native=cpu,baseline_native=old_cpu,baseline_bytes=len(old_coded),
                budget_met=passed,cpu_budget_fit=fitting))
            coded_stream+=struct.pack('<HH',len(part),len(coded))+coded
        rounds.append(dict(iteration=iteration,frozen_frames=len(frozen),failed_blocks=failed,
            raw_bytes=len(data),stream_bytes=len(coded_stream),
            decoder_tstates=sum(b['native']['tstates'] for b in result_blocks)))
        if not failed:
            final=data,bytes(coded_stream),result_blocks,states,details
            break
        previous=len(frozen)
        for i in failed:
            b=blocks[i]
            frozen.update(d['frame'] for d in details
                if d['original_raw_start']<b['raw_end'] and d['original_raw_end']>b['raw_start'])
        if len(frozen)==previous:
            # Even an unchanged block may no longer fit a new sector phase.
            # The original complete stream is always the conservative fallback.
            break
    selected=final is not None and len(final[1])<len(stream)
    if selected:
        data,coded,result_blocks,states,details=final
    else:
        data,coded,result_blocks,states=raw,stream,blocks,frames
        details=[]
    proof=decode_check(data,states,start,end,rows)
    rgb=verify_rgb(frames,states,start,end)
    before_t=sum(c['tstates'] for _,_,c in baseline)
    after_t=sum(b['native']['tstates'] for b in result_blocks) if selected else before_t
    report=dict(complete=True,release=False,selected=selected,rounds=rounds,
        baseline_raw_sha256=sha(raw),baseline_stream_sha256=sha(stream),
        raw_sha256=sha(data),stream_sha256=sha(coded),states_sha256=sha(states.tobytes()),
        original_states_sha256=sha(frames.tobytes()),bytes_before=len(stream),bytes_after=len(coded),
        decoder_tstates_before=before_t,decoder_tstates_after=after_t,
        raw_bytes_before=len(raw),raw_bytes_after=len(data),
        removed_attribute_writes=sum(d['removed'] for d in details),
        renderer_tstates_saved=-sum(d['attribute_stage_delta_tstates'] for d in details),
        every_selected_block_no_larger_or_slower=True,distinct_blocks_recompressed=len(measured),
        decoder_code_sha256=sha(b''.join(blob for _,blob in regions)),
        rgb_proof=rgb,proof=proof,details=details,frozen_frames=sorted(frozen),
        cost_scope='Independent non-streaming Z80 core, 256-byte output quotas; excludes IRQ/ULA/paging/physical disk.')
    return dict(raw=data,stream=coded,blocks=result_blocks,states=states,report=report)
