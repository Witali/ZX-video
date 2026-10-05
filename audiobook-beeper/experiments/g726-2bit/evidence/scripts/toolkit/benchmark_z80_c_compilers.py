"""Compare identical portable C LZMA decoders on a guarded Z80 CPU.

No OS startup, disk, paging, IRQ or ULA time is included. See Z80_C_COMPILERS.md.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import gzip
import importlib.metadata
import json
import lzma
from pathlib import Path
import random
import re

from z80 import Z80Machine
from benchmark_lzma_z80 import FILTERS, fixture, put_word, word, instruction_tstates

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / ".tmp/z80-c-probe"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def hex_image(path):
    memory = {}
    eof = False
    for line in path.read_text().splitlines():
        if not line.startswith(":"):
            continue
        row = bytes.fromhex(line[1:])
        assert sum(row) % 256 == 0 and len(row) == row[0] + 5
        size, addr, kind = row[0], int.from_bytes(row[1:3], "big"), row[3]
        if kind == 0:
            for i, b in enumerate(row[4:4+size]):
                assert addr+i < 65536
                memory[addr+i] = b
        elif kind == 1:
            eof = True
        else:
            assert kind == 4 and row[4:6] == b"\0\0"
    assert eof and memory
    return memory


def load_variant(name):
    folder = BASE / name
    mapping = (folder / "decoder.map").read_text(errors="replace")
    if name == "sdcc":
        memory = hex_image(folder / "decoder.ihx")
        entry = int(re.search(r"([0-9A-F]{8})\s+_entry\s", mapping)[1], 16)
        data = (0x9000, 0x901D)
    elif name == "hitech":
        entry = int(re.search(r"_entry\s+text\s+([0-9A-F]+)", mapping)[1], 16)
        end = int(re.search(r"__Htext\s+text\s+([0-9A-F]+)", mapping)[1], 16)
        payload = (folder / "decoder.out").read_bytes()[:end-0x200]
        assert len(payload) == end-0x200
        memory = dict(enumerate(payload, 0x200))
        data = (0x9000, 0x901D)
    elif name == "z88dk":
        symbols = {k:int(v,16) for k,v in re.findall(r'^(\w+)\s+= \$([0-9A-F]+)',mapping,re.M)}
        entry = symbols['_entry']
        data = (symbols['__bss_compiler_head'],symbols['__bss_compiler_tail'])
        payload = (folder/'decoder_code_compiler.bin').read_bytes()
        assert len(payload) == symbols['__rodata_compiler_tail'] - 0x200
        memory = dict(enumerate(payload,0x200))
    else:
        raise ValueError(name)
    return dict(name=name, memory=memory, entry=entry, data=data,
                code_bytes=len(memory), image_sha256=sha(bytes(memory[a] for a in sorted(memory))))


def timing(m):
    """Zilog UM0080 timing extension for compiler-generated indexed code."""
    op, sub = m.memory[m.pc:m.pc+2]
    if op in (0xDD,0xFD):
        if sub == 0xCB:
            return 20 if 0x40 <= m.memory[m.pc+3] < 0x80 else 23
        if sub in (0x34,0x35):
            return 23
        if sub == 0x36 or (0x40 <= sub < 0xC0 and sub != 0x76
                and ((sub & 7) == 6 or (sub < 0x80 and (sub >> 3) & 7 == 6))):
            return 19
        m.pc += 1
        try:
            return timing(m) + 4
        finally:
            m.pc -= 1
    if op == 0xE3:
        return 19
    if op == 0xE9:
        return 4
    if op == 0xF9:
        return 6
    if op == 0xED and sub == 0x44:
        return 8
    if op == 0xED and sub in (0xA0,0xA8):
        return 16
    if op & 0xC7 in (0xC0,0xC2,0xC4):
        flags = [not(m.f&64),m.f&64,not(m.f&1),m.f&1,
                 not(m.f&4),m.f&4,not(m.f&128),m.f&128]
        yes = flags[(op>>3)&7]
        return 10 if op&7 == 2 else (11 if yes else 5) if op&7 == 0 else (17 if yes else 10)
    return instruction_tstates(m)


def execute(v, packed, size, audit=False):
    m = Z80Machine()
    m.memory[:] = b"\xa5" * 65536
    for addr, b in v["memory"].items():
        m.memory[addr] = b
    inp, out, stack, stop = 0x4000, 0xC000, 0xBFF0, 0x100
    assert len(packed) <= 16384 and size <= 15873
    m.set_memory_block(inp, packed)
    for i, value in enumerate((inp, inp+len(packed), out, size, 0xFFFF, 0, 0, 0)):
        put_word(m, 0xB000+i*2, value)
    put_word(m, stack-2, stop)
    m.pc, m.sp = v["entry"], stack-2
    m.ix, m.iy = 0x1234, 0x5678
    m.set_breakpoint(stop)
    budget = 2_000_000_000
    m.ticks_to_stop = budget
    high, low_sp = out, stack-2
    # Only models, compiler BSS and mailbox are writable without callbacks.
    m.mark_addrs(0, 65536, m.READ_MARK | m.WRITE_MARK)
    for addr in v["memory"]:
        m.unmark_addr(addr, m.READ_MARK)
    for lo, hi in ((inp, inp+len(packed)), (stack-1024, stack)):
        m.unmark_addrs(lo, hi-lo, m.READ_MARK)
    for lo, hi in ((0xA000, 0xAF2E), v["data"], (0xB000, 0xB010)):
        m.unmark_addrs(lo, hi-lo, m.READ_MARK | m.WRITE_MARK)

    def read(addr):
        assert out <= addr < high, f"invalid read {addr:04x} at {m.pc:04x}"
        return m.memory[addr]

    def write(addr, b):
        nonlocal high, low_sp
        if out <= addr < out+min(size,15872):
            assert addr <= high
            high = max(high, addr+1)
        elif stack-1024 <= addr < stack:
            low_sp = min(low_sp,addr)
        else:
            raise AssertionError(f"invalid write {addr:04x} at {m.pc:04x}")
        m.memory[addr] = b

    m.set_read_callback(read)
    m.set_write_callback(write)
    counts, cycles, audited = Counter(), Counter(), 0
    while m.pc != stop:
        if audit:
            expected = timing(m)
            before_pc = m.pc
            prefix = m.memory[m.pc]
            category = 'indexed_prefix' if prefix in (0xDD,0xFD) else 'other'
            before = m.frame_tick
            # This emulator can yield just after an IX/IY prefix (4 T).
            # Permit its body as well, so the audit counts complete instructions.
            m.ticks_to_stop = 5 if prefix in (0xDD,0xFD) else 1
        events = m.run()
        if audit:
            actual = (m.frame_tick-before) % 100000
            assert actual == expected,(v['name'],hex(before_pc),hex(m.pc),actual,expected,
                                       bytes(m.memory[before_pc:before_pc+4]).hex())
            audited += actual
            counts[category] += 1
            cycles[category] += actual
            assert audited < budget
        else:
            assert not events & m._TICKS_LIMIT_HIT, f"time limit at {m.pc:04x}"
    assert m.sp == stack and word(m, 0xB00E) == 0x0204
    status = word(m, 0xB008)
    assert status in (0,1)
    return dict(ok=status == 0, decoded=bytes(m.memory[out:high]),
                tstates=audited if audit else budget-m.ticks_to_stop, consumed=word(m,0xB00A),
                produced=word(m,0xB00C), stack_bytes=stack-low_sp,
                ix_preserved=m.ix == 0x1234, iy_preserved=m.iy == 0x5678,
                **(dict(instruction_counts=dict(counts),category_tstates=dict(cycles)) if audit else {}))


def check(v, raw, packed=None):
    if packed is None:
        packed=lzma.compress(raw,format=lzma.FORMAT_RAW,filters=FILTERS)
    result=execute(v,packed,len(raw))
    assert result['ok'],(v['name'],{k:x for k,x in result.items() if k!='decoded'})
    assert result.pop('decoded')==raw,v['name']
    assert result['produced']==len(raw) and result['consumed']==len(packed)
    return dict(raw_bytes=len(raw),packed_bytes=len(packed),raw_sha256=sha(raw),**result)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--variants',nargs='+',default=['sdcc','hitech','z88dk'])
    p.add_argument('--smoke',action='store_true')
    p.add_argument('--reuse',type=Path,help='Reuse complete results with identical C source, image and fixture hashes')
    p.add_argument('--output',type=Path,default=ROOT/'toolkit/z80_c_compiler_benchmark.json')
    a=p.parse_args()
    rng=random.Random(991)
    cases=[('empty',b''),('one',b'X'),('overlap',b'A'*15872),
           ('alphabet',bytes(range(256))*8),('random',rng.randbytes(1024)),
           ('matched',b'abcabcXabcabcY'*90)]
    source_hash=sha((ROOT/'toolkit/lzma_decoder_c89.c').read_text().encode())
    blocks=fixture()
    cached=json.loads(a.reuse.read_text()) if a.reuse else {}
    if cached:
        assert cached['complete'] and cached['c_source_sha256_lf']==source_hash
        if 'compressed_payload_sha256' in cached:
            assert cached['compressed_payload_sha256']==sha(b''.join(p for _,p in blocks))
    results={}
    fresh=[]
    for name in a.variants:
        v=load_variant(name)
        old=cached.get('variants',{}).get(name)
        if old:
            for key in ('image_sha256','code_bytes','entry'):
                assert old[key]==v[key]
            assert tuple(old['data'])==v['data'] and len(old['blocks'])==len(blocks)
            for row,(raw,packed) in zip(old['blocks'],blocks):
                assert row['raw_sha256']==sha(raw) and row['raw_bytes']==len(raw)
                assert row['packed_bytes']==len(packed) and row['ok']
            results[name]=old
            print(name,'reused verified image and fixture',flush=True)
            continue
        fresh.append(name)
        rows=[]
        for case,raw in cases:
            r=check(v,raw);rows.append(dict(case=case,**r))
            print(name,case,r['tstates'],'T',flush=True)
        badraw=b'abcdabcX'*8
        packed=lzma.compress(badraw,format=lzma.FORMAT_RAW,filters=FILTERS)
        errors=[(packed[:i],len(badraw)) for i in range(len(packed))]
        errors += [(packed,len(badraw)-1),(packed,len(badraw)+1),
                   (b'\x01'+packed[1:],len(badraw)),(packed+b'\0',len(badraw)),
                   (packed,15873)]
        for payload,size in errors:
            assert not execute(v,payload,size)['ok']
        results[name]={k:v[k] for k in ('entry','code_bytes','data','image_sha256')}
        results[name].update(edges=rows,rejected_cases=len(errors),blocks=[])
    if not a.smoke and fresh:
        for i,(raw,packed) in enumerate(blocks):
            for name in fresh:
                r=check(load_variant(name),raw,packed)
                results[name]['blocks'].append(dict(block=i,**r))
            print('block',i,'exact',flush=True)
    for name,r in results.items():
        r['total_tstates']=sum(x['tstates'] for x in r['blocks'])
        r['maximum_stack_bytes']=max(x['stack_bytes'] for x in r['edges']+r['blocks'])
        audit_raw=b'abcabcXabcabcY'
        payload=lzma.compress(audit_raw,format=lzma.FORMAT_RAW,filters=FILTERS)
        audited=execute(load_variant(name),payload,len(audit_raw),audit=True)
        assert audited['ok'] and audited.pop('decoded')==audit_raw
        ordinary=execute(load_variant(name),payload,len(audit_raw))
        assert audited['tstates']==ordinary['tstates']
        r['instruction_audit']=dict(raw_sha256=sha(audit_raw),raw_bytes=len(audit_raw),**audited)
        metadata=BASE/name/'build.json'
        if metadata.exists():
            r['build']=json.loads(metadata.read_text())
            assert r['build']['source_sha256_lf']==source_hash
    report=dict(complete=not a.smoke,release=False,variants=results,
                c_source_sha256_lf=source_hash,
                harness_sha256_lf=sha(Path(__file__).read_text().encode()),
                compressed_payload_sha256=sha(b''.join(p for _,p in blocks)),
                compressed_payload_bytes=sum(len(p) for _,p in blocks),
                framed_stream_bytes=sum(len(p)+4 for _,p in blocks),
                raw_stream_sha256=sha(b''.join(r for r,_ in blocks)),
                emulator=dict(package='z80',version=importlib.metadata.version('z80')),
                scope='Component CPU only; excludes startup, disk, paging, IRQ, ULA and frame output.')
    if not a.smoke:
        evidence=ROOT/'toolkit/z80_c_compiler_evidence'
        evidence.mkdir(exist_ok=True)
        artifacts={}
        for name in a.variants:
            for source,suffix in [('decoder.map','map'),
                    ('decoder.c.lis' if name=='z88dk' else 'decoder.asm','listing')]:
                raw=(BASE/name/source).read_bytes()
                path=evidence/f'{name}.{suffix}.gz'
                path.write_bytes(gzip.compress(raw,mtime=0))
                artifacts[str(path.relative_to(ROOT))]=dict(uncompressed_sha256=sha(raw),bytes=len(raw))
        report['generated_code_evidence']=artifacts
    a.output.write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    main()
