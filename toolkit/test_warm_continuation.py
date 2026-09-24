"""Real boot/reset/prompt opcodes with poisoned mutable RAM and mocked ROM.

This does not pretend to play the predecessor: the full Fuse chain supplies
that evidence. Here every declared mutable byte is poisoned before a swap.
"""
import argparse
import json
from pathlib import Path
import struct
import unittest

import numpy as np
from build_fap3_trd import sha
import fap3_disk_z80 as disk
from test_fap3_disk import DiskCPU
from validate_streaming_player import extract_file,parse_dir
from warm_startup import immutable_fixed
from warm_resume_snapshot import make_snapshot
from zx0_codec import decompress


def player(image): return extract_file(image,next(e for e in parse_dir(image) if e[0]=='PLAYER'))


def until(cpu,pc):
    steps=cpu.steps
    while cpu.pc!=pc:
        cpu.step()
        if cpu.steps-steps>3000000: raise AssertionError(f'boot stalled at {cpu.pc:04x}')


def verify(directory,states):
    records=json.loads((directory/'volumes.json').read_text())
    metas=[json.loads((directory/r['metadata']).read_text()) for r in records]
    images=[(directory/r['file']).read_bytes() for r in records]
    cpu=DiskCPU(player(images[0]),images[0]); until(cpu,disk.DRIVER)
    reports=[]
    for index in range(1,len(images)):
        current,following=metas[index-1:index+1]
        # A continuation must not cold boot by accident, even in dirty RAM.
        cold=DiskCPU(player(images[index]),images[index]); cold.sp=0x5ff0
        cold.push(0x5e00); cold.pc=0x6000; cold.step()
        if cold.pc!=0x5e00 or cold.dos_reads: raise AssertionError('cold continuation was not refused')
        # Poison every runtime-mutated fixed location, all other banks, and
        # both native screens. Keep only immutable fixed data and compact n-1.
        for lo,hi in following['warm_reset_ranges']:
            for address in range(lo,hi): cpu.write8(address,0xa7)
        for bank in (0,1,3,4,7): cpu.banks[bank][:]=b'\xa7'*16384
        cpu.banks[5][:6912]=b'\xa7'*6912
        cpu.banks[5][0x2400:0x3300]=states[following['frame_start']-1].tobytes()
        invariant=bytes(cpu.banks[6])+immutable_fixed(bytes(cpu.banks[5]+cpu.banks[2]),following['warm_reset_ranges'])
        if sha(invariant)!=following['warm_immutable_sha256']: raise AssertionError('fixture lost immutable data')
        cpu.pc=disk.WAIT_NEXT; poll=current['bootstrap_labels']['poll_next']; until(cpu,poll)
        for bank in (5,7):
            for row in range(7):
                if bytes(cpu.banks[bank][0x10c0+row*256:0x10e0+row*256])!=disk.prompt_bitmap()[32*row:32*(row+1)]:
                    raise AssertionError('wrong prompt pixels')
        wrong_series=bytearray(images[index]);wrong_series[15*256+8]^=1
        for bad in (images[index-1],bytes(wrong_series)):
            cpu.trd=bad; reads=cpu.dos_reads; cpu.step(); until(cpu,poll)
            if cpu.dos_reads!=reads+1: raise AssertionError('bad disk was not rejected')
        cpu.trd=images[index]; cpu.step(); until(cpu,disk.DRIVER)
        fixed=bytes(cpu.banks[5]+cpu.banks[2])
        if sha(bytes(cpu.banks[6])+immutable_fixed(fixed,following['warm_reset_ranges']))!=following['warm_immutable_sha256']:
            raise AssertionError('bootstrap changed immutable data')
        if fixed[0x2400:0x3300]!=states[following['frame_start']-1].tobytes():
            raise AssertionError('bootstrap changed retained compact predictor')
        ranges_checked=0
        for section in following['sections']:
            at=section['sector']*256
            decoded=decompress(images[index][at:at+section['compressed_bytes']],limit=section['decoded_bytes'])
            if section.get('warm_reset'):
                pos=0
                while (count:=struct.unpack_from('<H',decoded,pos)[0]):
                    address=struct.unpack_from('<H',decoded,pos+2)[0]; pos+=4
                    if fixed[address-0x4000:address-0x4000+count]!=decoded[pos:pos+count]:
                        raise AssertionError(f'warm reset failed at {address:04x}')
                    pos+=count; ranges_checked+=1
                if pos+2!=len(decoded): raise AssertionError('trailing reset bytes')
            elif section['bank'] in (5,7):
                offset=section['address']&16383
                if bytes(cpu.banks[section['bank']][offset:offset+len(decoded)])!=decoded:
                    raise AssertionError('screen or bank-7 code differs')
        reports.append(dict(from_part=index,to_part=index+1,rom_mocked=True,predecessor_played=False,
            all_mutable_fixed_bytes_poisoned=True,reset_ranges_exact=ranges_checked,
            compact_retained_exact=True,immutable_retained_exact=True,prompt_exact=True,
            wrong_disk_rejected=True,wrong_series_rejected=True,cold_start_refused=True))
    return reports


class WarmTests(unittest.TestCase):
    def test_reset_routine_real_opcode_counts(self):
        section=dict(bank=2,address=0x4000,buffer=0xa6a0,sectors=1,sector=32,warm_reset=True)
        blob,labels=disk.build_bootstrap([section],33,1,warm_set=True,continuation=True)
        for count in (1,257):
            cpu=DiskCPU(blob,b''); data=bytes(i%251 for i in range(count))
            encoded=struct.pack('<HH',count,0x8100)+data+bytes(2)
            cpu.banks[5][:len(encoded)]=encoded;cpu.set_hl(0x4000);cpu.sp=0x5ff0;cpu.push(0x5e00)
            cpu.pc=labels['warm_reset'];until(cpu,0x5e00)
            self.assertEqual(bytes(cpu.banks[2][0x100:0x100+count]),data)
            # Header (39/45), destination 26, LDIR 21*N-5, JP 10.
            self.assertEqual(cpu.tstates,21*count+70+45)

    def test_snapshot_names_128_model_and_preserves_only_real_retained_banks(self):
        data=bytes((i*17)%251 for i in range(49152)); result=make_snapshot(data)
        self.assertEqual(result[:8],b'ZXST\x01\x05\x02\x00')
        pos=8; banks={}
        while pos<len(result):
            tag=result[pos:pos+4]; size=struct.unpack_from('<I',result,pos+4)[0]
            blob=result[pos+8:pos+8+size];pos+=8+size
            if tag==b'RAMP': banks[blob[2]]=blob[3:]
        self.assertEqual(banks[5]+banks[2]+banks[6],data)
        self.assertTrue(all(banks[b]==b'\xa5'*16384 for b in (0,1,3,4,7)))
        with self.assertRaises(ValueError): make_snapshot(bytes(2))


if __name__=='__main__':
    import sys
    if '--volumes' in sys.argv:
        p=argparse.ArgumentParser();p.add_argument('--volumes',type=Path,required=True)
        p.add_argument('--states',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
        a=p.parse_args()
        with np.load(a.states,allow_pickle=False) as saved: states=saved['states']
        result=verify(a.volumes,states);a.output.write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result),flush=True)
    else: unittest.main()
