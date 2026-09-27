"""Cold-installed copy placement variant; half-row packet bytes are unchanged."""
from build_fap3_trd import sha, padded, sectors
from half_row_player import Builder as PreviousBuilder
from uncontended_half_copy import install


class Builder(PreviousBuilder):
    def ram(self, start, end, next_sector, remaining):
        sections, metadata = super().ram(start, end, next_sector, remaining)
        banks = self.expected_banks
        def bank_at(at): return 5 if at<0x8000 else 2 if at<0xc000 else 7
        def read8(at): return banks[bank_at(at)][at&16383]
        def put(at, code):
            if (at&16383)+len(code)>16384: raise ValueError('cross-bank patch')
            banks[bank_at(at)][at&16383:(at&16383)+len(code)] = code
        install(read8, put, metadata)
        result = []
        for section in sections:
            at = section['address']&16383
            raw = bytes(banks[section['bank']][at:at+section['decoded_bytes']])
            if sha(raw)==section['sha256']:
                result.append(section); continue
            if section.get('startup_delta'): raise ValueError('unexpected table modification')
            coded = self.compress(raw)
            result.append(dict(section, data=padded(coded), compressed_bytes=len(coded),
                               sectors=sectors(coded), sha256=sha(raw)))
        return result, metadata
