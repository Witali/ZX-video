"""Verify compact IMA3 tables, saved-clock equivalence and full RAM capacity.

Run with --input pointing at a completed build_ima3_direct output. The
baseline must reproduce its disk hash before its old timing can be reused.
--fuse additionally verifies two entire cold loops and their unchanged
relative output timestamps. No encoder or psychoacoustic metric is changed.
"""
import argparse
from functools import partial
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import struct

import numpy as np

from ima_codec import INDEX, STEPS
from ima3_direct_player import build_disk
from verify_direct import reference, intervals
from verify_packet import native_check, fuse_check
from verify_pcm import extract_player, save


def check_tables(disk, meta):
    """Check all 712 transitions, including states unused by the recording."""
    blob=extract_player(disk)
    labels=meta['player_labels']; rows=meta['decoder_rows']
    assert len(rows)==len(set(rows))==89
    for index,address in enumerate(rows):
        assert address%32==0 and 0x8000<=address<0x8000+meta['resident_reserve']
        step=int(STEPS[index])
        for code in range(0,16,2):
            delta=(step>>3)+(step if code&4 else 0)+(step>>1 if code&2 else 0)
            if code&8:delta=-delta
            expected=(delta&65535,rows[max(0,min(88,index+int(INDEX[code&7])))])
            assert struct.unpack_from('<HH',blob,address-0x8000+code*2)==expected
        if address<labels['first_base']:
            assert labels['startup_end']<=address and address+32<=labels['first_base']
        elif address<labels['phase_base']:
            assert max(meta['second_addresses'])+20<=address and address+32<=labels['phase_base']
        else:
            assert labels['pcm_high']+256<=address
    for section in meta['sections']:
        if section['bank']==2:
            assert section['address']-0x4000>=0x8000+meta['resident_reserve']
    return dict(exact_decoder_transitions=89*8,all_rows_retained=True,
                decoder_addresses_aligned=True,no_code_or_audio_overlap=True)


def verify_capacity_fuse(out, original, fuse):
    """Exercise disk loading into the reclaimed bank-2 area as well as CPU use."""
    meta=json.loads((out/'capacity/player.json').read_bytes())
    full=original+bytes(meta['resident_audio_bytes']//3*4-len(original))
    disk,reproduced=build_disk(full,out/'capacity/assembly',model=meta['model'])
    assert reproduced==meta,'capacity build changed'
    (out/'capacity/audiobook-preview.trd').write_bytes(disk)
    result=fuse_check(fuse,out/'capacity',meta,full,False,
                      partial(reference,model=meta['model']),intervals)
    result['scope']='Complete cold boot and two loops at new full capacity; recording plus synthetic silence. No quality claim for this uncalibrated capacity fixture.'
    save(out/'capacity/fuse.json',result)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--fuse',type=Path)
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    old=json.loads((a.input/'player.json').read_bytes())
    packed=gzip.decompress((a.input/'soundtrack.ima.gz').read_bytes())
    kwargs=dict(model=old['model'],idle_pairs=old['loop_idle_pairs'],idle_pad=old['loop_idle_pad_tstates'])
    baseline,bmeta=build_disk(packed,out/'baseline-assembly',compact_tables=False,**kwargs)
    baseline_sha=hashlib.sha256(baseline).hexdigest()
    # The original root image is not needed; saved assembly hashes and every
    # original file in the original directory identify its complete TRD.
    assert bmeta['binary_sha256']==old['binary_sha256'],'baseline player identity changed'
    assert bmeta['packed_sha256']==old['packed_sha256'],'baseline audio identity changed'
    old_disk=a.input/'audiobook-preview.trd'
    if old_disk.exists():assert baseline==old_disk.read_bytes(),'baseline disk identity changed'
    disk,meta=build_disk(packed,out/'assembly',**kwargs)
    save(out/'player.json',meta);(out/'audiobook-preview.trd').write_bytes(disk)
    for name in ('soundtrack.ima.gz','soundtrack.ima3.gz','source-preview.wav'):
        shutil.copy2(a.input/name,out/name)
    table=check_tables(disk,meta)
    before=extract_player(baseline);after=extract_player(disk)
    lo=meta['player_labels']['first_base']-0x8000
    hi=max(meta['second_addresses'])+20-0x8000
    assert before[lo:hi]==after[lo:hi],'pulse instruction bytes changed'
    lo=meta['phase_base']-0x8000;hi=meta['player_labels']['pcm_high']-0x8000
    assert before[lo:hi]==after[lo:hi],'extraction instruction bytes changed'
    assert np.array_equal(intervals(bmeta),intervals(meta))
    ref=partial(reference,model=meta['model'],idle_pairs=meta['loop_idle_pairs'])
    native=native_check(disk,meta,packed,ref,intervals);save(out/'native.json',native)
    report=dict(baseline_disk_sha256=baseline_sha,candidate_disk_sha256=hashlib.sha256(disk).hexdigest(),
                baseline_player_identical=True,table_checks=table,memory=meta['memory'],
                pulse_and_extraction_instruction_bytes_identical=True,ordinary_tstates_before=bmeta['ordinary_tstates'],
                ordinary_tstates_after=meta['ordinary_tstates'],ordinary_delta_tstates=0,
                page_extra_tstates=14,bank_extra_tstates=140,complete_native=True,
                actual_fuse_verified=False,physical_hardware_tested=False)
    save(out/'comparison.json',report)
    print(json.dumps(dict(stage='native-reference',**report)),flush=True)
    capacity=meta['memory']['maximum_ima3_bytes']
    full=packed+bytes(capacity//3*4-len(packed))
    for name,pairs,pad in [('capacity',0,0),('maximum-filler',1530,260),('large-filler-fallback',1,300)]:
        # Oversized fillers intentionally avoid the startup gap. This case
        # checks the fallback's own capacity, rather than overfilling it.
        material=full if name!='large-filler-fallback' else packed
        d,m=build_disk(material,out/name/'assembly',model=old['model'],idle_pairs=pairs,idle_pad=pad)
        save(out/name/'player.json',m);check_tables(d,m)
        if name=='capacity':
            r=native_check(d,m,material,partial(reference,model=m['model']),intervals)
            r['scope']+='; original recording plus synthetic silence to exercise new full capacity'
            save(out/name/'native.json',r)
            report['full_capacity_native']=r
        print(json.dumps(dict(stage=name,reserve=m['resident_reserve'],startup_end=m['player_labels']['startup_end'])),flush=True)
    if a.fuse:
        result=fuse_check(a.fuse,out,meta,packed,False,ref,intervals);save(out/'fuse.json',result)
        new_times=np.frombuffer(gzip.decompress((out/'output-times.u32.gz').read_bytes()),'<u4').astype(np.int64)
        old_times=np.frombuffer(gzip.decompress((a.input/'output-times.u32.gz').read_bytes()),'<u4').astype(np.int64)
        assert len(new_times)==len(old_times)
        assert np.array_equal(new_times-new_times[0],old_times-old_times[0]),'actual output timing changed'
        report.update(actual_fuse_verified=True,relative_output_timestamps_identical=True,
                      timestamps_compared=len(new_times),fuse=result)
        if (a.input/'quality.json').exists():
            report['reused_quality']=json.loads((a.input/'quality.json').read_bytes())
            report['quality_reuse_reason']='Identical PCM source, compressed codes, every output bit and every relative Fuse timestamp.'
        # Finish the reference comparison before the separate capacity check.
        save(out/'comparison.json',report)
        report['full_capacity_fuse']=verify_capacity_fuse(out,packed,a.fuse)
    save(out/'comparison.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('fuse','full_capacity_native')}),flush=True)


if __name__=='__main__':
    main()
