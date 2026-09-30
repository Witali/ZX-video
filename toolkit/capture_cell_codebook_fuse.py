"""Check every full CB41 window screen in separate real-Fuse publication runs.

The uninterrupted timing run is separate: captures redirect only after the
selected publication, using the existing capture harness, never screen patches.
"""
import argparse,json
from pathlib import Path
import numpy as np
from build_fap3_trd import sha
from build_five_level_test_trd import save
from capture_five_level_fuse import capture
from row_dictionary_video import display_screen
from disk_progress_z80 import reference_screen


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('fuse','trd','metadata','states','work','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.work.mkdir(parents=True,exist_ok=True);m=json.loads(a.metadata.read_bytes())
    with np.load(a.states,allow_pickle=False) as f:states=f['states']
    assert sha(states.tobytes())==m['states_sha256']
    result=dict(complete=False,release=False,trd_sha256=sha(a.trd.read_bytes()),
        states_sha256=sha(states.tobytes()),scope=__doc__,screens=[])
    for i in range(m['frames']):
        screen,record=capture(a.fuse,a.trd,m,i,a.work)
        expected=reference_screen(display_screen(states[m['frame_start']+i].tobytes(),m),i,m['frames'])
        assert screen==expected,('screen differs',i,[k for k,(x,y) in enumerate(zip(screen,expected)) if x!=y][:12])
        record.update(source_state=m['frame_start']+i,compared_bytes=6912,exact=True,screen_hex=screen.hex())
        result['screens'].append(record)
        if i%16==15:print(json.dumps(dict(captured=i+1,total=m['frames'],exact=True)),flush=True)
    result.update(complete=True,full_screens_exact=True,compared_bytes=m['frames']*6912,
        source_sha256_lf={n:sha((Path(__file__).parent/n).read_bytes().replace(b'\r\n',b'\n'))
            for n in ('capture_cell_codebook_fuse.py','capture_five_level_fuse.py','row_dictionary_video.py')})
    save(a.output,result)


if __name__=='__main__':main()
