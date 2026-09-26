"""Run complete cold playback of real integrated TRDs, without RAM patches."""
import argparse
import json
from pathlib import Path
import subprocess
import sys


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('fuse','directory','raw-directory','states','output'):
        p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    for part in (1,2,3):
        stem=f'ZX-video-huffman-preview_part{part:02}'
        m=json.loads((a.directory/(stem+'.json')).read_bytes())
        if not m.get('integrated_slot_queue') or m.get('slot_queue_fixture'):
            raise ValueError('expected a real integrated bootstrap')
        command=[sys.executable,str(Path(__file__).with_name('measure_fap3_fuse.py')),
            '--fuse',str(a.fuse),'--trd',str(a.directory/(stem+'.trd')),
            '--metadata',str(a.directory/(stem+'.json')),'--raw',str(a.raw_directory/f'volume-{part}.raw'),
            '--states',str(a.states),'--output',str(a.output/f'part{part:02}.json'),'--timeout','300']
        completed=subprocess.run(command,capture_output=True,text=True)
        (a.output/f'part{part:02}.log').write_text(completed.stdout+completed.stderr,encoding='utf-8')
        completed.check_returncode()
        report=json.loads((a.output/f'part{part:02}.json').read_bytes())
        if not report['complete'] or report['errors'] or report['failure']:
            raise ValueError(('incomplete playback',part))
        print(json.dumps({k:report[k] for k in ('part','complete','frames','audio_underruns',
            'nominal_late_frames','max_late_fields','runtime_sectors_checked','bad_actual_intervals')}),flush=True)


if __name__=='__main__':main()
