/* Complete host IMA/PDM beam search. Linked after waveform_kernel.SOURCE.
   The Spectrum program and the original Python encoder are unchanged.

   Floating-point matrix products call the same ILP64 OpenBLAS used by NumPy.
   Candidate error terms and their 16-element reduction retain NumPy's order;
   equal scores retain the existing candidate-ID tie break. All allocation,
   ancestry, prefix replay and the two 64-sample PCM guard blocks run here. */
#include <stdlib.h>
#include <math.h>

typedef void (*nwf_gemm)(int,int,int,int64_t,int64_t,int64_t,double,
    const double*,int64_t,const double*,int64_t,double,double*,int64_t);
typedef void (*nwf_gemv)(int,int,int64_t,int64_t,double,const double*,
    int64_t,const double*,int64_t,double,double*,int64_t);

/* A is rows by 6, B is columns by 6; compute A * B.T exactly as matmul.
   NumPy's one-row special case uses GEMV rather than GEMM. */
static void nwf_product(nwf_gemm gemm,nwf_gemv gemv,const double *a,
    const double *b,size_t rows,size_t columns,double *out) {
    if (rows==1) gemv(101,111,(int64_t)columns,6,1.,b,6,a,1,0.,out,1);
    else gemm(101,111,112,(int64_t)rows,(int64_t)columns,6,
              1.,a,6,b,6,0.,out,(int64_t)columns);
}
static double nwf_sum16(const double *a) {
    double r0=a[0]+a[8],r1=a[1]+a[9],r2=a[2]+a[10],r3=a[3]+a[11];
    double r4=a[4]+a[12],r5=a[5]+a[13],r6=a[6]+a[14],r7=a[7]+a[15];
    return ((r0+r1)+(r2+r3))+((r4+r5)+(r6+r7));
}

API int native_waveform_encode(const uint8_t *source,size_t samples,
    const double *desired,const double *aa,const double *ll,
    const double *response,const double *endpoint,const double *weights,
    const int64_t *ids,size_t shapes,const int64_t *nxt,
    const int64_t *delta,const int64_t *successor,size_t width,size_t horizon,
    size_t commit,double regularization,void *gemm_pointer,void *gemv_pointer,
    uint8_t *packed,int64_t *statistics) {
    if (samples<128 || samples%2 || width<32 || width>4096 || horizon<64 ||
        horizon>8192 || !commit || commit>horizon || !isfinite(regularization) || regularization<0)
        return 1;
    if (!gemm_pointer || !gemv_pointer) return 2;
    nwf_gemm gemm=(nwf_gemm)gemm_pointer;nwf_gemv gemv=(nwf_gemv)gemv_pointer;
    size_t maximum=width*16,capacity=1;
    while (capacity<maximum*2) capacity*=2;
    int result=3;
    int64_t *preds=calloc(width,sizeof(int64_t)),*indices=calloc(width,sizeof(int64_t));
    int64_t *qs=calloc(width,sizeof(int64_t)),*p2=malloc(width*sizeof(int64_t));
    int64_t *i2=malloc(width*sizeof(int64_t)),*q2=malloc(width*sizeof(int64_t));
    double *states=calloc(width*6,sizeof(double)),*s2=malloc(width*6*sizeof(double));
    double *costs=calloc(width,sizeof(double)),*c2=malloc(width*sizeof(double));
    double *base=malloc(width*16*sizeof(double)),*advance=malloc(width*6*sizeof(double));
    double *score=malloc(maximum*sizeof(double));
    int64_t *predicted=malloc(maximum*sizeof(int64_t)),*next_index=malloc(maximum*sizeof(int64_t));
    int64_t *word_ids=malloc(maximum*sizeof(int64_t)),*next_q=malloc(maximum*sizeof(int64_t));
    int64_t *candidates=malloc(maximum*sizeof(int64_t)),*keys=malloc(maximum*sizeof(int64_t));
    int64_t *table_keys=malloc(capacity*sizeof(int64_t)),*table_values=malloc(capacity*sizeof(int64_t));
    int64_t *heap=malloc(width*sizeof(int64_t)),*parents=malloc(horizon*width*sizeof(int64_t));
    uint8_t *path_codes=malloc(horizon*width),*path=malloc(horizon),*chosen=calloc(samples,1);
    if (!preds||!indices||!qs||!p2||!i2||!q2||!states||!s2||!costs||!c2||!base||
        !advance||!score||!predicted||!next_index||!word_ids||!next_q||!candidates||
        !keys||!table_keys||!table_values||!heap||!parents||!path_codes||!path||!chosen)
        goto cleanup;
    int64_t pred=0,index=0,q=16;double filter[6]={0};
    size_t count=samples-128,iterations=0;
    for (size_t start=0;start<count;start+=commit) {
        size_t stop=start+horizon;if (stop>count) stop=count;
        size_t active=1;preds[0]=pred;indices[0]=index;qs[0]=q;costs[0]=0.;
        memcpy(states,filter,6*sizeof(double));
        for (size_t sample=start;sample<stop;++sample) {
            int64_t fid=ids[sample];if (fid<0 || (size_t)fid>=shapes) {result=4;goto cleanup;}
            const double *a=aa+fid*36,*l=ll+fid*96,*r=response+fid*32768;
            const double *e=endpoint+fid*12288,*w=weights+fid*16,*wanted=desired+sample*16;
            nwf_product(gemm,gemv,states,l,active,16,base);
            size_t valid=0;
            double target=((double)source[sample]-128.)/128.;
            for (size_t p=0;p<active;++p) for (size_t code=0;code<16;++code) {
                size_t k=p*16+code;
                int64_t predicted_value=preds[p]+delta[indices[p]*16+code];
                int64_t ni=successor[indices[p]*16+code];
                predicted[k]=predicted_value;next_index[k]=ni;
                if (predicted_value < -32768 || predicted_value > 32767) continue;
                size_t level=(size_t)(predicted_value+32768)/1024;
                size_t word=level*32+(size_t)qs[p];word_ids[k]=(int64_t)word;
                double terms[16];
                for (size_t j=0;j<16;++j) {
                    double observed=base[p*16+j]+r[word*16+j];
                    double error=observed-wanted[j];double square=error*error;
                    terms[j]=square*w[j];
                }
                double s=costs[p]+nwf_sum16(terms);
                double distance=(double)predicted_value/32768.-target;
                s+=regularization*(distance*distance);score[k]=s;
                next_q[k]=nxt[level*32+qs[p]];
                candidates[valid]=(int64_t)k;
                keys[valid]=((predicted_value+32768)*89+ni)*32+next_q[k];++valid;
            }
            if (!valid) {result=5;goto cleanup;}
            size_t used=waveform_select(candidates,keys,score,valid,width,
                                       table_keys,table_values,capacity,heap);
            nwf_product(gemm,gemv,states,a,active,6,advance);
            for (size_t j=0;j<used;++j) {
                size_t k=(size_t)heap[j],parent=k/16,word=(size_t)word_ids[k];
                p2[j]=predicted[k];i2[j]=next_index[k];q2[j]=next_q[k];c2[j]=score[k];
                for (size_t d=0;d<6;++d) s2[j*6+d]=advance[parent*6+d]+e[word*6+d];
                parents[(sample-start)*width+j]=(int64_t)parent;
                path_codes[(sample-start)*width+j]=(uint8_t)(k%16);
            }
            memcpy(preds,p2,used*sizeof(int64_t));memcpy(indices,i2,used*sizeof(int64_t));
            memcpy(qs,q2,used*sizeof(int64_t));memcpy(costs,c2,used*sizeof(double));
            memcpy(states,s2,used*6*sizeof(double));active=used;++iterations;
        }
        size_t winner=0;
        for (size_t position=stop-start;position>0;) {
            --position;path[position]=path_codes[position*width+winner];
            winner=(size_t)parents[position*width+winner];
        }
        size_t accepted=start+commit;if (accepted>stop) accepted=stop;
        memcpy(chosen+start,path,accepted-start);
        if (accepted==stop) {
            pred=preds[0];index=indices[0];q=qs[0];memcpy(filter,states,6*sizeof(double));
        } else for (size_t sample=start;sample<accepted;++sample) {
            size_t code=chosen[sample];pred+=delta[index*16+code];index=successor[index*16+code];
            size_t level=(size_t)(pred+32768)/1024,word=level*32+(size_t)q,fid=(size_t)ids[sample];
            double advanced[6];gemv(101,111,6,6,1.,aa+fid*36,6,filter,1,0.,advanced,1);
            for (size_t d=0;d<6;++d) filter[d]=advanced[d]+endpoint[fid*12288+word*6+d];
            q=nxt[level*32+q];
        }
    }
    /* Exact PCM guard reference: width32, two64-sample blocks, integer
       squared costs. Every cost is below2^53, so its double representation
       used by the shared selector is exact and preserves all integer ties. */
    for (size_t start=count;start<samples;start+=64) {
        size_t active=1;preds[0]=pred;indices[0]=index;costs[0]=0.;
        for (size_t position=0;position<64;++position) {
            size_t valid=0;
            for (size_t p=0;p<active;++p) for (size_t code=0;code<16;++code) {
                size_t k=p*16+code;int64_t value=preds[p]+delta[indices[p]*16+code];
                if (value < -32768 || value > 32767) continue;
                predicted[k]=value;next_index[k]=successor[indices[p]*16+code];
                score[k]=costs[p]+(double)(value*value);candidates[valid]=(int64_t)k;
                keys[valid]=(value+32768)*89+next_index[k];++valid;
            }
            if (!valid) {result=5;goto cleanup;}
            size_t used=waveform_select(candidates,keys,score,valid,32,
                                       table_keys,table_values,capacity,heap);
            for (size_t j=0;j<used;++j) {
                size_t k=(size_t)heap[j];p2[j]=predicted[k];i2[j]=next_index[k];c2[j]=score[k];
                parents[position*width+j]=(int64_t)(k/16);path_codes[position*width+j]=(uint8_t)(k%16);
            }
            memcpy(preds,p2,used*sizeof(int64_t));memcpy(indices,i2,used*sizeof(int64_t));
            memcpy(costs,c2,used*sizeof(double));active=used;
        }
        size_t winner=0;
        for (size_t position=64;position>0;) {
            --position;chosen[start+position]=path_codes[position*width+winner];
            winner=(size_t)parents[position*width+winner];
        }
        pred=preds[0];index=indices[0];
    }
    if (pred || index) {result=7;goto cleanup;}
    for (size_t i=0;i<samples;i+=2) packed[i/2]=chosen[i]|(chosen[i+1]<<4);
    statistics[0]=(int64_t)iterations;statistics[1]=pred;statistics[2]=index;result=0;
cleanup:
    free(preds);free(indices);free(qs);free(p2);free(i2);free(q2);free(states);free(s2);
    free(costs);free(c2);free(base);free(advance);free(score);free(predicted);free(next_index);
    free(word_ids);free(next_q);free(candidates);free(keys);free(table_keys);free(table_values);
    free(heap);free(parents);free(path_codes);free(path);free(chosen);return result;
}

#ifdef NWF_STANDALONE
/* Standalone conversion consumes a versioned workset prepared by the host
   front end. Its source clock, analytic coefficients and desired waveform
   are explicit binary inputs; no Python process or callback runs in this
   executable. NumPy's installed BLAS supplies matrix arithmetic only. */
#include <stdio.h>
#include <windows.h>

static void *nwf_read(FILE *file,size_t count,size_t bytes) {
    if (count && bytes>SIZE_MAX/count) return NULL;
    void *result=malloc(count*bytes ? count*bytes : 1);
    if (result && fread(result,bytes,count,file)!=count) {free(result);return NULL;}
    return result;
}
static int nwf_finite(const double *values,size_t count) {
    for (size_t i=0;i<count;++i) if (!isfinite(values[i])) return 0;
    return 1;
}
int wmain(int argc,wchar_t **argv) {
    if (argc!=4) {
        fprintf(stderr,"Usage: kernel.exe workset.bin output.ima numpy-openblas.dll\n");return 64;
    }
    int status=65;FILE *file=_wfopen(argv[1],L"rb");
    if (!file) {perror("workset");return 66;}
    char magic[8];uint64_t n=0,f=0,width=0,horizon=0,commit=0;double reg=0.;
    if (fread(magic,1,8,file)!=8 || memcmp(magic,"NWFB001",8) ||
        fread(&n,8,1,file)!=1 || fread(&f,8,1,file)!=1 ||
        fread(&width,8,1,file)!=1 || fread(&horizon,8,1,file)!=1 ||
        fread(&commit,8,1,file)!=1 || fread(&reg,8,1,file)!=1 ||
        n<128 || n%2 || n>16000000 || !f || f>4096 || width<32 || width>4096 ||
        horizon<64 || horizon>8192 || !commit || commit>horizon || !isfinite(reg) || reg<0) {
        fprintf(stderr,"Invalid or unsupported workset header\n");fclose(file);return 65;
    }
    /* Bound all array sizes before reading untrusted header-derived lengths. */
    uint64_t memory=n+(n-128)*136+f*(36+96+32768+12288+16)*8+4096*8+2848*8;
    if (memory>UINT64_C(2147483648)) {
        fprintf(stderr,"Workset arrays exceed the 2-GiB input bound\n");fclose(file);return 65;
    }
    uint8_t *source=nwf_read(file,(size_t)n,1),*packed=malloc((size_t)n/2);
    double *desired=nwf_read(file,(size_t)(n-128)*16,8),*aa=nwf_read(file,(size_t)f*36,8);
    double *ll=nwf_read(file,(size_t)f*96,8),*response=nwf_read(file,(size_t)f*32768,8);
    double *endpoint=nwf_read(file,(size_t)f*12288,8),*weights=nwf_read(file,(size_t)f*16,8);
    int64_t *ids=nwf_read(file,(size_t)(n-128),8),*nxt=nwf_read(file,2048,8);
    int64_t *delta=nwf_read(file,1424,8),*successor=nwf_read(file,1424,8);
    if (!source||!packed||!desired||!aa||!ll||!response||!endpoint||!weights||
        !ids||!nxt||!delta||!successor || fgetc(file)!=EOF) {
        fprintf(stderr,"Truncated, oversized or unallocatable workset\n");goto finish;
    }
    for (size_t i=(size_t)n-128;i<(size_t)n;++i) if (source[i]!=128) {
        fprintf(stderr,"Source guard is not silent\n");goto finish;
    }
    for (size_t i=0;i<(size_t)n-128;++i) if (ids[i]<0 || ids[i]>=(int64_t)f) {
        fprintf(stderr,"Packet ID outside feature catalogue\n");goto finish;
    }
    for (size_t i=0;i<2048;++i) if (nxt[i]<0 || nxt[i]>=32) {
        fprintf(stderr,"Feedback state outside table\n");goto finish;
    }
    static const int64_t step[89]={7,8,9,10,11,12,13,14,16,17,19,21,23,25,28,31,34,
        37,41,45,50,55,60,66,73,80,88,97,107,118,130,143,157,173,190,209,230,253,
        279,307,337,371,408,449,494,544,598,658,724,796,876,963,1060,1166,1282,1411,
        1552,1707,1878,2066,2272,2499,2749,3024,3327,3660,4026,4428,4871,5358,5894,
        6484,7132,7845,8630,9493,10442,11487,12635,13899,15289,16818,18500,20350,
        22385,24623,27086,29794,32767};
    static const int next[8]={-1,-1,-1,-1,2,4,6,8};
    for (int i=0;i<89;++i) for (int code=0;code<16;++code) {
        int64_t difference=(step[i]>>3)+((code&4)?step[i]:0)+((code&2)?(step[i]>>1):0)+
                           ((code&1)?(step[i]>>2):0);
        if (code&8) difference=-difference;
        int ni=i+next[code&7];if (ni<0) ni=0;if (ni>88) ni=88;
        if (delta[i*16+code]!=difference || successor[i*16+code]!=ni) {
            fprintf(stderr,"IMA transition table differs from reference\n");goto finish;
        }
    }
    if (!nwf_finite(desired,(size_t)(n-128)*16)||!nwf_finite(aa,(size_t)f*36)||
        !nwf_finite(ll,(size_t)f*96)||!nwf_finite(response,(size_t)f*32768)||
        !nwf_finite(endpoint,(size_t)f*12288)||!nwf_finite(weights,(size_t)f*16)) {
        fprintf(stderr,"Nonfinite workset coefficient\n");goto finish;
    }
    for (size_t i=0;i<(size_t)f*16;++i) if (weights[i]<0) {
        fprintf(stderr,"Negative quadrature weight\n");goto finish;
    }
    HMODULE blas=LoadLibraryExW(argv[3],NULL,LOAD_WITH_ALTERED_SEARCH_PATH);
    if (!blas) {fprintf(stderr,"Cannot load installed NumPy OpenBLAS DLL\n");goto finish;}
    FARPROC gemm=GetProcAddress(blas,"scipy_cblas_dgemm64_");
    FARPROC gemv=GetProcAddress(blas,"scipy_cblas_dgemv64_");
    int64_t statistics[3]={0};
    int error=native_waveform_encode(source,(size_t)n,desired,aa,ll,response,endpoint,weights,
        ids,(size_t)f,nxt,delta,successor,(size_t)width,(size_t)horizon,(size_t)commit,reg,
        (void*)gemm,(void*)gemv,packed,statistics);
    FreeLibrary(blas);
    if (error) {fprintf(stderr,"Native encoding failed: %d\n",error);goto finish;}
    FILE *output=_wfopen(argv[2],L"wb");
    if (!output) {perror("output");goto finish;}
    size_t written=fwrite(packed,1,(size_t)n/2,output);
    int closed=fclose(output);
    if (written!=(size_t)n/2 || closed) {fprintf(stderr,"Output write failed\n");goto finish;}
    printf("{\"samples\":%llu,\"search_iterations\":%lld,\"final_predictor\":%lld,\"final_index\":%lld}\n",
        (unsigned long long)n,(long long)statistics[0],(long long)statistics[1],(long long)statistics[2]);
    status=0;
finish:
    fclose(file);free(source);free(packed);free(desired);free(aa);free(ll);free(response);
    free(endpoint);free(weights);free(ids);free(nxt);free(delta);free(successor);return status;
}
#endif
