/* Host-only independent encoder/reference, compiled against unmodified Speex. */
#include <speex/speex.h>
#include <speex/speex_bits.h>
#define API __declspec(dllexport)
static void *encoder,*decoder;
static SpeexBits eb,db;
API void reference_reset(void)
{
    int mode=3,zero=0,complexity=10;
    if(encoder) {speex_encoder_destroy(encoder);speex_bits_destroy(&eb);}
    if(decoder) {speex_decoder_destroy(decoder);speex_bits_destroy(&db);}
    encoder=speex_encoder_init(&speex_nb_mode);
    decoder=speex_decoder_init(&speex_nb_mode);
    speex_encoder_ctl(encoder,SPEEX_SET_MODE,&mode);
    speex_encoder_ctl(encoder,SPEEX_SET_VBR,&zero);
    speex_encoder_ctl(encoder,SPEEX_SET_DTX,&zero);
    speex_encoder_ctl(encoder,SPEEX_SET_COMPLEXITY,&complexity);
    speex_decoder_ctl(decoder,SPEEX_SET_ENH,&zero);
    speex_decoder_ctl(decoder,SPEEX_SET_HIGHPASS,&zero);
    speex_bits_init(&eb);speex_bits_init(&db);
}
API int reference_encode(short *in,char *out)
{
    speex_bits_reset(&eb);speex_encode_int(encoder,in,&eb);
    return speex_bits_write(&eb,out,20);
}
API int reference_decode(char *in,short *out)
{
    speex_bits_read_from(&db,in,20);
    return speex_decode_int(decoder,&db,out);
}
