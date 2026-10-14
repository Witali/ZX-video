"""Optional UI validation and authenticated historical default compatibility."""
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from build_stream_trd import build
from direct_player import build_disk,canonical_pcm_model


REPO=Path(__file__).resolve().parents[3]
SNAPSHOT=Path(__file__).resolve().parent/'evidence/achieved-disk/generated'


class AudioUiBuilder(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (REPO/'.tmp').mkdir(exist_ok=True)

    def test_flag_is_strict_and_false_preserves_canonical_model(self):
        before=canonical_pcm_model()
        self.assertEqual(canonical_pcm_model(dict(before,audio_progress_ui=False)),before)
        self.assertIs(canonical_pcm_model(dict(before,audio_progress_ui=True))['audio_progress_ui'],True)
        for flag in (0,1,None,'true',[],{}):
            with self.subTest(flag=flag),self.assertRaisesRegex(ValueError,'boolean'):
                canonical_pcm_model(dict(before,audio_progress_ui=flag))

    def test_direct_builder_rejects_unimplemented_ui_before_output(self):
        with tempfile.TemporaryDirectory(dir=REPO/'.tmp',prefix='audio-ui-invalid-') as work:
            destination=Path(work)/'not-created'
            with self.assertRaisesRegex(ValueError,'build_stream_trd'):
                build_disk(bytes(256),destination,dict(canonical_pcm_model(),audio_progress_ui=True))
            self.assertFalse(destination.exists())

    def test_short_source_and_compact_layout_are_rejected(self):
        model=json.loads((SNAPSHOT/'player.json').read_text())['model']
        with tempfile.TemporaryDirectory(dir=REPO/'.tmp',prefix='audio-ui-capacity-') as work:
            with self.assertRaisesRegex(ValueError,'two bar cells'):
                build(bytes(32768),Path(work)/'short',bytes(6912),dict(model,audio_progress_ui=True))
            with self.assertRaisesRegex(ValueError,'noncompact'):
                build(bytes(32768),Path(work)/'compact',bytes(6912),
                      dict(model,audio_progress_ui=True,compact_stream_loader=True))

    def test_complete_song_default_and_false_equal_authenticated_snapshot(self):
        before=json.loads((SNAPSHOT/'player.json').read_text())
        disk=(SNAPSHOT/'audio.trd').read_bytes()
        self.assertEqual(hashlib.sha256(disk).hexdigest(),
                         'ccab87249b9ce148f3b84cc317d64078a05f51c1e7d5ca7aa9f14958e8fc9074')
        packed=gzip.decompress((SNAPSHOT/'soundtrack.ima.gz').read_bytes())
        cover=(SNAPSHOT/'cover.scr').read_bytes()
        with tempfile.TemporaryDirectory(dir=REPO/'.tmp',prefix='audio-ui-default-') as work:
            for flag in (None,False):
                model=dict(before['model'])
                if flag is not None:model['audio_progress_ui']=flag
                generated,meta=build(packed,Path(work)/str(flag),cover,model)
                self.assertEqual(generated,disk)
                self.assertEqual(meta,before)


if __name__=='__main__':unittest.main()
