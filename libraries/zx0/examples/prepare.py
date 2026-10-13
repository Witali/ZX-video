"""Create a complete tiny ZX0 Z80 example; run after installing this library."""
from pathlib import Path
import sys
from zx0 import Token, encode, decompress
from zx0.resumable import build
from zx0.export import export

destination=Path(sys.argv[1])
seed=b'ZX0 library sample.\n';raw=seed*32
payload=encode(raw,[Token(0,len(seed)),Token(len(seed),len(raw)-len(seed),len(seed))])
assert decompress(payload,limit=len(raw))==raw
export(destination,*build('fast'))
(destination/'sample.raw').write_bytes(raw)
(destination/'sample.zx0').write_bytes(payload)
(destination/'constants.inc').write_text(f'raw_length equ {len(raw)}\n',encoding='utf-8')
(destination/'example.asm').write_bytes(Path(__file__).with_name('example.asm').read_bytes())
print(destination/'example.asm')
