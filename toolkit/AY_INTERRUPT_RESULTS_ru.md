# Экспериментальная очередь AY на 50 Гц

17 сентября 2026. Дополнительный режим `--ay-50hz` использует поток v11.
Шесть звуковых тактов перед каждым видеопакетом при 25/3 кадра/с.
Обычная сборка v10 и доставленная ранее `ZX-video-AY-noise.trd` остаются
базой сравнения. Прототип пока не принят для замены этой дискеты.

## Реализация

IM2 потребляет один опубликованный слот за прерывание. В слоте лежат число
изменений и пары «регистр, значение»; ноль означает такт без обращения к AY.
Первый такт инициализирует R0..R10. Основной код перестал писать эти
регистры при смене экрана: иначе прерывание могло бы изменить выбранный
регистр между обращениями к FFFD и BFFD.

Очередь A000..A3FF содержит 32 слота по 32 байта, из них 31 доступен.
Производитель копирует слот целиком и только потом публикует индекс одним
байтом. Обработчик сохраняет AF, BC, DE, HL; не переключает банки и не
читает диск. Последние такты доигрываются до отключения звука. Режим
требует wrapped input, interleaved layout и memory clock.

## Z80 T-states

Источник: [Zilog UM0080](https://www.zilog.com/docs/z80/um0080.pdf).
Расчёты проверяет `benchmark_ay_interrupt.py`; таблица в
`ay_interrupt_cycles.json`. CPU-валидатор не включает ROM, ULA, ожидание
HALT, физический диск и IRQ в показатели подготовки кадров.

| Участок | Прежде | Сейчас | Разница |
|---|---:|---:|---:|
| Быстрый IM2, пустой аудиотакт | 116 | 510 | +394 |
| Быстрый IM2, 1 изменение | 116 | 583 | +467 |
| Быстрый IM2, 3 изменения | 116 | 749 | +633 |
| Быстрый IM2, 11 изменений | 116 | 1413 | +1297 |
| Подготовка аудиоданных кадра | 204 | 1722 + 42n | 1518 + 42n |
| Применение звука в основном коде, тон / шум, включая CALL | 807 / 809 | 0 | −807 / −809 |

Здесь n — общее число изменённых регистров в шести тактах. Старое копирование
9 байт: `LD DE` 10 + `LD BC` 10 + `LDIR` 184 = 204 T. Новая подготовка:
CALL 17 + `audio_enqueue_six` (1705 + 42n). В неё входят проверки заполнения
и публикация всех шести слотов. Таблица IM2 включает подтверждение 19 T,
диспетчер, ROM NOP/RET и CALL обработчика. Отдельно `audio_tick`:
отключён 58 T, недогрузка 205 T, пустой слот 377 T, непустой 367 + 83n T;
последний такт добавляет 24 T. Для медленного IM2 старые 184/211/210/225 T
увеличиваются на 17 + стоимость `audio_tick`. Копирование шаблона IM2 при
старте длиннее на три байта: +63 T, один раз.

## Измерения прототипа

Сборка использует `build_audio_rate_experiment/50Hz/raw.bin` (SHA-256
`6353c9bd4fb73b1908a4a8a21a95c6e0d387f015c8debbf70e00787be7006776`).

- Все 1000 экранов совпали с исходными побайтно в CPU-валидаторе.
- Fuse выполнил все 6000 звуковых тактов и 10934 записи регистров,
  сверенных по порядку и значениям с исходными состояниями.
- 1451 неизменившийся такт не сделал ни одной записи в AY.
- Интервалы завершения обработки аудиотактов: 19,738..20,199 мс.
  Разброс включает различное число записей в обработчике. Недогрузок нет.
- PLAYER — 5120 байт. Нужно **две TRD**, 987 + 13 экранов; вторая часть
  начинает звук заново после смены диска. Это не непрерывный однодисковый ролик.
- Максимальный видеоинтервал первой части — **128,549 мс**, второй —
  120,019 мс. Средний FPS первой части 8,33687. Условие ≤125 мс ещё нарушено.
- Средние CPU затраты: 133609,40 T переднего плана + 84476,51 T фоновой
  подготовки = 218085,91 T. IRQ и ROM в этих числах исключены.

Точки трассы записей отмечают начало инструкции OUT (BFFD),A; сама операция
I/O завершается внутри её 12 T. Это проверка записей и времени, не запись
звукового выхода Fuse. Идеальный WAV на 50 Гц пока даёт F1 атак 0,75601;
достижимость 0,95 рассмотрена в `AY_ONSET_FEASIBILITY_ru.md`.

## Повторение

После `benchmark_ay_rate.py` и подготовки прежней компактной сборки:

```powershell
python toolkit/build_fast_sparse_trd.py --source-build toolkit/build_audio_noise --output toolkit/build_audio_irq_trd --ay-50hz toolkit/build_audio_rate_experiment/50Hz/raw.bin --packing zx0 --zx0 zx0.exe --drawing registers --disk-reader trdos503-irq --disk-layout interleaved --pacing deadline --zx0-decoding incremental --motor-keepalive-fields 64 --prefetch-quota 3 --rom-clock full --disk-seek cached --packet-lookahead --uncontended --read-reserve 64 --memory-clock --direct-input --wrapped-input
python toolkit/measure_fuse.py FUSE.exe toolkit/build_audio_irq_trd --output toolkit/build_audio_irq_trd/fuse_timing.json --timeout 120
python toolkit/verify_ay_trace.py toolkit/build_audio_irq_trd --source toolkit/build_audio_rate_experiment/50Hz/raw.bin --timing toolkit/build_audio_irq_trd/fuse_timing.json --output toolkit/build_audio_irq_trd/audio_validation.json
python toolkit/validate_fast_sparse.py toolkit/build_audio_irq_trd --source-build toolkit/build_audio_noise --ay-50hz toolkit/build_audio_rate_experiment/50Hz/raw.bin --fuse-timing toolkit/build_audio_irq_trd/fuse_timing.json --output toolkit/build_audio_irq_trd/cpu_validation.json
python toolkit/benchmark_ay_interrupt.py --output toolkit/ay_interrupt_cycles.json
python -m unittest discover -s toolkit -p 'test_*.py'
```

Ограничение одной TRD снято пользователем. Контрольный фрагмент принят
с блоками 6144 байта: все видеоинтервалы ≤125 мс, звук сравнен по фактической
временной трассе. Подробности: `AY_BLOCK_SIZE_RESULTS_ru.md`.
Сводные аудиопроверки первого прототипа — в `ay_interrupt_validation.json`.
