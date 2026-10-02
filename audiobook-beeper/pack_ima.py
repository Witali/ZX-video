"""Package an already assembled player.bin; never assemble or emit Z80 code.

Run after the standalone pyz80 command in the prepared assembly directory.
Edited binaries are testing candidates until native/Fuse verification is rerun
with an updated symbol map. This packer does not certify playback timing.
"""
import argparse,gzip,json
from pathlib import Path
from pcm_player import TrdFile,basic_line,place_files,calculate_file_start
from ima_codec import require_unclipped


def pack(directory,output):
    meta=json.loads((directory/'player.json').read_bytes())
    blob=(directory/'assembly/player.bin').read_bytes()
    packed=gzip.decompress((directory/'soundtrack.ima.gz').read_bytes())
    if meta.get('uniform_timing') or meta.get('pwm'):
        require_unclipped(packed,meta['initial_predictor'],meta['initial_index'])
    if len(blob)!=meta['resident_reserve']+6912 or len(packed)!=meta['packed_bytes']:
        raise ValueError('binary or payload no longer fits the prepared memory layout')
    basic=b''.join([basic_line(10,b'\xfd \xb0 "32767"'),
        basic_line(20,b'\xf9 \xc0 \xb0 "15619":\xea:\xef "PLAYER" \xaf'),
        basic_line(30,b'\xf9 \xc0 \xb0 "32768"')])
    files=[TrdFile('boot','B',basic,autostart_line=10),TrdFile('PLAYER','C',blob,start=32768)]
    offset=0
    for i,section in enumerate(meta['sections']):
        track,sector=calculate_file_start(files)
        if track*16+sector!=section['sector']:raise ValueError('prepared disk addresses changed')
        files.append(TrdFile(f'IMA{i}','C',packed[offset:offset+section['bytes']],start=section['address']))
        offset+=section['bytes']
    if offset!=len(packed):raise ValueError('unmapped ADPCM data')
    disk,_,_=place_files(files,'IMAPDM');output.write_bytes(disk)
    return disk


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('directory',type=Path);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();pack(args.directory,args.output)
