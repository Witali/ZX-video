/* Specialized fixed-point Speex 1.2.1 mode-3 decoder.
 * Algorithms adapted from Xiph Speex (Jean-Marc Valin and contributors).
 * BSD-3-Clause: see LICENSE.speex. No encoder, PLC, enhancement or highpass.
 * 20 bytes -> 160 PCM16 samples, with the reference decoder's 40-sample delay.
 */
#include "decoder.h"
#include <string.h>
#include "tables.h"

#define M(a,b) ((s32)(s16)(a)*(s16)(b))
#define P13(a,b) ((M(a,b)+4096)>>13)
#define P14(a,b) ((M(a,b)+8192)>>14)
static s32 q14(s16 a,s32 b) { return M(a,b>>14)+(M(a,b&16383)>>14); }
static s32 q15(s16 a,s32 b) { return M(a,b>>15)+(M(a,b&32767)>>15); }
s16 zx_clip(s32 x) { return x>32767?32767:x< -32767?-32767:(s16)x; }
#define clip zx_clip
static s16 excitation[344]; /* history 184, current frame 160 */
static s16 old_lsp[10], lsp[10], interp[10], next_lpc[10];
s16 zx_lpc[10];
s32 zx_memory[10];
static s32 polynomial_p[6][13],polynomial_q[6][13];
static s16 frequency[10];
static u8 first;
static const u8 *bitptr;
static u8 bitmask;
#ifndef __SDCC
static s16 trace_lpc[40],trace_interp[40];
EXPORT void zx_speex_state(int kind,void *out)
{
    if(kind==0) memcpy(out,excitation,sizeof(excitation));
    if(kind==1) memcpy(out,trace_lpc,sizeof(trace_lpc));
    if(kind==2) memcpy(out,trace_interp,sizeof(trace_interp));
}
#endif

static u16 bits(u8 count)
{
    u16 v=0;
    while(count--) {
        v=(v<<1)|((*bitptr & bitmask)!=0);
        bitmask>>=1;
        if(!bitmask) { bitmask=128; ++bitptr; }
    }
    return v;
}

static s16 cosine(s16 x)
{
    s16 x2;
    if(x<12868) {
        x2=(s16)P13(x,x);
        return (s16)(8192+P13(x2,-4096+P13(x2,340+P13(-10,x2))));
    }
    x=25736-x;
    x2=(s16)P13(x,x);
    return (s16)(-8192-P13(x2,-4096+P13(x2,340+P13(-10,x2))));
}

void zx_speex_lpc(void)
{
    u8 i,j;
    s32 p=0,q=0,a;
    for(i=0;i<10;i++) frequency[i]=(s16)(cosine(interp[i])*4);
    for(i=0;i<=5;i++) {
        polynomial_p[i][1]=polynomial_q[i][1]=0;
        polynomial_p[i][2]=polynomial_q[i][2]=1048576L;
        polynomial_p[i][2+2*i]=polynomial_q[i][2+2*i]=1048576L;
    }
    polynomial_p[1][3]=-q14(frequency[0],1048576L);
    polynomial_q[1][3]=-q14(frequency[1],1048576L);
    for(i=1;i<5;i++) {
        for(j=1;j<2*(i+1)-1;j++) {
            polynomial_p[i+1][j+2]=polynomial_p[i][j+2]-q14(frequency[2*i],polynomial_p[i][j+1])+polynomial_p[i][j];
            polynomial_q[i+1][j+2]=polynomial_q[i][j+2]-q14(frequency[2*i+1],polynomial_q[i][j+1])+polynomial_q[i][j];
        }
        polynomial_p[i+1][j+2]=polynomial_p[i][j]-q14(frequency[2*i],polynomial_p[i][j+1]);
        polynomial_q[i+1][j+2]=polynomial_q[i][j]-q14(frequency[2*i+1],polynomial_q[i][j+1]);
    }
    for(j=1;j<=10;j++) {
        a=(polynomial_p[5][j+2]+p+polynomial_q[5][j+2]-q+128)>>8;
        p=polynomial_p[5][j+2];q=polynomial_q[5][j+2];
        next_lpc[j-1]=clip(a);
    }
}

EXPORT void zx_speex_reset(void)
{
    memset(excitation,0,sizeof(excitation));
    memset(zx_memory,0,sizeof(zx_memory));
    memset(zx_lpc,0,sizeof(zx_lpc));
    first=1;
}

#ifndef ASM_FILTER
EXPORT void zx_speex_filter(const s16 *input,s16 *output)
{
    u8 i,j;
    s16 y,n;
    for(i=0;i<40;i++) {
        y=clip((s32)input[i]+((zx_memory[0]+4096)>>13));
        n=-y;
        for(j=0;j<9;j++) zx_memory[j]=zx_memory[j+1]+M(zx_lpc[j],n);
        zx_memory[9]=M(zx_lpc[9],n);
        output[i]=y;
    }
}
#endif

EXPORT int zx_speex_decode(const u8 *packet,s16 *output)
{
    u8 i,j,sub,k,index,shape[4];
    s16 gains[3],pitch,delay,at,phase;
    s16 *e;
    s32 gain,energy,v,innov;
    bitptr=packet;bitmask=128;
    if(bits(5)!=3) return -1; /* reject WB, DTX and every other mode */
    memmove(excitation,excitation+160,184*sizeof(s16));
    index=(u8)bits(6);
    for(i=0;i<10;i++) lsp[i]=(s16)((i+1)*2048+(s16)cdbk_nb[index*10+i]*32);
    index=(u8)bits(6);
    for(i=0;i<5;i++) lsp[i]+=(s16)cdbk_nb_low1[index*5+i]*16;
    index=(u8)bits(6);
    for(i=0;i<5;i++) lsp[i+5]+=(s16)cdbk_nb_high1[index*5+i]*16;
    if(first) memcpy(old_lsp,lsp,sizeof(lsp));
    gain=q15(28406,ol_gain_table[bits(5)]);
    for(sub=0;sub<4;sub++) {
        e=excitation+184+sub*40;
        pitch=(s16)bits(7)+17;
        index=(u8)bits(5);
        for(k=0;k<3;k++) gains[k]=(32+(s16)gain_cdbk_lbr[index*4+k])*128;
        energy=q14(bits(1)?17224:11546,gain);
        for(k=0;k<4;k++) shape[k]=(u8)bits(5);
        for(j=0;j<40;j++) {
            v=0;
            for(k=0;k<3;k++) {
                delay=pitch+1-k;
                at=(s16)j-delay;
                if(at>=0) at-=pitch;
                if(at<0) v+=M(gains[2-k],e[at]);
            }
            if(v>262144000L) v=262144000L;
            if(v< -262144000L) v= -262144000L;
            innov=q14((s16)exc_10_32_table[shape[j/10]*10+j%10]*4,energy)*128;
            e[j]=clip((v*2+innov+8192)>>14);
        }
    }
    /* libspeex without perceptual enhancement outputs the previous subframe. */
    for(sub=0;sub<4;sub++) {
        phase=(sub+1)*4096;
        for(i=0;i<10;i++) interp[i]=(s16)(P14(16384-phase,old_lsp[i])+P14(phase,lsp[i]));
        if(interp[0]<16) interp[0]=16;
        if(interp[9]>25720) interp[9]=25720;
        for(i=1;i<9;i++) {
            if(interp[i]<interp[i-1]+16) interp[i]=interp[i-1]+16;
            if(interp[i]>interp[i+1]-16) interp[i]=(interp[i]>>1)+((interp[i+1]-16)>>1);
        }
        zx_speex_lpc();
#ifndef __SDCC
        memcpy(trace_lpc+sub*10,next_lpc,sizeof(next_lpc));
        memcpy(trace_interp+sub*10,interp,sizeof(interp));
#endif
        zx_speex_filter(excitation+144+sub*40,output+sub*40);
        memcpy(zx_lpc,next_lpc,sizeof(zx_lpc));
    }
    memcpy(old_lsp,lsp,sizeof(lsp));first=0;
    return 0;
}
