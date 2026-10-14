"""Complete playback through Pentagon1024 bank32; test512K refill too."""
import argparse
import gzip
import json
from pathlib import Path

from build_stream_trd import build
from verify_stream_trd import native_check,fuse_check
from verify_pcm import save


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--song',type=Path,required=True)
    p.add_argument('--cover',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--fuse',type=Path,required=True)
    p.add_argument('--captured',action='store_true')
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    song=gzip.decompress((a.song/'soundtrack.ima.gz').read_bytes())
    assert len(song)<512000
    packed=song+bytes(512000-len(song))
    # Use the non-silent song in ordinary banks, then append silence. An
    # aliased high selector would overwrite earlier song bytes, so a falsely
    # accepted high bank fails the full-source bit/state comparison too.
    disk,meta=build(packed,out/'assembly',a.cover.read_bytes())
    if a.captured:
        assert (out/'audio.trd').read_bytes()==disk
        assert json.loads((out/'player.json').read_bytes())==meta
    else:
        (out/'audio.trd').write_bytes(disk)
        (out/'soundtrack.ima.gz').write_bytes(gzip.compress(packed,mtime=0));save(out/'player.json',meta)
    verify=out/'verification';verify.mkdir(exist_ok=True)
    results=[]
    for profile in ('pentagon1024','pentagon512'):
        native=native_check(disk,meta,packed,profile,out=verify/f'native-{profile}.json')
        actual=fuse_check(out/'audio.trd',meta,packed,profile,verify/profile,a.fuse,captured=a.captured)
        results.append(dict(profile=profile,native=native,fuse=actual));print('Complete: '+profile,flush=True)
    save(verify/'report.json',dict(complete=True,profiles=results,trd_sha256=meta['trd_sha256']))


if __name__=='__main__':main()
