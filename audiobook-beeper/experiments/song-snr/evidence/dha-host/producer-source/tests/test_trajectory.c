/* Focused public-API test: gain-aligned incremental searches must preserve
 * the exact same predictor path as one call, and framing must add no loss. */
#include "dha_codec.h"
#include <math.h>
#include <stdio.h>
#include <string.h>

#define COUNT 1031
#define REQUIRE(x) do { if (!(x)) { fprintf(stderr,"trajectory check failed at line%d: %s\n",__LINE__,#x); return 1; } } while (0)

static int same_state(const dha_predictor_state *a, const dha_predictor_state *b) {
    return a->q==b->q && a->d1==b->d1 && a->d2==b->d2 && a->d3==b->d3;
}

int main(void) {
    dha_stream_info info;
    dha_encoder_options options;
    dha_predictor_state initial={39,0,0,0}, whole, current, unchanged;
    int16_t pcm[COUNT], q[COUNT], chunk_q[COUNT], decoded[COUNT];
    uint8_t symbols[COUNT], chunks[COUNT], gains[(COUNT+255)/256], chunk_gains[(COUNT+255)/256];
    uint8_t packet[DHA_MAX_FRAME_BYTES];
    unsigned i, first;
    size_t bytes, written;
    REQUIRE(dha_stream_default(&info,25000,1,4096,COUNT)==DHA_OK);
    dha_encoder_default(&options);
    options.beam_width=8; options.gain_candidates=2; options.lookahead=1;
    options.allow_pcm_fallback=0;
    for(i=0;i<COUNT;++i) pcm[i]=(int16_t)floor(5000*cos(i*0.07)+1200*sin(i*0.12)+0.5);
    REQUIRE(dha_encode_trajectory(&info,&options,&initial,pcm,COUNT,symbols,gains,q,&whole)==DHA_OK);
    current=initial;
    for(first=0;first<COUNT;first+=256) {
        uint16_t count=(uint16_t)(COUNT-first<256?COUNT-first:256);
        REQUIRE(dha_encode_trajectory(&info,&options,&current,pcm+first,count,
                chunks+first,chunk_gains+first/256,chunk_q+first,&current)==DHA_OK);
    }
    REQUIRE(!memcmp(q,chunk_q,sizeof(q)));
    REQUIRE(!memcmp(symbols,chunks,sizeof(symbols)));
    REQUIRE(!memcmp(gains,chunk_gains,sizeof(gains)));
    REQUIRE(same_state(&whole,&current));
    REQUIRE(dha_pack_frame(&info,&initial,symbols,gains,COUNT,0,0,
                          packet,sizeof(packet),&bytes)==DHA_OK);
    REQUIRE(dha_decode_frame(&info,packet,bytes,decoded,COUNT,&written,NULL)==DHA_OK);
    REQUIRE(written==COUNT);
    for(i=0;i<COUNT;++i) REQUIRE(decoded[i]==(((q[i]+257)/2)-128)*256);
    unchanged=current;
    REQUIRE(dha_encode_trajectory(&info,&options,&initial,pcm,0,
                                  symbols,gains,q,&current)==DHA_E_ARGUMENT);
    REQUIRE(same_state(&current,&unchanged));
    options.beam_width=0;
    REQUIRE(dha_encode_trajectory(&info,&options,&initial,pcm,COUNT,
                                  symbols,gains,q,&current)==DHA_E_ARGUMENT);
    REQUIRE(same_state(&current,&unchanged));
    puts("continuous trajectory, chunk equivalence and DHAF replay: PASS");
    return 0;
}
