"""Replay every selected block through Fast and the real sector/carry producer.

Input is the actual built TRD. ROM is mocked and the field clock is frozen;
this is a complete native byte/timing check, not actual publication timing.
"""
import argparse
import json
from pathlib import Path

from benchmark_bank_local_zx0 import disk_blocks
from benchmark_faster_zx0 import fixture
from benchmark_inplace_streaming import finish
from build_fap3_trd import sha

ROOT = Path(__file__).parent


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('directory','build','probe','output'): p.add_argument('--'+key,type=Path,required=True)
    args = p.parse_args()
    if args.output.exists(): p.error('refuse to overwrite evidence')
    build = json.loads(args.build.read_bytes()); probe = json.loads(args.probe.read_bytes())
    reference = json.loads((ROOT/'faster_zx0_cpu.json').read_bytes())
    if not build['complete'] or not probe['complete']: raise ValueError('complete inputs required')
    report = dict(complete=False,release=False,scope=__doc__,baseline_commit='2881667',volumes=[])
    def save(): args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    try:
        for part in (1,2,3):
            m,stream,blocks = disk_blocks(args.directory,part)
            built = build['volumes'][part-1]
            if sha(stream)!=built['stream_sha256'] or m['trd_sha256']!=built['trd_sha256']:
                raise ValueError('different built stream')
            h,layout = fixture(stream,m['video_start_sector'],'fast')
            v = dict(part=part,trd_sha256=m['trd_sha256'],stream_sha256=sha(stream),
                video_start_sector=m['video_start_sector'],layout=layout,blocks=h.results)
            report['volumes'].append(v)
            for index,(payload,raw) in enumerate(blocks):
                name = built['fast_token_selection']['names'][index]
                expected = probe['volumes'][part-1]['blocks'][index]['variants'][name]
                row = h.block(payload,raw,index)
                if row['payload_sha256']!=expected['payload_sha256'] or row['decoder_tstates']!=expected['decoder_tstates']:
                    raise AssertionError('selected stream differs from measured native option')
                old = reference['volumes'][part-1]['variants']['fast']['blocks'][index]
                row['decoder_delta_tstates'] = row['decoder_tstates']-old['decoder_tstates']
                row['producer_delta_tstates'] = row['producer_tstates']-old['producer_tstates']
                if index%16==0:
                    save(); print(f'disk {part}: {index+1}/{len(blocks)} selected producer/decoder blocks exact',flush=True)
            v['summary'] = finish(h)
            save()
        keys = ('producer_tstates','decoder_tstates','total_tstates','sector_reads','carry_copy_bytes')
        report['totals'] = {k:sum(v['summary'][k] for v in report['volumes']) for k in keys}
        report['baseline_totals'] = {k:reference['totals']['fast'][k] for k in keys}
        report['deltas'] = {k:report['totals'][k]-report['baseline_totals'][k] for k in keys}
        report['complete'] = True
    except Exception as exc: report['failure'] = repr(exc); raise
    finally:
        report['references'] = {args.build.name:sha(args.build.read_bytes()),args.probe.name:sha(args.probe.read_bytes()),
            'faster_zx0_cpu.json':sha((ROOT/'faster_zx0_cpu.json').read_bytes())}
        names = ('benchmark_fast_token_player.py','benchmark_inplace_streaming.py','benchmark_inplace_slot.py',
                 'faster_zx0.py','inplace_slot_input_z80.py','verify_streaming_zx0_input.py')
        report['source_sha256_lf'] = {n:sha((ROOT/n).read_bytes().replace(b'\r\n',b'\n')) for n in names}
        save()
    print(json.dumps(dict(totals=report['totals'],deltas=report['deltas'])),flush=True)


if __name__=='__main__': main()
