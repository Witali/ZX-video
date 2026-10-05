#define OPT 0
/* Two-bit G.726 /16 kbit/s, uniform PCM interface.
 * Adapted from FFmpeg n8.0 libavcodec/g726.c,
 * Copyright (c) 2004 Roman Shaposhnik; modifications (c) 2026 ZX-video.
 * SPDX-License-Identifier: LGPL-2.1-or-later
 * See COPYING.LGPLv2.1 and the unmodified ffmpeg-reference.c.
 *
 * OPT=0 preserves straightforward wide integer arithmetic. Three bounded
 * optimizations retain exactly the same state/output: OPT1 uses proven
 * 16-bit Float11 operands, OPT2 adds small mantissa/log tables, OPT3 adds
 * inverse-quantizer tables over the complete reachable scale-factor range
 * and replaces products by known signs with conditional additions.
 * State variables remain 32-bit: narrowing adaptive coefficients without a
 * range proof would silently change the codec. No allocation or host calls
 * are required by the decoder. The SDCC build is a flat CPU benchmark,
 * not a Spectrum player or a disk loader.
 */
#include <stdint.h>
#include <string.h>
#ifndef OPT
#define OPT 3
#endif
#ifdef __SDCC
#define API
#elif defined(_WIN32)
#define API __declspec(dllexport)
#else
#define API
#endif

typedef struct { uint8_t sign, exp, mant; } Float11;
typedef struct {
    Float11 sr[2], dq[6];
    int32_t a[2], b[6], pk[2];
    int32_t ap, yu, yl, dms, dml, td, se, sez, y;
} G726;

#if OPT >= 2
#include "small_tables.inc"
#endif
#if OPT >= 3
#include "inverse_tables.inc"
#endif

static int32_t clip(int32_t x, int32_t lo, int32_t hi)
{ return x < lo ? lo : x > hi ? hi : x; }
static int32_t sign(int32_t x) { return x < 0 ? -1 : 1; }

/* The coefficient/4, reconstructed sample and quantized difference passed
 * here fit signed16 bits. Float11 has a sign, a bit-length exponent and a
 * six-bit mantissa; zero uses mantissa32 and exponent0, as G.726 requires.
 * OPT1 avoids an intermediate 32-bit left shift; OPT2 removes the loop. */
static void to_float(int32_t input, Float11 *f)
{
#if OPT == 0
    int32_t value, copy;
#else
    uint16_t value, copy;
#endif
    uint8_t e=0;
    f->sign=input<0;
    value=(input<0 ? -input : input);
#if OPT >= 2
    e=(value>>8) ? 8+g726_log[value>>8] : g726_log[value];
#else
    copy=value;
    while(copy) { ++e; copy>>=1; }
#endif
    f->exp=e;
#if OPT == 0
    f->mant=value ? (value<<6)>>e : 32;
#else
    f->mant=!value ? 32 : e>6 ? value>>(e-6) : value<<(6-e);
#endif
}

/* Float11 multiplication rounds mantissas before scaling, and returns a
 * signed16 modular result. OPT2's1024-byte table covers32..63 in each
 * operand, including the special zero representation. Sign and exponent
 * are not discarded. Unsigned shifts explicitly preserve modulo arithmetic. */
static int16_t multiply(const Float11 *a,const Float11 *b)
{
    uint8_t e=a->exp+b->exp;
#if OPT == 0
    int32_t r=(((int32_t)a->mant*b->mant)+48)>>4;
#else
    uint16_t r;
#if OPT >= 2
    r=g726_product[((uint16_t)(a->mant-32)<<5)+(b->mant-32)];
#else
    r=(((uint16_t)a->mant*b->mant)+48)>>4;
#endif
#endif
#if OPT == 0
    r=e>19 ? r<<(e-19) : r>>(19-e);
#else
    /* A shift of eight or more annihilates the <=251 mantissa product.
     * Handle it explicitly, including shifts >=the16-bit target width. */
    r=e<=11 ? 0 : e>19 ? r<<(e-19) : r>>(19-e);
#endif
    return (int16_t)((a->sign^b->sign) ? -r : r);
}

API uint16_t g726_state_bytes(void) { return sizeof(G726); }
API void g726_reset(G726 *c)
{
    uint8_t i;
    memset(c,0,sizeof(*c));
    for(i=0;i<2;++i) { c->sr[i].mant=32; c->pk[i]=1; }
    for(i=0;i<6;++i)c->dq[i].mant=32;
    c->yu=c->y=544; c->yl=34816L;
}

/* Complete state transition. Every subtraction uses signed arithmetic
 * with arithmetic right shifts (verified on host and SDCC/Z80). Predictor
 * accumulation and slow adaptation remain32-bit. Output wrap follows the
 * FFmpeg uniform PCM interface; it must not be mistaken for IMA saturation. */
API int16_t g726_decode_one(G726 *c,uint8_t code)
{
    int32_t dq, reconstructed, pk, dqsign, fa, integer, fraction, threshold;
    int32_t al, difference, dql, exponent;
    uint8_t i, negative=code>>1, transition;
    Float11 f;
    static const int16_t weights[4]={-22,439,439,-22};
    static const uint8_t activity[4]={0,7,7,0};
#if OPT >= 3
    dq=g726_inverse[(code==1 || code==2) ? 1 : 0][(c->y>>2)-136];
#else
    dql=((code==1 || code==2) ? 365 : 116)+(c->y>>2);
    exponent=(dql>>7)&15;
    dq=dql<0 ? 0 : (((128+(dql&127))<<exponent)>>7);
#endif
    integer=c->yl>>15; fraction=(c->yl>>10)&31;
    threshold=integer>9 ? 31744L : (32+fraction)<<integer;
    transition=c->td && dq>((3*threshold)>>2);
    if(negative)dq=-dq;
    reconstructed=(int16_t)(c->se+dq);
    pk=(c->sez+dq) ? sign(c->sez+dq) : 0;
    dqsign=dq ? sign(dq) : 0;
    if(transition) {
        c->a[0]=c->a[1]=0;
        for(i=0;i<6;++i)c->b[i]=0;
    } else {
        /* The upper limit of this signed nine-bit clip is255, not256. */
#if OPT >= 3
        /* pk is -1/0/+1 and saved pk is -1/+1. General long products
         * waste thousands of target cycles without adding information. */
        fa=pk ? (pk==c->pk[0] ? -c->a[0] : c->a[0]) : 0;
        fa=clip(fa>>5,-256,255);
        c->a[1]=clip(c->a[1]+(pk ? (pk==c->pk[1] ? 128 : -128) : 0)+fa-(c->a[1]>>7),-12288,12288);
        c->a[0]+=(pk ? (pk==c->pk[0] ? 192 : -192) : 0)-(c->a[0]>>8);
#else
        fa=clip((-c->a[0]*c->pk[0]*pk)>>5,-256,255);
        c->a[1]=clip(c->a[1]+128*pk*c->pk[1]+fa-(c->a[1]>>7),-12288,12288);
        c->a[0]+=192*pk*c->pk[0]-(c->a[0]>>8);
#endif
        c->a[0]=clip(c->a[0],-(15360-c->a[1]),15360-c->a[1]);
        for(i=0;i<6;++i)
#if OPT >= 3
            c->b[i]+=(dqsign ? ((dqsign<0)==c->dq[i].sign ? 128 : -128) : 0)-(c->b[i]>>8);
#else
            c->b[i]+=128*dqsign*(c->dq[i].sign ? -1 : 1)-(c->b[i]>>8);
#endif
    }
    c->pk[1]=c->pk[0]; c->pk[0]=pk ? pk : 1;
    c->sr[1]=c->sr[0]; to_float(reconstructed,&c->sr[0]);
    for(i=5;i>0;--i)c->dq[i]=c->dq[i-1];
    to_float(dq,&c->dq[0]); c->dq[0].sign=negative;
    c->td=c->a[1]<-11776;
    c->dms+=((int32_t)activity[code]<<4)+((-c->dms)>>5);
    c->dml+=((int32_t)activity[code]<<4)+((-c->dml)>>7);
    if(transition)c->ap=256;
    else {
        c->ap+=(-c->ap)>>4;
        difference=(c->dms<<2)-c->dml;
        if(difference<0)difference=-difference;
        if(c->y<=1535 || c->td || difference>=(c->dml>>3))c->ap+=32;
    }
    c->yu=clip(c->y+weights[code]+((-c->y)>>5),544,5120);
    c->yl+=c->yu+((-c->yl)>>6);
    al=c->ap>=256 ? 64 : c->ap>>2;
    c->y=(c->yl+(c->yu-(c->yl>>6))*al)>>6;
    c->se=0;
    for(i=0;i<6;++i) { to_float(c->b[i]>>2,&f); c->se+=multiply(&f,&c->dq[i]); }
    c->sez=c->se>>1;
    for(i=0;i<2;++i) { to_float(c->a[i]>>2,&f); c->se+=multiply(&f,&c->sr[i]); }
    c->se>>=1;
    return (int16_t)clip(reconstructed*4,-65535L,65535L);
}

#ifndef __SDCC
/* PC-only standard encoder. Division by4 must truncate toward zero,
 * unlike a signed right shift. This follows the FFmpeg PCM16 interface. */
API uint8_t g726_encode_one(G726 *c,int16_t sample)
{
    int32_t d=sample/4-c->se, value, logarithm;
    uint8_t negative=d<0, exponent=0, code;
    if(negative)d=-d;
    value=d;
    while(value>1) { ++exponent; value>>=1; }
    logarithm=((int32_t)exponent<<7)+(((d<<7)>>exponent)&127)-(c->y>>2);
    code=logarithm>260;
    if(negative)code=(~code)&3;
    g726_decode_one(c,code);
    return code;
}
API void g726_encode_pcm(const int16_t *pcm,uint8_t *codes,uint32_t count)
{ G726 c; uint32_t i; g726_reset(&c); for(i=0;i<count;++i)codes[i]=g726_encode_one(&c,pcm[i]); }
API void g726_decode_codes(G726 *c,const uint8_t *codes,int16_t *pcm,uint32_t count)
{ uint32_t i; for(i=0;i<count;++i)pcm[i]=g726_decode_one(c,codes[i]); }
#else
/* Flat benchmark mailbox8F00: input pointer, sample count, output pointer,
 * reset flag, produced samples, completion flag, state size. One byte holds
 * four codes, most significant first. State remains between blocks; the
 * final100-byte state is copied to8F20 for independent host comparison.
 * No player OUT, paging, ROM, ULA or disk cost is hidden in this benchmark. */
#define MAIL ((volatile uint16_t *)0x8f00)
static G726 state;
void entry(void)
{
    const uint8_t *src=(const uint8_t *)MAIL[0];
    int16_t *dst=(int16_t *)MAIL[2];
    uint16_t count=MAIL[1],i;
    uint8_t byte=0;
    if(MAIL[3])g726_reset(&state);
    for(i=0;i<count;++i) {
        if(!(i&3))byte=*src++;
        *dst++=g726_decode_one(&state,byte>>6); byte<<=2;
    }
    memcpy((void *)0x8f20,&state,sizeof(state));
    MAIL[4]=count; MAIL[5]=0; MAIL[6]=sizeof(state);
}
#endif
