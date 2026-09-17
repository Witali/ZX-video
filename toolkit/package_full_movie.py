"""Package a fully verified multi-disk movie, with an explicit playback order."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import zipfile

from build_full_movie import digest
from summarize_ay_delivery import summarize
from verify_ay_trace import verify_build


def timecode(seconds):
    return f'{int(seconds)//60:02d}:{seconds%60:06.3f}'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('build',type=Path)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--report',type=Path,required=True)
    p.add_argument('--ffmpeg',type=Path,required=True);args=p.parse_args()
    root=args.build;disks=root/'disks';comparison=root/'comparison'
    manifest=json.loads((root/'manifest.json').read_text())
    for stage in ('audio','video','disks'):
        if not manifest['stages'].get(stage):raise ValueError(f'missing stage: {stage}')
        for name,expected in manifest['stages'][stage].items():
            if digest(root/name)!=expected:raise ValueError(f'changed stage artifact: {name}')
    meta=json.loads((disks/'build_metadata.json').read_text())
    timing=json.loads((disks/'fuse_timing.json').read_text())
    cpu=json.loads((disks/'cpu_validation.json').read_text())
    quality=json.loads((comparison/'comparison.json').read_text())
    settings=manifest['settings'];count=settings['frames'];first=0
    if len(timing)!=len(meta['volumes']):raise ValueError('missing disk timing')
    for volume,trace in zip(meta['volumes'],timing):
        if trace.get('trd_sha256')!=digest(disks/volume['trd_name']):
            raise ValueError('Fuse timing belongs to another disk image')
    for volume in meta['volumes']:
        if volume['frame_start']!=first or volume['frames']!=volume['frame_end']-first:
            raise ValueError('gap or overlap between disks')
        first=volume['frame_end']
    if first!=count or meta['frames']!=count or cpu['frames']!=count:
        raise ValueError('movie is incomplete')
    if any(v['underflows'] for v in cpu['volumes']):raise ValueError('disk underrun')
    if sum(v['verified_audio_ticks'] for v in cpu['volumes'])!=count*6:
        raise ValueError('CPU audio verification incomplete')
    audio=verify_build(meta,timing,(root/'audio/50Hz/raw.bin').read_bytes())
    if quality['verified_audio']!=audio:raise ValueError('quality comparison belongs to another trace')
    delivery=summarize(meta,timing)
    if delivery['intervals_over_125ms']:raise ValueError('video timing exceeds 125 ms')
    if not quality['required_metrics_pass']:raise ValueError('audio metrics below saved thresholds')
    out=args.output;out.mkdir(parents=True,exist_ok=True)
    parts=[]
    for volume in meta['volumes']:
        name=volume['trd_name'];shutil.copyfile(disks/name,out/name)
        parts.append(dict(file=name,sha256=digest(out/name),frames=volume['frames'],
            frame_start=volume['frame_start'],frame_end=volume['frame_end'],
            source_start_seconds=volume['frame_start']/meta['frame_rate'],
            source_end_seconds=volume['frame_end']/meta['frame_rate']))
    report=dict(source=settings,disk_settings=manifest['disk_settings'],parts=parts,player_sha256=digest(disks/'PLAYER.C.bin'),
        verified_frames=cpu['frames'],verified_audio=audio,delivery=delivery,
        cpu={k:v for k,v in cpu.items() if k!='volumes'},
        audio_metrics=quality['metrics'],quality_model=quality['model'],
        evidence_sha256={name:digest(disks/name) for name in ('build_metadata.json','fuse_timing.json','cpu_validation.json')},
        disk_change_pause=True,physical_drive_verified=False)
    text=json.dumps(report,indent=2)+'\n'
    args.report.write_text(text,encoding='utf-8');(out/'measurements.json').write_text(text,encoding='utf-8')
    rows=['| Диск | Исходный интервал | Кадров |','|---|---|---:|']
    rows += [f'| {i+1}: `{part["file"]}` | {timecode(part["source_start_seconds"])}–{timecode(part["source_end_seconds"])} | {part["frames"]} |' for i,part in enumerate(parts)]
    readme=f'''# Big Buck Bunny целиком — ZX Spectrum 128

Исходник: {settings['source_duration_seconds']:.6f} с; сборка: {settings['encoded_duration_seconds']:.2f} с.
Все {count} кадров и {count*6} состояний AY проверены. Частота видео 25/3 кадра/с,
звук — 50 Гц от IM2, только изменения регистров, с шумовым каналом.

## Запуск

Spectrum 128 + Beta128, TR-DOS 5.03 (проверено в Fuse 1.9.0).
Вставьте диск 1 в привод A и загрузите BASIC-файл `boot` через TR-DOS.
Когда часть закончится, вставьте следующий диск и снова загрузите `boot`.
Каждая часть самостоятельна: между дисками есть пауза на смену и загрузку.
Автоматического бесшовного перехода нет. Последний диск содержит окончание и титры.

Комплект содержит {len(parts)} дискет. Насыщенные сцены разбиты на короткие части,
чтобы сохранить запас буфера и непрерывный звук внутри каждой части.
Объём свободного места на дискете сам по себе не определяет допустимую длину:
проверка учитывает скорость чтения и распаковки. Параметры сборки и причины
такого разбиения описаны в репозитории: toolkit/FULL_MOVIE_BUILD_ru.md.

{chr(10).join(rows)}

## Проверки

Максимальный интервал видео в Fuse: {max(v['maximum_ms'] for v in delivery['volumes']):.6f} мс.
Ни одного интервала длиннее 125 мс; недогрузок нет. Это проверка модели эмулятора;
физический дисковод не измерялся. SHA-256 дисков и показатели аудио — в measurements.json.
Проценты chroma/динамики являются техническими метриками, не процентом сходства на слух.

Отдельный preview.mp4 (вне ZIP) — приближённый синтез AY по времени Fuse, без пауз смены дискет;
это не запись звукового выхода эмулятора.
'''
    (out/'README.md').write_text(readme,encoding='utf-8')
    subprocess.run([str(args.ffmpeg.resolve()),'-v','error','-y','-i',str(root/'source/preview.mp4'),
        '-i',str(comparison/'measured_timing.wav'),'-map','0:v:0','-map','1:a:0',
        '-vf','setpts=N*3/(25*TB)','-r','25/3','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k',
        '-movflags','+faststart','-shortest',str(out/'preview.mp4')],check=True)
    archive=out.with_suffix('.zip')
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name in [*(p['file'] for p in parts),'README.md','measurements.json']:
            z.write(out/name,name)
    print(json.dumps(dict(directory=str(out.resolve()),archive=str(archive.resolve()),
        disks=len(parts),frames=count,ticks=count*6),indent=2))


if __name__=='__main__':main()
