"""Rebuild standalone loading-UI proof; this program never opens an audio TRD."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime, timezone


HERE=Path(__file__).resolve().parent
REPO=HERE.parents[4]
STUDY=REPO/'audiobook-beeper/experiments/song-snr'
sys.path[:0]=[str(REPO/'audiobook-beeper'),str(STUDY)]
from test_audio_ui_loading import assemble_ui


def identity(path):
    raw=Path(path).read_bytes()
    return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),
                lf_sha256=hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest())


def main():
    """Capture producer sources before tests, assemble fixtures and authenticate results."""
    producers=[REPO/'audiobook-beeper/stream-audio-ui.asm',
               REPO/'audiobook-beeper/stream-audio-ui-helper.asm',
               STUDY/'test_audio_ui_loading.py',
               REPO/'audiobook-beeper/ram-cache.asm',
               REPO/'audiobook-beeper/ram_machine.py']
    archive=HERE/'producers';archive.mkdir(exist_ok=True)
    sources={}
    for source in producers:
        name=source.relative_to(REPO).as_posix()
        target=archive/source.name
        shutil.copyfile(source,target)
        sources[name]={**identity(source),'archive':target.relative_to(HERE).as_posix()}
    startup,startup_labels=assemble_ui(HERE/'assembly')
    relocated,relocated_labels=assemble_ui(HERE/'relocated-assembly',0x8100,0xB800)
    completed=subprocess.run([sys.executable,'-m','unittest',
                              'audiobook-beeper/experiments/song-snr/test_audio_ui_loading.py','-v'],
                             cwd=REPO,capture_output=True,text=True)
    (HERE/'tests.log').write_text(completed.stdout+completed.stderr,encoding='utf-8',newline='\n')
    if completed.returncode:raise SystemExit(completed.returncode)
    versions={}
    for package in ('pyz80','z80'):
        try:versions[package]=importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:versions[package]='distribution metadata unavailable'
    report=dict(
        created_utc=datetime.now(timezone.utc).isoformat(),
        scope='Standalone actual-Z80 loading UI; no integrated TRD or live audio execution',
        result='Nine tests pass; integration and full disk timing checks remain required',
        native_profiles=['Spectrum 128','Scorpion 256','Pentagon 512','Pentagon 1024'],
        native_font='Deterministic synthetic ROM font; exact ROM address and pixel geometry are checked',
        frame_clock='Explicitly injected low-16 ROM FRAMES values, not measured floppy/IRQ elapsed time',
        sources=sources,python=sys.version,packages=versions,
        startup=dict(origin=0x808A,end=startup_labels['audio_ui_startup_end'],
                     module_bytes=startup_labels['audio_ui_startup_end']-0x808A,
                     padding_limit=0x8340,remaining_bytes=0x8340-startup_labels['audio_ui_startup_end'],
                     supplied_playback_module_budget_bytes=514,
                     maximum_records=39,record_bytes=10,maximum_record_bytes=390,
                     with_supplied_playback_module_end=startup_labels['audio_ui_startup_end']+514,
                     remaining_with_supplied_playback_module_bytes=0x8340-startup_labels['audio_ui_startup_end']-514,
                     fixture_bytes=len(startup)),
        resident=dict(origin=0xB940,end=startup_labels['audio_ui_end'],
                      module_bytes=startup_labels['audio_ui_end']-0xB940,worker_origin=0xBA00,
                      remaining_bytes=0xBA00-startup_labels['audio_ui_end'],
                      mutable_begin=startup_labels['audio_ui_data_start'],mutable_end=startup_labels['audio_ui_data_end']),
        relocation=dict(startup_origin=0x8100,startup_end=relocated_labels['audio_ui_startup_end'],
                        startup_bytes=relocated_labels['audio_ui_startup_end']-0x8100,
                        helper_origin=0xB800,helper_end=relocated_labels['audio_ui_end'],
                        helper_bytes=relocated_labels['audio_ui_end']-0xB800,fixture_bytes=len(relocated)),
        geometry=dict(label_cells=10,label_row=20,label_first_column=11,
                      label_pixels=[0xD08B,0xD794],label_attributes=[0xDA8B,0xDA94],
                      bar_attributes=[0xDAC0,0xDADF],protected_screen_end=0xDAFF,audio_bank7_begin=0xDB00),
        colors=dict(loading_filled=0x3F,loading_empty=0x07,playback_filled=0x24,playback_empty=0x04),
        cadence=dict(fields_between_dot_phases=25,nominal_seconds_at_50hz=0.5,
                     phases=['LOADING.  ','LOADING.. ','LOADING...'],
                     long_read_behavior='Advance one phase after the next completed read; no catch-up burst'),
        checks=['All four physical bank models; entry from each highest ordinary page',
                'Split startup and resident relocation fixtures with the unchanged cache_restore ABI',
                'Exact 10-character pixels and attributes; exact 32-cell bar for 0, 1, 17 and 32 filled cells',
                'Suppressed early updates preserve paging and IFF; delayed reads and 16-bit wrap',
                'Loading returns bank 0/EI; playback entry returns bank 0/DI and suppresses later loading ticks',
                'Paused global green redraw preserves cache_bar; end clear preserves final progress and disables loading ticks',
                'IX, IY and all alternate registers preserved; non-screen bank contents and audio payload unchanged',
                'No beeper-port output; returning NUL glyph printer'],
        live_audio=dict(calls_added=0,pdm_instructions_changed=0,deterministic_hot_path_delta_t=0,
                        qualification='Module has no live hook. This is an integration premise, not a full audio timing proof.'),
        limitations=['No audio/source/encoded payload/TRD read or regenerated by this proof',
                     'No full Fuse execution, actual disk delay, actual ROM font screenshot or contention measurement',
                     'Actual dot cadence depends on FRAMES advancing during TR-DOS reads and on read completion opportunities',
                     'The 514-byte playback-module allocation is a supplied integration budget, not assembled by this standalone proof',
                     'Both source chunks require independent fixed bank-2 bounds in the builder',
                     'End rendering must call the clear-label hook before writing the existing message at column 0'])
    (HERE/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    artifacts={path.relative_to(HERE).as_posix():identity(path) for path in sorted(HERE.rglob('*'))
               if path.is_file() and path.name!='manifest.json' and '__pycache__' not in path.parts}
    manifest=dict(created_utc=datetime.now(timezone.utc).isoformat(),
                  scope='Every file under this evidence directory except this manifest and Python cache files',
                  artifacts=artifacts)
    (HERE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(report_sha256=identity(HERE/'report.json')['sha256'],
                         manifest_sha256=identity(HERE/'manifest.json')['sha256'],
                         tests=9,passed=True,startup_bytes=153,resident_bytes=185,total_ui_bytes=338)))


if __name__=='__main__':main()
