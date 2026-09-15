"""Compare history-reuse gate on saved player binaries, without contention."""
import argparse
import json
from pathlib import Path

from benchmark_player_relocation import fixture
from test_packet_lookahead import word


def measure(build,consumed=False,last=False):
    cpu,labels,_,output=fixture(build)
    word(cpu,labels,'frames_remaining',1 if last else 3)
    word(cpu,labels,'block_frame_pointer',output+34 if consumed else output+17)
    word(cpu,labels,'block_end',output+34)
    cpu.write8(labels['ahead_state'],5)
    cpu.pc=labels['ahead_prefetch'];cpu.push(0x5F00);start=cpu.tstates
    # New path stops before the unchanged coroutine setup; old path returns idle.
    while cpu.pc not in (0x5F00,labels['ahead_run']):cpu.step()
    return dict(tstates=cpu.tstates-start,restarts=cpu.pc==labels['ahead_run'])


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--baseline-build',type=Path,required=True)
    p.add_argument('--build',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();rows={}
    for name,kw in [('last_frame',dict(last=True)),('old_packet_pending',{}),('old_block_consumed',dict(consumed=True))]:
        before=measure(args.baseline_build,**kw);after=measure(args.build,**kw)
        rows[name]=dict(previous_tstates=before['tstates'],current_tstates=after['tstates'],
                       delta=after['tstates']-before['tstates'],previous_restarts=before['restarts'],current_restarts=after['restarts'])
    report=dict(baseline_commit='3b96f43',timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        scope='ahead_prefetch entry through RET or to ahead_run entry; CALL excluded',
        exclusions=['IRQ','ULA contention','ROM','disk latency','decoder work after the new gate'],
        assumptions='ahead_state=5; frames_remaining=3 except last_frame=1; block end=history+34; pointer=history+17 or end',
        instruction_sums=dict(common_prefix=79,compare_pointers=55,old_idle_tail=14,
                              new_pending_tail=76,new_restart_tail=94),routines=rows)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
