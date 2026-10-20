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

static FILE *opened(const char *path,const char *mode) {
    FILE *file=fopen(path,mode);
    if(!file){fprintf(stderr,"Cannot open required file\n");exit(1);}
    return file;
}
static void byte(FILE *file,unsigned value) {
    if(fputc((int)(value&255),file)==EOF){fprintf(stderr,"Write failed\n");exit(1);}
}
int main(int argc,char **argv) {
    unsigned char table[6144];
    FILE *model,*ima,*out,*states,*decoded;
    int predictor=0,index=0,state=16,input;
    size_t samples=0;
    if(argc!=6){fprintf(stderr,"usage: uniform16 TABLE6144 INPUT.ima WORDS.u16 STATES.u8 PCM16.bin\n");return 2;}
    model=opened(argv[1],"rb");
    if(fread(table,1,sizeof table,model)!=sizeof table||fgetc(model)!=EOF)return 3;
    fclose(model);ima=opened(argv[2],"rb");out=opened(argv[3],"wb");
    states=opened(argv[4],"wb");decoded=opened(argv[5],"wb");
    while((input=fgetc(ima))!=EOF) {
        int half;
        for(half=0;half<2;++half) {
            int code=(input>>(half*4))&15,step=steps[index];
            int delta=(step>>3)+((code&4)?step:0)+((code&2)?step>>1:0)+((code&1)?step>>2:0);
            size_t at;
            if(code&8)delta=-delta;
            predictor+=delta;
            if(predictor < -32768 || predictor > 32767){fprintf(stderr,"Clipped predictor rejected\n");return 4;}
            index+=changes[code&7];if(index<0)index=0;if(index>88)index=88;
            at=(size_t)(((predictor+32768)>>10)*32+state)*3;
            byte(out,table[at]);byte(out,table[at+1]);state=table[at+2];
            if(state>=32)return 5;
            byte(states,(unsigned)state);byte(decoded,(unsigned)(uint16_t)predictor);
            byte(decoded,(unsigned)(uint16_t)predictor>>8);++samples;
        }
    }
    if(ferror(ima)||!samples)return 6;
    fclose(ima);if(fclose(out)||fclose(states)||fclose(decoded))return 7;
    printf("{\"samples\":%zu,\"decisions\":%zu,\"final_state\":%d,\"final_predictor\":%d,\"final_index\":%d}\n",
        samples,samples*16,state,predictor,index);
    return 0;
}
