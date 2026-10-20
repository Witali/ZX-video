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
literal_prefix=[]
if name=='zx0':
    for is_resident in (True,False):
        builder=importlib.import_module('zx0.'+('block' if is_resident else 'resumable')).build
        profile=builder(core=0x6000,core_limit=0x6400,literal_prefix=True,branch_tuned=True)
        at=destination/('literal-prefix-'+('block' if is_resident else 'coroutine'))
        export(at,*profile)
        rebuilt=[]
        for line in (at/'decoder.asm').read_text().splitlines():
            if line.startswith('org '):rebuilt.append((int(line[5:],16),bytearray()))
            elif line.startswith('db '):rebuilt[-1][1].extend(int(x[1:],16) for x in line[3:].split(','))
        assert [(address,bytes(data)) for address,data in rebuilt]==profile[0]
        sys.argv=['zx0','build','--variant','fast-block' if is_resident else 'fast',
                  '--literal-prefix','--branch-tuned','--core','0x6000','--core-limit','0x6400',
                  '--output',str(at/'cli')]
        runpy.run_module('zx0.__main__',run_name='__main__')
        assert json.loads((at/'cli/metadata.json').read_text())['literal_prefix']
        literal_prefix.append(dict(resident=is_resident,bytes=sum(len(data) for _,data in profile[0]),exact_export=True))
tail_refill=[]
if name=='zx0':
    for resident_mode in (False,True):
        builder=block_build if resident_mode else build
        regions,labels,metadata=builder(branch_tuned=True,inline_tail_refill=True)
        at=destination/('tail-refill-'+('block' if resident_mode else 'coroutine'))
        export(at,regions,labels,metadata)
        assert metadata['inline_tail_refill'] and metadata['tail_refill_code_delta_bytes']==3
        assert 'save 18/5 T' in (at/'decoder.asm').read_text()
        tail_refill.append(dict(resident=resident_mode,bytes=sum(len(blob) for _,blob in regions)))
    sys.argv=[name,'build','--variant','fast-block','--branch-tuned','--inline-tail-refill',
              '--output',str(destination/'tail-refill-cli')]
    runpy.run_module(name+'.__main__',run_name='__main__')
    assert json.loads((destination/'tail-refill-cli/metadata.json').read_text())['inline_tail_refill']
combined_profiles=[]
for is_resident in (True,False):
    builder=importlib.import_module(name+'.'+('block' if is_resident else 'resumable')).build
    options=(dict(branch_tuned=True,literal_prefix=True,inline_tail_refill=True) if name=='zx0' else
             dict(branch_tuned=True,fast_jumps=True,nibble_prefill=True))
    profile=builder(core=0x6000,core_limit=0x6400,**options)
    at=destination/('combined-'+('block' if is_resident else 'coroutine'))
    export(at,*profile)
    rebuilt=[]
    for line in (at/'decoder.asm').read_text().splitlines():
        if line.startswith('org '):rebuilt.append((int(line[5:],16),bytearray()))
        elif line.startswith('db '):rebuilt[-1][1].extend(int(x[1:],16) for x in line[3:].split(','))
    assert [(address,bytes(data)) for address,data in rebuilt]==profile[0]
    if name=='zx0':
        cli=['--variant','fast-block' if is_resident else 'fast','--literal-prefix','--inline-tail-refill']
    else:
        cli=(['--profile','fast-block'] if is_resident else [])+['--fast-jumps','--nibble-prefill']
    sys.argv=[name,'build',*cli,'--branch-tuned','--core','0x6000','--core-limit','0x6400','--output',str(at/'cli')]
    runpy.run_module(name+'.__main__',run_name='__main__')
    combined_profiles.append(dict(resident=is_resident,bytes=sum(len(data) for _,data in profile[0]),exact_export=True,options=options))
wide=[]
if name=='lzsa':
    for variant in ('wide','wide-shared'):
        regions,labels,metadata=block_build(variant,core=0x8000,core_limit=0xb000)
        assert metadata['service_memory_bytes']==metadata['code_bytes']+6<=10000
        at=destination/variant
        export(at,regions,labels,metadata)
        sys.argv=[name,'build','--profile',variant+'-block','--core','0x8000',
                  '--core-limit','0xb000','--output',str(destination/(variant+'-cli'))]
        runpy.run_module(name+'.__main__',run_name='__main__')
        cli=json.loads((destination/(variant+'-cli')/'metadata.json').read_text())
        assert cli['regions']==json.loads((at/'metadata.json').read_text())['regions']
        rebuilt=[]
        for line in (at/'decoder.asm').read_text().splitlines():
            if line.startswith('org '):rebuilt.append((int(line[5:],16),bytearray()))
            elif line.startswith('db '):rebuilt[-1][1].extend(int(x[1:],16) for x in line[3:].split(','))
        assert [(address,bytes(data)) for address,data in rebuilt]==regions
        wide.append(dict(variant=variant,code_bytes=metadata['code_bytes'],
                         service_memory_bytes=metadata['service_memory_bytes'],exact_export=True))
    for shared in (False,True):
        variant='wide-shared-coroutine' if shared else 'wide-coroutine'
        builder=importlib.import_module(name+'.wide_coroutine').build
        regions,labels,metadata=builder(shared_literals=shared)
        assert metadata['service_memory_bytes']==metadata['code_bytes']+16+4<=10000
        at=destination/variant
        export(at,regions,labels,metadata)
        sys.argv=[name,'build','--profile',variant,'--core','0x8000','--core-limit','0xb000',
                  '--output',str(destination/(variant+'-cli'))]
        runpy.run_module(name+'.__main__',run_name='__main__')
        cli=json.loads((destination/(variant+'-cli')/'metadata.json').read_text())
        assert cli['regions']==json.loads((at/'metadata.json').read_text())['regions']
        wide.append(dict(variant=variant,code_bytes=metadata['code_bytes'],
                         service_memory_bytes=metadata['service_memory_bytes'],exact_export=True))
assert not any(n.startswith(('toolkit','cv2','numpy')) for n in sys.modules)
mega_tuned=[]
if name=='zx0':
    for fast in (False,True):
        regions,labels,metadata=block_build('mega',fast_jumps=fast,mega_tuned=True)
        at=destination/('mega-tuned-'+str(fast))
        export(at,regions,labels,metadata)
        assert metadata['code_bytes']==669+fast and metadata['mega_tuned']
        assert 'No coroutine ABI' in (at/'decoder.asm').read_text()
        mega_tuned.append(dict(fast_jumps=fast,bytes=metadata['code_bytes']))
    sys.argv=[name,'build','--variant','mega','--mega-tuned','--fast-jumps',
              '--core','0x8000','--core-limit','0x8400','--output',str(destination/'mega-tuned-cli')]
    runpy.run_module(name+'.__main__',run_name='__main__')
    assert json.loads((destination/'mega-tuned-cli/metadata.json').read_text())['mega_tuned']
maximum=[]
if name=='zx0':
    maximum_build=importlib.import_module(name+'.maximum').build
    for cap in (31,63,127,227,228):
        irq_code,irq_stack=(3,2) if cap==228 else (13,6)
        regions,labels,metadata=maximum_build(prefix_cap=cap,irq_code_bytes=irq_code,irq_stack_bytes=irq_stack)
        at=destination/('maximum-'+str(cap))
        export(at,regions,labels,metadata)
        rebuilt=[]
        for line in (at/'decoder.asm').read_text().splitlines():
            if line.startswith('org '):rebuilt.append((int(line[5:],16),bytearray()))
            elif line.startswith('db '):rebuilt[-1][1].extend(int(x[1:],16) for x in line[3:].split(','))
        assert [(address,bytes(data)) for address,data in rebuilt]==regions
        assert metadata['service_memory_bytes']==metadata['code_bytes']+4+irq_code+irq_stack<=10000
        maximum.append(dict(prefix_cap=cap,bytes=metadata['code_bytes'],
                            irq_code_bytes=irq_code,irq_extra_stack_bytes=irq_stack,
                            service_with_selected_irq_bytes=metadata['service_memory_bytes'],exact_export=True))
    sys.argv=[name,'build','--variant','maximum','--irq-code-bytes','3','--irq-stack-bytes','2',
              '--output',str(destination/'maximum-cli')]
    runpy.run_module(name+'.__main__',run_name='__main__')
    assert json.loads((destination/'maximum-cli/metadata.json').read_text())['service_memory_bytes']==9995
    assert not any(n.startswith(('toolkit','tests','cv2','numpy')) for n in sys.modules)
assert not any(n.startswith(('toolkit','cv2','numpy')) for n in sys.modules)
if encoder:
    assert package.decompress(package.compress(raw,executable=encoder),limit=len(raw))==raw
report=dict(package=name,independent_wheel=True,custom_layout=True,cli_export=True,
            resources=True,exact_round_trip=True,external_encoder=bool(encoder),resident_profiles=resident,
            fast_jump_profiles=fast_jumps,branch_tuned_profiles=tuned,literal_prefix_profiles=literal_prefix,
            inline_tail_refill_profiles=tail_refill,combined_profiles=combined_profiles,wide_profiles=wide,
            mega_tuned_profiles=mega_tuned,maximum_profiles=maximum)
(destination/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report))
