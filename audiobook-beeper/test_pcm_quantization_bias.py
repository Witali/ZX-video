"""Prove centered hardware buckets, untouched defaults and native timing."""
import gzip
import json
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import numpy as np

from build_stream_trd import build
from direct_player import canonical_pcm_model, layout, pcm_high_lookup
from general import models
from ima_beam import encode
from convert_audio import pcm_wav
from verify_pcm import save
from verify_direct import reference
from verify_stream_trd import cold_load, native_check


HERE = Path(__file__).resolve().parent
EXPORT_ROOT = None
PROOF = {}


def prior_producers(root):
    """Run the actual pre-option builder/layout and assembler templates."""
    folder=root/'prior-producer'
    folder.mkdir()
    for name in ('build_stream_trd.py','direct_player.py','stream-player.asm',
                 'stream-worker.asm','stream-progress.asm','ram-cache.asm'):
        result=subprocess.run(['git','show','7938cbe6:audiobook-beeper/'+name],
                              cwd=HERE.parent,capture_output=True,check=True)
        (folder/name).write_bytes(result.stdout)
    namespaces=[]
    for name in ('direct_player.py','build_stream_trd.py'):
        namespace=dict(__file__=str(folder/name),__name__='_prior_'+name[:-3])
        exec(compile((folder/name).read_bytes(),str(folder/name),'exec'),namespace)
        namespaces.append(namespace)
    # The archived builder must use the archived layout, rather than its
    # normally imported current module. Decoder/PDM helpers are untouched.
    namespaces[1]['layout']=namespaces[0]['layout']
    return folder,namespaces[1]['build']


class PCMQuantizationBiasTests(unittest.TestCase):
    def setUp(self):
        scratch = HERE.parent / '.tmp' / 'pcm-quantization-bias-tests'
        scratch.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=scratch)
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def model(self, bias=None):
        model = dict(dict(models())['duration_zero'], compact_stream_loader=True)
        if bias is not None:
            model['pcm_quantization_bias'] = bias
        return model

    def test_all65536_signed_samples_and_endpoint_clamp(self):
        # Artificial distinct page-high values expose every selected bin. The
        # expected result uses full signed PCM16, independently of IXH logic.
        pages = [level << 8 for level in range(64)]
        signed = np.arange(-32768, 32768, dtype=np.int32)
        high = ((signed + 32768) >> 8).astype(np.uint8)
        for bias in (0, 512):
            lookup = np.frombuffer(pcm_high_lookup(pages, self.model(bias)), 'u1')
            expected = np.minimum(63, (signed + 32768 + bias) // 1024)
            np.testing.assert_array_equal(lookup[high], expected)
            self.assertEqual(len(lookup), 256)
            self.assertEqual(int(lookup[-1]), 63)
        centered = np.frombuffer(pcm_high_lookup(pages, self.model(512)), 'u1')
        self.assertTrue(np.all(centered[((np.arange(-512, 512) + 32768) >> 8)] == 32))
        self.assertEqual(int(centered[254]), 63)
        PROOF['mapping']=dict(signed_values_verified=65536,hardware_entries_verified=256,
                              zero_bucket_signed_range=[-512,511],upper_bin=63,
                              centered_lookup_bins_sha256=hashlib.sha256(centered.tobytes()).hexdigest())
        if EXPORT_ROOT is not None:
            (EXPORT_ROOT/'centered-lookup-bins.bin').write_bytes(centered.tobytes())

    def test_default_golden_disk_and_explicit_zero_metadata_are_exact(self):
        inputs = HERE / 'experiments/song-snr/evidence/study/inputs/song'
        original = (inputs / 'audio.trd').read_bytes()
        previous = json.loads((inputs / 'player.json').read_bytes())
        packed = gzip.decompress((inputs / 'soundtrack.ima.gz').read_bytes())
        entry = next(item for item in previous['directory'] if item['name'] == 'COVER')
        at = (entry['track'] * 16 + entry['sector']) * 256
        cover = original[at:at + 6912]
        folder,previous_build=prior_producers(self.root)
        prior_disk,prior_meta=previous_build(packed,self.root/'prior-result',cover,previous['model'])
        self.assertEqual(prior_disk,original)
        disk, meta = build(packed, self.root / 'default', cover, previous['model'])
        self.assertEqual(disk, original)
        self.assertEqual(meta, prior_meta)
        disk_zero, meta_zero = build(packed, self.root / 'explicit-zero', cover,
                                     dict(previous['model'], pcm_quantization_bias=0))
        self.assertEqual(disk_zero, original)
        self.assertEqual(meta_zero, prior_meta)
        self.assertNotIn('pcm_quantization_bias', meta_zero['model'])
        self.assertNotIn('pcm_quantization', meta_zero)
        PROOF['default_compatibility']=dict(prior_version='7938cbe6',old_disk_byte_exact=True,
            prior_version_metadata_exact=True,explicit_zero_disk_and_metadata_exact=True,
            trd_sha256=hashlib.sha256(original).hexdigest(),
            metadata_sha256=hashlib.sha256(json.dumps(prior_meta,sort_keys=True).encode()).hexdigest(),
            historical_metadata_scope='The older study archive predates worker metadata;7938 source supplies the correct pre-option metadata oracle')
        if EXPORT_ROOT is not None:
            shutil.copytree(folder,EXPORT_ROOT/'prior-producer')
            save(EXPORT_ROOT/'prior-player.json',prior_meta)
            save(EXPORT_ROOT/'default-player.json',meta)
            save(EXPORT_ROOT/'explicit-zero-player.json',meta_zero)

    def test_invalid_flags_and_unsupported_models_fail_before_build(self):
        packed = bytes(256)
        for value in (True, False, 0.0, 512.0, '512', None, -512, 256, 1024):
            model = dict(self.model(), pcm_quantization_bias=value)
            with self.subTest(value=value):
                for operation in (lambda: canonical_pcm_model(model),
                                  lambda: layout(packed, model, resident_limit=16384),
                                  lambda: build(packed, self.root / 'invalid', bytes(6912), model),
                                  lambda: reference(packed, cycles=1, model=model)):
                    with self.assertRaises(ValueError):
                        operation()
        for extra in ({'pcm_bins': 128}, {'family': 'sigma_delta2'}):
            model = dict(self.model(512), **extra)
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                build(packed, self.root / 'unsupported', bytes(6912), model)
            with self.assertRaises(ValueError):
                reference(packed, cycles=1, model=model)
        self.assertFalse((self.root / 'invalid').exists())
        self.assertFalse((self.root / 'unsupported').exists())
        PROOF['guards']=dict(invalid_bias_values_rejected=[dict(type=type(value).__name__,value=repr(value))
            for value in (True,False,0.0,512.0,'512',None,-512,256,1024)],
            unsupported_models_rejected=['pcm_bins128','sigma_delta2'],
            validation_before_output_creation=True)

    def test_centered_lookup_only_changes_data_and_all_native_profiles_pass(self):
        source = np.full(4096, 128, 'u1')
        source[:3968] = np.rint(128 + 96 * np.sin(2 * np.pi * 997 * np.arange(3968) / 8000)).astype('u1')
        source[256:384] = 255
        source[768:896] = 0
        packed = encode(source, width=32, block_samples=64)
        uncentered = self.model()
        centered = self.model(512)
        before, before_meta = build(packed, self.root / 'uncentered', bytes(6912), uncentered)
        after, after_meta = build(packed, self.root / 'centered', bytes(6912), centered)
        pointer = after_meta['player_labels']['pcm_high']
        self.assertEqual(pointer, before_meta['player_labels']['pcm_high'])
        player = next(item for item in after_meta['directory'] if item['name'] == 'PLAYER')
        disk_at = (player['track'] * 16 + player['sector']) * 256 + pointer - 0x8000
        changed = np.flatnonzero(np.frombuffer(before, 'u1') != np.frombuffer(after, 'u1'))
        expected_offsets = [disk_at + high for high in range(256) if high % 4 >= 2 and high < 254]
        self.assertEqual(changed.tolist(), expected_offsets)
        self.assertEqual(len(changed), 126)
        self.assertEqual(after_meta['pcm_quantization']['lookup_native_tstate_delta'], 0)
        self.assertFalse(after_meta['pcm_quantization']['live_instruction_changes'])
        old_pcm, old_indices, old_levels, old_bits = reference(packed, cycles=1, model=uncentered)
        pcm, indices, levels, bits = reference(packed, cycles=1, model=centered)
        np.testing.assert_array_equal(pcm, old_pcm)
        np.testing.assert_array_equal(indices, old_indices)
        np.testing.assert_array_equal(levels, old_levels)
        self.assertTrue(np.any(bits != old_bits))
        native=[]
        for profile in ('128', 'scorpion', 'pentagon512', 'pentagon1024'):
            with self.subTest(profile=profile):
                original_report = native_check(before, before_meta, packed, profile,out=self.root/'uncentered'/('native-'+profile+'.json'))
                report = native_check(after, after_meta, packed, profile,out=self.root/'centered'/('native-'+profile+'.json'))
                self.assertTrue(report['complete'])
                self.assertTrue(report['every_bit_predictor_index_exact'])
                self.assertTrue(report['every_continuous_native_hold_exact'])
                self.assertTrue(report['memory_guards_passed'])
                self.assertTrue(report['all256_hardware_lookup_entries_verified'])
                self.assertEqual(report['lookup_native_tstate_delta'], 0)
                self.assertEqual(report['ordinary_tstates'], 449 if profile.startswith('pentagon') else 423)
                self.assertEqual(report['ordinary_tstates'], original_report['ordinary_tstates'])
                self.assertEqual(report['interval_extras'], original_report['interval_extras'])
                self.assertEqual(report['maximum_native_hold_tstates'], original_report['maximum_native_hold_tstates'])
                native.append(dict(profile=profile,uncentered=original_report,centered=report))
        corrupt = bytearray(after)
        corrupt[disk_at] ^= 1
        with self.assertRaisesRegex(AssertionError, 'quantizer lookup'):
            cold_load(corrupt, after_meta, 'pentagon1024')
        PROOF['short_native']=dict(source_samples=len(source),source_sha256=hashlib.sha256(source.tobytes()).hexdigest(),
            packed_sha256=hashlib.sha256(packed).hexdigest(),model=centered,native=native,
            changed_disk_bytes=len(changed),only_hardware_lookup_data_changed=True,
            ordinary_native_tstates={'128':423,'scorpion':423,'pentagon512':449,'pentagon1024':449},
            native_tstate_delta=0,page_extra_tstates=14,bank_extra_tstates={'128':243,'scorpion':267,'pentagon512':243,'pentagon1024':243},
            actual_Fuse_or_hardware_timing_claim=False,
            ula_scope='Lookup selection changes addresses;128/Scorpion ULA waits can depend on source data and are not covered by native CPU counts')
        if EXPORT_ROOT is not None:
            for name,disk in (('uncentered',before),('centered',after)):
                (self.root/name/'audio.trd').write_bytes(disk)
                (self.root/name/'soundtrack.ima.gz').write_bytes(gzip.compress(packed,mtime=0))
                pcm_wav(self.root/name/'source-preview.wav',source)
                shutil.copytree(self.root/name,EXPORT_ROOT/name)


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser(add_help=False)
    parser.add_argument('--evidence',type=Path)
    args,remaining=parser.parse_known_args()
    if args.evidence is not None:
        EXPORT_ROOT=args.evidence.resolve()
        if EXPORT_ROOT.exists() and any(EXPORT_ROOT.iterdir()):
            parser.error('evidence output must be empty')
        EXPORT_ROOT.mkdir(parents=True,exist_ok=True)
    result=unittest.main(argv=[sys.argv[0],*remaining],exit=False).result
    if result.wasSuccessful() and EXPORT_ROOT is not None:
        producers={name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in
                   ('test_pcm_quantization_bias.py','build_stream_trd.py','direct_player.py','verify_direct.py','verify_stream_trd.py')}
        save(EXPORT_ROOT/'report.json',dict(complete=True,date='2026-10-14',proof=PROOF,
            producer_sha256=producers,scope='Short complete native CPU proof plus full quantizer arithmetic and old default compatibility; no audio quality or actual ULA timing claim',
            reproducer='python audiobook-beeper/test_pcm_quantization_bias.py --evidence NEW_EMPTY_FOLDER -v'))
    raise SystemExit(0 if result.wasSuccessful() else 1)
