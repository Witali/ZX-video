"""Integration control: the new C adapter changes only the supplied model."""
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from dha_common_host import HERE, run, validate
from dha_host_probe import save, sha


class CommonAdapterControl(unittest.TestCase):
    def test_original_model_reproduces_original_CLI_bytes(self):
        experiment=HERE/'evidence/dha-common-host'
        temporary=tempfile.TemporaryDirectory(prefix='dha-common-adapter-',dir=HERE.parents[2]/'.tmp')
        self.addCleanup(temporary.cleanup)
        folder=Path(temporary.name)
        old=HERE/'evidence/dha-host/sea_foam/pilot-first-frame/audio.dhaf'
        original=old.read_bytes();model=original[32:1056]
        self.assertEqual(sha(model),'70582ffa6ec234742248acd008bda13795f5243a884681f496af87bd6609260f')
        (folder/'original-model.bin').write_bytes(model)
        pcm=(experiment/'sea_foam/pilot-pcm16.bin').read_bytes()
        (folder/'source-pcm16.bin').write_bytes(pcm)
        build=json.loads((experiment/'build.json').read_bytes())
        executable=HERE.parents[2]/'.tmp/dha-common-native/dha_common_host.exe'
        self.assertEqual(sha(executable.read_bytes()),build['executable_sha256'])
        result=run(executable,folder/'original-model.bin',folder/'source-pcm16.bin',folder/'native','original-model-control')
        self.assertEqual((folder/'native/audio.dhaf').read_bytes(),original)
        source=np.frombuffer(pcm,'<i2')
        dll=HERE.parents[2]/'.tmp/dha-host-scratch/build/dha_codec.dll'
        _,validation=validate(folder/'native',source,model,dll)
        save(folder/'report.json',dict(passed=True,samples=len(source),
            original_CLI_container_byte_identical=True,old_model_sha256=sha(model),
            source_pcm16_sha256=sha(pcm),container_sha256=sha(original),
            new_C_adapter_run=result,validation=validation,
            control_source_sha256=sha(Path(__file__).read_bytes())))


if __name__=='__main__':unittest.main()
