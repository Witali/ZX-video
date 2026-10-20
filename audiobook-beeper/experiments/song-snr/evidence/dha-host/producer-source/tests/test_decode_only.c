#include "dha_codec.h"
#include <stdio.h>
#include <string.h>
#define CHECK(x) do {if(!(x)){fprintf(stderr,"line%d: %s\n",__LINE__,#x);return 1;}}while(0)
int main(void) {
    dha_stream_info info,parsed;
    uint8_t header[DHA_FILE_HEADER_BYTES];size_t bytes=0;unsigned i,ones=0;
    dha_pdm_state pdm={0};
    CHECK(dha_stream_default(&info,25000,1,4096,0)==DHA_OK);
    CHECK(dha_header_write(&info,header,sizeof(header),&bytes)==DHA_OK);
    CHECK(bytes==DHA_FILE_HEADER_BYTES);
    CHECK(dha_header_read(&parsed,header,bytes)==DHA_OK);
    CHECK(parsed.sample_rate==25000&&parsed.total_samples==0);
    CHECK(!memcmp(info.model,parsed.model,1024)&&!memcmp(info.ans,parsed.ans,512));
    header[100]^=1;CHECK(dha_header_read(&parsed,header,bytes)==DHA_E_CRC);
    for(i=0;i<256;i++)ones+=dha_pdm_next(&pdm,137);
    CHECK(ones==137&&pdm.accumulator==0);
    puts("decoder-only API passed");return 0;
}
