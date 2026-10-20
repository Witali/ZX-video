/* Source-preserving codec preconditioning, independent of the DHA library.
 * Even coded positions retain every physical PCM16 sample exactly. Odd
 * positions insert the arithmetic midpoint to the next sample; the final
 * midpoint repeats the final source sample. Integer division truncates toward
 * zero. The prepared PCM8-scaled source makes every midpoint exact.
 */
#include <stddef.h>
#include <stdint.h>

#if defined(_WIN32)
#define API __declspec(dllexport)
#else
#define API
#endif

API size_t bridge2_transform(const int16_t *source, size_t count,
                            int16_t *coded) {
    size_t i;
    for (i = 0; i < count; ++i) {
        int32_t a = source[i];
        int32_t b = source[i + (i + 1 < count)];
        coded[2 * i] = (int16_t)a;
        coded[2 * i + 1] = (int16_t)((a + b) / 2);
    }
    return 2 * count;
}

/* Remove helper positions after ordinary DHA decoding. No interpolation,
 * gain adjustment or change of the physical source timebase occurs here.
 */
API size_t bridge2_select_even(const int16_t *coded, size_t physical_count,
                              int16_t *physical) {
    size_t i;
    for (i = 0; i < physical_count; ++i) physical[i] = coded[2 * i];
    return physical_count;
}
