"""Test-only wide Mega: gamma-depth-proven LDI prefixes and delayed word shifts."""
from pathlib import Path
import re

from zx0._z80 import MiniAssembler,sha


FAMILIES=('length','literals','reuse')
PHASES=(1,3,5,7)


def after(phase):return phase-2 if phase>1 else 7


def build(*,origin=0x8000,prefix_cap=127,allow_oversize=False):
    """Keep ordinary copies; specialize only proven gamma lower bounds.

    A gamma count of at least K permits K-1 initial LDI instructions, leaving
    at least one byte for the original LDIR tail. Match clones preserve input
    on the caller stack and load the shared negative offset before copying.
    Count B remains provably zero through seven data bits; only subsequent
    word loops retain RL B. There is no table, runtime selector or new state.
    """
    if prefix_cap not in (7,15,31,63,127,227,228,229,255):raise ValueError(prefix_cap)
    source=Path(__file__).resolve().parents[1]/'zx0/src/zx0/asm/dzx0_mega.asm'
    original=[' '.join(line.split(';')[0].strip().split()).replace(', ', ',') for line in source.read_text().splitlines()]
    original=[line for line in original if line]
    lines=[];prefixes={};dead_stages=[];word_joins=[];shared_literals={}
    def copy(family,phase,lower):
        label=f'max_copy_{family}_{phase}_{lower}'
        prefix=min(prefix_cap,lower-1)
        prefixes[label]=dict(family=family,phase=phase,minimum_count=lower,prefix_bytes=prefix,
                             extra_offset_load_tstates=6 if family=='reuse' and phase==7 else 0)
        result=[label+':']
        if family!='literals':result+=['push hl','ld hl,(dzx0m_last_offset+1)','add hl,de']
        if lower==128 and prefix_cap>127:result+=[f'max_suffix_{family}_{phase}_128:']
        return result+['ldi']*prefix+[f'jp tail_{family}_{phase}']
    def stage(family,phase,level):
        name=f'max_gamma_{family}_{phase}_{level}'
        result=[name+':','add a,a','rl c']
        if level>=8:result+=['rl b']
        else:dead_stages.append(name)
        if phase==1:result+=['ld a,(hl)','inc hl']
        result+=['add a,a']
        q=after(phase)
        result+=[f'jp nc,max_gamma_{family}_{q}_{min(8,level+1)}']
        if level==8:
            join=f'max_word_join_{family}_{phase}'
            word_joins.append(join)
            if prefix_cap>127:
                entry=f'max_copy_{family}_{q}_256'
                prefixes[entry]=dict(family=family,phase=q,minimum_count=256,prefix_bytes=prefix_cap,
                    extra_offset_load_tstates=6 if family=='reuse' and q==7 else 0)
                result+=[entry+':']
                if family!='literals':result+=['push hl','ld hl,(dzx0m_last_offset+1)','add hl,de']
                result+=['ldi']*(prefix_cap-127)+[join+':',f'jp max_suffix_{family}_{q}_128']
                if family=='literals':shared_literals[join]=f'max_copy_{family}_{q}_128'
            else:result+=[join+':',f'jp max_copy_{family}_{q}_128']
        else:result+=copy(family,q,1<<level)
        return result
    counts={family:0 for family in FAMILIES}
    active=None;copy_context=None;last_label=None
    for line in original:
        if line.endswith(':'):
            label=line[:-1];last_label=label
            match=re.fullmatch(r'dzx0m_elias_(length|literals|reuse)([1357])',label)
            if match:
                active=(match[1],int(match[2]));dead_stages.append(label)
            match=re.fullmatch(r'dzx0m_(length|literals|reuse)([1357])',label)
            if match:copy_context=(match[1],int(match[2]))
            lines.append(line);continue
        if line=='rl b' and (active or last_label.startswith('dzx0m_elias_offset')):continue
        match=re.fullmatch(r'jp nc,dzx0m_elias_(length|literals|reuse)([1357])',line)
        if active and match:
            family,phase=active;q=after(phase)
            assert (family,q)==(match[1],int(match[2]))
            lines+=[f'jp nc,max_gamma_{family}_{q}_4']+copy(family,q,8)
            active=None;continue
        match=re.fullmatch(r'jp c,dzx0m_(length|literals|reuse)([1357])',line)
        if match:
            family,phase=match[1],int(match[2])
            if counts[family]%3==2:line=f'jp c,max_copy_{family}_{phase}_4'
            counts[family]+=1
        if line=='ldir':
            assert copy_context is not None
            lines.append(f'tail_{copy_context[0]}_{copy_context[1]}:')
        # The expanded fallthroughs can exceed JR reach. All changed branch
        # costs are included in native comparison, not hidden by the prefix.
        if line.startswith('jr '):line='jp '+line[3:]
        lines.append(line)
    assert all(value==12 for value in counts.values())
    for family in FAMILIES:
        for phase in PHASES:
            lines+=copy(family,phase,4)
        for level in range(4,9):
            for phase in PHASES:lines+=stage(family,phase,level)
    a=MiniAssembler(origin)
    simple={'push hl':(0xe5,),'pop hl':(0xe1,),'inc bc':(0x03,),
        'inc c':(0x0c,),'inc hl':(0x23,),'ldir':(0xed,0xb0),
        'ldi':(0xed,0xa0),'add a,a':(0x87,),'add hl,de':(0x19,),
        'ld b,c':(0x41,),'ld c,(hl)':(0x4e,),'ld a,(hl)':(0x7e,),
        'rr b':(0xcb,0x18),'rr c':(0xcb,0x19),'rl b':(0xcb,0x10),
        'rl c':(0xcb,0x11),'ret z':(0xc8,)}
    aliases={}
    for line in lines:
        if line.endswith(':'):a.label(line[:-1]);continue
        if line in simple:a.emit(*simple[line]);continue
        op,args=line.split(' ',1)
        if op=='jp':
            test,target=args.split(',',1) if ',' in args else ('',args)
            a.abs16({'':0xc3,'c':0xda,'nc':0xd2}[test],target)
        elif op=='ld':
            dest,value=args.split(',')
            if dest.startswith('('):
                expr=dest[1:-1];name,offset=expr.split('+');aliases[expr]=(name,int(offset));a.abs16((0xed,0x43),expr)
            elif value.startswith('('):
                expr=value[1:-1];name,offset=expr.split('+');aliases[expr]=(name,int(offset));a.abs16(0x2a,expr)
            else:
                value=int(value[1:],16) if value.startswith('$') else int(value)
                a.emit({'bc':0x01,'hl':0x21,'c':0x0e}[dest]);(a.word if dest in ('bc','hl') else a.emit)(value)
        else:raise ValueError(line)
    for name,(label,offset) in aliases.items():a.labels[name]=a.labels[label]+offset
    blob=a.resolve();assert allow_oversize or len(blob)+4<=10000
    return [(origin,blob)],a.labels,dict(entry='dzx0_mega',variant='mega-prefix-test',
        code_bytes=len(blob),workspace_bytes=len(blob)+4,max_decoder_stack_bytes=4,
        patched_addresses=[a.labels['dzx0m_last_offset+1']+i for i in (0,1)],
        source_sha256=sha(source.read_bytes()),prefix_cap=prefix_cap,prefixes=prefixes,
        removed_word_shift_stages=dead_stages,word_copy_joins=word_joins,
        shared_literal_suffixes=shared_literals,
        coroutine_supported=False,test_only=True)
