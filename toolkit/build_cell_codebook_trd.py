"""Build and fully CPU-check one independent CB41 window disk; ROM is mocked."""
import argparse,json
from collections import Counter
from pathlib import Path
import numpy as np
from build_fap3_trd import sha
from build_five_level_test_trd import save
from build_integrated_bootstrap import check_cold
from build_row_lzsa import LzsaDiskCPU
from test_warm_continuation import player,until
from row_dictionary_video import reference_tables
from frame_output_pipeline import display_screen
from disk_progress_z80 import reference_screen
import disk_progress_z80 as progress
from cell_codebook_player import Builder
from probe_cell_codebook import history_state
import fap3_disk_z80 as disk


def verify(image,m,states):
    listing=(m['cell_codebook']['packet_listing']+m['cell_codebook']['clock_listing']
             +m['cell_codebook']['native']['instruction_listing'])
    rows={r['address']:r for r in listing};hist=Counter();stages=Counter()
    retired=[(r['start'],r['end']) for r in m['cell_codebook'].get('obsolete_fixed_ranges',[])]
    class TrackedCPU(LzsaDiskCPU):
        tracking=False
        def check_retired(self,address):
            if self.tracking:
                assert not any(lo<=address&65535<hi for lo,hi in retired),('retired access',hex(self.pc),hex(address))
        def read8(self,address):
            self.check_retired(address)
            return super().read8(address)
        def write8(self,address,value):
            self.check_retired(address)
            if self.tracking and m.get('four_video_slots',{}).get('enabled') and address&65535>=0xc000:
                assert self.port_7ffd&7!=6,('write to immutable AY bank',hex(self.pc),hex(address))
            return super().write8(address,value)
        def step(self):
            pc,t=self.pc,self.tstates
            if pc==disk.DRIVER:self.tracking=True
            super().step()
            if self.tracking and pc in rows:
                r=rows[pc];dt=self.tstates-t;wanted=r['tstates']
                assert dt in (wanted if isinstance(wanted,list) else [wanted]),(r,dt)
                hist[pc,dt]+=1;stages[r.get('stage',r.get('phase'))]+=dt
    c=TrackedCPU(player(image),image)
    for b in (0,1,2,3,4,6,7):c.banks[b][:]=b'\xa7'*16384
    c.banks[5][:6912]=b'\xa7'*6912;c.banks[5][0x2400:]=b'\xa7'*(16384-0x2400)
    until(c,m['clock_labels']['start'])
    first=m['frame_start'];count=m['frames'];base=m['cell_codebook']['screen_base']
    dynamic=m['cell_codebook'].get('dynamic_rows',{}).get('enabled',False)
    def expected_screen(index):
        if dynamic:
            from dynamic_row_dictionary import screen
            return screen(states,index)
        return display_screen(history_state(states,index).tobytes(),black_borders=True)
    expected={7:reference_screen(expected_screen(first),0,count),
              5:reference_screen(expected_screen(first-1),0,count)}
    assert all(bytes(c.banks[b][:6912])==s for b,s in expected.items()),'primed screens differ'
    frames=[];minimum=c.sp
    immutable=[(b,lo,bytes(c.banks[b][lo:hi])) for b,lo,hi in
        ((2,0x1e00,0x2000),(2,0x2800,0x3100),(7,0x1c00,0x1c00+m['packet_labels']['state']-0xdc00))
        if not (dynamic and b==2 and lo==0x1e00)]
    def call(pc):
        nonlocal minimum
        c.pc=pc;c.sp=0x9df0;c.push(0x100);steps=c.steps;before=c.tstates;cost=Counter()
        while c.pc!=0x100:
            pc,t=c.pc,c.tstates;c.step();dt=c.tstates-t;minimum=min(minimum,c.sp)
            if pc in rows:
                r=rows[pc];wanted=r['tstates'];assert dt in (wanted if isinstance(wanted,list) else [wanted]),(r,dt)
                cost[r.get('stage',r.get('phase'))]+=dt
            assert c.steps-steps<4000000,'integrated frame stalled'
        assert c.sp==0x9df0 and c.port_7ffd&7==7
        return dict(tstates=c.tstates-before,new_component_stages=dict(cost))
    _,progress_labels,_,_=progress.build(count)
    def advance_progress(published):
        call(progress_labels['tick'])
        for b,s in expected.items():expected[b]=reference_screen(s,published,count)
        assert all(bytes(c.banks[b][:6912])==s for b,s in expected.items()),('progress',published)
    # First native frame and next packet were primed by the actual driver.
    advance_progress(1)
    for i in range(1,count):
        b=7 if i%2==0 else 5;c.write8(base,0xc0 if b==7 else 0x40)
        rendered=call(m['packet_labels']['draw_bridge'])
        expected[b]=reference_screen(expected_screen(first+i),i,count)
        assert all(bytes(c.banks[k][:6912])==s for k,s in expected.items()),('screens',i)
        for bank,lo,data in immutable:assert bytes(c.banks[bank][lo:lo+len(data)])==data,('immutable',bank,lo)
        advance_progress(i+1)
        read=call(m['packet_labels']['next_frame']) if i+1<count else None
        frames.append(dict(frame=first+i,draw=rendered,next_packet=read))
    d=m['disk_labels'];assert c.read8(d['remaining'])+256*c.read8(d['remaining']+1)==0
    return dict(complete=True,all_native_screens_exact=True,frames_checked=count,dirty_prime_exact=True,
        actual_irq_or_cadence=False,scope='Native packets/queue/copies/LZSA2/draw with mocked ROM, host-selected back screen after first prime; not scheduling.',
        minimum_sp=minimum,frames=frames,mocked_sector_reads=c.dos_reads,all_progress_steps_exact=True,
        new_instruction_stages=dict(stages),new_instruction_tstates=sum(stages.values()),
        retired_ranges_guarded=retired,retired_runtime_reads_writes_or_fetches=0,
        immutable_audio_bank_guarded=6 if m.get('four_video_slots',{}).get('enabled') else None,
        histogram=[dict(pc=pc,tstates=t,count=n) for (pc,t),n in sorted(hist.items())])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('raw','states','metadata','probe','cell-raw','options','zx0','lzsa','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    old=json.loads(a.metadata.read_bytes());probe=json.loads(a.probe.read_bytes());raw=a.raw.read_bytes();cell=a.cell_raw.read_bytes()
    with np.load(a.states,allow_pickle=False) as f:states=f['states']
    assert sha(raw)==old['raw_sha256'] and sha(states.tobytes())==probe['states_sha256']==old['states_sha256']
    assert sha(cell)==probe['variants']['codebook']['raw_sha256']
    options=json.loads(a.options.read_bytes())['contract']['options'];options['startup_delta']=False
    start=probe['start'];end=start+probe['count']
    with reference_tables(old['row_dictionary']):
        b=Builder(raw,states,a.zx0.resolve(),a.output/'zx0',row_dictionary=old['row_dictionary'],
            lzsa=a.lzsa.resolve(),series_fingerprint=b'CB41LZSA'+bytes.fromhex(sha(cell))[:6],
            cell_raw=cell,cell_start=start,**options)
        b.ends=[end];image,m=b.volume(start,end,1)
        assert image is not None,'window does not fit disk'
        (a.output/'candidate.trd').write_bytes(image);save(a.output/'metadata.json',m)
        # The generic cold test contains no runtime LZSA instructions.
        cold=check_cold(image,m,b.expected_banks)
        cpu=verify(image,m,states);save(a.output/'cpu.json',cpu)
    report=dict(complete=True,release=False,baseline_commit='4006665',trd_sha256=sha(image),
        states_sha256=sha(states.tobytes()),cell_raw_sha256=sha(cell),first=start,frames=end-start,
        video_bytes=m['video_bytes'],video_sectors=m['video_sectors'],used_sectors=m['used_sectors'],
        cold=cold,cpu_all_frames_exact=cpu['all_native_screens_exact'],real_playback_measured=False,
        source_sha256_lf={n:sha((Path(__file__).parent/n).read_bytes().replace(b'\r\n',b'\n'))
            for n in ('cell_codebook_player.py','build_cell_codebook_trd.py','cell_codebook_z80.py','probe_cell_codebook.py')})
    save(a.output/'build.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('cold','source_sha256_lf')}),flush=True)


if __name__=='__main__':main()
