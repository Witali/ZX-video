from pathlib import Path
import ast,gzip,json,re,hashlib
names=('ima3-direct-player.asm','ima3_direct_player.py')
rows=[]
for name in names:
    p=Path('audiobook-beeper')/name;before=p.read_bytes();after=re.sub(rb'[ \t]+(?=\r?$)',b'',before,flags=re.M).rstrip(b'\r\n')+b'\n'
    if name.endswith('.py'):assert ast.dump(ast.parse(before))==ast.dump(ast.parse(after))
    p.write_bytes(after);rows.append(dict(file=name,before=hashlib.sha256(before).hexdigest(),after=hashlib.sha256(after).hexdigest()))
from ima3_direct_player import build_disk
root=Path('.tmp/ima3-automatic-final');m=json.loads((root/'player.json').read_bytes());packed=gzip.decompress((root/'soundtrack.ima.gz').read_bytes())
disk,meta=build_disk(packed,Path('.tmp/ima3-cleanup-binary-check'),m['model'],m['hot_indices'],m['loop_idle_pairs'],m['loop_idle_pad_tstates'])
assert disk==(root/'audiobook-preview.trd').read_bytes()
report=dict(complete=True,python_ast_unchanged=True,entire_trd_byte_identical=True,trd_sha256=hashlib.sha256(disk).hexdigest(),scope='Whitespace-only source cleanup after the measured run; archived producer snapshots retain the measured raw bytes',source_changes=rows)
p=Path('audiobook-beeper/experiments/ima-3bit-direct/source-cleanup-check.json');p.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps(report))
