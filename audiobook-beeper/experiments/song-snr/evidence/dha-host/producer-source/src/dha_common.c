#include "dha_internal.h"
#include "dha_tables.inc.h"

/* Read a little-endian16 value from a caller-provided span of at least two
   bytes. Byte loads allow unaligned input and avoid host-endian assumptions. */
uint16_t dha_get16(const uint8_t *p) { return (uint16_t)((unsigned)p[0]|((unsigned)p[1]<<8)); }
/* Read a little-endian32 value from at least four bytes. Widen each byte
   before shifting; this internal helper does not perform span validation. */
uint32_t dha_get32(const uint8_t *p) { return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24); }
/* Read a little-endian64 value from at least eight bytes, combining its low
   and high32 halves without an aligned uint64_t access. */
uint64_t dha_get64(const uint8_t *p) { return (uint64_t)dha_get32(p)|((uint64_t)dha_get32(p+4)<<32); }
/* Write v in little-endian order into two caller-owned bytes. The caller has
   already checked the output span; no allocation or host-endian store occurs. */
void dha_put16(uint8_t *p,uint16_t v) { p[0]=(uint8_t)v;p[1]=(uint8_t)(v>>8); }
/* Write all four bytes of v, least significant first, to a validated output
   span. Byte-sized assignments also support unaligned destinations. */
void dha_put32(uint8_t *p,uint32_t v) { unsigned i;for(i=0;i<4;i++)p[i]=(uint8_t)(v>>(i*8)); }
/* Write a little-endian64 value into eight caller-owned bytes using two
   explicit32-bit halves; the caller provides the complete writable span. */
void dha_put64(uint8_t *p,uint64_t v) { dha_put32(p,(uint32_t)v);dha_put32(p+4,(uint32_t)(v>>32)); }

/* Update a reflected IEEE CRC32 register with bytes of caller-owned input.
   Start with UINT32_MAX, carry the returned internal register between spans,
   and XOR UINT32_MAX once after the final span. Zero bytes dereferences no
   input. This helper does not allocate, mutate input, or finalize the CRC. */
uint32_t dha_crc_update(uint32_t crc,const uint8_t *p,size_t bytes) {
    size_t i;unsigned bit;
    for(i=0;i<bytes;i++) {
        crc^=p[i];
        /* Process the next reflected bit with the IEEE polynomial. Unsigned
           shifts make the result independent of signed-right-shift behavior. */
        for(bit=0;bit<8;bit++)crc=(crc>>1)^((crc&1u)?UINT32_C(0xedb88320):0u);
    }
    return crc;
}

/* Return a borrowed static message for a public status, including OK/DONE
   and unknown values. The caller must not modify or free the string. */
const char *dha_error_string(int status) {
    switch(status) {
    case DHA_OK:return "success";case DHA_DONE:return "end of frame";
    case DHA_E_ARGUMENT:return "invalid argument";case DHA_E_BUFFER:return "output buffer too small";
    case DHA_E_TRUNCATED:return "truncated input";case DHA_E_FORMAT:return "invalid format";
    case DHA_E_CRC:return "CRC mismatch";case DHA_E_PROFILE:return "trajectory outside DHA profile";
    case DHA_E_MEMORY:return "allocation failed";case DHA_E_UNSUPPORTED:return "unsupported version or feature";
    default:return "unknown error";
    }
}

/* Check stream metadata and the complete1024-byte predictor/512-byte ANS
   model without changing info. Return DHA_E_ARGUMENT for NULL, otherwise
   DHA_E_FORMAT on invalid metadata, predictor invariants or inverse coverage.
   The bounded inverse matrix is stack scratch, not heap or retained state. */
int dha_stream_validate(const dha_stream_info *info) {
    uint8_t inverse[5][256];unsigned at,symbol,n,base,k;
    if(!info)return DHA_E_ARGUMENT;
    if(!info->sample_rate||info->sample_rate>192000u||info->channels<1||info->channels>2||
       !info->frame_samples||info->frame_samples>DHA_MAX_FRAME_SAMPLES)return DHA_E_FORMAT;
    if(info->total_samples!=DHA_UNKNOWN_SAMPLES&&
       info->total_samples>(UINT64_C(1)<<32)*info->frame_samples)return DHA_E_FORMAT;
    /* Row0 is an odd-half lookup: index0 represents |q|=256, while q=0
       bypasses the row. Its signed negation must fit a byte, excluding -128.
       Full difference rows must contribute zero at their biased-zero index. */
    for(at=0;at<256;at++)if(info->model[at]==-128)return DHA_E_FORMAT;
    if(info->model[384]||info->model[640]||info->model[896])return DHA_E_FORMAT;
    memset(inverse,0,sizeof(inverse));
    for(at=0;at<256;at++) {
        symbol=info->ans[2*at]>>4;n=info->ans[2*at]&15u;base=info->ans[2*at+1];
        if(symbol>4||n>6||base+(1u<<n)>256)return DHA_E_FORMAT;
        /* One decoder entry covers [base,base+2^N) following states for its
           symbol. Reject overlaps; alignment of base to2^N is not required. */
        for(k=base;k<base+(1u<<n);k++)if(inverse[symbol][k]++)return DHA_E_FORMAT;
    }
    /* Every one of the five symbols must encode every following state exactly
       once. Gaps would make otherwise valid reverse-ANS trajectories unencodable. */
    for(symbol=0;symbol<5;symbol++)for(k=0;k<256;k++)if(!inverse[symbol][k])return DHA_E_FORMAT;
    return DHA_OK;
}

/* Populate caller-owned info with metadata and immutable built-in table
   copies, then validate the resulting stream. No allocation is needed. A
   non-NULL info is overwritten even if the supplied metadata is rejected. */
int dha_stream_default(dha_stream_info *info,uint32_t rate,uint16_t channels,
                       uint16_t frame_samples,uint64_t total_samples) {
    if(!info)return DHA_E_ARGUMENT;
    memset(info,0,sizeof(*info));info->sample_rate=rate;info->channels=channels;
    info->frame_samples=frame_samples;info->total_samples=total_samples;
    memcpy(info->model,dha_default_model,sizeof(info->model));
    memcpy(info->ans,dha_default_ans,sizeof(info->ans));
    return dha_stream_validate(info);
}

/* Serialize one canonical DHAF header into caller-owned output. Validate info
   and capacity before modifying out; a non-NULL written starts at zero and
   becomes DHA_FILE_HEADER_BYTES only on success. Fields are little-endian,
   model bytes retain their signed-byte representation, and reserved bytes
   are zero. The caller keeps info and output as separate valid buffers. */
int dha_header_write(const dha_stream_info *info,uint8_t *out,size_t capacity,size_t *written) {
    int status;if(written)*written=0;
    if(!info||!out||!written)return DHA_E_ARGUMENT;
    status=dha_stream_validate(info);if(status!=DHA_OK)return status;
    if(capacity<DHA_FILE_HEADER_BYTES)return DHA_E_BUFFER;
    memset(out,0,DHA_FILE_HEADER_BYTES);memcpy(out,"DHAF",4);
    /* Fixed prefix0..31: magic/version/header size, rate, channel count,
       frame limit and per-channel total; the final eight bytes stay reserved. */
    dha_put16(out+4,1);dha_put16(out+6,DHA_FILE_HEADER_BYTES);
    dha_put32(out+8,info->sample_rate);dha_put16(out+12,info->channels);
    dha_put16(out+14,info->frame_samples);dha_put64(out+16,info->total_samples);
    memcpy(out+32,info->model,1024);memcpy(out+1056,info->ans,512);
    /* The CRC follows both tables and protects bytes0..1567, excluding its
       own four-byte field. Finalize only after the complete protected span. */
    dha_put32(out+1568,dha_crc_update(UINT32_MAX,out,1568)^UINT32_MAX);
    *written=DHA_FILE_HEADER_BYTES;return DHA_OK;
}

/* Parse and authenticate the first DHAF header in a caller-owned byte span.
   Additional bytes may follow it; packet parsing is the caller's next step.
   Validate version/reserved fields, CRC and table semantics in local storage,
   then replace info only on success. No input ownership is transferred. */
int dha_header_read(dha_stream_info *info,const uint8_t *in,size_t bytes) {
    dha_stream_info next;int status;
    if(!info||!in)return DHA_E_ARGUMENT;
    if(bytes<DHA_FILE_HEADER_BYTES)return DHA_E_TRUNCATED;
    if(memcmp(in,"DHAF",4))return DHA_E_FORMAT;
    if(dha_get16(in+4)!=1||dha_get16(in+6)!=DHA_FILE_HEADER_BYTES||
       dha_get32(in+24)||dha_get32(in+28))return DHA_E_UNSUPPORTED;
    /* Authenticate the serialized prefix/tables before accepting the parsed
       metadata. Byte readers avoid struct packing and host-endian dependencies. */
    if((dha_crc_update(UINT32_MAX,in,1568)^UINT32_MAX)!=dha_get32(in+1568))return DHA_E_CRC;
    memset(&next,0,sizeof(next));next.sample_rate=dha_get32(in+8);next.channels=dha_get16(in+12);
    next.frame_samples=dha_get16(in+14);next.total_samples=dha_get64(in+16);
    memcpy(next.model,in+32,1024);memcpy(next.ans,in+1056,512);
    status=dha_stream_validate(&next);if(status!=DHA_OK)return status;
    *info=next;return DHA_OK;
}

/* Compute the integer predictor from q and three signed8 backward differences.
   info contains validated tables; state and prediction are caller-owned. The
   odd q row and biased difference rows already contain offline-rounded terms,
   so no floating point or rounding is performed here. Write the calculated
   prediction and return DHA_E_PROFILE if q or the result leaves[-256,254];
   NULL arguments return DHA_E_ARGUMENT. The history itself is not advanced. */
int dha_predict(const dha_stream_info *info,const dha_predictor_state *state,int *prediction) {
    int q,correction;
    if(!info||!state||!prediction)return DHA_E_ARGUMENT;
    q=state->q;if(q < -256||q>254)return DHA_E_PROFILE;
    /* q=0 contributes exactly zero. Negative q uses the signed negation of
       the positive-half entry; |q|=256 wraps to its designated index0. */
    correction=q?info->model[(q<0?-q:q)&255]:0;
    if(q<0)correction=-correction;
    *prediction=q+correction+info->model[256+(int)state->d1+128]+
        info->model[512+(int)state->d2+128]+info->model[768+(int)state->d3+128];
    return (*prediction < -256||*prediction>254)?DHA_E_PROFILE:DHA_OK;
}

/* Advance an already valid predictor history to canonical q without clipping.
   Compute d1=q-oldq, d2=d1-oldd1 and d3=d2-oldd2 in wide integers; commit
   together only when each fits signed8. A NULL state or invalid q/differences
   returns DHA_E_PROFILE and leaves any existing state unchanged. */
int dha_advance(dha_predictor_state *state,int q) {
    int a,b,c;
    if(!state||q < -256||q>254)return DHA_E_PROFILE;
    a=q-state->q;b=a-state->d1;c=b-state->d2;
    /* Check before narrowing: a final frame sample must obey the same bounds
       as an intermediate sample, even though its history will not be reused. */
    if(a < -128||a>127||b < -128||b>127||c < -128||c>127)return DHA_E_PROFILE;
    state->q=(int16_t)q;state->d1=(int8_t)a;state->d2=(int8_t)b;state->d3=(int8_t)c;
    return DHA_OK;
}

/* Validate exactly one DHF1 packet against its stream and return metadata in
   frame only on success. All buffers remain caller-owned; no allocation or
   payload decoding occurs. Require exact packet length, bounded sample/channel
   metadata, kind-specific canonical layout and CRC. Cross-packet sequence and
   channel ordering remain the container caller's responsibility. DHA terminal
   state and recursive trajectory checks require finishing decoder_next. */
int dha_frame_read(const dha_stream_info *info,const uint8_t *packet,size_t bytes,dha_frame_info *frame) {
    dha_frame_info f;size_t payload;uint32_t crc;int status;
    if(!info||!packet||!frame)return DHA_E_ARGUMENT;
    status=dha_stream_validate(info);if(status!=DHA_OK)return status;
    if(bytes<DHA_FRAME_HEADER_BYTES)return DHA_E_TRUNCATED;
    if(memcmp(packet,"DHF1",4))return DHA_E_FORMAT;
    memset(&f,0,sizeof(f));f.packet_bytes=dha_get32(packet+4);f.sequence=dha_get32(packet+8);
    f.samples=dha_get16(packet+12);f.channel=packet[14];f.kind=packet[15];
    /* Explicit sign extension preserves the wire's two's-complement q16 and
       difference bytes without depending on a host's unsigned-to-signed cast. */
    f.initial.q=(int16_t)((int)dha_get16(packet+16)-(packet[17]&128u?65536:0));
    f.initial.d1=(int8_t)((int)packet[18]-(packet[18]&128u?256:0));
    f.initial.d2=(int8_t)((int)packet[19]-(packet[19]&128u?256:0));
    f.initial.d3=(int8_t)((int)packet[20]-(packet[20]&128u?256:0));
    f.ans_state=packet[21];f.payload_bits=dha_get32(packet+24);
    if(f.packet_bytes<DHA_FRAME_HEADER_BYTES||f.packet_bytes>DHA_MAX_FRAME_BYTES||
       !f.samples||f.samples>info->frame_samples||f.channel>=info->channels||packet[22]||packet[23])return DHA_E_FORMAT;
    if(bytes<f.packet_bytes)return DHA_E_TRUNCATED;
    /* Unlike the file-header reader, this API accepts no concatenated tail;
       the caller must split a stream into individually bounded packets first. */
    if(bytes!=f.packet_bytes)return DHA_E_FORMAT;
    payload=(size_t)f.packet_bytes-DHA_FRAME_HEADER_BYTES;
    if(f.kind==DHA_FRAME_PCM16) {
        /* Raw fallback is exact little-endian PCM16, with no predictor or ANS
           initialization and exactly16 meaningful bits per channel sample. */
        if(payload!=2u*f.samples||f.payload_bits!=16u*f.samples||f.initial.q||f.initial.d1||
           f.initial.d2||f.initial.d3||f.ans_state)return DHA_E_FORMAT;
    } else if(f.kind==DHA_FRAME_DHA) {
        /* Each started256-sample block carries one five-bit gain; each sample
           adds zero through six suffix bits. Store only the rounded-up byte
           span, and require the unused low bits of its final byte to be zero. */
        if(f.initial.q < -256||f.initial.q>254||f.payload_bits>6u*f.samples+5u*((f.samples+255u)/256u)||
           f.payload_bits<5u*((f.samples+255u)/256u)||payload!=(f.payload_bits+7u)/8u)return DHA_E_FORMAT;
        if((f.payload_bits&7u)&&payload&&(packet[bytes-1]&((1u<<(8u-(f.payload_bits&7u)))-1u)))return DHA_E_FORMAT;
    } else return DHA_E_UNSUPPORTED;
    /* Frame CRC spans header bytes0..27 and the full payload, skipping the
       checksum at28..31. It therefore binds sequence/channel/state/bit count
       and even canonical byte-padding bits to this packet. */
    crc=dha_crc_update(UINT32_MAX,packet,28);
    crc=dha_crc_update(crc,packet+DHA_FRAME_HEADER_BYTES,payload)^UINT32_MAX;
    if(crc!=dha_get32(packet+28))return DHA_E_CRC;
    *frame=f;return DHA_OK;
}

/* Assemble a bounded packet from caller-owned metadata and payload without
   allocation. A local header preserves canonical little-endian layout and
   reserved zeros. written starts at zero; success publishes the packet size.
   The final frame_read check validates the serialized result, so out may
   already have changed if semantic validation fails. This internal writer
   does not validate a DHA trajectory or claim transactional output on error. */
int dha_write_packet(const dha_stream_info *info,const dha_frame_info *f,const uint8_t *payload,
                     size_t bytes,uint8_t *out,size_t capacity,size_t *written) {
    uint8_t header[DHA_FRAME_HEADER_BYTES];uint32_t crc;dha_frame_info checked;int status;
    if(written)*written=0;
    if(!info||!f||!out||!written||(!payload&&bytes))return DHA_E_ARGUMENT;
    if(bytes>DHA_MAX_FRAME_BYTES-DHA_FRAME_HEADER_BYTES)return DHA_E_ARGUMENT;
    if(capacity<DHA_FRAME_HEADER_BYTES+bytes)return DHA_E_BUFFER;
    memset(header,0,sizeof(header));memcpy(header,"DHF1",4);
    /* Populate explicit offsets instead of serializing a native C struct;
       signed initial state is represented by its low16/8 two's-complement bits. */
    dha_put32(header+4,(uint32_t)(DHA_FRAME_HEADER_BYTES+bytes));dha_put32(header+8,f->sequence);
    dha_put16(header+12,f->samples);header[14]=f->channel;header[15]=f->kind;
    dha_put16(header+16,(uint16_t)f->initial.q);header[18]=(uint8_t)f->initial.d1;
    header[19]=(uint8_t)f->initial.d2;header[20]=(uint8_t)f->initial.d3;header[21]=f->ans_state;
    dha_put32(header+24,f->payload_bits);
    crc=dha_crc_update(UINT32_MAX,header,28);crc=dha_crc_update(crc,payload,bytes)^UINT32_MAX;
    dha_put32(header+28,crc);
    /* Compute CRC before copying. memmove permits payload overlap with its
       destination, and the saved local header is installed only afterwards. */
    if(bytes)memmove(out+DHA_FRAME_HEADER_BYTES,payload,bytes);
    memcpy(out,header,sizeof(header));
    status=dha_frame_read(info,out,DHA_FRAME_HEADER_BYTES+bytes,&checked);
    if(status!=DHA_OK)return status;
    *written=DHA_FRAME_HEADER_BYTES+bytes;return DHA_OK;
}
