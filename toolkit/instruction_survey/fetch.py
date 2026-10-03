"""Download selected archive images locally; retain URLs and hashes, not binaries, in Git."""
from pathlib import Path
import argparse
import concurrent.futures
import hashlib
import json
import urllib.request
import zipfile
import io

SOURCES = {
    'dizzy': '/gamez/d/DIZZY.ZIP',
    'elite': '/gamez/e/ELITE.ZIP',
    'exolon': '/gamez/e/EXLN_FM.zip',
    'rtype': '/gamez/r/R-TYPE.ZIP',
    'renegade': '/gamez/r/RENEG128.ZIP',
    'commander': '/system/FCOMM5_5.zip',
    'aeon': '/demoz/demozrus/AEON.ZIP',
    'demo63': '/demoz/demozrus/63_BIT!.ZIP',
    'beta': '/system/BC5_02.zip',
}
EVIDENCE = Path(__file__).parent/'evidence/summary.json'
EXPECTED = ({x['name']:x['source'] for x in json.loads(EVIDENCE.read_text())['cases']}
            if EVIDENCE.exists() else {})


def fetch(item, folder):
    name, relative = item
    url = 'https://trd.speccy.cz' + relative
    raw = urllib.request.urlopen(url, timeout=60).read()
    expected = EXPECTED.get(name)
    if expected and hashlib.sha256(raw).hexdigest() != expected['archive_sha256']:
        raise ValueError(f'{name}: archive changed; cannot reproduce the recorded version')
    (folder/(name+'.zip')).write_bytes(raw)
    files = []
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        for member in z.namelist():
            if Path(member).suffix.lower() not in ('.trd', '.scl'):
                continue
            data = z.read(member)
            filename = name + '-' + Path(member).name
            if expected:
                original = next(x for x in expected['files'] if x['member'] == member)
                assert hashlib.sha256(data).hexdigest() == original['sha256']
            (folder/filename).write_bytes(data)
            files.append(dict(file=filename, member=member, bytes=len(data),
                              sha256=hashlib.sha256(data).hexdigest()))
    print(name, files, flush=True)
    return dict(name=name, url=url, archive_sha256=hashlib.sha256(raw).hexdigest(), files=files)


if __name__ == '__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('folder', type=Path)
    args=ap.parse_args()
    args.folder.mkdir(parents=True,exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(4) as ex:
        rows=list(ex.map(lambda item: fetch(item,args.folder), SOURCES.items()))
    (args.folder/'manifest.json').write_text(json.dumps(rows,indent=2)+'\n')
