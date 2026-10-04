"""Exhaustive exact pitch constants, immutable pointers and instruction costs."""
import argparse
from collections import Counter
import json
import gzip
from contextlib import redirect_stdout
import io
from check_primitives import audit,call,machine,symbols
from check_inline_products import step
from check_s8_combined import expected_cost
from constant_pitch import gains
from verify import ROOT,HERE,native,sha


def constants(folder,plan):
    m=machine(folder);s=symbols(folder)
    m.mark_addrs(0,65536,m.WRITE_MARK)
    m.unmark_addrs(0xbf00,256,m.WRITE_MARK)
    def bad(address,value):raise AssertionError(('constant product write',hex(address),value))
    m.set_write_callback(bad)
    preserved=(0x1234,0xabcd,0x3456,0x5678,0xcafe,0xdead,0xbffe)
    def reset():
        m.alt_af,m.alt_bc,m.alt_de,m.alt_hl,m.ix,m.iy=preserved[:-1]
    direct=plan.get('result_registers')=='A:HL'
    def check(word,gain):
        got=(m.a<<16|m.hl) if direct else (m.hl<<16|m.de)
        assert got==(gain*word)&(0xffffff if direct else 0xffffffff),(gain,word,got)
        assert (m.alt_af,m.alt_bc,m.alt_de,m.alt_hl,m.ix,m.iy,m.sp)==preserved
    routines=plan['routines'];by_gain={r['gain']:r for r in routines}
    pointer=s['_pitch_gain_targets']
    for i,gain in enumerate(gains()):
        assert int.from_bytes(m.memory[pointer+2*i:pointer+2*i+2],'little')==s[by_gain[gain]['label']]
    rows=[];audit_instructions=0;total_bytes=1
    for i,r in enumerate(routines):
        gain=r['gain'];addr=s[r['label']];reset()
        for word in range(-32768,32768):
            cost=call(m,addr,de=word&65535)
            assert cost==r['tstates_including_ret'],(gain,word,cost,r)
            check(word,gain)
        # Independently step all sign/carry boundaries and the JP (HL) entry.
        audits=[]
        for word in (-32768,-32767,-257,-1,0,1,255,256,32767):
            reset();m.de=word&65535;m.hl=addr;m.pc=s['_pitch_indirect']
            m.sp=0xbffc;m.memory[m.sp:m.sp+2]=b'\x00\x7f';cost=0;count=0
            addresses=[]
            while m.pc!=0x7f00:
                addresses.append(m.pc);cost+=step(m);count+=1
            assert cost==r['tstates_including_ret']+4
            check(word,gain)
            assert addresses[0]==s['_pitch_indirect'] and addresses[1]==addr
            # Every generated constant path is straight-line through its RET.
            assert addresses[-1]-addr+1==r['bytes']
            if i+1<len(routines):assert s[routines[i+1]['label']]-addr==r['bytes']
            audits.append(dict(word=word,tstates=cost,instructions=count))
            audit_instructions+=count
        total_bytes+=r['bytes']
        rows.append(dict(gain=gain,words=65536,tstates=r['tstates_including_ret'],bytes=r['bytes'],audits=audits))
    return dict(exact_products=len(routines)*65536,unique_gains=len(routines),pointer_entries=96,
                pointer_bytes=192,code_bytes=total_bytes,all_costs_constant_and_exact=True,
                all_alternates_ix_iy_sp_preserved=True,writes_guarded=True,
                audited_instructions=audit_instructions,all_audited_instructions_match=True,routines=rows)


def speech(folder,variant,plan,baseline,previous_plan=None):
    out=ROOT/'build/speex-port'
    s=symbols(folder);by_name={r['label']:r for r in plan['routines']}
    counts=Counter();saving=0;negative_words=0
    previous={r['label']:r for r in previous_plan['routines']} if previous_plan else None
    old_add=48 if previous_plan and previous_plan.get('result_registers')=='A:HL' else 52
    new_add=48 if plan.get('result_registers')=='A:HL' else 52
    def observe(name,m):
        nonlocal saving,negative_words
        if name not in by_name:return
        row=by_name[name];word=m.de-65536 if m.de&32768 else m.de
        old=previous[name]['tstates_including_ret'] if previous else expected_cost(row['gain'],word)
        # Generic->constant dispatch adds 7 T; constant->constant is unchanged.
        # Direct A:HL also removes the caller's 4-T LD A,L before accumulation.
        saving+=old-row['tstates_including_ret']-(0 if previous else 7)+old_add-new_add
        counts[name]+=1;negative_words+=(word<0)
    with redirect_stdout(io.StringIO()):
        r=native(out,variant,folder,profile=tuple(by_name)+('_mul_s8',),entry_observer=observe)
    for name,n in counts.items():
        assert r['profile']['inclusive_tstates'][name]==n*by_name[name]['tstates_including_ret']
    assert baseline['total_tstates']-r['total_tstates']==saving
    return dict(samples=r['samples'],complete=True,every_pcm16_exact=r['every_pcm16_exact'],
                every_pcm8_exact=r['every_pcm8_exact'],total_tstates=r['total_tstates'],
                baseline_tstates=baseline['total_tstates'],delta_tstates=-saving,
                predicted_saving_tstates=saving,exact_total_delta_reconciles=True,
                pitch_products=sum(counts.values()),negative_history_words=negative_words,
                helper_calls=dict(counts),remaining_generic_calls=r['profile']['calls']['_mul_s8'],
                binary_sha256=r['binary_sha256'])


def extra_stream(folder,variant):
    """Reuse the independently decoded all-pitch fixture saved in round27."""
    fixture=ROOT/'build/speex-port/checks/all-pitches'
    fixture.mkdir(parents=True,exist_ok=True)
    for name in ('input.spxraw','reference.pcm16'):
        data=gzip.decompress((HERE/'rounds/27'/('all-pitches-'+name+'.gz')).read_bytes())
        target=fixture/name
        if target.exists():assert target.read_bytes()==data
        else:target.write_bytes(data)
    with redirect_stdout(io.StringIO()):r=native(fixture,variant,folder)
    r.pop('out_intervals_histogram',None)
    r['payload_sha256']=sha((fixture/'input.spxraw').read_bytes())
    r['reference_pcm16_sha256']=sha((fixture/'reference.pcm16').read_bytes())
    out=ROOT/'build/speex-port'
    r['first_speech_frame_audit']=audit(folder,(out/'input.spxraw').read_bytes(),(out/'reference.pcm16').read_bytes())
    return r


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--variants',nargs='+',default=['pure-r28-binary','pure-r28'])
    p.add_argument('--previous',default='pure-r27');a=p.parse_args()
    out=ROOT/'build/speex-port';baseline=json.loads((out/a.previous/'report.json').read_text())
    previous_path=out/a.previous/'constant-pitch-plan.json'
    previous_plan=json.loads(previous_path.read_text()) if previous_path.exists() else None
    results={}
    for variant in a.variants:
        folder=out/variant;plan=json.loads((folder/'constant-pitch-plan.json').read_text())
        checks=constants(folder,plan)
        print(variant,'exhaustive constants passed:',checks['exact_products'],'products,',checks['code_bytes'],'code bytes',flush=True)
        checks['speech']=speech(folder,variant,plan,baseline,previous_plan)
        checks['all_pitches']=extra_stream(folder,variant)
        (folder/'constant-pitch-checks.json').write_text(json.dumps(checks,indent=2)+'\n',newline='\n')
        results[variant]=checks
        print(variant,{k:v for k,v in checks['speech'].items() if k!='helper_calls'},flush=True)
    if len(results)==2:
        binary,chain=(results[x] for x in a.variants)
        assert all(c['tstates']<=b['tstates'] for b,c in zip(binary['routines'],chain['routines']))


if __name__=='__main__':main()
