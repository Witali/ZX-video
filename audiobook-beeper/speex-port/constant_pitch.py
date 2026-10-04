"""Generate exact constant signed24 products for the finite mode-3 pitch book."""
import heapq
from make_decoder import array


def gains():
    book=array('gain_cdbk_lbr')
    return [book[4*i+j]+32 for i in range(32) for j in range(3)]


def label(gain):return '_pitch_const_'+('m'+str(-gain) if gain<0 else str(gain))


def chain_plans():
    # Search a bounded family of A:HL modulo24 recurrences. The Boolean says
    # whether B's original-word sign is needed; charge its 4-T initialization
    # once, retroactively, when the first addition/subtraction is chosen.
    seeds=[(20,5,1,False,'positive'),(49,11,-1,True,'negative')]
    best={};queue=[]
    for cost,size,k,uses_b,seed in seeds:
        state=(k,uses_b);best[state]=(cost,size,seed,())
        heapq.heappush(queue,(cost,size,k,uses_b))
    while queue:
        cost,size,k,uses_b=heapq.heappop(queue);state=(k,uses_b)
        if best[state][:2]!=(cost,size):continue
        _,_,seed,path=best[state]
        for op,dest,tstates,nbytes in (('double',2*k,15,2),('plus',k+1,15,2),('minus',k-1,23,4)):
            if not -256<=dest<=256:continue
            need=op!='double';new_b=uses_b or need
            nc=cost+tstates+(4 if need and not uses_b else 0)
            ns=size+nbytes+(1 if need and not uses_b else 0)
            target=(dest,new_b)
            if target not in best or (nc,ns)<best[target][:2]:
                best[target]=(nc,ns,seed,path+(op,))
                heapq.heappush(queue,(nc,ns,dest,new_b))
    plans={}
    for gain in set(gains()):
        options=[(value[0],value[1],value[2],value[3],state[1]) for state,value in best.items() if state[0]==gain]
        cost,size,seed,path,uses_b=min(options)
        plans[gain]=dict(seed=seed,operations=list(path),uses_b=uses_b,core_tstates=cost,core_bytes=size)
    return plans


def binary_plan(gain):
    bits=bin(abs(gain))[3:];path=[]
    for bit in bits:
        path.append('double')
        if bit=='1':path.append('plus' if gain>0 else 'minus')
    uses_b=gain<0 or any(op!='double' for op in path)
    cost=(49 if gain<0 else 24 if uses_b else 20)+sum(15 if op!='minus' else 23 for op in path)
    size=(11 if gain<0 else 6 if uses_b else 5)+sum(2 if op!='minus' else 4 for op in path)
    return dict(seed='negative' if gain<0 else 'positive',operations=path,uses_b=uses_b,core_tstates=cost,core_bytes=size)


def generate(strategy):
    assert strategy in ('binary','chain')
    plans=chain_plans() if strategy=='chain' else {g:binary_plan(g) for g in set(gains())}
    code='''; DE signed16 history, HL selected immutable routine address. CALL this
; trampoline so the routine's RET returns directly to the pitch accumulator.
; Every constant routine returns signed32 HL:DE and preserves IX/IY, all
; alternate registers and the real stack. Ordinary AF/BC may be clobbered.
.globl _pitch_indirect
_pitch_indirect::
jp (hl)
; A:HL is a modulo24 accumulator; DE stays the original word. B, when used,
; is its sign extension. ADD/ADC and SBC/SBC include low-word carry/borrow.
; Intermediate wrap is harmless: every final book gain*word fits signed24,
; so sign-extending the final high byte gives the exact signed32 result.
'''
    records=[]
    for gain in sorted(plans):
        plan=plans[gain];name=label(gain)
        code+=f'; Constant {gain}: {strategy} sequence; no data-dependent branches.\n.globl {name}\n{name}::\n'
        if gain==0:
            code+='ld hl,#0\nld de,#0\nret\n';cost=30;size=7
            plan=dict(seed='zero',operations=[],uses_b=False)
        elif gain==1:
            code+='ld a,d\nadd a,a\nsbc a,a\nld l,a\nld h,a\nret\n';cost=30;size=6
            plan=dict(seed='identity',operations=[],uses_b=False)
        else:
            code+='ld a,d\nadd a,a\nsbc a,a\n'
            if plan['uses_b']:code+='ld b,a\n'
            if plan['seed']=='positive':code+='ld h,d\nld l,e\n'
            else:
                code+='''; Initialize -word from zero. XOR clears borrow and LD preserves it;
; B is the original sign byte, so this also handles -32768 exactly.
xor a,a
ld hl,#0
sbc hl,de
sbc a,b
'''
            for op in plan['operations']:
                code+=dict(double='add hl,hl\nrla\n',plus='add hl,de\nadc a,b\n',
                           minus='or a,a\nsbc hl,de\nsbc a,b\n')[op]
            code+='''; Transfer the low word to DE, then sign-extend the final high byte.
ex de,hl
ld l,a
add a,a
sbc a,a
ld h,a
ret
'''
            cost=plan['core_tstates']+30;size=plan['core_bytes']+6
        records.append(dict(gain=gain,label=name,tstates_including_ret=cost,bytes=size,**plan))
    return code,dict(strategy=strategy,search_multiplier_bound=256 if strategy=='chain' else None,
                     pointer_table_bytes=192,trampoline_tstates=4,trampoline_bytes=1,routines=records)
