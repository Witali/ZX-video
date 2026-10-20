/* Frozen uniform-clock IMA -> tabled PDM control. This is a host model of
   the native resident-PCM8 component, not an integrated IMA/Z80 player.
   Keep the full signed predictor until quantizing by the existing64-level
   table map. No gain, clock adjustment, clipping or source shortening. */
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>

static const int steps[89]={7,8,9,10,11,12,13,14,16,17,19,21,23,25,28,31,
34,37,41,45,50,55,60,66,73,80,88,97,107,118,130,143,157,173,190,209,230,
253,279,307,337,371,408,449,494,544,598,658,724,796,876,963,1060,1166,
1282,1411,1552,1707,1878,2066,2272,2499,2749,3024,3327,3660,4026,4428,
4871,5358,5894,6484,7132,7845,8630,9493,10442,11487,12635,13899,15289,
16818,18500,20350,22385,24623,27086,29794,32767};
static const int changes[8]={-1,-1,-1,-1,2,4,6,8};

static void transitions(int *delta,unsigned char *successor) {
    /* The1424 exact IMA transitions depend only on index/code. Preserve
       shift/add rounding, including the zero delta at index0/code8. The
       largest magnitude61436 needs more than a signed16-bit table entry. */
    for(int i=0;i<89;++i)for(int code=0;code<16;++code) {
        int step=steps[i],difference=(step>>3)+((code&4)?step:0)+
            ((code&2)?step>>1:0)+((code&1)?step>>2:0);
        int next=i+changes[code&7];
        delta[i*16+code]=(code&8)?-difference:difference;
        successor[i*16+code]=(unsigned char)(next<0?0:next>88?88:next);
    }
}

static int advance(int *predictor,int *index,int code,
    const int *delta,const unsigned char *successor) {
    size_t transition=(size_t)*index*16+code;
    *predictor+=delta[transition];
    /* Live player inputs are guarded: reject overflow, never saturate. */
    if(*predictor < -32768 || *predictor > 32767)return 0;
    *index=successor[transition];return 1;
}

static FILE *opened(const char *path,const char *mode) {
    FILE *file=fopen(path,mode);
    if(!file){fprintf(stderr,"Cannot open required file\n");exit(1);}
    return file;
}
static void written(FILE *file,const unsigned char *data,size_t size) {
    if(fwrite(data,1,size,file)!=size){fprintf(stderr,"Write failed\n");exit(1);}
}
static void flush_outputs(FILE *out,FILE *states,FILE *decoded,
    const unsigned char *words,size_t word_bytes,const unsigned char *state_bytes,
    size_t state_count,const unsigned char *pcm,size_t pcm_bytes) {
    written(out,words,word_bytes);written(states,state_bytes,state_count);
    written(decoded,pcm,pcm_bytes);
}
int main(int argc,char **argv) {
    unsigned char table[6144];
    /* A chunk is32768 compressed bytes /65536 original samples. Explicit
       little-endian bytes keep the files independent of host word order.
       Static storage avoids putting328KiB on a small Windows thread stack. */
    static unsigned char input_bytes[32768],word_bytes[131072];
    static unsigned char state_bytes[65536],pcm_bytes[131072];
    int delta[89*16];unsigned char successor[89*16];
    FILE *model,*ima,*out,*states,*decoded;
    int predictor=0,index=0,state=16;
    size_t samples=0;
    if(argc!=6){fprintf(stderr,"usage: uniform16 TABLE6144 INPUT.ima WORDS.u16 STATES.u8 PCM16.bin\n");return 2;}
    model=opened(argv[1],"rb");
    if(fread(table,1,sizeof table,model)!=sizeof table||fgetc(model)!=EOF)return 3;
    fclose(model);ima=opened(argv[2],"rb");out=opened(argv[3],"wb");
    states=opened(argv[4],"wb");decoded=opened(argv[5],"wb");
    transitions(delta,successor);
    for(;;) {
        size_t count=fread(input_bytes,1,sizeof input_bytes,ima),produced=0;
        for(size_t i=0;i<count;++i)for(int half=0;half<2;++half) {
            int code=(input_bytes[i]>>(half*4))&15;
            size_t at;
            if(!advance(&predictor,&index,code,delta,successor)) {
                flush_outputs(out,states,decoded,word_bytes,produced*2,
                    state_bytes,produced,pcm_bytes,produced*2);
                fprintf(stderr,"Clipped predictor rejected\n");return 4;
            }
            at=(size_t)(((predictor+32768)>>10)*32+state)*3;
            word_bytes[produced*2]=table[at];word_bytes[produced*2+1]=table[at+1];
            state=table[at+2];
            if(state>=32) {
                /* The old byte writer emits the invalid cell's word before
                   rejecting its successor, but no state or PCM for it. */
                flush_outputs(out,states,decoded,word_bytes,produced*2+2,
                    state_bytes,produced,pcm_bytes,produced*2);
                return 5;
            }
            state_bytes[produced]=(unsigned char)state;
            pcm_bytes[produced*2]=(unsigned char)(uint16_t)predictor;
            pcm_bytes[produced*2+1]=(unsigned char)((uint16_t)predictor>>8);
            ++produced;++samples;
        }
        flush_outputs(out,states,decoded,word_bytes,produced*2,
            state_bytes,produced,pcm_bytes,produced*2);
        if(count<sizeof input_bytes)break;
    }
    if(ferror(ima)||!samples)return 6;
    fclose(ima);if(fclose(out)||fclose(states)||fclose(decoded))return 7;
    printf("{\"samples\":%zu,\"decisions\":%zu,\"final_state\":%d,\"final_predictor\":%d,\"final_index\":%d}\n",
        samples,samples*16,state,predictor,index);
    return 0;
}
