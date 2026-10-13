"""Create a complete tiny raw LZSA2 example after installing this library."""
from pathlib import Path
import sys
from lzsa import encode, decompress
from lzsa.resumable import build
from lzsa.export import export

destination=Path(sys.argv[1])
seed=b'LZSA2 library sample.\n';raw=seed*32
payload=encode(raw,[(len(seed),len(raw)-len(seed),len(seed))])
assert decompress(payload,limit=len(raw))==raw
export(destination,*build())
(destination/'sample.raw').write_bytes(raw)
(destination/'sample.lzsa').write_bytes(payload)
(destination/'constants.inc').write_text(f'raw_length equ {len(raw)}\n',encoding='utf-8')
(destination/'example.asm').write_bytes(Path(__file__).with_name('example.asm').read_bytes())
print(destination/'example.asm')
