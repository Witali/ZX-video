"""Follow-up assembly transforms, always starting from the verified round-four code."""
from optimize import replace_once


def immediate_offsets(d, f):
    """Four self-modified immediate operands replace forty memory loads/sample."""
    for i in range(4):
        d=replace_once(d,f'ld (coef_nibbles+{i}),a',f'ld (_smc{i}),a')
        source='coef_nibbles' + (f'+{i}' if i else '')
        d=replace_once(d,f'ld a,({source})\nld l,a',
                       f'product_offset_{i}:\nld l,#0')
    d += '\n; Only these immediate bytes are writable code. Not reentrant; IRQ is disabled.\n'
    for i in range(4):
        d += f'.globl _smc{i}\n_smc{i} = product_offset_{i}+1\n'
    d=d.replace('; HL signed sample multiplier. Split it once for all ten taps; clobbers AF only.',
                '; HL signed multiplier: patch four LD L,n operands once for all ten taps.\n'
                '; Code must reside in writable RAM. Clobbers AF; no opcode is modified.')
    return d,f


def apply(folder, variant):
    d=(folder/'decoder.s').read_text();f=(folder/'filter.s').read_text()
    d,f=immediate_offsets(d,f)
    (folder/'decoder.s').write_text(d,newline='\n')
    (folder/'filter.s').write_text(f,newline='\n')
