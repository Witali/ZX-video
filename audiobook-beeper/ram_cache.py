"""Shared host metadata for the adaptive loader; legacy builders remain explicit."""
from pathlib import Path
import re

STATE=0x5B70
WORKER=0xB800
IMA4_BYTES=5*16384+7936
IMA3_BYTES=5*16383+7935
PROFILES={
    '128':dict(mode=0,ram_kib=128,pages=0,cpu=3546900,field=70908,ima4_extra=0,ima3_extra=0),
    'scorpion':dict(mode=1,ram_kib=256,pages=8,cpu=3500000,field=69888,ima4_extra=0,ima3_extra=0),
    'pentagon512':dict(mode=2,ram_kib=512,pages=24,cpu=3584000,field=71680,ima4_extra=26,ima3_extra=18),
    'pentagon1024':dict(mode=3,ram_kib=1024,pages=56,cpu=3584000,field=71680,ima4_extra=26,ima3_extra=18),
}


def enabled(model):return bool(model.get('extended_ram',False))


def copy_worker(work):
    source=Path(__file__).with_name('ram-cache.asm')
    (Path(work)/source.name).write_bytes(source.read_bytes())


def pack_controller(raw):
    """Bounded greedy parse for this2-KiB loader, independently decoded.

    This only compresses immutable controller code/header. It never touches
    audio or chooses video compression parameters. The shared LZSA2 serializer
    preserves canonical format/EOF, with no new executable dependency.
    """
    import codec_libraries
    from lzsa.oracle import encode
    from lzsa.codec import decompress
    positions={};matches=[];at=0
    while at<len(raw)-2:
        key=raw[at:at+3];best=(0,0)
        for previous in reversed(positions.get(key,[])[-64:]):
            length=3
            while at+length<len(raw) and raw[previous+length]==raw[at+length]:length+=1
            if length>best[0]:best=(length,at-previous)
        advance=best[0] if best[0]>=3 else 1
        if advance>1:matches.append((at,advance,best[1]))
        for i in range(at,min(at+advance,len(raw)-2)):
            positions.setdefault(raw[i:i+3],[]).append(i)
        at+=advance
    payload=encode(raw,matches)
    assert decompress(payload,limit=len(raw))==raw
    return payload


def write_decoder(work):
    """Normalize upstream forward LZSA2 syntax for pyz80, retaining its notice.

    Colon-separated instructions/local labels are syntax only. Select the
    original default forward/non-unrolled branches; do not emit opcodes from
    Python. Native round-trip tests must prove the resulting decoder.
    """
    root=Path(__file__).resolve().parents[1]
    source=root/'libraries/lzsa/src/lzsa/asm/unlzsa2_fast.asm'
    original=source.read_text(encoding='utf-8')
    head,body=original.split('@DecompressLZSA2:',1)
    comments=[line for line in head.splitlines() if line.lstrip().startswith(';')]
    lines=['; Syntax-adapted forward LZSA2 decoder; original default instructions.',*comments]
    parent='DecompressLZSA2';lines.append(parent+':')
    operations={'ld','scf','exa','jr','jp','ret','add','adc','sbc','sub','cp','or','and','xor',
        'inc','dec','push','pop','rrca','rlca','rr','rl','ldi','ldir','ex','call','next_hl','add_offset','copy1','copybc'}
    active=True;stack=[]
    for raw in body.splitlines():
        line=raw.split(';',1)[0].strip()
        if not line:continue
        if line.upper().startswith('IFDEF'):
            stack.append(active);active=False;continue
        if line.upper().startswith('IFNDEF'):
            stack.append(active);continue
        if line.upper()=='ELSE':active=stack[-1] and not active;continue
        if line.upper()=='ENDIF':active=stack.pop();continue
        if not active:continue
        first=line.split()[0].rstrip(':')
        if first.lower() not in operations:
            rest=line[len(first):].lstrip(': \t')
            name=parent+'_'+first[1:] if first.startswith('.') else first
            if not first.startswith('.'):parent=first
            if rest.upper().startswith('EQU'):
                expression,separator,following=rest.partition(':')
                lines.append(name+': '+expression.strip());line=following.strip()
            else:
                lines.append(name+':');line=rest
        for instruction in line.split(':'):
            instruction=instruction.strip()
            if not instruction:continue
            instruction=re.sub(r'\b(\w+)\.(\w+)\b',r'\1_\2',instruction)
            instruction=re.sub(r'(?<![\w])\.([A-Za-z_]\w*)',lambda m:parent+'_'+m[1],instruction)
            instruction=re.sub(r'#([\da-fA-F]+)',r'0x\1',instruction)
            instruction=re.sub(r'%([01]+)',r'0b\1',instruction)
            replacements={'NEXT_HL':'INC HL','ADD_OFFSET':'ADD HL,DE','COPY1':'LDI','COPYBC':'LDIR','EXA':"EX AF,AF'"}
            instruction=replacements.get(instruction.upper(),instruction)
            if re.match(r'(?i)^add\s+\(hl\)$',instruction):instruction='ADD A,(HL)'
            lines.append('        '+instruction)
    assert not stack
    (Path(work)/'cache-lzsa.asm').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')


def playback_patch(meta,profile):
    """Three-byte FIRST jump fits the unreachable byte after old JP(IY).

    Preserve AF,all main/alternate registers and SP. An absolute JP(10 T)
    followed by2/4 NOPs and the original JP(IY) adds18/26 T at
    slot7. Spectrum128 and Scorpion retain their original JP(IY), delta0.
    """
    p=PROFILES[profile]
    if p['mode'] in (0,1):return []
    packed3=bool(meta.get('packed_ima3_direct'))
    entry=meta['player_labels']['hardware_delay']
    entry+=4 if packed3 and p['mode']==1 else 2 if packed3 else 3 if p['mode']==1 else 0
    size=meta['first_code_bytes']
    return [(address+size-3,bytes([0xc3,entry&255,entry>>8])) for address in meta['first_addresses']]


def timing_extra(meta,profile):return PROFILES[profile]['ima3_extra' if meta.get('packed_ima3_direct') else 'ima4_extra']
