/* Complete integer PCM-error IMA trellis. Link after waveform_kernel.SOURCE
   to reuse its exact decoder-state hash merge and candidate-ID heap ties.
   The reference Python encoder and Spectrum decoder are unchanged. */
#include <stdlib.h>
#include <stdio.h>

static const int64_t nima_steps[89]={7,8,9,10,11,12,13,14,16,17,19,21,23,25,28,
    31,34,37,41,45,50,55,60,66,73,80,88,97,107,118,130,143,157,173,190,209,230,
    253,279,307,337,371,408,449,494,544,598,658,724,796,876,963,1060,1166,1282,
    1411,1552,1707,1878,2066,2272,2499,2749,3024,3327,3660,4026,4428,4871,
    5358,5894,6484,7132,7845,8630,9493,10442,11487,12635,13899,15289,16818,
    18500,20350,22385,24623,27086,29794,32767};
static const int nima_index[8]={-1,-1,-1,-1,2,4,6,8};

API int native_ima_encode(const uint8_t *pcm,size_t samples,const uint8_t *codes,
    size_t branches,size_t width,size_t block_samples,int64_t predictor,
    int64_t index,int64_t lower,int64_t upper,uint8_t *packed,int64_t *stats) {
    /* With block<=65536, each valid PCM16-target squared difference is at
       most65535^2 and complete cost<2^49. Casts to the shared double selector
       are therefore exact integers and cannot change score/tie ordering. */
    if (samples%2 || !branches || branches>16 || !width || width>4096 ||
        block_samples<2 || block_samples>65536 || block_samples%2 ||
        lower < -32768 || upper>32767 || predictor<lower || predictor>upper ||
        lower>upper || index<0 || index>88) return 1;
    unsigned seen=0;
    for (size_t b=0;b<branches;++b) {
        if (codes[b]>15 || (seen&(1u<<codes[b]))) return 1;
        seen|=1u<<codes[b];
    }
    int64_t delta[89*16],successor[89*16];
    for (int i=0;i<89;++i) for (int code=0;code<16;++code) {
        int64_t step=nima_steps[i];
        int64_t value=(step>>3)+((code&4)?step:0)+((code&2)?(step>>1):0)+
                      ((code&1)?(step>>2):0);
        delta[i*16+code]=(code&8)?-value:value;
        int ni=i+nima_index[code&7];successor[i*16+code]=ni<0?0:ni>88?88:ni;
    }
    size_t maximum=width*branches,capacity=1;
    while (capacity<maximum*2) capacity*=2;
    int result=2;
    int64_t *preds=malloc(width*sizeof(int64_t)),*indices=malloc(width*sizeof(int64_t));
    int64_t *costs=malloc(width*sizeof(int64_t)),*p2=malloc(width*sizeof(int64_t));
    int64_t *i2=malloc(width*sizeof(int64_t)),*c2=malloc(width*sizeof(int64_t));
    int64_t *predicted=malloc(maximum*sizeof(int64_t)),*next_index=malloc(maximum*sizeof(int64_t));
    int64_t *integer_score=malloc(maximum*sizeof(int64_t));double *score=malloc(maximum*sizeof(double));
    int64_t *candidates=malloc(maximum*sizeof(int64_t)),*keys=malloc(maximum*sizeof(int64_t));
    int64_t *table_keys=malloc(capacity*sizeof(int64_t)),*table_values=malloc(capacity*sizeof(int64_t));
    int64_t *heap=malloc(width*sizeof(int64_t)),*parents=malloc(block_samples*width*sizeof(int64_t));
    uint8_t *path_codes=malloc(block_samples*width),*chosen=malloc(samples?samples:1);
    if (!preds||!indices||!costs||!p2||!i2||!c2||!predicted||!next_index||!integer_score||
        !score||!candidates||!keys||!table_keys||!table_values||!heap||!parents||!path_codes||!chosen)
        goto cleanup;
    int64_t initial_predictor=predictor,initial_index=index;
    for (size_t start=0;start<samples;start+=block_samples) {
        size_t count=samples-start;if (count>block_samples) count=block_samples;
        size_t active=1;preds[0]=predictor;indices[0]=index;costs[0]=0;
        for (size_t position=0;position<count;++position) {
            int64_t target=((int64_t)pcm[start+position]-128)*256;
            size_t valid=0;
            for (size_t p=0;p<active;++p) for (size_t b=0;b<branches;++b) {
                size_t k=p*branches+b;uint8_t code=codes[b];
                int64_t value=preds[p]+delta[indices[p]*16+code];
                if (value<lower || value>upper) continue;
                predicted[k]=value;next_index[k]=successor[indices[p]*16+code];
                int64_t error=value-target;integer_score[k]=costs[p]+error*error;
                score[k]=(double)integer_score[k];candidates[valid]=(int64_t)k;
                keys[valid]=(value+32768)*89+next_index[k];++valid;
            }
            if (!valid) {stats[6]=(int64_t)(start+position);result=3;goto cleanup;}
            size_t used=waveform_select(candidates,keys,score,valid,width,
                                       table_keys,table_values,capacity,heap);
            for (size_t j=0;j<used;++j) {
                size_t k=(size_t)heap[j];p2[j]=predicted[k];i2[j]=next_index[k];c2[j]=integer_score[k];
                parents[position*width+j]=(int64_t)(k/branches);
                path_codes[position*width+j]=codes[k%branches];
            }
            memcpy(preds,p2,used*sizeof(int64_t));memcpy(indices,i2,used*sizeof(int64_t));
            memcpy(costs,c2,used*sizeof(int64_t));active=used;
        }
        size_t winner=0;
        for (size_t position=count;position>0;) {
            --position;chosen[start+position]=path_codes[position*width+winner];
            winner=(size_t)parents[position*width+winner];
        }
        predictor=preds[0];index=indices[0];
    }
    stats[0]=(int64_t)samples;stats[1]=predictor;stats[2]=index;
    /* Independently replay accepted nibbles to verify bounds and packing.
       This also reports extrema of the actual output, not rejected branches. */
    int64_t pred=initial_predictor,idx=initial_index,minimum=32767,maximum_value=-32768;
    for (size_t i=0;i<samples;++i) {
        uint8_t code=chosen[i];pred+=delta[idx*16+code];idx=successor[idx*16+code];
        if (pred<lower || pred>upper) {result=4;goto cleanup;}
        if (pred<minimum) minimum=pred;if (pred>maximum_value) maximum_value=pred;
        if (!(i&1)) packed[i/2]=code;else packed[i/2]|=code<<4;
    }
    if (pred!=predictor || idx!=index) {result=4;goto cleanup;}
    stats[3]=minimum;stats[4]=maximum_value;stats[5]=0;stats[6]=-1;result=0;
cleanup:
    free(preds);free(indices);free(costs);free(p2);free(i2);free(c2);free(predicted);
    free(next_index);free(integer_score);free(score);free(candidates);free(keys);
    free(table_keys);free(table_values);free(heap);free(parents);free(path_codes);free(chosen);
    return result;
}

#ifdef NIMA_STANDALONE
/* Default raw uint8 PCM input, headerless low-nibble-first IMA output.
   The statically linked executable needs neither Python nor BLAS at runtime. */
#include <windows.h>
int wmain(int argc,wchar_t **argv) {
    if (argc!=3) {fprintf(stderr,"Usage: kernel.exe pcm8.raw output.ima\n");return 64;}
    FILE *file=_wfopen(argv[1],L"rb");if (!file) {perror("input");return 66;}
    if (_fseeki64(file,0,SEEK_END)) {fclose(file);return 65;}
    __int64 length=_ftelli64(file);
    if (length<0 || (length&1) || length>16000000 || _fseeki64(file,0,SEEK_SET)) {
        fprintf(stderr,"Need even raw PCM input within the16-million-sample bound\n");fclose(file);return 65;
    }
    size_t n=(size_t)length;uint8_t *source=malloc(n?n:1),*packed=malloc(n?n/2:1);
    if (!source || !packed) {fclose(file);free(source);free(packed);return 71;}
    if (fread(source,1,n,file)!=n || fclose(file)) {free(source);free(packed);return 65;}
    uint8_t codes[16];for (int i=0;i<16;++i) codes[i]=(uint8_t)i;
    int64_t stats[7]={0};int error=native_ima_encode(source,n,codes,16,32,64,0,0,-32768,32767,packed,stats);
    free(source);
    if (error) {fprintf(stderr,"Native PCM encoding failed: %d\n",error);free(packed);return 70;}
    FILE *output=_wfopen(argv[2],L"wb");if (!output) {perror("output");free(packed);return 73;}
    size_t written=fwrite(packed,1,n/2,output);free(packed);int closed=fclose(output);
    if (written!=n/2 || closed) return 74;
    printf("{\"samples\":%llu,\"final_predictor\":%lld,\"final_index\":%lld}\n",
           (unsigned long long)n,(long long)stats[1],(long long)stats[2]);return 0;
}
#endif
