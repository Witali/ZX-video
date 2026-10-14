"""Preserve the failed FRAMES-based UI phase result and complete saved clocks."""
import gzip
import hashlib
import json
from pathlib import Path
import re
import runpy

import numpy as np


HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
BASELINE=ROOT/'audiobook-beeper/experiments/song-snr/evidence/clock-joint/sea_foam'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    tools=runpy.run_path(str(HERE/'verify.py'))
    proofs=[]
    for folder,profile in (('installed-full-512','pentagon512'),('installed-full-1024','pentagon1024')):
        path=HERE/folder/profile
        raw=gzip.decompress((path/'trace.txt.gz').read_bytes())
        events=[]
        for match in re.finditer(rb'(?m)^(?:-108|4294967188|0xffffff94)\r?$',raw):
            values=[int(x,0) for x in re.findall(rb'(?m)^(-?\d+|0x[\da-fA-F]+)\r?$',raw[match.end()+1:match.end()+1500])[:129]]
            assert len(values)==129
            events.append(values)
        loading=[row for row in events if row[4]]
        phases=[]
        for row in loading:
            if not phases or phases[-1]!=row[5]:
                phases.append(row[5])
        assert phases==[1]
        assert all(row[7+90:]==[0x3f]*row[6]+[7]*(32-row[6]) for row in loading)
        old=np.frombuffer(gzip.decompress((BASELINE/'verification'/profile/'times.u32.gz').read_bytes()),'<u4')
        new=np.frombuffer(gzip.decompress((path/'times.u32.gz').read_bytes()),'<u4')
        assert len(old)==len(new)==11526111
        assert np.array_equal(old,new)
        old_mute=tools['teardown_mute'](BASELINE/'verification'/profile)
        new_mute=tools['teardown_mute'](path)
        proof=dict(profile=profile,complete_audio=True,complete_ui=False,complete_source_clock_comparison=True,
            source_pulse_times_compared=len(new),every_source_timestamp_exact=True,
            source_clock_sha256=sha(new.tobytes()),maximum_source_clock_change_tstates=0,
            every_source_bit_and_state_check_passed_before_ui_assertion=True,
            actual_capture_reached_terminal=True,captured_stderr_bytes=(path/'stderr.txt').stat().st_size,
            loading_observations=len(loading),loading_phases=phases,
            loading_frames_start=loading[0][3],loading_frames_end=loading[-1][3],
            loading_observed_seconds=(loading[-1][0]-loading[0][0])/3584000,
            gray_attributes_exact=True,previous_mute=old_mute,current_mute=new_mute,
            mute_delta_tstates=new_mute['last_source_to_mute_tstates']-old_mute['last_source_to_mute_tstates'],
            script_sha256=sha((path/'debugger.txt').read_bytes()),
            trace_sha256=sha((path/'trace.txt.gz').read_bytes()),
            scope='Complete actual cold-Fuse source clock; UI acceptance fails because LOADING remains at one dot. Source bit/state checks ran before the failing strict phase assertion in archived verifier f6c97433.',
        )
        (HERE/folder/'phase-failure-report.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
        proofs.append(proof)
    producer=HERE/'attempts'/'frames-phase-control-producers'
    producer.mkdir(parents=True,exist_ok=True)
    source_hashes={}
    for relative in ('audiobook-beeper/verify_stream_trd.py',
                     'audiobook-beeper/experiments/song-snr/evidence/audio-ui-emulator/verify.py'):
        path=ROOT/relative
        data=path.read_bytes()
        source_hashes[relative]=sha(data)
        (producer/(path.name+'.gz')).write_bytes(gzip.compress(data,mtime=0))
    assert source_hashes['audiobook-beeper/verify_stream_trd.py']=='f6c97433bdf3a044ba6b19de9f930187f09d289e77a8e1be477cc98499c6cdd9'
    report=dict(date='2026-10-14',accepted=False,complete_audio=True,complete_ui=False,
        trd_sha256='55216119144fdb4e574bb3525b496d15c528b6f1a826da39c5070c3f57be9e1d',
        executable='C:/Program Files (x86)/Fuse/fuse.exe',
        executable_sha256=sha(Path('C:/Program Files (x86)/Fuse/fuse.exe').read_bytes()),
        source_hashes=source_hashes,profiles=proofs,
        quality_reuse=dict(snr_db=20.25031588676249,remeasured=False,
            reference_trd_sha256='ccab87249b9ce148f3b84cc317d64078a05f51c1e7d5ca7aa9f14958e8fc9074',
            scope='Exact compressed source/model and complete actual relative source pulse clocks match the prior best disk; its existing metric is reused. Explicit post-source mute differs by18T.'),
        decision='Fix the loading-only time source. ROM FRAMES advances only1..2 fields while TR-DOS mostly keeps interrupts disabled; do not relax phase1→2→3 acceptance.',
        reproduction='Run frozen verify.py with the same disk/metadata/packed bytes and explicit installed Fuse. Both complete raw captures are preserved; the saved summarize_phase_failure.py compares clocks without relaunching Fuse.')
    (HERE/'frames-phase-control.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
