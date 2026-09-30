"""Validate and archive the fixed-command LZSA2 distance experiment.

Cross-check the token model at length boundaries and compare the DP with
exhaustively serialized tiny alternatives. Native block/slice verification
is supplied by benchmark_row_lzsa.py and verify_lzsa2_search.py.
"""
import argparse,gzip,itertools,json,struct
from pathlib import Path
from unittest.mock import patch
import benchmark_inplace_slot as banked
from benchmark_row_lzsa import fixture
from build_fap3_trd import sha
from build_five_level_test_trd import save
from lzsa2_distance_cost import Costs
from lzsa2_oracle import encode
from lzsa2_oracle_host import Author
from optimize_lzsa2_distances import candidates,evaluate,optimize,parse
import resumable_lzsa2
import lzsa2_stream

ROOT=Path(__file__).resolve().parent


def blocks(stream):
    at=0;rows=[]
    while at<len(stream):
        n,size=struct.unpack_from('<HH',stream,at);at+=4
        payload=stream[at:at+size];at+=size
        assert len(payload)==size
        rows.append((n,payload))
    assert at==len(stream)
    return rows


def check_costs(costs):
    literals=(0,1,2,3,4,17,18,19,255,256,257,511,512,513)
    matches=(2,3,8,9,10,23,24,25,255,256,257,511,512,513)
    checked=0
    for ll,n,kind,pending in itertools.product(literals,matches,range(8),(False,True)):
        assert costs.token(ll,n,kind,pending)==costs.measured(ll,n,kind,pending)
        checked+=1
    for ll,pending in itertools.product(literals,(False,True)):
        assert costs.token(ll,0,7,pending)==costs.measured(ll,0,7,pending)
        checked+=1
    # Native block ceiling, separately avoiding mixed lengths beyond it.
    for ll,n in ((0,15872),(1,15871),(15870,2),(15872,0)):
        for kind,pending in itertools.product(range(8) if n else (7,),(False,True)):
            assert costs.token(ll,n,kind,pending)==costs.measured(ll,n,kind,pending)
            checked+=1
    return checked


def check_exhaustive(costs,author):
    cases=alternatives=0;rows=[]
    # Every valid fixed two-byte-match layout with at most three commands
    # for these short sources; all source distances are then enumerated.
    for raw in (b'A'*10,b'AB'*6,b'ABC'*4,b'AABAABAAB',b'ABCDEFGHI'):
        positions=[p for p in range(1,len(raw)-1) if candidates(raw,p,2)]
        for count in range(4):
            for ps in itertools.combinations(positions,count):
                if any(b<a+2 for a,b in zip(ps,ps[1:])):continue
                ds=[candidates(raw,p,2) for p in ps]
                baseline=encode(raw,[(p,2,d[0]) for p,d in zip(ps,ds)])
                _,commands,tail=parse(baseline,len(raw))
                best=minimum=None;num=0
                for distances in itertools.product(*ds):
                    data=encode(raw,[(p,2,d) for p,d in zip(ps,distances)])
                    assert author.decompress(data,len(raw))==raw
                    units,t=evaluate(commands,distances,tail,costs)
                    assert (units+1)//2==len(data)
                    minimum=units if minimum is None else min(minimum,units)
                    if len(data)<=len(baseline):best=t if best is None else min(best,t)
                    num+=1
                result,report=optimize(baseline,len(raw),costs)
                assert report['candidate_token_tstates']==best
                assert report['minimum_nibbles']==minimum
                assert author.decompress(result,len(raw))==raw
                cases+=1;alternatives+=num
                rows.append(dict(raw=raw.hex(),positions=ps,alternatives=num,
                    minimum_nibbles=minimum,best_tstates=best,candidate_hex=result.hex()))
    return dict(layouts=cases,serialized_alternatives=alternatives,rows=rows)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('baseline','work','author','output','evidence'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();author=Author(a.author);costs=Costs()
    model_cases=check_costs(costs);brute=check_exhaustive(costs,author)
    probe=json.loads((a.work/'probe.json').read_bytes())
    cpu=json.loads((a.work/'cpu.json').read_bytes())
    independent=json.loads((a.work/'verification.json').read_bytes())
    base=json.loads(gzip.decompress((ROOT/'lzsa2_stage_evidence/transport.json.gz').read_bytes()))
    old=a.baseline.read_bytes();new=(a.work/'video.stream').read_bytes();raw=(a.work/'video.raw').read_bytes()
    assert sha(old)==base['stream_sha256']==probe['baseline_stream_sha256']
    assert sha(new)==cpu['stream_sha256']==independent['stream_sha256']==probe['candidate_stream_sha256']
    assert sha(raw)==cpu['raw_sha256']==base['raw_sha256']==independent['raw_sha256']
    assert probe['complete'] and cpu['complete'] and independent['complete']
    assert cpu['all_instruction_timings_verified'] and cpu['sectors_exact_once']
    assert costs.native==base['native']==cpu['native']==probe['native']
    assert cpu['decoder_tstates']==independent['decoder_tstates']
    assert cpu['decoder_tstates']-base['decoder_tstates']==probe['modeled_delta_tstates']
    assert cpu['producer_tstates']==base['producer_tstates'] and cpu['sector_reads']==base['sector_reads']
    old_blocks=blocks(old);new_blocks=blocks(new);changed=[];at=0
    assert len(old_blocks)==len(new_blocks)==len(cpu['blocks'])==len(independent['rows'])==21
    for i,((n,old_data),(m,new_data)) in enumerate(zip(old_blocks,new_blocks)):
        assert n==m
        expected=raw[at:at+n];at+=n
        assert author.decompress(new_data,n)==expected
        if old_data!=new_data:changed.append(i)
    assert at==len(raw) and changed==[probe['block']]
    n,old_data=old_blocks[probe['block']]
    result,repeated=optimize(old_data,n,costs)
    assert result==new_blocks[probe['block']][1]
    for key in ('baseline_token_tstates','candidate_token_tstates','minimum_nibbles','peak_states'):
        assert repeated[key]==probe[key]
    # Separately exercise a failed/short sector followed by retry, with the
    # changed block isolated at a fresh stream start. This is not playback.
    one=struct.pack('<HH',n,len(result))+result
    h,_=fixture(one,57,0x8de0,0x8ef7)
    with patch.object(banked,'trace',lzsa2_stream.trace):
        short=h.block(result,author.decompress(result,n),0,short=True)
    assert not h.cpu.short_once
    retry=h.finish()
    assert retry['complete'] and retry['sectors_exact_once']
    # Save the exact instruction-cost table and every small enumeration.
    checks=dict(complete=True,release=False,token_boundary_cases=model_cases,
        exhaustive=brute,measured_token_costs=costs.rows,author_video_roundtrips=len(new_blocks),
        isolated_short_sector_retry=dict(complete=True,block=short,summary=retry))
    save(a.work/'checks.json',checks)
    retained=json.loads((ROOT/'borrowed_literals_profile.json').read_bytes())
    assert sha((ROOT.parent/'ZX-video-five-level-lzsa2-test.trd').read_bytes())==retained['trd_sha256']
    report={k:v for k,v in probe.items() if k not in ('rows','native_cost_model','native')}
    report.update(date='2026-09-30',baseline_commit='ca95df5',
        baseline={k:base[k] for k in ('stream_bytes','decoder_tstates','producer_tstates','total_tstates','sector_reads')},
        candidate={k:cpu[k] for k in ('stream_bytes','decoder_tstates','producer_tstates','total_tstates','sector_reads')},
        token_boundary_cases=model_cases,exhaustive_layouts=brute['layouts'],
        serialized_alternatives=brute['serialized_alternatives'],
        author_video_roundtrips=len(new_blocks),independent_slices_exact=True,
        isolated_short_sector_retry=True,
        injected_interrupts=independent['injected_interrupts'],
        native_machine_code_sha256=sha(b''.join(blob for _,blob in resumable_lzsa2.build()[0])),
        root_trd_unchanged=True,root_trd_sha256=retained['trd_sha256'],
        current_measured_fps=retained['fps'],candidate_playback_measured=False,goal_achieved=False,
        decision='Do not integrate or broaden this distance-only search: unchanged size and only 108 decoder T saved on the selected complete block. Retain the prototype and verified model as bounded evidence.',
        next='Measure a small set of independent-block reset positions on a saved difficult window, retaining LZSA2 format and decoded bytes. Account for headers, overlap, sectors and native cycles before any playback integration.',
        evidence=[])
    a.evidence.mkdir(parents=True,exist_ok=True)
    for name in ('probe.json','cpu.json','verification.json','checks.json','video.stream'):
        data=(a.work/name).read_bytes();packed=gzip.compress(data,mtime=0)
        (a.evidence/(name+'.gz')).write_bytes(packed)
        report['evidence'].append(dict(file=name+'.gz',sha256=sha(packed),raw_sha256=sha(data)))
    report['source_sha256_lf']={name:sha((ROOT/name).read_bytes().replace(b'\r\n',b'\n')) for name in (
        'lzsa2_distance_cost.py','optimize_lzsa2_distances.py','verify_lzsa2_distances.py',
        'lzsa2_oracle.py','lzsa2_stream.py','resumable_lzsa2.py','benchmark_row_lzsa.py',
        'verify_lzsa2_search.py','verify_lzsa2_dispatch.py','lzsa2_oracle_host.py','lzsa2_oracle_host.c')}
    save(a.output,report)
    print(json.dumps({key:report[key] for key in ('modeled_delta_tstates','token_boundary_cases',
        'exhaustive_layouts','serialized_alternatives','injected_interrupts','root_trd_unchanged')}))


if __name__=='__main__':main()
