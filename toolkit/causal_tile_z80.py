"""Causal in-place FPD1 frame reconstruction with a 16-row motion cache.

Consumes expanded frame vectors/bitmaps/attribute masks and contiguous
Huffman input. The entire motion predictor and masked value application
execute on Z80. History is one 3840-byte compact frame; 1024 cache bytes
hold 16 rows with horizontal zero padding. No host-generated predictions.
Optional hybrid=True accepts FHT1 inline literals, raster-order attributes
and a validated per-frame motion-cache flag. Default FPD1 code is unchanged.
With intra_above=True, vector82 instead reads the already corrected above
row (FHS1 motion context). intra_extended=True adds left/second-above (83/84).
fast_fragments=True adds FHF1 raw/repeated-row/two-row/fill tiles (85..88).
unrolled_motion=True removes row loops and uses alternate DE as the output
cursor; phases 2/6 use rotate/mask merges. No stream or table changes.
raw_intra=True adds FHC1 high-bit flags on spatial modes 82..84. Only
masked bytes are literal; their spatial predictions are never computed.
split_literals=True adds an independent FSF1 fragment cursor in state;
fragment loads do not align or change the retained Huffman IX/C position.
raw_attributes=True optionally copies 768 final attributes from that cursor;
the default keeps the earlier generated machine code byte for byte.
selective_cache=True reads three coverage bytes at BA40 and skips unneeded
four-row copies. Map consumption and a skipped group's pointer advance run
on Z80. Virtual border rows still clear normally; the disk ring is unchanged.
Experimental cache_columns=16 reads six coverage bytes and copies only the
requested halves. unrolled_cache=True retains the three-byte map and copies
rows in pairs. They are mutually exclusive; default machine code is unchanged.
attribute_flags=True uses the metadata flags at BFB0..BFBB to skip eight
empty attribute masks, with a controller at 9360 below the AY handler.
It requires the pipeline's fixed A640 mask layout and decoded metadata.
sparse_patches=True jumps to the final correction as soon as SLA B has
shifted out the last set bit. It retains the input order and Huffman state,
uses HL as the bitmap cursor, and requires the hybrid skip-empty path.
fast_noop_scan=True combines vector/mask checks; requires even mask pairs,
retains 16-bit vector pointers for zero-copy packets, and uses no new RAM.
static_cache_borders=True omits virtual-row clearing when the validated
static-stripe marker proves that no tile can sample those rows this frame.
This is not yet a streamed/displaying player: metadata/ZX0 decoding,
window refill, screen expansion, paging and disk delivery are separate.
"""
from build_zxv_trd import MiniAssembler
import prefix_huffman_z80 as prefix

CODE, FRAME, CACHE = prefix.CODE, 0x6400, 0x7400
VECTOR_X, VECTOR_Y, VECTOR_PHASE, ROW_LOW, ROW_HIGH = 0x9800, 0x9900, 0x9a00, 0x9b00, 0x9c00
CACHE_MAP = 0xba40  # Three MSB-first bytes covering 24 four-row groups.
NOOP_SCANNER = 0x7a00
STATIC_EDGE = 0x7a80


def validate_static_stripes(vectors, masks):
    """A zero first vector is a stream-level promise that the edge is idle.

    A nonzero first vector always takes the complete existing path. The
    movie uses this escape for its post-credit splice; literals still run.
    """
    if len(vectors) != 192 or len(masks) != 384: raise ValueError('one frame required')
    for first in (0,176):
        if vectors[first] == 0 and (any(vectors[first:first+16]) or any(masks[2*first:2*first+32])):
            raise ValueError('zero edge marker does not describe an unchanged stripe')


def static_stripe_delta_tstates(vectors, masks):
    """Exact delta against skip_noop_runs, including ten inner dispatches."""
    validate_static_stripes(vectors,masks)
    return 440+(67 if vectors[0] else -1485)+(81 if vectors[176] else -1471)


def noop_run_delta_tstates(vectors, masks):
    """Exact delta against current hybrid tile traversal; no data change."""
    if len(vectors) != 192 or len(masks) != 384: raise ValueError('one frame required')
    delta = 0
    for first in range(0,192,16):
        i, end = first, first+16
        while i < end:
            if vectors[i]:
                delta += 10 if vectors[i] < 82 else 14; i += 1
            elif masks[i*2:i*2+2] != b'\0\0':
                delta += 7; i += 1
            else:
                start = i
                while i < end and vectors[i] == 0 and masks[i*2:i*2+2] == b'\0\0': i += 1
                delta += (200 if i == end else 236 if vectors[i] else 282)-168*(i-start)
    return delta


def encoded_run_delta_tstates(vectors, masks, *, commands=None, inplace=False, scan_uncoded=False):
    """FAP4 traversal delta against the original per-tile masked path."""
    if len(vectors) != 192 or len(masks) != 384: raise ValueError('one frame required')
    from vector_run_stream import encode_vectors,decode_vectors
    if commands is None: commands = encode_vectors(vectors,masks,inplace=inplace)[0]
    if decode_vectors(commands,masks,inplace=inplace)[0] != vectors: raise ValueError('commands differ')
    delta = i = pos = 0
    while i < 192:
        tag = commands[pos]; pos += 1
        if tag < 128:
            if not scan_uncoded: delta += 17; i += 1
            elif tag: delta += 17+(10 if tag < 82 else 14); i += 1
            elif masks[2*i:2*i+2] != b'\0\0': delta += 7; i += 1
            else:
                start = i; i += 1
                while i % 16 and commands[pos] == 0 and masks[2*i:2*i+2] == b'\0\0':
                    i += 1; pos += 1
                delta += (200 if i % 16 == 0 else 236 if commands[pos] else 282)-168*(i-start)
        else:
            count = tag-128; i += count
            if inplace: pos += count-1
            delta += (230 if i % 16 == 0 else 240)+12*inplace+14*scan_uncoded-260*count
    return delta


def selective_cache_delta_tstates(flags, enabled):
    """Relative to full cache fills, including 46-T per-frame mask setup.

    Across all twelve calls old cache_copy costs 55572 T. The new loop
    costs 3795+2305*N for N copied groups. Zero-border calls are identical;
    cache-disabled frames branch before the new setup and have zero delta.
    """
    if len(flags) != 3:
        raise ValueError('three cache coverage bytes required')
    return 3589-2305*(24-sum(v.bit_count() for v in flags)) if enabled else 0


def intra_tstates(vector, tile, corrections, *, extended=False):
    """Instruction-table formula, including RET, excluding caller/Huffman.

    Common body is 629 T. Above reads cost 32/53 T across a page (zero
    boundary/visible) or 26 T in the same page. Left reads cost 32/42 T
    for even fields; odd fields already have the corrected byte in A.
    Extended dispatch costs 17 T for left and 34 T for either above mode.
    """
    if not 0 <= tile < 192 or not 0 <= corrections <= 16:
        raise ValueError('invalid intra tile')
    if vector == 82:
        base = 1057 if tile < 16 else 1099
        return base+25*corrections+(34 if extended else 0)
    if not extended or vector not in (83, 84):
        raise ValueError('unsupported intra vector')
    if vector == 83:
        return 629+17+8*(32 if tile % 16 == 0 else 42)+25*corrections
    return 629+34+4*(32 if tile < 16 else 53)+12*26+25*corrections


def fast_tstates(vector, *, unaligned=False, selector=0, split_literals=False):
    """Whole-fragment routine incl. RET; caller/outer traversal are separate."""
    if vector not in (85, 86, 87, 88) or not 0 <= selector <= 255:
        raise ValueError('invalid fast fragment')
    base = {85: 546, 86: 541, 87: 818+10*(8-selector.bit_count()), 88: 513}[vector]
    return base-54 if split_literals else base+10*bool(unaligned)


def motion_tstates(vector, offsets, *, unrolled=False):
    """Motion routine incl. RET, excluding caller; stripes start at y%8=0."""
    if not 1 <= vector <= 81:
        raise ValueError('motion is called only for vectors 1..81')
    if vector == 81:
        return 324 if unrolled else 445
    dx, dy = offsets[vector]
    phase = 2*((-dx) % 4)
    if not unrolled:
        return {0: 995, 2: 2076, 4: 2093, 6: 2103}[phase]
    return {0: 826, 2: 1616, 4: 1713, 6: 1643}[phase]+21*bool(dy % 4)


def raw_intra_tstates(vector, tile, mask, *, unaligned=False):
    """FHC1 fused raw/spatial body incl. RET; no caller/outer traversal.

    The 16-bit mask is MSB first. Corrected fields read a literal instead
    of computing the spatial predictor. Their branch/read costs 39 T.
    """
    if vector not in (82, 83, 84) or not 0 <= tile < 192 or not 0 <= mask <= 65535:
        raise ValueError('invalid raw intra tile')
    total = 693+(17 if vector == 83 else 34)+10*bool(unaligned)
    for field in range(16):
        if mask & (32768 >> field):
            total += 39
        elif vector == 83:
            total += 0 if field % 2 else (32 if tile % 16 == 0 else 42)
        else:
            distance = 1 if vector == 82 else 2
            total += (32 if tile < 16 else 53) if field < 2*distance else 26
    return total


def patch_half_tstates(mask, half, *, sparse_patches=False):
    """One skip-empty half including its exit, excluding Huffman bodies.

    First-half exit includes positioning the cursor at row four; second
    includes RET. The DE/HL target load and LD B,C are separate (24/20 T).
    Both-zero masks return before either half and must not use this sum.
    """
    if not 0 <= mask <= 255 or half not in (0, 1):
        raise ValueError('expected an 8-bit mask and half 0/1')
    if not sparse_patches:
        if not mask: return 33 if half == 0 else 28
        return (248 if half == 0 else 233)+39*mask.bit_count()
    exit_cost = 22 if half == 0 else 10
    if not mask: return 18+exit_cost
    last = 7-((mask & -mask).bit_length()-1)
    advances = sum(4 if j % 2 == 0 else 12 if j in (1, 5) else 15 for j in range(last))
    checks = mask.bit_count()-int(bool(mask & 1))
    return 18+18*(last+1)+10*checks+39*mask.bit_count()+advances+exit_cost


def patch_delta_tstates(vectors, masks):
    """Exact sparse-patch delta for expanded temporal/zero tile metadata."""
    if len(vectors) != 192 or len(masks) != 384:
        raise ValueError('one expanded frame required')
    return sum(-4+sum(patch_half_tstates(m, h, sparse_patches=True)-patch_half_tstates(m, h)
                         for h, m in enumerate((b, c)))
        for v, b, c in zip(vectors, masks[::2], masks[1::2]) if v <= 81 and (b or c))


def build(tables, mapping, offsets, *, skip_empty=False, hybrid=False, raw_kind=None, intra_above=False, intra_extended=False, fast_fragments=False, unrolled_motion=False, raw_intra=False, split_literals=False, raw_attributes=False, selective_cache=False, skip_noop_runs=False, encoded_noop_runs=False, skip_static_stripes=False, cache_columns=32, unrolled_cache=False, attribute_flags=False, sparse_patches=False, fast_noop_scan=False, static_cache_borders=False,carry_huffman=False):
    if static_cache_borders and not skip_static_stripes:
        raise ValueError('static cache borders require validated static stripes')
    if fast_noop_scan and (not skip_noop_runs or encoded_noop_runs):
        raise ValueError('fast scanner requires plain no-op runs and even bitmap-mask addresses')
    if sparse_patches and not (hybrid and skip_empty and raw_kind is None and not raw_intra):
        raise ValueError('sparse patches require hybrid skip-empty Huffman patches')
    if attribute_flags and not (hybrid and raw_attributes):
        raise ValueError('attribute flags require the hybrid raw-attribute path')
    if cache_columns not in (16,32) or (cache_columns != 32 or unrolled_cache) and not selective_cache:
        raise ValueError('cache variants require selective coverage with 16/32 columns')
    if unrolled_cache and cache_columns != 32:
        raise ValueError('unrolled cache experiment retains the three-byte map')
    if skip_static_stripes and (not skip_noop_runs or encoded_noop_runs):
        raise ValueError('static stripes require the plain vector/no-op scanner path')
    if encoded_noop_runs and not (hybrid and skip_empty and intra_extended and raw_kind is None and not raw_intra):
        raise ValueError('encoded runs require the hybrid masked path')
    if skip_noop_runs and not (hybrid and skip_empty and intra_extended and raw_kind is None and not raw_intra):
        raise ValueError('no-op scanner requires the current hybrid masked path')
    if selective_cache and not hybrid:
        raise ValueError('selective cache requires per-frame cache flag')
    if raw_attributes and not (hybrid and split_literals):
        raise ValueError('raw attributes require hybrid split literals')
    if split_literals and (not fast_fragments or raw_intra):
        raise ValueError('split literals require FHF fast fragments without raw intra')
    if raw_intra and not fast_fragments:
        raise ValueError('raw intra requires fast fragments')
    if fast_fragments and not intra_extended:
        raise ValueError('fast fragments require extended spatial mode')
    if intra_extended and not intra_above:
        raise ValueError('extended intra requires intra_above')
    if intra_above and (not hybrid or not skip_empty or raw_kind is not None):
        raise ValueError('intra above requires the separate attribute/skip-empty path')
    if raw_kind is not None and (raw_kind not in (0, 1) or not hybrid or not skip_empty):
        raise ValueError('raw direct/XOR patches require hybrid and empty-half skips')
    if len(offsets) != 81 or offsets[0] != (0, 0) or set(offsets) != {(x, y) for x in range(-4, 5) for y in range(-4, 5)}:
        raise ValueError('expected the complete +/-4 motion alphabet')
    original, labels, instructions, layout = prefix.build(tables, mapping,carry_huffman=carry_huffman)
    bit_base=0xf8 if carry_huffman else 0xf0
    end = labels['primitive_end']
    a = MiniAssembler(CODE)
    a.emit(*original[:end-CODE])
    a.labels.update({name: address for name, address in labels.items() if address < end})
    if skip_noop_runs: a.labels['scan_zero_run'] = NOOP_SCANNER
    if encoded_noop_runs: a.labels['encoded_zero_run'] = NOOP_SCANNER+128*skip_noop_runs
    if skip_static_stripes: a.labels['static_edge'] = STATIC_EDGE
    listing = [dict(row, stage='huffman') for row in instructions if row['address'] < end]
    stage = 'control'

    def emit(name, data, ticks):
        listing.append(dict(address=a.pc, instruction=name, tstates=ticks, stage=stage)); a.emit(*data)

    def wordop(name, opcode, value, ticks):
        emit(name, [opcode, value & 255, value >> 8], ticks)

    def jump(name, opcode, target, ticks, relative=False):
        listing.append(dict(address=a.pc, instruction=name, tstates=ticks, stage=stage))
        (a.rel8 if relative else a.abs16)(opcode, target)

    def load(name, opcode, target, ticks):
        jump(name, opcode, target, ticks)

    def cache_advance(tag, amount):
        # Source/cache column is 0..34, so only crossing a 256-byte page
        # requires wrapping the cache's high byte. Padding avoids edge reads.
        emit('LD A,E', [0x7b], 4); emit(f'ADD A,{amount}', [0xc6, amount], 7)
        emit('LD E,A', [0x5f], 4)
        jump('JR NC,cache_page_ready', 0x30, tag, [7, 12], True)
        emit('INC D', [0x14], 4); emit('LD A,D', [0x7a], 4)
        emit('AND 3', [0xe6, 3], 7); emit('OR cache_page', [0xf6, CACHE >> 8], 7)
        emit('LD D,A', [0x57], 4); a.label(tag)

    def next_output_row():
        emit('LD A,L', [0x7d], 4); emit('ADD A,31', [0xc6, 31], 7); emit('LD L,A', [0x6f], 4)

    def read_above(field, distance=1, prefix=''):
        # Tiles align to eight rows / one 256-byte page. First 2*distance fields
        # refer to the previous page (or virtual zero top); all later
        # fields have their above byte in the same page as DE.
        tag = prefix+(f'{field}' if distance == 1 else f'{distance}_{field}')
        if field < 2*distance:
            emit('LD A,D', [0x7a], 4); emit('CP frame_page', [0xfe, FRAME >> 8], 7)
            jump('JR NZ,above_visible', 0x20, f'above_visible_{tag}', [7, 12], True)
            emit('XOR A', [0xaf], 4); jump('JP above_ready', 0xc3, f'above_ready_{tag}', 10)
            a.label(f'above_visible_{tag}')
            emit('LD H,D', [0x62], 4); emit('DEC H', [0x25], 4)
            emit('LD A,E', [0x7b], 4); emit(f'ADD A,{256-32*distance}', [0xc6, 256-32*distance], 7)
            emit('LD L,A', [0x6f], 4); emit('LD A,(HL)', [0x7e], 7)
            a.label(f'above_ready_{tag}')
        else:
            emit('LD A,E', [0x7b], 4); emit(f'SUB {32*distance}', [0xd6, 32*distance], 7)
            emit('LD L,A', [0x6f], 4); emit('LD H,D', [0x62], 4); emit('LD A,(HL)', [0x7e], 7)

    def read_left(field, prefix=''):
        # Odd fields use A from the immediately preceding corrected store.
        # INC E / SLA B / JP do not alter A, and no row boundary lies here.
        if field % 2:
            return
        emit('LD A,E', [0x7b], 4); emit('AND 31', [0xe6, 31], 7)
        jump('JR NZ,left_visible', 0x20, f'left_visible_{prefix}{field}', [7, 12], True)
        emit('XOR A', [0xaf], 4); jump('JP left_ready', 0xc3, f'left_ready_{prefix}{field}', 10)
        a.label(f'left_visible_{prefix}{field}')
        emit('LD H,D', [0x62], 4); emit('LD L,E', [0x6b], 4)
        emit('DEC L', [0x2d], 4); emit('LD A,(HL)', [0x7e], 7)
        a.label(f'left_ready_{prefix}{field}')

    a.label('frame')
    load('LD IX,(source)', (0xdd, 0x2a), 'source', 20)
    load('LD A,(bit_page)', 0x3a, 'bit_page', 13)
    emit('EXX', [0xd9], 4); emit('LD C,A', [0x4f], 4); emit('EXX', [0xd9], 4)
    wordop('LD HL,compact_frame', 0x21, FRAME, 10); load('LD (target),HL', 0x22, 'target', 16)
    if not hybrid:
        wordop('LD HL,attributes', 0x21, FRAME+3072, 10); load('LD (attr_target),HL', 0x22, 'attr_target', 16)
    emit('XOR A', [0xaf], 4); load('LD (stripe_y),A', 0x32, 'stripe_y', 13)
    emit('LD A,12', [0x3e, 12], 7); load('LD (stripes_left),A', 0x32, 'stripes_left', 13)
    if hybrid:
        load('LD A,(cache_enabled)', 0x3a, 'cache_enabled', 13)
        emit('OR A', [0xb7], 4); jump('JP Z,stripe', 0xca, 'stripe', 10)
    # The top four virtual rows are black. Padding columns stay zero from
    # cache initialization; no routine writes them.
    if selective_cache:
        wordop('LD HL,cache_map', 0x21, CACHE_MAP, 10)
        load('LD (cache_mask_source),HL', 0x22, 'cache_mask_source', 16)
        emit('LD A,80h', [0x3e, 128], 7)
        load('LD (cache_mask_shift),A', 0x32, 'cache_mask_shift', 13)
    if static_cache_borders:
        load('LD HL,(vectors)', 0x2a, 'vectors', 16)
        emit('LD A,(HL)', [0x7e], 7); emit('OR A', [0xb7], 4)
        jump('JP Z,top_cache_ready', 0xca, 'top_cache_ready', 10)
    wordop('LD DE,top_virtual_cache_rows', 0x11, CACHE+12*64+1, 10)
    emit('LD B,4', [0x06, 4], 7); jump('CALL cache_zero', 0xcd, 'cache_zero', 17)
    if static_cache_borders: a.label('top_cache_ready')
    wordop('LD HL,compact_frame', 0x21, FRAME, 10)
    wordop('LD DE,cache_first_visible', 0x11, CACHE+1, 10)
    emit('LD B,12', [0x06, 12], 7); jump('CALL cache_copy', 0xcd, 'cache_copy', 17)
    a.label('save_cache')
    load('LD (cache_read),HL', 0x22, 'cache_read', 16)
    load('LD (cache_write),DE', (0xed, 0x53), 'cache_write', 20)
    a.label('stripe')
    if skip_static_stripes:
        load('LD A,(stripes_left)',0x3a,'stripes_left',13)
        emit('CP first stripe',[0xfe,12],7); jump('JP Z,static_edge',0xca,'static_edge',10)
        emit('DEC A (last stripe)',[0x3d],4); jump('JP Z,static_edge',0xca,'static_edge',10)
    a.label('regular_stripe')
    emit('LD A,16', [0x3e, 16], 7); load('LD (tiles_left),A', 0x32, 'tiles_left', 13)
    a.label('tile')
    load('LD HL,(vectors)', 0x2a, 'vectors', 16)
    emit('LD A,(HL)', [0x7e], 7)
    if skip_noop_runs:
        emit('OR A',[0xb7],4); jump('JP Z,scan_zero_run',0xca,'scan_zero_run',10)
    if encoded_noop_runs == 'inplace':
        emit('CP run tag',[0xfe,128],7); jump('JP NC,encoded_zero_run',0xd2,'encoded_zero_run',10)
    emit('INC HL', [0x23], 6)
    load('LD (vectors),HL', 0x22, 'vectors', 16)
    if encoded_noop_runs and encoded_noop_runs != 'inplace':
        emit('CP run tag',[0xfe,128],7); jump('JP NC,encoded_zero_run',0xd2,'encoded_zero_run',10)
    if raw_kind is not None:
        emit('PUSH AF', [0xf5], 11); emit('AND 7Fh', [0xe6, 127], 7)
        jump('CALL NZ,motion', 0xc4, 'motion', [10, 17])
        emit('POP AF', [0xf1], 10); emit('BIT 7,A', [0xcb, 0x7f], 8)
        jump('JP NZ,raw_tile', 0xc2, 'raw_tile', 10)
        jump('CALL patches', 0xcd, 'patches', 17)
        jump('JP tile_done', 0xc3, 'tile_done', 10)
        a.label('raw_tile'); jump('CALL raw_patches', 0xcd, 'raw_patches', 17)
        a.label('tile_done')
    elif hybrid:
        emit('CP intra_vector' if intra_above else 'CP literal_vector', [0xfe, 82], 7)
        jump('JP NC,literal_tile' if intra_extended else 'JP Z,literal_tile',
             0xd2 if intra_extended else 0xca, 'literal_tile', 10)
    if raw_kind is None:
        if skip_noop_runs:
            jump('CALL motion',0xcd,'motion',17)
        else:
            emit('OR A', [0xb7], 4); jump('CALL NZ,motion', 0xc4, 'motion', [10, 17])
        jump('CALL patches', 0xcd, 'patches', 17)
    if hybrid and raw_kind is None:
        jump('JP tile_done', 0xc3, 'tile_done', 10)
        a.label('literal_tile')
        if intra_above:
            if raw_intra:
                # High-bit raw flags only exist on spatial modes 82..84.
                # Ordinary temporal tiles do not pay this dispatch cost.
                emit('BIT 7,A', [0xcb, 0x7f], 8)
                jump('JP NZ,raw_intra_tile', 0xc2, 'raw_intra_tile', 10)
            if fast_fragments:
                emit('CP fast_vector', [0xfe, 85], 7)
                jump('JP NC,fast_tile', 0xd2, 'fast_tile', 10)
            jump('CALL intra_above', 0xcd, 'intra_above', 17)
            if fast_fragments:
                jump('JP tile_done', 0xc3, 'tile_done', 10)
                a.label('fast_tile'); jump('CALL fast_fragment', 0xcd, 'fast_fragment', 17)
            if raw_intra:
                jump('JP tile_done', 0xc3, 'tile_done', 10)
                a.label('raw_intra_tile'); jump('CALL raw_intra', 0xcd, 'raw_intra', 17)
        else:
            load('LD HL,(bitmap_masks)', 0x2a, 'bitmap_masks', 16)
            emit('INC HL', [0x23], 6); emit('INC HL', [0x23], 6)
            load('LD (bitmap_masks),HL', 0x22, 'bitmap_masks', 16)
            jump('CALL literal', 0xcd, 'literal', 17)
        a.label('tile_done')
    load('LD HL,(target)', 0x2a, 'target', 16)
    emit('INC L', [0x2c], 4); emit('INC L', [0x2c], 4)
    load('LD (target),HL', 0x22, 'target', 16)
    if not hybrid:
        load('LD HL,(attr_target)', 0x2a, 'attr_target', 16)
        emit('INC HL', [0x23], 6); emit('INC HL', [0x23], 6)
        load('LD (attr_target),HL', 0x22, 'attr_target', 16)
    load('LD HL,tiles_left', 0x21, 'tiles_left', 10)
    emit('DEC (HL)', [0x35], 11); jump('JP NZ,tile', 0xc2, 'tile', 10)
    a.label('stripe_done')
    load('LD HL,stripes_left', 0x21, 'stripes_left', 10)
    emit('DEC (HL)', [0x35], 11); jump('JP Z,frame_done', 0xca, 'frame_done', 10)
    load('LD HL,(target)', 0x2a, 'target', 16); wordop('LD DE,224', 0x11, 224, 10)
    emit('ADD HL,DE', [0x19], 11); load('LD (target),HL', 0x22, 'target', 16)
    if not hybrid:
        load('LD HL,(attr_target)', 0x2a, 'attr_target', 16); wordop('LD DE,32', 0x11, 32, 10)
        emit('ADD HL,DE', [0x19], 11); load('LD (attr_target),HL', 0x22, 'attr_target', 16)
    load('LD A,(stripe_y)', 0x3a, 'stripe_y', 13)
    emit('ADD A,8', [0xc6, 8], 7); load('LD (stripe_y),A', 0x32, 'stripe_y', 13)
    if hybrid:
        load('LD A,(cache_enabled)', 0x3a, 'cache_enabled', 13)
        emit('OR A', [0xb7], 4); jump('JP Z,stripe', 0xca, 'stripe', 10)
    load('LD HL,(cache_read)', 0x2a, 'cache_read', 16)
    load('LD DE,(cache_write)', (0xed, 0x5b), 'cache_write', 20)
    load('LD A,(stripes_left)', 0x3a, 'stripes_left', 13)
    emit('CP 1', [0xfe, 1], 7); jump('JR Z,last_prefetch', 0x28, 'last_prefetch', [7, 12], True)
    emit('LD B,8', [0x06, 8], 7); jump('CALL cache_copy', 0xcd, 'cache_copy', 17)
    jump('JP save_cache', 0xc3, 'save_cache', 10)
    a.label('last_prefetch')
    emit('LD B,4', [0x06, 4], 7); jump('CALL cache_copy', 0xcd, 'cache_copy', 17)
    if static_cache_borders:
        # The final stripe is the sole reader of virtual rows 96..99.
        # Preserve HL (the next source row) and C' (the Huffman position).
        emit('EXX', [0xd9], 4)
        load('LD HL,(vectors)', 0x2a, 'vectors', 16)
        emit('LD A,(HL)', [0x7e], 7); emit('EXX', [0xd9], 4)
        emit('OR A', [0xb7], 4)
        jump('JP NZ,clear_bottom_cache', 0xc2, 'clear_bottom_cache', 10)
        # Four rows advance exactly 7401h -> 7501h. Keep the saved cursor
        # identical even though its bytes are never sampled by this frame.
        emit('INC D', [0x14], 4)
        jump('JP save_cache', 0xc3, 'save_cache', 10)
        a.label('clear_bottom_cache')
    emit('LD B,4', [0x06, 4], 7); jump('CALL cache_zero', 0xcd, 'cache_zero', 17)
    jump('JP save_cache', 0xc3, 'save_cache', 10)
    a.label('frame_done')
    if hybrid:
        jump('CALL attribute_pass', 0xcd, 'attribute_pass', 17)
    load('LD (source),IX', (0xdd, 0x22), 'source', 20)
    emit('EXX', [0xd9], 4); emit('LD A,C', [0x79], 4); emit('EXX', [0xd9], 4)
    load('LD (bit_page),A', 0x32, 'bit_page', 13); emit('RET', [0xc9], 10)

    if hybrid and raw_kind is None and not intra_above:
        stage = 'literal'
        a.label('literal')
        # IX points at the current Huffman byte. Skip its unused low bits;
        # the format requires those bits to be zero. Use the alternate bank
        # so LDI cannot destroy traversal registers, and preserve reservoir C.
        emit('EXX', [0xd9], 4); emit('LD A,C', [0x79], 4)
        emit('AND 7', [0xe6, 7], 7); jump('JP Z,literal_aligned', 0xca, 'literal_aligned', 10)
        emit('INC IX', [0xdd, 0x23], 10); a.label('literal_aligned')
        emit('LD C,bit_base', [0x0e, bit_base], 7); emit('PUSH BC', [0xc5], 11)
        emit('PUSH IX', [0xdd, 0xe5], 15); emit('POP HL', [0xe1], 10)
        load('LD DE,(target)', (0xed, 0x5b), 'target', 20)
        for row in range(8):
            emit('LDI', [0xed, 0xa0], 16); emit('LDI', [0xed, 0xa0], 16)
            if row < 7:
                emit('LD A,E', [0x7b], 4); emit('ADD A,30', [0xc6, 30], 7); emit('LD E,A', [0x5f], 4)
        emit('PUSH HL', [0xe5], 11); emit('POP IX', [0xdd, 0xe1], 14)
        emit('POP BC', [0xc1], 10); emit('EXX', [0xd9], 4); emit('RET', [0xc9], 10)

    if intra_above:
        stage = 'intra'
        a.label('intra_above')
        load('LD HL,(bitmap_masks)', 0x2a, 'bitmap_masks', 16)
        emit('LD B,(HL)', [0x46], 7); emit('INC HL', [0x23], 6)
        emit('LD C,(HL)', [0x4e], 7); emit('INC HL', [0x23], 6)
        load('LD (bitmap_masks),HL', 0x22, 'bitmap_masks', 16)
        load('LD DE,(target)', (0xed, 0x5b), 'target', 20)
        if intra_extended:
            emit('CP left_vector', [0xfe, 83], 7)
            jump('JP Z,intra_left', 0xca, 'intra_left', 10)
            emit('CP second_above_vector', [0xfe, 84], 7)
            jump('JP Z,intra_above2', 0xca, 'intra_above2', 10)
        for name in (('above', 'left', 'above2') if intra_extended else ('above',)):
            if name != 'above':
                a.label('intra_'+name)
            for field in range(16):
                if field == 8:
                    emit('LD B,C', [0x41], 4)
                if name == 'left':
                    read_left(field)
                else:
                    read_above(field, 2 if name == 'above2' else 1)
                tag = str(field) if name == 'above' else f'{name}_{field}'
                emit('SLA B', [0xcb, 0x20], 8)
                jump('JP NC,intra_store', 0xd2, f'intra_store_{tag}', 10)
                emit('EXX', [0xd9], 4); jump('CALL bitmap', 0xcd, 'bitmap', 17); emit('EXX', [0xd9], 4)
                a.label(f'intra_store_{tag}'); emit('LD (DE),A', [0x12], 7)
                if field < 15:
                    if not field % 2:
                        emit('INC E', [0x1c], 4)
                    else:
                        emit('LD A,E', [0x7b], 4); emit('ADD A,31', [0xc6, 31], 7); emit('LD E,A', [0x5f], 4)
            emit('RET', [0xc9], 10)

    if raw_intra:
        stage = 'raw_intra'
        a.label('raw_intra')
        emit('AND 7Fh', [0xe6, 127], 7); emit('PUSH AF', [0xf5], 11)
        load('LD HL,(bitmap_masks)', 0x2a, 'bitmap_masks', 16)
        emit('LD B,(HL)', [0x46], 7); emit('INC HL', [0x23], 6)
        emit('LD C,(HL)', [0x4e], 7); emit('INC HL', [0x23], 6)
        load('LD (bitmap_masks),HL', 0x22, 'bitmap_masks', 16)
        emit('EXX', [0xd9], 4); emit('LD A,C', [0x79], 4)
        emit('AND 7', [0xe6, 7], 7); jump('JP Z,raw_intra_aligned', 0xca, 'raw_intra_aligned', 10)
        emit('INC IX', [0xdd, 0x23], 10); a.label('raw_intra_aligned')
        emit('LD C,bit_base', [0x0e, bit_base], 7); emit('EXX', [0xd9], 4)
        load('LD DE,(target)', (0xed, 0x5b), 'target', 20); emit('POP AF', [0xf1], 10)
        emit('CP left_vector', [0xfe, 83], 7); jump('JP Z,raw_intra_left', 0xca, 'raw_intra_left', 10)
        emit('CP second_above_vector', [0xfe, 84], 7); jump('JP Z,raw_intra_above2', 0xca, 'raw_intra_above2', 10)
        for name in ('above', 'left', 'above2'):
            a.label('raw_intra_'+name)
            for field in range(16):
                tag = f'raw_{name}_{field}'
                if field == 8:
                    emit('LD B,C', [0x41], 4)
                emit('SLA B', [0xcb, 0x20], 8)
                jump('JP NC,raw_intra_predict', 0xd2, tag+'_predict', 10)
                emit('LD A,(IX+0)', [0xdd, 0x7e, 0], 19); emit('INC IX', [0xdd, 0x23], 10)
                jump('JP raw_intra_store', 0xc3, tag+'_store', 10)
                a.label(tag+'_predict')
                if name == 'left':
                    read_left(field, 'raw_')
                else:
                    read_above(field, 2 if name == 'above2' else 1, 'raw_')
                a.label(tag+'_store'); emit('LD (DE),A', [0x12], 7)
                if field < 15:
                    if not field % 2:
                        emit('INC E', [0x1c], 4)
                    else:
                        emit('LD A,E', [0x7b], 4); emit('ADD A,31', [0xc6, 31], 7); emit('LD E,A', [0x5f], 4)
            emit('RET', [0xc9], 10)

    if fast_fragments:
        stage = 'fast_fragment'
        a.label('fast_fragment')
        # Masks are validated as zero by the container. Keep the normal
        # bitmap-mask cursor in sync without touching predictor memory.
        load('LD HL,(bitmap_masks)', 0x2a, 'bitmap_masks', 16)
        emit('INC HL', [0x23], 6); emit('INC HL', [0x23], 6)
        load('LD (bitmap_masks),HL', 0x22, 'bitmap_masks', 16)
        emit('LD B,A', [0x47], 4)
        if split_literals:
            load('LD HL,(literal_source)', 0x2a, 'literal_source', 16)
        else:
            emit('EXX', [0xd9], 4); emit('LD A,C', [0x79], 4)
            emit('AND 7', [0xe6, 7], 7); jump('JP Z,fragment_aligned', 0xca, 'fragment_aligned', 10)
            emit('INC IX', [0xdd, 0x23], 10); a.label('fragment_aligned')
            emit('LD C,bit_base', [0x0e, bit_base], 7); emit('EXX', [0xd9], 4)
            emit('PUSH IX', [0xdd, 0xe5], 15); emit('POP HL', [0xe1], 10)
        load('LD DE,(target)', (0xed, 0x5b), 'target', 20)
        emit('LD A,B', [0x78], 4)
        for value, label in ((85, 'fragment_raw'), (86, 'fragment_repeat'), (87, 'fragment_rows')):
            emit(f'CP {value}', [0xfe, value], 7); jump('JP Z,'+label, 0xca, label, 10)

        def save_fragment_cursor():
            if split_literals:
                load('LD (literal_source),HL', 0x22, 'literal_source', 16)
            else:
                emit('PUSH HL', [0xe5], 11); emit('POP IX', [0xdd, 0xe1], 14)

        def row_advance():
            emit('LD A,E', [0x7b], 4); emit('ADD A,31', [0xc6, 31], 7); emit('LD E,A', [0x5f], 4)

        def write_pair(first, second):
            emit('LD A,'+first, [0x78 if first == 'B' else 0x7c], 4)
            emit('LD (DE),A', [0x12], 7); emit('INC E', [0x1c], 4)
            emit('LD A,'+second, [0x79 if second == 'C' else 0x7d], 4)
            emit('LD (DE),A', [0x12], 7)

        a.label('fragment_fill')
        emit('LD B,(HL)', [0x46], 7); emit('INC HL', [0x23], 6); save_fragment_cursor()
        for row in range(8):
            emit('LD A,B', [0x78], 4); emit('LD (DE),A', [0x12], 7)
            emit('INC E', [0x1c], 4); emit('LD (DE),A', [0x12], 7)
            if row < 7:
                row_advance()
        emit('RET', [0xc9], 10)

        a.label('fragment_raw')
        for row in range(8):
            emit('LDI', [0xed, 0xa0], 16); emit('LDI', [0xed, 0xa0], 16)
            if row < 7:
                emit('LD A,E', [0x7b], 4); emit('ADD A,30', [0xc6, 30], 7); emit('LD E,A', [0x5f], 4)
        save_fragment_cursor(); emit('RET', [0xc9], 10)

        a.label('fragment_repeat')
        emit('LD B,(HL)', [0x46], 7); emit('INC HL', [0x23], 6)
        emit('LD C,(HL)', [0x4e], 7); emit('INC HL', [0x23], 6); save_fragment_cursor()
        for row in range(8):
            write_pair('B', 'C')
            if row < 7:
                row_advance()
        emit('RET', [0xc9], 10)

        a.label('fragment_rows')
        for name, opcode in (('B', 0x46), ('C', 0x4e), ('D', 0x56), ('E', 0x5e), ('A', 0x7e)):
            emit(f'LD {name},(HL)', [opcode], 7); emit('INC HL', [0x23], 6)
        save_fragment_cursor()
        emit('PUSH DE', [0xd5], 11); emit('POP HL', [0xe1], 10)
        load('LD DE,(target)', (0xed, 0x5b), 'target', 20)
        emit("EX AF,AF'", [0x08], 4)
        for row in range(8):
            emit("EX AF,AF'", [0x08], 4); emit('RLA', [0x17], 4)
            jump('JP C,second_pair', 0xda, f'fragment_second_{row}', 10)
            emit("EX AF,AF'", [0x08], 4); write_pair('B', 'C')
            jump('JP pair_done', 0xc3, f'fragment_pair_done_{row}', 10)
            a.label(f'fragment_second_{row}'); emit("EX AF,AF'", [0x08], 4); write_pair('H', 'L')
            a.label(f'fragment_pair_done_{row}')
            if row < 7:
                row_advance()
        emit('RET', [0xc9], 10)

    if raw_kind is not None:
        stage = 'raw_patch'
        a.label('raw_patches')
        load('LD HL,(bitmap_masks)', 0x2a, 'bitmap_masks', 16)
        emit('LD B,(HL)', [0x46], 7); emit('INC HL', [0x23], 6)
        emit('LD C,(HL)', [0x4e], 7); emit('INC HL', [0x23], 6)
        load('LD (bitmap_masks),HL', 0x22, 'bitmap_masks', 16)
        # Cache/motion have already formed the predictor. Align the shared
        # bit input, then read raw bytes with HL while primary BC keeps masks.
        emit('EXX', [0xd9], 4); emit('LD A,C', [0x79], 4)
        emit('AND 7', [0xe6, 7], 7); jump('JP Z,raw_aligned', 0xca, 'raw_aligned', 10)
        emit('INC IX', [0xdd, 0x23], 10); a.label('raw_aligned')
        emit('LD C,bit_base', [0x0e, bit_base], 7); emit('EXX', [0xd9], 4)
        emit('PUSH IX', [0xdd, 0xe5], 15); emit('POP HL', [0xe1], 10)
        load('LD DE,(target)', (0xed, 0x5b), 'target', 20)
        for field in range(16):
            if field == 8:
                a.label('raw_skip_half_0')
                emit('LD A,E', [0x7b], 4); emit('ADD A,128', [0xc6, 128], 7); emit('LD E,A', [0x5f], 4)
                a.label('raw_second_half'); emit('LD B,C', [0x41], 4)
            if field in (0, 8):
                emit('LD A,B', [0x78], 4); emit('OR A', [0xb7], 4)
                jump('JP Z,raw_empty_half', 0xca, 'raw_skip_half_0' if field == 0 else 'raw_done', 10)
            emit('SLA B', [0xcb, 0x20], 8); jump('JP NC,raw_keep', 0xd2, f'raw_keep_{field}', 10)
            a.label(f'raw_value_{field}')
            if raw_kind == 1:
                emit('LD A,(DE)', [0x1a], 7); emit('XOR (HL)', [0xae], 7)
            else:
                emit('LD A,(HL)', [0x7e], 7)
            emit('INC HL', [0x23], 6); emit('LD (DE),A', [0x12], 7)
            a.label(f'raw_keep_{field}')
            if field < 15:
                if not field % 2:
                    emit('INC E', [0x1c], 4)
                else:
                    emit('LD A,E', [0x7b], 4); emit('ADD A,31', [0xc6, 31], 7); emit('LD E,A', [0x5f], 4)
            if field == 7:
                jump('JP raw_second_half', 0xc3, 'raw_second_half', 10)
        a.label('raw_done')
        emit('PUSH HL', [0xe5], 11); emit('POP IX', [0xdd, 0xe1], 14); emit('RET', [0xc9], 10)

    stage = 'cache'
    if selective_cache:
        # B is the original row count (4, 8 or 12). One flag covers four
        # consecutive source rows and therefore one 256-byte cache page.
        a.label('cache_copy')
        emit('PUSH BC', [0xc5], 11)
        load('LD A,(cache_mask_shift)', 0x3a, 'cache_mask_shift', 13)
        emit('ADD A,A', [0x87], 4)
        jump('JR NZ,cache_mask_ready', 0x20, 'cache_mask_ready', [7, 12], True)
        emit('PUSH HL', [0xe5], 11)
        load('LD HL,(cache_mask_source)', 0x2a, 'cache_mask_source', 16)
        emit('LD A,(HL)', [0x7e], 7); emit('INC HL', [0x23], 6)
        load('LD (cache_mask_source),HL', 0x22, 'cache_mask_source', 16)
        emit('POP HL', [0xe1], 10)
        # The exhausted 80h sentinel left carry set. All loads above retain
        # it, so ADC appends a new sentinel without a redundant SCF.
        emit('ADC A,A', [0x8f], 4)
        a.label('cache_mask_ready')
        if cache_columns == 16:
            # A byte holds four MSB-first pairs. The first shift/reload above
            # produces bit one in carry; retain it while consuming bit two.
            emit('LD C,0', [0x0e,0], 7); emit('RL C', [0xcb,0x11], 8)
            emit('ADD A,A', [0x87], 4); emit('RL C', [0xcb,0x11], 8)
        load('LD (cache_mask_shift),A', 0x32, 'cache_mask_shift', 13)
        if cache_columns == 16:
            emit('LD A,C', [0x79], 4); emit('OR A', [0xb7], 4)
            jump('JR Z,cache_skip_four', 0x28, 'cache_skip_four', [7,12], True)
            emit('LD B,4', [0x06,4], 7); emit('CP 3', [0xfe,3], 7)
            jump('JR NZ,cache_half', 0x20, 'cache_half', [7,12], True)
        else:
            jump('JP NC,cache_skip_four', 0xd2, 'cache_skip_four', 10)
            emit('LD B,4', [0x06, 4], 7)
        jump('CALL cache_copy_rows', 0xcd, 'cache_copy_rows', 17)
        if cache_columns == 16:
            jump('JR cache_four_done', 0x18, 'cache_four_done', 12, True)
        else:
            jump('JP cache_four_done', 0xc3, 'cache_four_done', 10)
        a.label('cache_skip_four')
        wordop('LD BC,128', 0x01, 128, 10); emit('ADD HL,BC', [0x09], 11)
        emit('INC D', [0x14], 4); emit('LD A,D', [0x7a], 4)
        emit('AND 3', [0xe6, 3], 7); emit('OR cache_page', [0xf6, CACHE >> 8], 7)
        emit('LD D,A', [0x57], 4)
        a.label('cache_four_done')
        emit('POP BC', [0xc1], 10)
        emit('LD A,B', [0x78], 4); emit('SUB 4', [0xd6, 4], 7); emit('LD B,A', [0x47], 4)
        jump('JP NZ,cache_copy', 0xc2, 'cache_copy', 10)
        emit('RET', [0xc9], 10)
    if cache_columns == 16:
        a.label('cache_half')
        # C=1 right half, C=2 left half. Each row preserves it across LDI.
        emit('CP 1', [0xfe,1], 7)
        jump('JR NZ,cache_half_start', 0x20, 'cache_half_start', [7,12], True)
        # Groups start at source low byte 0/128, so +16 cannot carry.
        emit('LD A,L', [0x7d], 4); emit('ADD A,16', [0xc6,16], 7); emit('LD L,A', [0x6f], 4)
        emit('LD A,E', [0x7b], 4); emit('ADD A,16', [0xc6,16], 7); emit('LD E,A', [0x5f], 4)
        a.label('cache_half_start')
        a.label('cache_half_row'); emit('PUSH BC', [0xc5], 11)
        for _ in range(16): emit('LDI', [0xed,0xa0], 16)
        wordop('LD BC,16', 0x01, 16, 10); emit('ADD HL,BC', [0x09], 11)
        emit('POP BC', [0xc1], 10)
        cache_advance('cache_half_advanced',48)
        jump('DJNZ cache_half_row', 0x10, 'cache_half_row', [8,13], True)
        emit('DEC C', [0x0d], 4)
        jump('JR NZ,cache_four_done', 0x20, 'cache_four_done', [7,12], True)
        wordop('LD BC,-16', 0x01, 65520, 10); emit('ADD HL,BC', [0x09], 11)
        emit('LD E,1', [0x1e,1], 7)
        jump('JR cache_four_done', 0x18, 'cache_four_done', 12, True)
    for zero in (False, True):
        name = 'cache_zero' if zero else 'cache_copy_rows' if selective_cache else 'cache_copy'
        a.label(name)
        if unrolled_cache and not zero:
            # Two iterations of two rows fit the actual movie's code map.
            # The first row cannot cross a cache page; the second may.
            emit('LD B,2', [0x06,2], 7); a.label('cache_pair')
            emit('PUSH BC', [0xc5], 11)
            for _ in range(32): emit('LDI', [0xed,0xa0], 16)
            emit('LD A,E', [0x7b], 4); emit('ADD A,32', [0xc6,32], 7); emit('LD E,A', [0x5f], 4)
            for _ in range(32): emit('LDI', [0xed,0xa0], 16)
            emit('POP BC', [0xc1], 10); cache_advance('cache_pair_advanced',32)
            # The 64 LDI instructions alone exceed the relative range.
            emit('DEC B', [0x05], 4); jump('JP NZ,cache_pair', 0xc2, 'cache_pair', 10)
            emit('RET', [0xc9], 10)
            continue
        if zero:
            emit('XOR A', [0xaf], 4)
            for _ in range(32):
                emit('LD (DE),A', [0x12], 7); emit('INC E', [0x1c], 4)
        else:
            emit('PUSH BC', [0xc5], 11)
            for _ in range(32):
                emit('LDI', [0xed, 0xa0], 16)
            emit('POP BC', [0xc1], 10)
        cache_advance(name+'_advanced', 32)
        jump('DJNZ cache_row', 0x10, name, [8, 13], True)
        emit('RET', [0xc9], 10)

    stage = 'motion'
    a.label('motion')
    emit('CP zero_vector', [0xfe, len(offsets)], 7)
    jump('JP Z,clear_tile', 0xca, 'clear_tile', 10)
    emit('LD L,A', [0x6f], 4); emit('LD H,vector_x', [0x26, VECTOR_X >> 8], 7)
    emit('LD A,(HL)', [0x7e], 7); emit('LD B,A', [0x47], 4)
    load('LD A,(target_low)', 0x3a, 'target', 13)
    emit('AND 31', [0xe6, 31], 7); emit('ADD A,B', [0x80], 4); emit('INC A', [0x3c], 4)
    emit('LD C,A', [0x4f], 4)
    emit('INC H', [0x24], 4); emit('LD B,(HL)', [0x46], 7)
    emit('INC H', [0x24], 4); emit('LD A,(HL)', [0x7e], 7)
    load('LD (phase),A', 0x32, 'phase', 13)
    load('LD A,(stripe_y)', 0x3a, 'stripe_y', 13)
    emit('ADD A,B', [0x80], 4); emit('AND 15', [0xe6, 15], 7)
    emit('LD L,A', [0x6f], 4); emit('LD H,row_low', [0x26, ROW_LOW >> 8], 7)
    emit('LD A,(HL)', [0x7e], 7); emit('ADD A,C', [0x81], 4); emit('LD E,A', [0x5f], 4)
    emit('INC H', [0x24], 4); emit('LD D,(HL)', [0x56], 7)
    load('LD HL,(target)', 0x2a, 'target', 16)
    if not unrolled_motion:
        emit('LD B,8', [0x06, 8], 7)
    load('LD A,(phase)', 0x3a, 'phase', 13)
    for phase in (0, 2, 4):
        emit(f'CP {phase}', [0xfe, phase], 7)
        jump(f'JP Z,predict_{phase}', 0xca, f'predict_{phase}', 10)
    jump('JP predict_6', 0xc3, 'predict_6', 10)
    for phase in (0, 2, 4, 6):
        a.label(f'predict_{phase}')
        if unrolled_motion:
            if phase:
                # Alternate C retains the Huffman bit page. Alternate DE is
                # free between Huffman calls and survives every AY interrupt.
                emit('PUSH HL', [0xe5], 11); emit('EXX', [0xd9], 4)
                emit('POP DE', [0xd1], 10); emit('EXX', [0xd9], 4)
            for row in range(8):
                if phase == 0:
                    emit('LD A,(DE)', [0x1a], 7); emit('LD (HL),A', [0x77], 7)
                    emit('INC E', [0x1c], 4); emit('INC L', [0x2c], 4)
                    emit('LD A,(DE)', [0x1a], 7); emit('LD (HL),A', [0x77], 7)
                elif phase == 4:
                    emit('LD A,(DE)', [0x1a], 7); emit('INC E', [0x1c], 4); emit('LD L,A', [0x6f], 4)
                    emit('LD H,left_shift', [0x26, 0xf4], 7); emit('LD B,(HL)', [0x46], 7)
                    emit('LD A,(DE)', [0x1a], 7); emit('LD L,A', [0x6f], 4)
                    emit('LD H,right_shift', [0x26, 0xfc], 7); emit('LD A,(HL)', [0x7e], 7)
                    emit('OR B', [0xb0], 4)
                    emit('EXX', [0xd9], 4); emit('LD (DE),A', [0x12], 7)
                    emit('INC E', [0x1c], 4); emit('EXX', [0xd9], 4)
                    emit('LD H,left_shift', [0x26, 0xf4], 7); emit('LD B,(HL)', [0x46], 7)
                    emit('INC E', [0x1c], 4); emit('LD A,(DE)', [0x1a], 7); emit('LD L,A', [0x6f], 4)
                    emit('LD H,right_shift', [0x26, 0xfc], 7); emit('LD A,(HL)', [0x7e], 7)
                    emit('OR B', [0xb0], 4)
                else:
                    rotate, opcode, mask = ('RLCA', 0x07, 3) if phase == 2 else ('RRCA', 0x0f, 63)
                    emit('LD A,(DE)', [0x1a], 7)
                    emit(rotate, [opcode], 4); emit(rotate, [opcode], 4); emit('LD C,A', [0x4f], 4)
                    emit('INC E', [0x1c], 4); emit('LD A,(DE)', [0x1a], 7)
                    emit(rotate, [opcode], 4); emit(rotate, [opcode], 4); emit('LD B,A', [0x47], 4)
                    emit('XOR C', [0xa9], 4); emit('AND merge_mask', [0xe6, mask], 7); emit('XOR C', [0xa9], 4)
                    emit('EXX', [0xd9], 4); emit('LD (DE),A', [0x12], 7)
                    emit('INC E', [0x1c], 4); emit('EXX', [0xd9], 4)
                    emit('LD C,B', [0x48], 4); emit('INC E', [0x1c], 4); emit('LD A,(DE)', [0x1a], 7)
                    emit(rotate, [opcode], 4); emit(rotate, [opcode], 4)
                    emit('XOR C', [0xa9], 4); emit('AND merge_mask', [0xe6, mask], 7); emit('XOR C', [0xa9], 4)
                if phase:
                    emit('EXX', [0xd9], 4); emit('LD (DE),A', [0x12], 7)
                    if row < 7:
                        emit('LD A,E', [0x7b], 4); emit('ADD A,31', [0xc6, 31], 7); emit('LD E,A', [0x5f], 4)
                    emit('EXX', [0xd9], 4)
                if row < 7:
                    cache_advance(f'predict_{phase}_{row}_advanced', 63 if not phase else 62)
                    if not phase:
                        next_output_row()
            emit('RET', [0xc9], 10)
            continue
        if not phase:
            emit('LD A,(DE)', [0x1a], 7); emit('LD (HL),A', [0x77], 7)
            emit('INC E', [0x1c], 4); emit('INC L', [0x2c], 4)
            emit('LD A,(DE)', [0x1a], 7); emit('LD (HL),A', [0x77], 7)
        else:
            emit('PUSH BC', [0xc5], 11); emit('PUSH HL', [0xe5], 11)
            emit('LD A,(DE)', [0x1a], 7); emit('INC E', [0x1c], 4); emit('LD L,A', [0x6f], 4)
            emit('LD H,left_shift', [0x26, 0xf0+phase], 7); emit('LD B,(HL)', [0x46], 7)
            emit('LD A,(DE)', [0x1a], 7); emit('LD L,A', [0x6f], 4)
            emit('LD H,right_shift', [0x26, 0xf8+phase], 7); emit('LD A,(HL)', [0x7e], 7)
            emit('OR B', [0xb0], 4); emit('LD B,A', [0x47], 4)
            emit('LD H,left_shift', [0x26, 0xf0+phase], 7); emit('LD C,(HL)', [0x4e], 7)
            emit('INC E', [0x1c], 4); emit('LD A,(DE)', [0x1a], 7); emit('LD L,A', [0x6f], 4)
            emit('LD H,right_shift', [0x26, 0xf8+phase], 7); emit('LD A,(HL)', [0x7e], 7)
            emit('OR C', [0xb1], 4); emit('POP HL', [0xe1], 10)
            emit('LD (HL),B', [0x70], 7); emit('INC L', [0x2c], 4); emit('LD (HL),A', [0x77], 7)
            emit('POP BC', [0xc1], 10)
        cache_advance(f'predict_{phase}_advanced', 63 if not phase else 62)
        next_output_row()
        jump('DJNZ predict_row', 0x10, f'predict_{phase}', [8, 13], True)
        emit('RET', [0xc9], 10)
    a.label('clear_tile')
    load('LD HL,(target)', 0x2a, 'target', 16)
    if unrolled_motion:
        for row in range(8):
            emit('XOR A', [0xaf], 4)
            emit('LD (HL),A', [0x77], 7); emit('INC L', [0x2c], 4); emit('LD (HL),A', [0x77], 7)
            if row < 7:
                next_output_row()
        emit('RET', [0xc9], 10)
    else:
        emit('LD B,8', [0x06, 8], 7)
        a.label('clear_row'); emit('XOR A', [0xaf], 4)
        emit('LD (HL),A', [0x77], 7); emit('INC L', [0x2c], 4); emit('LD (HL),A', [0x77], 7)
        next_output_row(); jump('DJNZ clear_row', 0x10, 'clear_row', [8, 13], True); emit('RET', [0xc9], 10)

    stage = 'patch'
    a.label('patches')
    load('LD HL,(bitmap_masks)', 0x2a, 'bitmap_masks', 16)
    emit('LD B,(HL)', [0x46], 7); emit('INC HL', [0x23], 6)
    emit('LD C,(HL)', [0x4e], 7); emit('INC HL', [0x23], 6)
    load('LD (bitmap_masks),HL', 0x22, 'bitmap_masks', 16)
    emit('LD A,B', [0x78], 4); emit('OR C', [0xb1], 4)
    jump('JP Z,attributes', 0xca, 'attributes', 10)
    a.label('patches_nonzero')
    if sparse_patches:
        load('LD HL,(target)', 0x2a, 'target', 16)
        for half in range(2):
            if half:
                a.label('patch_second_half')
                # Every tile begins at an even column. An early last byte
                # may be in either column and any of the first four rows.
                emit('LD A,L', [0x7d], 4); emit('AND 30', [0xe6, 30], 7)
                emit('OR 128', [0xf6, 128], 7); emit('LD L,A', [0x6f], 4)
                emit('LD B,C', [0x41], 4)
            emit('LD A,B', [0x78], 4); emit('OR A', [0xb7], 4)
            jump('JP Z,empty_bitmap_half', 0xca, 'patch_second_half' if not half else 'attributes', 10)
            for field in range(8):
                tag = half*8+field
                emit('SLA B', [0xcb, 0x20], 8)
                jump('JP NC,keep_bitmap', 0xd2, f'keep_bm_{tag}', 10)
                if field < 7:
                    # JP NC preserves SLA's Z flag. If B is now zero, the
                    # current byte is the last correction; reuse field 7's
                    # apply/exit code without changing the target cursor.
                    jump('JP Z,last_bitmap_patch', 0xca, f'last_bm_{half}', 10)
                else:
                    a.label(f'last_bm_{half}')
                emit('LD A,(HL)', [0x7e], 7); emit('EXX', [0xd9], 4)
                jump('CALL bitmap', 0xcd, 'bitmap', 17); emit('EXX', [0xd9], 4)
                emit('LD (HL),A', [0x77], 7)
                a.label(f'keep_bm_{tag}')
                if field < 7:
                    if field % 2 == 0:
                        emit('INC L', [0x2c], 4)
                    elif field in (1, 5):
                        emit('DEC L', [0x2d], 4); emit('SET 5,L', [0xcb, 0xed], 8)
                    else:
                        emit('LD A,L', [0x7d], 4); emit('ADD A,31', [0xc6, 31], 7); emit('LD L,A', [0x6f], 4)
    else:
        load('LD DE,(target)', (0xed, 0x5b), 'target', 20)
    for field in range(0 if sparse_patches else 16):
        if field == 8:
            if skip_empty:
                a.label('skip_half_0')
                # A skipped first half still advances the raster by four rows.
                # Normal first-half traversal already arrived here via JP.
                emit('LD A,E', [0x7b], 4); emit('ADD A,128', [0xc6, 128], 7); emit('LD E,A', [0x5f], 4)
                a.label('second_half')
            emit('LD B,C', [0x41], 4)
        if skip_empty and field in (0, 8):
            emit('LD A,B', [0x78], 4); emit('OR A', [0xb7], 4)
            jump('JP Z,empty_bitmap_half', 0xca, 'skip_half_0' if field == 0 else 'attributes', 10)
        emit('SLA B', [0xcb, 0x20], 8); jump('JP NC,keep_bitmap', 0xd2, f'keep_bm_{field}', 10)
        emit('LD A,(DE)', [0x1a], 7); emit('EXX', [0xd9], 4)
        jump('CALL bitmap', 0xcd, 'bitmap', 17); emit('EXX', [0xd9], 4); emit('LD (DE),A', [0x12], 7)
        a.label(f'keep_bm_{field}')
        if field < 15:
            if not field % 2:
                emit('INC E', [0x1c], 4)
            else:
                emit('LD A,E', [0x7b], 4); emit('ADD A,31', [0xc6, 31], 7); emit('LD E,A', [0x5f], 4)
        if skip_empty and field == 7:
            jump('JP second_half', 0xc3, 'second_half', 10)
    a.label('attributes')
    if hybrid:
        emit('RET', [0xc9], 10)
        stage = 'attribute_pass'
        a.label('attribute_pass')
        if raw_attributes:
            load('LD A,(raw_attributes)', 0x3a, 'raw_attributes', 13)
            emit('OR A', [0xb7], 4)
            jump('JR Z,coded_attributes', 0x28, 'coded_attributes', [7, 12], True)
            load('LD HL,(literal_source)', 0x2a, 'literal_source', 16)
            wordop('LD DE,attributes', 0x11, FRAME+3072, 10)
            wordop('LD BC,768', 0x01, 768, 10)
            emit('LDIR', [0xed, 0xb0], [16, 21])
            load('LD (literal_source),HL', 0x22, 'literal_source', 16)
            emit('RET', [0xc9], 10)
            a.label('coded_attributes')
        if attribute_flags:
            from attribute_mask_z80 import CODE as attribute_controller
            wordop('JP attribute_flag_scan',0xc3,attribute_controller,10)
            a.label('attribute_group_apply')
        else:
            load('LD HL,(attribute_masks)', 0x2a, 'attribute_masks', 16)
            wordop('LD DE,attributes', 0x11, FRAME+3072, 10)
            a.label('attribute_mask')
            emit('LD A,(HL)', [0x7e], 7); emit('INC HL', [0x23], 6)
            emit('OR A', [0xb7], 4); jump('JP Z,attribute_empty', 0xca, 'attribute_empty', 10)
            emit('LD B,A', [0x47], 4)
        for field in range(8):
            emit('SLA B', [0xcb, 0x20], 8); jump('JP NC,keep_attribute', 0xd2, f'keep_raster_{field}', 10)
            emit('LD A,(DE)', [0x1a], 7); emit('LD C,A', [0x4f], 4); emit('EXX', [0xd9], 4)
            jump('CALL attribute', 0xcd, 'attribute', 17); emit('EXX', [0xd9], 4)
            emit('XOR C', [0xa9], 4); emit('LD (DE),A', [0x12], 7)
            a.label(f'keep_raster_{field}')
            emit('INC E' if field < 7 else 'INC DE', [0x1c if field < 7 else 0x13], 4 if field < 7 else 6)
        if attribute_flags:
            emit('RET', [0xc9], 10)
        else:
            jump('JP attribute_next', 0xc3, 'attribute_next', 10)
            a.label('attribute_empty')
            emit('LD A,E', [0x7b], 4); emit('ADD A,8', [0xc6, 8], 7); emit('LD E,A', [0x5f], 4)
            jump('JR NC,attribute_next', 0x30, 'attribute_next', [7, 12], True)
            emit('INC D', [0x14], 4)
            a.label('attribute_next')
            emit('LD A,D', [0x7a], 4); emit('CP attribute_end', [0xfe, (FRAME+3840) >> 8], 7)
            jump('JP NZ,attribute_mask', 0xc2, 'attribute_mask', 10)
            load('LD (attribute_masks),HL', 0x22, 'attribute_masks', 16); emit('RET', [0xc9], 10)
    else:
        emit_tile_attributes(a, emit, load, jump, skip_empty)
    a.label('state')
    for name in ('source', 'vectors', 'bitmap_masks', 'attribute_masks', 'target', 'attr_target', 'cache_read', 'cache_write'):
        a.label(name); a.word(0)
    for name, value in [('bit_page', bit_base), ('stripe_y', 0), ('stripes_left', 0), ('tiles_left', 0), ('phase', 0), ('attr_bits', 0)]:
        a.label(name); a.emit(value)
    if hybrid:
        a.label('cache_enabled'); a.emit(1)
    if split_literals:
        a.label('literal_source'); a.word(0)
    if raw_attributes:
        a.label('raw_attributes'); a.emit(0)
    if selective_cache:
        a.label('cache_mask_source'); a.word(0)
        a.label('cache_mask_shift'); a.emit(0)
    a.label('end')
    if a.pc > VECTOR_X:
        raise ValueError('frame code collides with motion tables')
    regions = layout['regions']+[
        (VECTOR_X, bytes((-dx//4) & 255 for dx, _ in offsets)),
        (VECTOR_Y, bytes((-dy) & 255 for _, dy in offsets)),
        (VECTOR_PHASE, bytes(2*((-dx) % 4) for dx, _ in offsets)),
        (ROW_LOW, bytes((row*64) & 255 for row in range(16))),
        (ROW_HIGH, bytes((CACHE+row*64) >> 8 for row in range(16)))]
    code, labels = a.resolve(), dict(a.labels)
    if attribute_flags:
        import attribute_mask_z80 as attributes
        extra,labels,rows=attributes.build(labels)
        regions.append((attributes.CODE,extra)); listing.extend(rows)
    if skip_noop_runs:
        a = MiniAssembler(NOOP_SCANNER); a.labels.update(labels)
        stage = 'noop_control'
        load('LD DE,(bitmap_masks)',(0xed,0x5b),'bitmap_masks',20)
        emit('EX DE,HL',[0xeb],4)
        # Mask pairs always start even; neither byte crosses a page.
        # Vectors can cross pages in zero-copy packets: retain INC DE.
        emit('LD B,(HL)',[0x46],7)
        emit('INC L' if fast_noop_scan else 'INC HL',[0x2c if fast_noop_scan else 0x23],4 if fast_noop_scan else 6)
        emit('LD C,(HL)',[0x4e],7)
        emit('DEC L' if fast_noop_scan else 'DEC HL',[0x2d if fast_noop_scan else 0x2b],4 if fast_noop_scan else 6)
        emit('LD A,B',[0x78],4); emit('OR C',[0xb1],4)
        jump('JP NZ,scan_zero_patch',0xc2,'scan_zero_patch',10)
        load('LD A,(tiles_left)',0x3a,'tiles_left',13)
        emit('LD B,A',[0x47],4); emit('LD C,0',[0x0e,0],7)
        a.label('scan_skip')
        emit('INC DE',[0x13],6)
        emit('INC L' if fast_noop_scan else 'INC HL',[0x2c if fast_noop_scan else 0x23],4 if fast_noop_scan else 6)
        emit('INC HL',[0x23],6)
        emit('INC C',[0x0c],4); jump('DJNZ scan_check',0x10,'scan_check',[8,13],True)
        a.label('scan_done')
        load('LD (bitmap_masks),HL',0x22,'bitmap_masks',16)
        load('LD (vectors),DE',(0xed,0x53),'vectors',20)
        emit('LD A,B',[0x78],4); load('LD (tiles_left),A',0x32,'tiles_left',13)
        load('LD HL,(target)',0x2a,'target',16)
        emit('LD A,C',[0x79],4); emit('ADD A,A',[0x87],4)
        emit('LD E,A',[0x5f],4); emit('LD D,0',[0x16,0],7); emit('ADD HL,DE',[0x19],11)
        load('LD (target),HL',0x22,'target',16)
        emit('LD A,B',[0x78],4); emit('OR A',[0xb7],4)
        jump('JP Z,stripe_done',0xca,'stripe_done',10); jump('JP tile',0xc3,'tile',10)
        a.label('scan_check')
        emit('LD A,(DE)',[0x1a],7)
        if fast_noop_scan:
            emit('OR (HL)',[0xb6],7); emit('INC L',[0x2c],4)
        else:
            emit('OR A',[0xb7],4); jump('JP NZ,scan_done',0xc2,'scan_done',10)
            emit('LD A,(HL)',[0x7e],7); emit('INC HL',[0x23],6)
        # DEC HL preserves Z from OR; DEC L would test the pointer instead.
        emit('OR (HL)',[0xb6],7); emit('DEC HL',[0x2b],6)
        jump('JP Z,scan_skip',0xca,'scan_skip',10); jump('JP scan_done',0xc3,'scan_done',10)
        a.label('scan_zero_patch')
        emit('INC DE',[0x13],6); load('LD (vectors),DE',(0xed,0x53),'vectors',20)
        emit('INC L' if fast_noop_scan else 'INC HL',[0x2c if fast_noop_scan else 0x23],4 if fast_noop_scan else 6)
        emit('INC HL',[0x23],6)
        load('LD (bitmap_masks),HL',0x22,'bitmap_masks',16)
        jump('CALL patches_nonzero',0xcd,'patches_nonzero',17); jump('JP tile_done',0xc3,'tile_done',10)
        if a.pc > (NOOP_SCANNER+128 if encoded_noop_runs or skip_static_stripes else 0x7b00):
            raise ValueError('no-op scanner overlaps following code')
        labels.update({k:v for k,v in a.labels.items() if k not in labels})
        labels['noop_scanner_end'] = a.pc
        regions.append((NOOP_SCANNER,a.resolve()))
    if encoded_noop_runs:
        origin = labels['encoded_zero_run']
        a = MiniAssembler(origin); a.labels.update(labels)
        stage = 'encoded_noop_control'
        emit('AND run length',[0xe6,31],7); emit('LD C,A',[0x4f],4)
        if encoded_noop_runs == 'inplace':
            emit('LD B,0',[0x06,0],7); emit('ADD HL,BC',[0x09],11)
            load('LD (vectors),HL',0x22,'vectors',16)
        load('LD A,(tiles_left)',0x3a,'tiles_left',13); emit('SUB C',[0x91],4)
        load('LD (tiles_left),A',0x32,'tiles_left',13); emit('LD B,A',[0x47],4)
        emit('LD A,C',[0x79],4); emit('ADD A,A',[0x87],4)
        emit('LD E,A',[0x5f],4); emit('LD D,0',[0x16,0],7)
        load('LD HL,(bitmap_masks)',0x2a,'bitmap_masks',16); emit('ADD HL,DE',[0x19],11)
        load('LD (bitmap_masks),HL',0x22,'bitmap_masks',16)
        load('LD HL,(target)',0x2a,'target',16); emit('ADD HL,DE',[0x19],11)
        load('LD (target),HL',0x22,'target',16)
        emit('LD A,B',[0x78],4); emit('OR A',[0xb7],4)
        jump('JP Z,stripe_done',0xca,'stripe_done',10); jump('JP tile',0xc3,'tile',10)
        if a.pc > 0x7b00: raise ValueError('encoded run handler overlaps initializer')
        labels['encoded_run_end'] = a.pc
        regions.append((origin,a.resolve()))
    if skip_static_stripes:
        a = MiniAssembler(STATIC_EDGE); a.labels.update(labels)
        stage = 'static_edge'
        load('LD HL,(vectors)',0x2a,'vectors',16); emit('LD A,(HL)',[0x7e],7)
        emit('OR A',[0xb7],4); jump('JP NZ,regular_stripe',0xc2,'regular_stripe',10)
        wordop('LD DE,16',0x11,16,10); emit('ADD HL,DE',[0x19],11)
        load('LD (vectors),HL',0x22,'vectors',16)
        emit('LD E,32',[0x1e,32],7)
        load('LD HL,(bitmap_masks)',0x2a,'bitmap_masks',16); emit('ADD HL,DE',[0x19],11)
        load('LD (bitmap_masks),HL',0x22,'bitmap_masks',16)
        load('LD HL,(target)',0x2a,'target',16); emit('ADD HL,DE',[0x19],11)
        load('LD (target),HL',0x22,'target',16)
        jump('JP stripe_done',0xc3,'stripe_done',10)
        labels['static_edge_end'] = a.pc
        if a.pc > 0x7b00: raise ValueError('static edge handler overlaps initializer')
        regions.append((STATIC_EDGE,a.resolve()))
    return code, labels, listing, regions


def emit_tile_attributes(a, emit, load, jump, skip_empty):
    """Unchanged FPD1 path, retained byte-for-byte for baseline timings."""
    load('LD A,(tiles_left)', 0x3a, 'tiles_left', 13); emit('AND 1', [0xe6, 1], 7)
    jump('JR NZ,reuse_attr_bits', 0x20, 'reuse_attr_bits', [7, 12], True)
    load('LD HL,(attribute_masks)', 0x2a, 'attribute_masks', 16)
    emit('LD B,(HL)', [0x46], 7); emit('INC HL', [0x23], 6)
    load('LD (attribute_masks),HL', 0x22, 'attribute_masks', 16)
    jump('JR attr_ready', 0x18, 'attr_ready', 12, True)
    a.label('reuse_attr_bits'); load('LD A,(attr_bits)', 0x3a, 'attr_bits', 13); emit('LD B,A', [0x47], 4)
    a.label('attr_ready')
    if skip_empty:
        emit('LD A,B', [0x78], 4); emit('AND F0h', [0xe6, 0xf0], 7)
        jump('JP Z,empty_attr_nibble', 0xca, 'empty_attr_nibble', 10)
    load('LD DE,(attr_target)', (0xed, 0x5b), 'attr_target', 20)
    for field in range(4):
        emit('SLA B', [0xcb, 0x20], 8); jump('JP NC,keep_attribute', 0xd2, f'keep_at_{field}', 10)
        emit('LD A,(DE)', [0x1a], 7); emit('LD C,A', [0x4f], 4); emit('EXX', [0xd9], 4)
        jump('CALL attribute', 0xcd, 'attribute', 17); emit('EXX', [0xd9], 4)
        emit('XOR C', [0xa9], 4); emit('LD (DE),A', [0x12], 7)
        a.label(f'keep_at_{field}')
        if field in (0, 2):
            emit('INC E', [0x1c], 4)
        elif field == 1:
            emit('LD A,E', [0x7b], 4); emit('ADD A,31', [0xc6, 31], 7); emit('LD E,A', [0x5f], 4)
    emit('LD A,B', [0x78], 4); load('LD (attr_bits),A', 0x32, 'attr_bits', 13); emit('RET', [0xc9], 10)
    if skip_empty:
        a.label('empty_attr_nibble')
        emit('LD A,B', [0x78], 4)
        for _ in range(4):
            emit('ADD A,A', [0x87], 4)
        load('LD (attr_bits),A', 0x32, 'attr_bits', 13); emit('RET', [0xc9], 10)
