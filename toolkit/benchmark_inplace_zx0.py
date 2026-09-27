"""Execute all selected ZX0 blocks with disjoint and shared source/history.

This uses the bundled 126-byte turbo decoder, not the player's coroutine.
Instruction-table T-states exclude IRQ, ULA, loading, paging, producer and
queue control. Every input read/output write is guarded and traced.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import struct

from benchmark_compact_screen import NativeCPU
from build_fap3_trd import sha
from build_zxv_trd import MiniAssembler
from validate_fast_sparse import CPU
from zx0_codec import emit_decoder, decompress

ROOT = Path(__file__).parent
CODE, STACK, STOP = 0x8000, 0xbdf0, 0xbdf0


class GuardCPU(NativeCPU):
    def read8(self, address):
        address &= 65535
        if self.guarding and (address>=0xc000 or 0x4000<=address<0x8000 or address<0x4000):
            if address==self.source_start+self.input_reads and self.input_reads<len(self.payload):
                result = CPU.read8(self, address)
                if result!=self.payload[self.input_reads]: raise AssertionError('unread source changed')
                self.input_reads += 1
                return result
            if not self.output_base<=address<self.output_base+self.produced:
                raise AssertionError(f'read outside input/live history: {address:04x}')
        return CPU.read8(self, address)

    def write8(self, address, value):
        address &= 65535
        if self.guarding:
            if self.output_base<=address<self.output_base+len(self.expected):
                if address!=self.output_base+self.produced or value!=self.expected[self.produced]:
                    raise AssertionError('output byte or cursor differs')
                if self.input_reads<len(self.payload):
                    if self.source_start+self.input_reads<=address<self.source_start+len(self.payload):
                        raise AssertionError('output overwrites unread input')
                    self.minimum = max(self.minimum, self.produced+1-self.input_reads)
                self.digest.update(self.input_reads.to_bytes(4, 'little'))
                self.produced += 1
            elif not (STACK-64<=address<STACK or address in self.patched):
                raise AssertionError(f'write outside decoder contract: {address:04x}')
        return CPU.write8(self, address, value)


def native(payload, expected, input_start, *, shared=True, slot=0):
    if (not 0<=input_start or input_start+len(payload)>16384 or not 1<=len(expected)<=16384
            or slot not in (0, 1, 3)):
        raise ValueError('invalid decoder bank layout')
    a = MiniAssembler(CODE); entry = emit_decoder(a, 'turbo'); code = a.resolve()
    c = GuardCPU(b'', b''); c.guarding = False
    for bank in c.banks: bank[:] = b'\xa5'*16384
    for i, value in enumerate(code): c.write8(CODE+i, value)
    c.port_7ffd = 0x10|slot; c.banks[slot][input_start:input_start+len(payload)] = payload
    c.source_start = 0xc000+input_start; c.output_base = 0xc000 if shared else 0x4000
    c.payload, c.expected = payload, expected
    c.produced = c.input_reads = c.minimum = 0; c.digest = hashlib.sha256()
    c.patched = {a.labels['dzx0t_last_offset']+1, a.labels['dzx0t_last_offset']+2}
    c.set_hl(c.source_start); c.set_de(c.output_base); c.sp = STACK; c.push(STOP)
    c.pc = a.labels[entry]; c.guarding = True
    while c.pc!=STOP:
        if c.steps>2_000_000: raise AssertionError('decoder did not finish')
        c.step()
    c.guarding = False
    actual = bytes(c.read8(c.output_base+i) for i in range(len(expected)))
    if (actual!=expected or c.input_reads!=len(payload) or c.produced!=len(expected)
            or c.sp!=STACK or c.hl()!=(c.source_start+len(payload))&65535
            or c.de()!=(c.output_base+len(expected))&65535 or c.port_7ffd!=0x10|slot):
        raise AssertionError('final decoder state differs')
    return dict(tstates=c.tstates, input_reads=c.input_reads, output_writes=c.produced,
        minimum_input_start=c.minimum, write_input_cursors_sha256=c.digest.hexdigest(),
        code_sha256=sha(code), code_bytes=len(code), stack_bytes=STACK-c.min_sp)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--probe', type=Path, required=True)
    p.add_argument('--evidence', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--block-bytes', type=int, nargs='+', default=[8192, 15872])
    a = p.parse_args(); probe = json.loads(a.probe.read_bytes())
    if not probe['complete']: raise ValueError('complete host probe required')
    variants = [v for v in probe['variants'] if v['block_bytes'] in a.block_bytes]
    if len(variants)!=len(a.block_bytes) or not all(v['all_sector_layouts_safe'] for v in variants):
        raise ValueError('selected variants must exist and be safe')
    report = dict(complete=False, release=False, scope=__doc__, probe_sha256=sha(a.probe.read_bytes()),
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf', variants=[])
    def save(): a.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')
    try:
        for variant in variants:
            size = variant['block_bytes']; item = dict(block_bytes=size, volumes=[])
            report['variants'].append(item)
            for volume in variant['volumes']:
                part = volume['part']; filename = f'block{size}-part{part:02}.stream.gz'
                descriptor = next(v for v in probe['archives'] if v['file']==filename)
                packed = (a.evidence/filename).read_bytes(); stream = gzip.decompress(packed)
                if sha(packed)!=descriptor['sha256'] or sha(stream)!=descriptor['decoded_sha256']:
                    raise ValueError('archived stream changed')
                row = dict(part=part, blocks=[]); item['volumes'].append(row)
                at = 0
                for old in volume['blocks']:
                    n, length = struct.unpack_from('<HH', stream, at); at += 4
                    payload = stream[at:at+length]; at += length; expected = decompress(payload, limit=n)
                    if sha(payload)!=old['payload_sha256'] or sha(expected)!=old['raw_sha256']:
                        raise ValueError('block bytes changed')
                    baseline = native(payload, expected, 0, shared=False, slot=(0, 1, 3)[part-1])
                    overlap = native(payload, expected, old['layout']['input_start'], slot=(0, 1, 3)[part-1])
                    if baseline!=overlap: raise AssertionError('shared/disjoint native trace or cost differs')
                    for key in ('minimum_input_start', 'write_input_cursors_sha256'):
                        if overlap[key]!=old['trace'][key]: raise AssertionError('host/native byte trace differs')
                    row['blocks'].append(dict(index=old['index'], **overlap, disjoint_tstates=baseline['tstates'],
                        delta_tstates=0, exact=True, input_start=old['layout']['input_start']))
                    if old['index']%25==0:
                        save(); print(f'{size} bytes: disk {part}, block {old["index"]+1}/{len(volume["blocks"])} native exact', flush=True)
                if at!=len(stream): raise ValueError('unconsumed stream')
                row.update(complete=True, tstates=sum(b['tstates'] for b in row['blocks']),
                    output_bytes=sum(b['output_writes'] for b in row['blocks']))
                save()
            item.update(complete=True, tstates=sum(v['tstates'] for v in item['volumes']),
                output_bytes=sum(v['output_bytes'] for v in item['volumes']))
        report['complete'] = True
    except Exception as exc:
        report['failure'] = repr(exc); raise
    finally:
        report['source_sha256_lf'] = {n:sha((ROOT/n).read_bytes().replace(b'\r\n', b'\n')) for n in
            ('benchmark_inplace_zx0.py', 'test_inplace_zx0_native.py', 'zx0_codec.py',
             'benchmark_compact_screen.py', 'build_zxv_trd.py', 'validate_fast_sparse.py', 'validate_streaming_player.py',
             'third_party/zx0/dzx0_turbo.asm')}
        save()
    print(json.dumps([{k:v for k,v in r.items() if k!='volumes'} for r in report['variants']]), flush=True)


if __name__ == '__main__': main()
