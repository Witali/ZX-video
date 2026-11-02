"""Compare complete native audio CPU costs with an authenticated old build.

The instruction formulas are in libraries/Z80_TIMINGS.md and README.md.
Field histograms include the normal 41-T audio caller. choose includes its
first stream row, mute, bank selection and RET; its external CALL is 17 T.
ULA contention, IRQ/HALT, UI and ROM/disk costs stay separate.
"""
import argparse
import json
from pathlib import Path

from build import ROOT, sha
from verify import Machine, boot


def sum_histogram(values):
    return sum(int(tstates)*count for tstates,count in values.items())


def measure(folder):
    meta = json.loads((folder/'build.json').read_text())
    native = json.loads((folder/'native.json').read_text())
    blob = (folder/'assembly/player.bin').read_bytes()
    disk = (folder/'ZX-Music-Menu.trd').read_bytes()
    assert sha(blob)==native['player_sha256']==meta['player_sha256']
    assert sha(disk)==meta['trd_sha256']
    result = []
    for index,song in enumerate(native['songs']):
        machine = Machine(blob,meta['player_labels'])
        boot(machine,disk)
        machine.byte('selected',index)
        initialization = machine.call('choose')
        fields = sum_histogram(song['audio_service_with_caller_tstates'])
        result.append(dict(song=song['song'],choose_body_with_tick_zero_tstates=initialization,
            subsequent_fields_audio_with_caller_tstates=fields,
            audio_with_required_choose_and_call_tstates=fields+initialization+17))
    return meta,native,result


def compare(output, baseline):
    old,old_native,before = measure(baseline)
    new,new_native,after = measure(output)
    report = dict(baseline_trd_sha256=old['trd_sha256'],trd_sha256=new['trd_sha256'],
        scope=__doc__,startup_only_autoplay_call_and_jump_tstates=27,
        previous_autoplay_control_tstates=0,autoplay_control_delta_tstates=27,
        first_autoplay_foreground_native_tstates=new_native['songs'][0]['autoplay_first_field_tstates'],
        per_call_components=dict(held_audio_with_caller=[92,92,0],
            zero_write_delta_record=[1452,1452,0],one_write_delta_record=[1616,1616,0],
            fourteen_write_delta_record=[3748,3748,0],mute=[1164,1164,0],
            irq_body=[18,18,0],im2_entry_and_body=[37,37,0],
            ordinary_byte_reader=[75,75,0],extra_bank_crossing=[185,185,0]),songs=[])
    for left,right in zip(before,after):
        assert left['song']==right['song']
        report['songs'].append(dict(song=left['song'],before=left,after=right,
            audio_cpu_delta_tstates=right['audio_with_required_choose_and_call_tstates']-left['audio_with_required_choose_and_call_tstates']))
    (output/'timing-comparison.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(report,indent=2))
    return report


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'build/music-menu-autoplay')
    parser.add_argument('--baseline-output',type=Path,required=True)
    args = parser.parse_args()
    compare(args.output,args.baseline_output)
