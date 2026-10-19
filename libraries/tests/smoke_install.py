"""Isolated smoke check: python -I smoke_install.py INSTALLED_DIR PACKAGE OUTPUT [ENCODER]."""
import importlib
import json
from pathlib import Path
import runpy
import sys

installed=Path(sys.argv[1]).resolve();name=sys.argv[2];destination=Path(sys.argv[3]).resolve()
encoder=sys.argv[4] if len(sys.argv)>4 else None
sys.path.insert(0,str(installed))
package=importlib.import_module(name)
assert Path(package.__file__).is_relative_to(installed)
assert not any(n.startswith(('toolkit','cv2','numpy')) for n in sys.modules)
seed=b'Independent project\n';raw=seed*32
payload=(package.encode(raw,[package.Token(0,len(seed)),package.Token(len(seed),len(raw)-len(seed),len(seed))])
         if name=='zx0' else package.encode(raw,[(len(seed),len(raw)-len(seed),len(seed))]))
assert package.decompress(payload,limit=len(raw))==raw
build=importlib.import_module(name+'.resumable').build
export=importlib.import_module(name+'.export').export
kwargs=dict(prefix=0x5000,prefix_limit=0x5400,core=0x6000,core_limit=0x6400,stack=0x4ff0,output_base=0xa000)
regions,labels,metadata=build(**kwargs)
export(destination/'custom',regions,labels,metadata)
assert (destination/'custom/LICENSE').is_file()
sys.argv=[name,'build','--output',str(destination/'cli')]
if name=='lzsa':sys.argv+=['--streaming','--direct-header']
runpy.run_module(name+'.__main__',run_name='__main__')
assert (destination/'cli/decoder.asm').is_file()
resident=[]
for variant in (('fast','small') if name=='lzsa' else ('standard','turbo','fast','mega')):
    block_build=importlib.import_module(name+'.block').build
    regions,labels,metadata=block_build(variant,core=0x8000,core_limit=0x8400)
    assert metadata['one_shot'] and metadata['state_bytes']==metadata['private_stack_bytes']==0
    assert 'input_pointer' not in labels and 'slice_until' not in labels
    at=destination/('block-'+variant)
    export(at,regions,labels,metadata)
    rebuilt=[]
    for line in (at/'decoder.asm').read_text().splitlines():
        if line.startswith('org '):rebuilt.append((int(line[5:],16),bytearray()))
        elif line.startswith('db '):rebuilt[-1][1].extend(int(x[1:],16) for x in line[3:].split(','))
    assert [(address,bytes(data)) for address,data in rebuilt]==regions
    assert 'caller stack' in (at/'decoder.asm').read_text()
    resident.append(dict(variant=variant,bytes=sum(len(data) for _,data in regions),exact_export=True))
if name=='lzsa':
    assert (installed/'lzsa/asm/unlzsa2_small.asm').is_file()
    sys.argv=[name,'build','--profile','small-block','--output',str(destination/'small-cli')]
else:
    assert (installed/'zx0/asm/dzx0_mega.asm').is_file()
    sys.argv=[name,'build','--variant','fast-block','--output',str(destination/'fast-block-cli')]
runpy.run_module(name+'.__main__',run_name='__main__')
fast_jumps=[]
for variant in (('fast',) if name=='lzsa' else ('standard','turbo','mega','fast')):
    block_build=importlib.import_module(name+'.block').build
    regions,labels,metadata=block_build(variant,fast_jumps=True)
    at=destination/('fast-jumps-'+variant)
    export(at,regions,labels,metadata)
    rebuilt=[]
    for line in (at/'decoder.asm').read_text().splitlines():
        if line.startswith('org '):rebuilt.append((int(line[5:],16),bytearray()))
        elif line.startswith('db '):rebuilt[-1][1].extend(int(x[1:],16) for x in line[3:].split(','))
    assert [(address,bytes(data)) for address,data in rebuilt]==regions
    assert metadata['fast_jumps'] and '12 -> 10 T' in (at/'decoder.asm').read_text()
    fast_jumps.append(dict(variant=variant,bytes=sum(len(data) for _,data in regions),exact_export=True))
sys.argv=([name,'build','--profile','fast-block'] if name=='lzsa' else
          [name,'build','--variant','standard'])+['--fast-jumps','--output',str(destination/'fast-jumps-cli')]
runpy.run_module(name+'.__main__',run_name='__main__')
assert json.loads((destination/'fast-jumps-cli/metadata.json').read_text())['fast_jumps']
tuned=[]
for variant in ('fast',):
    block_build=importlib.import_module(name+'.block').build
    regions,labels,metadata=block_build(variant,branch_tuned=True)
    at=destination/'branch-tuned'
    export(at,regions,labels,metadata)
    rebuilt=[]
    for line in (at/'decoder.asm').read_text().splitlines():
        if line.startswith('org '):rebuilt.append((int(line[5:],16),bytearray()))
        elif line.startswith('db '):rebuilt[-1][1].extend(int(x[1:],16) for x in line[3:].split(','))
    assert [(address,bytes(data)) for address,data in rebuilt]==regions
    assert metadata['branch_tuned'] and metadata['branch_changes']
    tuned.append(dict(variant=variant,bytes=sum(len(data) for _,data in regions),exact_export=True))
sys.argv=([name,'build','--profile','fast-block'] if name=='lzsa' else
          [name,'build','--variant','fast-block'])+['--branch-tuned','--output',str(destination/'branch-tuned-cli')]
runpy.run_module(name+'.__main__',run_name='__main__')
assert json.loads((destination/'branch-tuned-cli/metadata.json').read_text())['branch_tuned']
assert not any(n.startswith(('toolkit','cv2','numpy')) for n in sys.modules)
if encoder:
    assert package.decompress(package.compress(raw,executable=encoder),limit=len(raw))==raw
report=dict(package=name,independent_wheel=True,custom_layout=True,cli_export=True,
            resources=True,exact_round_trip=True,external_encoder=bool(encoder),resident_profiles=resident,
            fast_jump_profiles=fast_jumps,branch_tuned_profiles=tuned)
(destination/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report))
