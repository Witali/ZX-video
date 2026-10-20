/* Exact offline reference preparation for the unchanged waveform search.
   NumPy remains the reference implementation. The 6x6 recurrence calls the
   same installed ILP64 OpenBLAS GEMV; scalar expressions use strict IEEE order.
   Query gathering avoids the Python implementation's N*16*6 temporaries. */
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>

#ifdef _WIN32
#define API __declspec(dllexport)
#else
#define API
#endif

typedef void (*prepare_gemv)(int,int,int64_t,int64_t,double,const double*,
    int64_t,const double*,int64_t,double,double*,int64_t);

static uint64_t prepare_row_hash(const double *row) {
    uint64_t hash=UINT64_C(0x9e3779b97f4a7c15);
    for (size_t k=0;k<16;++k) {
        uint64_t word;memcpy(&word,row+k,sizeof(word));
        hash^=word+UINT64_C(0x9e3779b97f4a7c15)+(hash<<6)+(hash>>2);
    }
    hash^=hash>>30;hash*=UINT64_C(0xbf58476d1ce4e5b9);
    hash^=hash>>27;hash*=UINT64_C(0x94d049bb133111eb);
    return hash^(hash>>31);
}

static int prepare_row_less(const double *rows,size_t left,size_t right) {
    for (size_t k=0;k<16;++k) {
        if (rows[16*left+k]<rows[16*right+k]) return 1;
        if (rows[16*left+k]>rows[16*right+k]) return 0;
    }
    return 0;
}

/* Match np.unique(holds,axis=0,return_inverse=True) on finite positive holds.
   Hash every complete float64 row, sort only the unique rows in the same
   numeric lexicographic order, then remap the inverse IDs. No rounding or
   canonical packet substitution is allowed. All state is local/reentrant. */
API int waveform_prepare_unique_holds(const double *rows,size_t samples,
    int64_t *indices,int64_t *inverse,size_t *count) {
    if (!samples || samples>INT64_MAX || samples>SIZE_MAX/16) return 1;
    size_t capacity=256,used=0;int result=2;
    size_t *table=calloc(capacity,sizeof(size_t));
    int64_t *temporary=NULL,*mapping=NULL;
    if (!table) return 2;
    for (size_t i=0;i<samples;++i) {
        for (size_t k=0;k<16;++k)
            if (!(rows[i*16+k]>0.) || !isfinite(rows[i*16+k])) {result=3;goto done;}
        if ((used+1)*3>capacity*2) {
            if (capacity>SIZE_MAX/(2*sizeof(size_t))) goto done;
            size_t old_capacity=capacity;capacity*=2;
            size_t *larger=calloc(capacity,sizeof(size_t));
            if (!larger) goto done;
            for (size_t j=0;j<old_capacity;++j) if (table[j]) {
                size_t id=table[j]-1;
                size_t slot=(size_t)prepare_row_hash(rows+16*indices[id])&(capacity-1);
                while (larger[slot]) slot=(slot+1)&(capacity-1);
                larger[slot]=id+1;
            }
            free(table);table=larger;
        }
        size_t slot=(size_t)prepare_row_hash(rows+16*i)&(capacity-1);
        while (table[slot] && memcmp(rows+16*indices[table[slot]-1],rows+16*i,16*sizeof(double)))
            slot=(slot+1)&(capacity-1);
        if (!table[slot]) {indices[used]=(int64_t)i;table[slot]=++used;}
        inverse[i]=(int64_t)(table[slot]-1);
    }
    temporary=malloc(used*sizeof(int64_t));mapping=malloc(used*sizeof(int64_t));
    if (!temporary || !mapping) goto done;
    for (size_t width=1;width<used;) {
        for (size_t start=0;start<used;start+=2*width) {
            size_t middle=start+width,end=start+2*width;
            if (middle>used) middle=used;if (end>used) end=used;
            size_t left=start,right=middle;
            for (size_t j=start;j<end;++j) {
                if (left<middle && (right>=end ||
                    prepare_row_less(rows,(size_t)indices[left],(size_t)indices[right])))
                    temporary[j]=indices[left++];
                else temporary[j]=indices[right++];
            }
        }
        memcpy(indices,temporary,used*sizeof(int64_t));
        if (width>used/2) break;width*=2;
    }
    for (size_t i=0;i<used;++i) mapping[inverse[indices[i]]]=(int64_t)i;
    for (size_t i=0;i<samples;++i) inverse[i]=mapping[inverse[i]];
    *count=used;result=0;
done:
    free(table);free(temporary);free(mapping);return result;
}

API int waveform_prepare_reference(const uint8_t *source,size_t samples,
    const int64_t *units,size_t queries,const double *e,const double *u,
    const double *row,const double *steady,void *gemv_pointer,double *out) {
    if (!samples || !queries || !gemv_pointer) return 1;
    size_t values=samples;
    for (size_t j=0;j<queries;++j) {
        if (units[j]<0) return 2;
        uint64_t index=(uint64_t)units[j]/35469;
        if (index>=SIZE_MAX-1) return 2;
        if ((size_t)index>=values) values=(size_t)index+1;
    }
    if (values>SIZE_MAX/(6*sizeof(double))-1) return 3;
    double *states=calloc((values+1)*6,sizeof(double));
    if (!states) return 3;
    prepare_gemv gemv=(prepare_gemv)gemv_pointer;
    for (size_t i=0;i<values;++i) {
        double advanced[6];
        double x=i<samples ? ((double)source[i]-128.)/128. : 0.;
        gemv(101,111,6,6,1.,e,6,states+6*i,1,0.,advanced,1);
        for (size_t k=0;k<6;++k) states[6*(i+1)+k]=advanced[k]+u[k]*x;
    }
    for (size_t j=0;j<queries;++j) {
        size_t index=(size_t)(units[j]/35469),fraction=(size_t)(units[j]%35469);
        double x=index<samples ? ((double)source[index]-128.)/128. : 0.;
        const double *r=row+6*fraction,*state=states+6*index;
        /* NumPy's contiguous reduction for fewer than eight elements adds
           the six products in order, beginning at negative zero. */
        double sum=-0.;
        for (size_t k=0;k<6;++k) {
            double difference=state[k]-x*steady[k];
            double product=r[k]*difference;
            sum+=product;
        }
        out[j]=sum;
    }
    free(states);
    return 0;
}
