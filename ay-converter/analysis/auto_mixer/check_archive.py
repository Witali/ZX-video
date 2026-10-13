"""Authenticate the bounded audio evidence and the common CLI output."""
import gzip
import hashlib
import json
from pathlib import Path


def main():
    root=Path(__file__).with_name('evidence')
    manifest=json.loads((root/'manifest.json').read_bytes())
    for name,expected in manifest['files'].items():
        data=(root/name).read_bytes()
        assert len(data)==expected['bytes'],name
        assert hashlib.sha256(data).hexdigest()==expected['sha256'],name
    movie=(root/'public-movie-cli/work/ay.bin').read_bytes()
    audio=gzip.decompress((root/'public-movie-as-audio/soundtrack.ay9.gz').read_bytes())
    assert movie==audio and len(movie)==25*9
    for case in ('entertainer','o-henry','movie-430'):
        proof=json.loads((root/case/'auto/fuse.json').read_bytes())
        assert proof['complete'] and proof['cold_boot'] and proof['every_register_exact']
        assert proof['ticks']==800 and not proof['missing_or_duplicate_fields']
    report=json.loads((root/'public-audio-cli/report.json').read_bytes())
    for name,expected in report['producer_sources_sha256_lf'].items():
        data=(root/'public-audio-cli/producers'/name).read_bytes().replace(b'\r\n',b'\n')
        assert hashlib.sha256(data).hexdigest()==expected,name
    print(f"Authenticated {len(manifest['files'])} files; common CLI states and three cold Fuse auditions pass")


if __name__=='__main__':main()
