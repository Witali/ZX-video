/* Portable C89 counterpart of lzma_z80.asm; fixed raw LZMA1 lc=lp=0, pb=2.
 * Same 1943 probability models, output <=15872 bytes, required EOS.
 * No host calls, headers, inline assembly, allocation or compiler intrinsics.
 * Both target compilers use 16-bit unsigned int and 32-bit unsigned long.
 * Flat synchronous benchmark ABI: 16-bit mailbox at B000:
 * [0] input, [1] input end, [2] output, [3] output size,
 * [4] status (0 success, 1 error), [5] consumed, [6] produced,
 * [7] type widths: sizeof(U16)*256 + sizeof(U32), expected 0x0204.
 * Probability storage A000..AF2E; output is also the match dictionary.
 */
typedef unsigned char U8;
typedef unsigned int U16;
typedef unsigned long U32;
#define P ((U16 *)0xa000)
#define MAIL ((U16 *)0xb000)
#define MATCH 0
#define REP 48
#define G0 60
#define G1 72
#define G2 84
#define SHORT 96
#define SLOT 144
#define DIST 400
#define ALIGN 515
#define LEN 531
#define RLEN 853
#define LIT 1175
#define NUMPROBS 1943

static U8 *src, *limit, *dst, *start, *finish;
static U32 range_value, code_value;
static U16 reps[4];
static U8 bad, state, pos;

static U8 read_byte(void)
{
    if (src >= limit) { bad = 1; return 0; }
    return *src++;
}

static void normalize(void)
{
    if (range_value < (U32)0x1000000L) {
        range_value <<= 8;
        code_value = (code_value << 8) | read_byte();
    }
}

static U8 bit(U16 *prob)
{
    U32 bound;
    U16 value;
    normalize();
    value = *prob;
    bound = (range_value >> 11) * (U32)value;
    if (code_value < bound) {
        range_value = bound;
        *prob = value + ((2048 - value) >> 5);
        return 0;
    }
    range_value -= bound;
    code_value -= bound;
    *prob = value - (value >> 5);
    return 1;
}

static U16 tree(U16 base, U8 count)
{
    U16 node, top;
    node = 1;
    top = (U16)1 << count;
    do { node = (node << 1) | bit(P + base + node); } while (--count);
    return node - top;
}

static U16 reverse(U16 base, U8 count)
{
    U16 node, value, mask;
    U8 b;
    node = mask = 1;
    value = 0;
    do {
        b = bit(P + base + node);
        node = (node << 1) | b;
        if (b) value |= mask;
        mask <<= 1;
    } while (--count);
    return value;
}

static U16 length(U16 base)
{
    if (!bit(P + base)) return tree(base + 2 + (U16)pos * 8, 3);
    if (!bit(P + base + 1)) return 8 + tree(base + 34 + (U16)pos * 8, 3);
    return 16 + tree(base + 66, 8);
}

static U32 distance(U16 len)
{
    U16 slot;
    U8 n, count;
    U32 value, middle;
    slot = tree(SLOT + (len < 4 ? len : 3) * 64, 6);
    if (slot < 4) return slot;
    n = (U8)((slot >> 1) - 1);
    value = (U32)(2 | (slot & 1)) << n;
    if (slot < 14) return value + reverse(DIST + (U16)value - slot, n);
    count = n - 4;
    middle = 0;
    do {
        normalize();
        range_value >>= 1;
        middle <<= 1;
        if (code_value >= range_value) {
            code_value -= range_value;
            middle |= 1;
        }
    } while (--count);
    return value + (middle << 4) + reverse(ALIGN, 4);
}

static void literal(void)
{
    U16 node;
    U8 match, matchbit, b;
    node = 1;
    if (state >= 7) {
        match = *(dst - reps[0] - 1);
        do {
            matchbit = match >> 7;
            match <<= 1;
            b = bit(P + LIT + ((1 + (U16)matchbit) << 8) + node);
            node = (node << 1) | b;
            if (matchbit != b) break;
        } while (node < 256);
    }
    while (node < 256) node = (node << 1) | bit(P + LIT + node);
    *dst++ = (U8)node;
    state = state < 4 ? 0 : (state < 10 ? state - 3 : state - 6);
}

static U8 decode(void)
{
    U16 i, len, d, index;
    U32 wide;
    U8 *copy;
    for (i = 0; i < NUMPROBS; ++i) P[i] = 1024;
    range_value = (U32)0xffffffffL;
    code_value = 0;
    state = bad = 0;
    for (i = 0; i < 4; ++i) reps[i] = 0;
    if (read_byte() != 0) return 1;
    for (i = 0; i < 4; ++i) code_value = (code_value << 8) | read_byte();
    if (bad || code_value == (U32)0xffffffffL) return 1;
    for (;;) {
        pos = (U8)((U16)(dst - start) & 3);
        index = (U16)state * 4 + pos;
        if (!bit(P + MATCH + index)) {
            if (dst == finish || bad) return 1;
            literal();
            if (bad) return 1;
            continue;
        }
        if (!bit(P + REP + state)) {
            reps[3] = reps[2]; reps[2] = reps[1]; reps[1] = reps[0];
            len = length(LEN);
            state = state < 7 ? 7 : 10;
            wide = distance(len);
            if (wide == (U32)0xffffffffL) {
                normalize();
                return bad || code_value != 0 || dst != finish || src != limit;
            }
            if (wide >= (U32)16384L) return 1;
            reps[0] = (U16)wide;
            len += 2;
        } else {
            len = 0;
            if (!bit(P + G0 + state)) {
                if (!bit(P + SHORT + index)) {
                    state = state < 7 ? 9 : 11;
                    len = 1;
                }
            } else {
                if (!bit(P + G1 + state)) d = reps[1];
                else {
                    if (!bit(P + G2 + state)) d = reps[2];
                    else { d = reps[3]; reps[3] = reps[2]; }
                    reps[2] = reps[1];
                }
                reps[1] = reps[0]; reps[0] = d;
            }
            if (!len) {
                len = length(RLEN) + 2;
                state = state < 7 ? 8 : 11;
            }
        }
        d = reps[0] + 1;
        if (bad || d > (U16)(dst - start) || len > (U16)(finish - dst)) return 1;
        copy = dst - d;
        do { *dst++ = *copy++; } while (--len);
    }
}

/* Called directly by the CPU harness; no operating-system startup is linked. */
void entry(void)
{
    src = (U8 *)MAIL[0];
    limit = (U8 *)MAIL[1];
    dst = start = (U8 *)MAIL[2];
    finish = dst + MAIL[3];
    if (MAIL[3] > 15872 || (U16)finish < (U16)start) MAIL[4] = 1;
    else MAIL[4] = decode();
    MAIL[5] = (U16)(src - (U8 *)MAIL[0]);
    MAIL[6] = (U16)(dst - start);
    MAIL[7] = sizeof(U16) * 256 + sizeof(U32);
}
