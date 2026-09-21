"""Compare complete rearranged streams and bootstrap ring bytes to linear disks."""
import argparse
import hashlib
import json
from pathlib import Path
import disk_layout
import fap3_disk_z80 as disk
from test_fap3_disk import DiskCPU
from validate_streaming_player import extract_file,parse_dir


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('build','baseline','output'): p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args(); rows=[]
    for part in range(1,5):
        stem=f'ZX-video-optimized-preview_part{part:02}'
        meta=json.loads((args.build/(stem+'.json')).read_text())
        old=json.loads((args.baseline/(stem+'.json')).read_text())
        image=(args.build/(stem+'.trd')).read_bytes()
        previous=(args.baseline/(stem+'.trd')).read_bytes()
        assert meta['interleaved'] and not old.get('interleaved')
        assert hashlib.sha256(image).hexdigest()==meta['trd_sha256']
        assert hashlib.sha256(previous).hexdigest()==old['trd_sha256']
        first=meta['video_start_sector']; count=meta['video_sectors']
        offsets=list(disk_layout.positions(count,first%16))
        stream=b''.join(image[(first+offset)*256:(first+offset+1)*256] for offset in offsets)
        baseline=previous[old['video_start_sector']*256:(old['video_start_sector']+old['video_sectors'])*256]
        assert stream==baseline and count==old['video_sectors']
        player=extract_file(image,next(entry for entry in parse_dir(image) if entry[0]=='PLAYER'))
        cpu=DiskCPU(player,image)
        while cpu.pc!=disk.DRIVER:
            cpu.step()
            assert cpu.steps<3000000,'bootstrap stalled'
        ring=b''.join(bytes(cpu.banks[bank]) for bank in (0,1,3,4))
        assert ring[:min(count,256)*256]==stream[:65536]
        assert cpu.read8(0x5cf5)==meta['initial_cached_track']
        rows.append(dict(part=part,logical_stream_exact=True,bootstrap_ring_exact=True,
            bootstrap_track_exact=True,rom_mocked=True,logical_sectors=count,
            physical_sectors=meta['video_physical_sectors'],layout_padding_sectors=meta['layout_padding_sectors'],
            used_sectors=meta['used_sectors'],previous_used_sectors=old['used_sectors'],
            stream_sha256=hashlib.sha256(stream).hexdigest()))
    args.output.write_text(json.dumps(rows,indent=2)+'\n'); print(json.dumps(rows))


if __name__=='__main__': main()
