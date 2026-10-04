/* RAM input, unsigned PCM8 at low-byte port FB. No PDM/AY/disk/ROM calls. */
#include "decoder.h"
#include <string.h>
__sfr __at (0xfb) dac;
volatile u16 packet_count;
volatile u16 status;
s16 pcm[160];
u8 packet[20];
static void page(u8 bank) __sdcccall(1) __naked
{
    bank;
    __asm
        or #16
        ld bc,#0x7ffd
        out (c),a
        ret
    __endasm;
}
void complete(void) __naked { __asm halt __endasm; }
void entry(void)
{
    const u8 *input=(const u8 *)0xc000;
    u16 frames;
    u8 i,bank=0;
    __asm di __endasm;
    zx_speex_reset();
    frames=packet_count;
    status=0;
    page(0);
    while(frames--) {
        for(i=0;i<20;i++) {
            packet[i]=*input++;
            if(!input) {page(++bank);input=(const u8 *)0xc000;}
        }
        if(zx_speex_decode(packet,pcm)) {status=1;break;}
        for(i=0;i<160;i++) dac=(u8)(((u16)pcm[i]>>8)^128);
    }
    complete();
}
