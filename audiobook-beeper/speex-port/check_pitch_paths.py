"""Check all pitch periods, history-read addresses and complete upstream frames."""
from collections import Counter
import ctypes as C
import json
import random
import struct
from check_primitives import machine,symbols
from check_inline_products import step
from verify import native,ROOT,sha


def run(m,start,endpoints):
    m.pc=start;m.ticks_to_stop=10000
    m.step_over_breakpoint()
    while m.pc not in endpoints:
        before=m.ticks_to_stop;event=m.run()
        assert not(event&m._TICKS_LIMIT_HIT)
        assert m.pc in endpoints or m.ticks_to_stop<before,('unexpected breakpoint',hex(m.pc))
    return 10000-m.ticks_to_stop


def audit(m,start,end):
    m.pc=start;m.clear_breakpoint(start);total=0;instructions=0
    while m.pc!=end:total+=step(m);instructions+=1
    return dict(tstates=total,instructions=instructions,every_instruction_matches=True)


def history_paths(out):
    variants=('pure-r26','pure-r27');syms=[symbols(out/v) for v in variants]
    cpus=[machine(out/v) for v in variants];bindings=syms[1];reads=[[],[]]
    # This transform adds no state: bind the older binary to identical slots,
    # and confirm its first pitch load really addresses that same period byte.
    assert syms[0]['s__DATA']==syms[1]['s__DATA'] and syms[0]['l__DATA']==syms[1]['l__DATA']
    assert syms[0]['_pitch_sum_state']==syms[1]['_pitch_sum_state']
    old_start=syms[0]['_pitch_init_end']
    assert bytes(cpus[0].memory[old_start:old_start+3])==b'\x3a'+bindings['_pitch27_period'].to_bytes(2,'little')
    for i,m in enumerate(cpus):
        m.mark_addrs(0,65536,m.WRITE_MARK)
        m.unmark_addrs(syms[i]['s__DATA'],syms[i]['l__DATA'],m.WRITE_MARK)
        m.unmark_addrs(0xbf00,256,m.WRITE_MARK)
        def bad(address,value):raise AssertionError(('pitch-path write',hex(address),value))
        m.set_write_callback(bad);m.mark_addrs(0xc000,16384,m.READ_MARK)
        def read(address,cpu=m,trace=reads[i]):trace.append(address);return cpu.memory[address]
        m.set_read_callback(read)
        m.set_breakpoint(syms[i]['_pitch_flush_end'])
    cpus[1].set_breakpoint(bindings['_pitch27_fast_sum_end'])
    ready={bindings['_pitch27_general_ready'],bindings['_pitch27_fast_ready']}
    for address in ready:cpus[1].set_breakpoint(address)
    rng=random.Random(2727);base=0xd400
    gains_list=[(0,0,0),(-128,127,-1),(127,-128,1),(32,64,32)]
    gains_list += [tuple(rng.randrange(-128,128) for _ in range(3)) for _ in range(12)]
    samples=0;audits=[];delta_hist=Counter();setup_hist=Counter()
    for gains_no,gains in enumerate(gains_list):
        history=[rng.randrange(-32768,32768) for _ in range(184)]
        for m in cpus:
            m.memory[base-368:base]=struct.pack('<184h',*history)
            m.memory[bindings['_pitch27_gains']:bindings['_pitch27_gains']+6]=struct.pack('<3h',*gains)
        for pitch in range(17,145):
            for m in cpus:
                m.memory[bindings['_pitch27_period']]=pitch
                m.memory[bindings['_pitch27_exc_ptr']:bindings['_pitch27_exc_ptr']+2]=base.to_bytes(2,'little')
                m.sp=0xbffe;m.ix=0x1234;m.iy=0x5678
            setup=run(cpus[1],bindings['_pitch27_setup'],ready);setup_hist[setup]+=1
            assert setup==(128 if pitch>=41 else 30)
            assert cpus[1].pc==bindings['_pitch27_fast_ready' if pitch>=41 else '_pitch27_general_ready']
            assert cpus[1].ix==(base-2*(pitch+1) if pitch>=41 else 0x1234)
            for j in range(40):
                want=0;addresses=[]
                for tap in range(3):
                    at=j-(pitch+1-tap)
                    if at>=0:at-=pitch
                    if at<0:
                        assert -184<=at<0
                        want+=gains[2-tap]*history[184+at]
                        addresses += [base+2*at,base+2*at+1]
                costs=[]
                for i,m in enumerate(cpus):
                    m.memory[bindings['_pitch27_sample_index']]=j
                    m.memory[bindings['_pitch27_exc_ptr']:bindings['_pitch27_exc_ptr']+2]=(base+2*j).to_bytes(2,'little')
                    start=syms[i]['_pitch_init_start'];end=syms[i]['_pitch_flush_end']
                    if i==1 and pitch>=41:start=bindings['_pitch27_fast_sum_start'];end=bindings['_pitch27_fast_sum_end']
                    before_ix=m.ix;reads[i].clear()
                    costs.append(run(m,start,{end}))
                    address=bindings['_pitch_sum_state']
                    assert int.from_bytes(m.memory[address:address+3],'little')==want&0xffffff,(i,pitch,j,gains)
                    assert reads[i]==addresses,(i,pitch,j,reads[i],addresses)
                    assert (m.sp,m.iy)==(0xbffe,0x5678)
                    assert m.ix==(base-2*(pitch+1)+2*(j+1) if i==1 and pitch>=41 else 0x1234)
                    if gains_no<2 and pitch in (17,40,41,144) and j in (0,39):
                        m.ix=before_ix;reads[i].clear()
                        r=audit(m,start,end);assert r['tstates']==costs[-1] and reads[i]==addresses
                        r.update(variant=variants[i],pitch=pitch,sample=j,gain_set=gains_no);audits.append(r)
                delta=costs[0]-costs[1];delta_hist[delta]+=1
                assert delta==(295 if pitch>=41 else 0)
                samples+=1
    return dict(pitch_values=128,gain_sets=len(gains_list),samples_per_variant=samples,
                all_history_read_addresses_and_modulo24_sums_exact=True,
                writes_guarded_and_sp_iy_preserved=True,ix_cursor_exact=True,
                setup_tstate_histogram=dict(setup_hist),sum_saving_histogram=dict(delta_hist),instruction_audits=audits)


def packet_periods(payload):
    counts=Counter()
    for start in range(0,len(payload),20):
        value=int.from_bytes(payload[start:start+20],'big');assert value>>(160-5)==3
        for sub in range(4):counts[((value>>(160-(28+33*sub)-7))&127)+17]+=1
    return counts


def all_pitch_frames(out):
    base=(out/'input.spxraw').read_bytes();payload=bytearray()
    for pitch in range(17,145):
        pos=(pitch-17)% (len(base)//20);value=int.from_bytes(base[20*pos:20*pos+20],'big')
        for sub in range(4):
            shift=160-(28+33*sub)-7
            value=(value&~(127<<shift))|((pitch-17)<<shift)
        payload.extend(value.to_bytes(20,'big'))
    assert packet_periods(payload)==Counter({pitch:4 for pitch in range(17,145)})
    ref=C.CDLL(str(out/'host/reference.dll'));ref.reference_reset();pcm=bytearray()
    for at in range(0,len(payload),20):
        packet=(C.c_char*20).from_buffer_copy(payload[at:at+20]);decoded=(C.c_short*160)()
        assert ref.reference_decode(packet,decoded)==0;pcm.extend(bytes(decoded))
    target=out/'checks/all-pitches';target.mkdir(parents=True,exist_ok=True)
    (target/'input.spxraw').write_bytes(payload);(target/'reference.pcm16').write_bytes(pcm)
    result=dict(frames=128,samples=128*160,every_pitch_in_every_subframe_position=True,
                payload_sha256=sha(payload),upstream_pcm16_sha256=sha(pcm),variants={})
    for variant in ('pure-r26','pure-r27'):
        r=native(target,variant,out/variant);r.pop('out_intervals_histogram')
        result['variants'][variant]=r
    return result


def main():
    out=ROOT/'build/speex-port';r=dict(history_paths=history_paths(out),all_pitch_frames=all_pitch_frames(out))
    periods=packet_periods((out/'input.spxraw').read_bytes())
    fast=sum(n for p,n in periods.items() if p>=41);general=sum(periods.values())-fast
    saving=fast*(40*(295+21)-128)-general*40
    old=json.loads((out/'pure-r26/report.json').read_text());new=json.loads((out/'pure-r27/report.json').read_text())
    assert old['total_tstates']-new['total_tstates']==saving
    r['speech']=dict(pitch_histogram=dict(sorted(periods.items())),fast_subframes=fast,general_subframes=general,
                     fast_saving_per_sample=316,fast_setup_tstates=128,general_extra_tstates_per_subframe=40,
                     predicted_and_measured_saving_tstates=saving)
    (out/'pure-r27/pitch-path-checks.json').write_text(json.dumps(r,indent=2)+'\n')
    print(r['history_paths']['samples_per_variant'],r['speech'],flush=True)


if __name__=='__main__':main()
