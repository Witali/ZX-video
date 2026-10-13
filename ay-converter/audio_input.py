"""Explicit six-channel mono reduction, shared by standalone and movie input."""
from pathlib import Path
import json
import shutil
import subprocess

# Keep the centre/dialogue prominent; surround effects remain present at a
# lower weight. LFE is omitted from this narrow three-voice mono arrangement.
PAN_51='pan=mono|c0=0.23*c0+0.23*c1+0.40*c2+0.07*c4+0.07*c5'


def mono_filter(channels,layout=''):
    return PAN_51 if channels==6 and layout in ('5.1','5.1(side)','') else None


def probe_filter(source,ffmpeg):
    executable=Path(str(ffmpeg))
    sibling=executable.with_name('ffprobe.exe' if executable.suffix.lower()=='.exe' else 'ffprobe')
    probe=str(sibling) if sibling.exists() else shutil.which('ffprobe')
    if not probe:return None,dict(method='FFmpeg standard mono downmix',reason='ffprobe unavailable')
    result=subprocess.run([probe,'-v','error','-select_streams','a:0','-show_entries','stream=channels,channel_layout',
        '-of','json',str(source)],capture_output=True,check=True)
    stream=json.loads(result.stdout)['streams'][0]
    selected=mono_filter(stream.get('channels'),stream.get('channel_layout',''))
    return selected,dict(method='centre-priority 5.1 mono' if selected else 'FFmpeg standard mono downmix',
        channels=stream.get('channels'),layout=stream.get('channel_layout'),filter=selected,
        coefficients=dict(FL=.23,FR=.23,FC=.40,LFE=0,surround_left=.07,surround_right=.07) if selected else None)
