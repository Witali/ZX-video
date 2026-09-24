# ZX-video

Конвертер видео в дискеты TRD для **ZX Spectrum 128 + Beta Disk**.
Входной формат определяет FFmpeg: MP4, MKV, AVI, MOV и другие поддерживаемые
им форматы. Исходник целиком, без привязки к мультфильму или удаления титров.

## Запуск

Нужны Python 3.11+, FFmpeg/ffprobe и компрессор ZX0 v2 в `PATH`.

```powershell
python -m pip install -r requirements.txt
python toolkit/convert_video.py "C:/Video/example.mp4" --output "build/example"
```

Папка результата должна быть новой или пустой. Конвертер создаёт
`ZX-video_part01.trd`, `ZX-video_part02.trd` и столько частей, сколько требуется.
Пути к инструментам можно передать через `--ffmpeg`, `--ffprobe`, `--zx0`.

Сохраняются пропорции изображения, разрешение плеера 256×192 с активной
областью 256×144, целевая частота 25/3 кадра/с и синтез AY с шагом 50 Гц.
Есть шумовой канал, прогресс текущей дискеты и автоматическое продолжение
после вставки следующей. Без аудиодорожки создаётся тишина.

По умолчанию проверяются все кадры и такты Z80 при идеальной подаче данных.
**Плавность с реальным чтением диска проверяется отдельно в Fuse**:

```powershell
python toolkit/convert_video.py "C:/Video/example.mp4" --output "build/example-tested" --disk-profile trdos503 --trdos-rom "C:/Program Files (x86)/Fuse/roms/trdos.rom" --verify fuse --fuse "C:/Program Files (x86)/Fuse/fuse.exe"
```

Сложное видео может не выдержать 8⅓ кадра/с. Отчёт `timing.json` показывает
каждое опоздание и задержки диска; успешная сборка сама по себе не подтверждает
плавность. Синтез AY приближает исходный звук, точность 95% не заявлена.

[Параметры, формат отчётов и проверка](toolkit/GENERIC_CONVERTER_ru.md) ·
[H.263 и простые блочные кодеки](toolkit/LIGHT_VIDEO_CODECS_ru.md) ·
[Отложенное чтение диска: измерения](toolkit/FAP3_DEFERRED_DISK_ru.md) ·
[История экспериментов](CHANGELOG.md) ·
[Ранее собранный мультфильм и исследования](toolkit/README_ru.md)
