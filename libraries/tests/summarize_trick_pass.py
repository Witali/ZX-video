"""Authenticate retained evidence and exact defaults; no new playback qualification."""
import argparse
import hashlib
import json
from pathlib import Path

from test_libraries import profiles,ROOT


def read(name):return json.loads((ROOT/name).read_text())


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();defaults=profiles();assert defaults==read('tests/decoder_baseline.json')['profiles']
    lz=read('evidence/long_copy_native.json');stream=read('evidence/long_copy_streaming.json')
    zx=read('evidence/ring_table_native.json');extraction=read('verification.json')
    assert lz['complete'] and zx['complete'] and stream['complete']
    assert lz['summary']['slower_blocks']==lz['summary']['slower_slices']==0
    assert zx['summary']['slower_blocks']==zx['summary']['slower_slices']==0
    for mode in ('direct','call'):
        assert stream[mode]['cases']==42 and stream[mode]['summary']['sectors_exact_once']
        assert stream[mode]['summary']['slower_blocks']==0
    resources=[]
    for row in extraction['upstream_resources']:
        path=ROOT/row['package']/'src'/row['package']/'asm'/row['file']
        digest=hashlib.sha256(path.read_bytes()).hexdigest();assert digest==row['sha256']
        resources.append(dict(row,exact=True))
    audits=[]
    for index in range(2,10):
        name=f'evidence/trick_{index:02}.json';row=read(name)
        assert row['item']==f'{index:02}' and row['complete']
        audits.append(dict(item=row['item'],decision=row['decision'],evidence=name))
    assert lz['baseline']['standalone_raw_region_sectors']==2 and lz['candidate']['standalone_raw_region_sectors']==3
    assert all(row['standalone_raw_sectors_before']==3 and row['standalone_raw_sectors_after']==4 for row in zx['layouts'])
    report=dict(date='2026-10-13',baseline_revision='6168ba14',complete=True,release=False,
        branch='codex/z80-codec-tricks',scope=__doc__,
        default_profiles=len(defaults),default_bytes_addresses_labels_exact=True,
        default_instruction_delta_tstates=0,original_resources=resources,
        lzsa2=dict(evidence='evidence/long_copy_native.json',**lz['summary'],
            code_bytes_added=87,streaming_code_bytes_added=84,escaped_word_forms_unchanged=True,
            regression_record='evidence/long_copy_correction.json',
            standalone_raw_code_sectors=dict(before=2,after=3)),
        streaming=dict(evidence='evidence/long_copy_streaming.json',cases_per_mode=42,
            placements_per_case=6,modes={mode:stream[mode]['summary'] for mode in ('direct','call')}),
        zx0=dict(evidence='evidence/ring_table_native.json',**zx['summary'],page_checks=zx['page_checks'],
            whole_ring_page_tstates=dict(before=108,after=87,delta=-21),
            standalone_raw_code_sectors=dict(before=3,after=4)),audits=audits,
        unit_checks_observed=dict(library_suite=12,existing_toolkit_suite=66,
            additional_aligned_ay_im2_test=1,unique_tests=79,post_correction_direct_header_recheck=3),
        runtime_payload_bytes_changed=0,boot_code_packing_measured=False,
        physical_disk_ula_rom_publication_measured=False,
        commands=[
            'python -m unittest discover -s libraries/tests -v',
            'python libraries/tests/measure_long_copy.py --output libraries/evidence/long_copy_native.json',
            'python libraries/tests/measure_ring_table.py --output libraries/evidence/ring_table_native.json',
            'python libraries/tests/summarize_long_copy_streaming.py --directory .tmp --output libraries/evidence/long_copy_streaming.json',
            'python libraries/tests/summarize_trick_pass.py --output libraries/optimization_verification.json'])
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(complete=True,default_profiles=len(defaults),native_lzsa_cases=lz['summary']['cases'],
        native_banked_zx0_cases=zx['summary']['cases'],audited_items=len(audits)+1)))


if __name__=='__main__':main()
