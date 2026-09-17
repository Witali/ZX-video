# Полный мультфильм на нескольких дискетах

Пользователь снял ограничение одной дискеты и попросил весь исходник,
включая окончание и титры. Новый `build_full_movie.py` получает длительность
видео/аудио через FFprobe и округляет **вверх** до целого видеокадра.

Для имеющегося MOV длительность 596,461667 с. На сетке 25/3 кадра/с это
4971 кадр / 596,52 с и 29826 состояний AY при 50 Гц. Дополнение конца —
58,333 мс: последний экран удерживается, в аудио добавляется тишина.
Сам исходник не обрезается и скорость не меняется. Пространственное
кадрирование и качество изображения сохраняют прежние настройки.

## Сборка

Нужны Python с NumPy, Pillow, OpenCV; FFmpeg/FFprobe и ZX0 v2.

```text
python toolkit/build_full_movie.py --input-video SOURCE.mov --output toolkit/build_full_movie --ffmpeg ffmpeg.exe --ffprobe ffprobe.exe --zx0 zx0.exe
```

Этапы: `audio`, `video`, `disks`; для повторного запуска одного этапа
добавить `--stage ИМЯ`. Manifest хранит SHA-256 исходника и готовых этапов,
проверяет их перед использованием. Видео/аудио сравниваются на всей
длительности; метрики двухминутной проверки не переносятся на весь фильм.

Блоки ZX0 — 6144 байта. При заполнении тома упаковка останавливается;
она больше не сжимает заранее весь оставшийся фильм на каждой дискете.
Повторная сборка контрольных 120 секунд этим методом дала побайтно те же
две TRD (хеши в `ay_block_size_measurements.json`). Изменений процедур
проигрывателя и их стоимости нет: 0 T относительно принятой версии v11.

## Проверка

```text
python toolkit/measure_fuse.py FUSE.exe toolkit/build_full_movie/disks --output toolkit/build_full_movie/disks/fuse_timing.json --timeout 180
python toolkit/validate_fast_sparse.py toolkit/build_full_movie/disks --source-build toolkit/build_full_movie/source --ay-50hz toolkit/build_full_movie/audio/50Hz/raw.bin --fuse-timing toolkit/build_full_movie/disks/fuse_timing.json --output toolkit/build_full_movie/disks/cpu_validation.json
python toolkit/compare_ay_trace.py toolkit/build_full_movie/disks --timing toolkit/build_full_movie/disks/fuse_timing.json --ay-50hz toolkit/build_full_movie/audio/50Hz/raw.bin --rate-report toolkit/build_full_movie/audio/comparison.json --input-video SOURCE.mov --ffmpeg ffmpeg.exe --output toolkit/build_full_movie/comparison
```

Каждый том самостоятельно загружается через `boot`. Между дискетами есть
пауза на смену и загрузку; автоматического бесшовного перехода пока нет.
Порядок и диапазоны кадров определяются `disks/build_metadata.json`.
Для проигрывания нужен Spectrum 128 с Beta128 и проверенной TR-DOS 5.03.
