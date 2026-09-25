# Запись повторяемых фрагментов прямо из регистров

25 сентября 2026, база `7152e10`. Необязательный `--register-fragments`
в сборщике и универсальном конвертере. Все байты FAP3/ZX0, исходные
кадры, разрешение и AY-записи сохраняются. Это оптимизация исполнения,
а не новый формат сжатия. Требования плавного выпуска пока не выполнены.

## Изменение

Раньше адрес назначения находился в DE. Для записи строки из двух байтов
плеер выполнял `LD A,B / LD (DE),A / INC E / LD A,C / LD (DE),A`.
Теперь литеральный указатель сначала сохраняется, назначение загружается
в HL, а строка записывается как `LD (HL),B / INC L / LD (HL),C`.
Для фрагмента с двумя вариантами строки вторая пара остаётся в DE;
убраны лишние переносы через стек и преждевременная загрузка назначения.

Режимы: 85 — 16 произвольных байтов, 86 — повтор пары байтов,
87 — выбор из двух пар по восьмибитовому селектору, 88 — заливка байтом.
У 85 сохранены две LDI на строку. Порядок строк/символов и обе позиции
входных потоков прежние. Нет новых DI/EI, буферов и копирований.

## Абсолютные такты

Источник — [таблица Zilog UM0080](https://www.zilog.com/docs/z80/um0080.pdf).
LD A,r — 4 T, LD (DE),A и LD (HL),r — 7 T, INC r — 4 T;
LD DE,(nn) — 20 T, LD HL,(nn) — 16 T, PUSH/POP — 11/10 T.
Каждая исполняемая инструкция сравнивается со своим листингом.

| FAP3-фрагмент, включая RET | Прежде | Теперь | Δ T |
|---|---:|---:|---:|
| 85: произвольные байты | 492 | 492 | 0 |
| 86: повторяемая строка | 487 | 419 | −68 |
| 87: две строки | 764+10z | 655+10z | −109 |
| 88: заливка | 459 | 423 | −36 |

`z = 8 − popcount(selector)` — число нулевых битов селектора.
Сюда входят диспетчеризация, продвижение bitmap-mask/literal-указателей,
чтение фрагмента и запись всех 16 компактных байтов. Внешний CALL,
обход плиток, атрибуты, ZX0, IRQ/ULA и диск исключены.

Для старого совмещённого FHF1-входа к обеим колонкам добавляются 54 T
при выравнивании и ещё 10 T при неполном предыдущем байте Huffman.
Разность остаётся той же. Повтор строки экономит `8×8+4 = 68 T`,
заливка `8×4+4 = 36 T`; две строки — `8×8+20+21+4 = 109 T`.

Код реконструкции меньше на **53 байта**, конец **8FE6h→8FB1h**;
до renderer 9000h свободно 79 байтов. Новый код не расширяет таблицы
и не увеличивает глубину стека. Экраны 5/7, Huffman в банке 6,
дисковое кольцо 64 КиБ в 0/1/3/4, история ZX0, AY/IRQ, TR-DOS workspace
и размещение остальных частей 128 КиБ прежние.

## Проверки

- **3108 парных случаев Z80:** четыре режима, все 256 селекторов,
  начало/середина/последний столбец последней полосы, оба варианта входа;
  у совмещённого потока смещения 0/3/7. Проверены полные compact-байты,
  сохранность соседней памяти, оба курсора, стек и абсолютные такты.
- Смешанные последовательные кадры с пространственными предикторами
  и фрагментами, два канала ввода и прежний совмещённый формат.
- Настоящий AY IRQ после каждой инструкции, оба варианта каналов;
  регистры, селектор и входные позиции сохраняются.
- **34 теста прошли:** четыре новых и 30 регрессий, включая прежний
  машинный код с выключенной опцией и проверки дисков/конвертера.
- Полная стадия CPU на всех 4221 кадре сравнивает все compact и оба
  native-экрана с эталоном, а каждую покадровую разность тактов — с
  количеством режимов 86/87/88. Таблицы Huffman тома 1 используются
  на всём фильме. Здесь нет исполнения ZX0/IRQ/диска.
- Полный CPU-плеер с идеальным диском на трёх парных диапазонах по
  восемь кадров: −4639 / 0 / −2788 T. Все кадры/AY точны; тяжёлый
  диапазон 2921..2928 сохраняет три поздних публикации у обеих версий.
  Эти 48 исполнений / 288 AY не заменяют полный замер сроков фильма.

Полные стадийные такты и парные случаи:
[CPU-отчёт](register_fragments_pipeline.json).
Кадровый плеер: [локальные CPU-прогоны](register_fragments_frame_cpu.json).

Полная стадия: **1 063 006 286→1 062 161 744 T (−844 542)**,
ни одного замедленного кадра. Эту сумму нельзя выдавать за стоимость
всего плеера: она не включает ZX0 и доставку с диска.

[Анализ бюджета](register_fragments_deadlines.json) по этому полному
исполнению выделяет один кадр, индекс **3506**: **425 659 T** против
номинальных **425 448 T**, превышение **211 T** даже без ZX0/IRQ/ULA/диска.
У предыдущего варианта таких кадров было два, максимум 2382 T.
Все проверенные окна 2/4/8/16/32/64/128 кадров укладываются в сумму
номинальных бюджетов изолированной стадии. Это подсказка для следующего
шага — рассмотреть предварительную распаковку и подачу пакетов с учётом
оставшегося тяжёлого кадра, а не доказательство готовности очереди.
Здесь таблицы Huffman тома 1 на всём фильме; фактические тома используют
свои таблицы. Ёмкость RAM, дополнительное копирование и сроки полного
плеера новой схемой ещё должны быть измерены.

## Полные дискеты

Параметры прежние: границы 1624/2921/4221, fast-noop-scan,
IRQ-safe paging, inline ZX0, static-cache-borders, carry-huffman,
deferred=248, keepalive=64 и обслуживание после кадра.

| Том | Сектора | FPS до → после | Поздние кадры до → после | Пропущенные поля AY до → после |
|---|---:|---:|---:|---:|
| 1 | 2543 | 8,028514 → 8,030102 | 1063 → 1062 | 368 → 366 |
| 2 | 2544 | 7,441164 → 7,442018 | 1194 → 1195 | 931 → 930 |
| 3 | 2543 | 7,328012 → 7,332146 | 1296 → 1297 | 1093 → 1088 |

Три полных независимых холодных запуска до EOF: **4221 публикация /
25 326 точных AY-записей / 6733 точных runtime-сектора**, без повторов
чтения. Стартовые таблицы точны; переходы между дисками и отказ чужим
дискам проверены отдельно с подменённой ROM. Fuse сверяет 80 экранных
байтов на кадр; физический привод не проверен. Логические ZX0-потоки
сравниваются после обратного interleave, общий запас прежние 512 байтов.

Средняя скорость немного выросла, но число номинальных промахов
**3553→3554**. Оба критерия плавности провалены. Времена фактических OUT,
каждый промах и восстановление серий сохраняются в
[сводке](register_fragments_summary.json) и [полных трассах](register_fragments_evidence/index.json).
Микрофаза OUT учитывается с точностью 64 T; допуск поля этим не скрывается.
Время Fuse включает ROM, эмуляцию привода, ULA и IRQ; оно не складывается
с отдельными детерминированными суммами CPU.

Playback **554,896994→554,742471 с (−0,154523 с)**, без bootstrap/смены.
Восстановленные серии фактических OUT: 4/1/0; на каждом томе остаётся
одна невосстановленная серия до EOF. Максимальные отклонения
**7,436854 / 18,692092 / 21,850749 с**. Все 2384 пропущенных поля AY
соответствуют пустой очереди; других потерянных IRQ-полей здесь не найдено.

Универсальный конвертер: шесть входов / 68 кадров / 408 AY / восемь
независимых TRD, полный CPU/Fuse и два перехода. Все FAP3 побайтно прежние.
Пять простых входов проходят сроки, шумовой — нет: 492 пропущенных поля
AY, 78 чтений. Deferred в этом CLI не используется.
[Отчёт](register_fragments_generic.json).
Сохраняем как небольшое ускорение и освобождение места под код.
Это не выпуск с точными 8⅓ кадра/с; корневые TRD этим опытом не заменены.

## Воспроизведение

Из `.worktree/register-fragments`, с Python/NumPy и `PYTHONPATH=toolkit`:

```powershell
$states = '../three-disk-quality/.tmp/no_credits/source/conversion.npz'
$source = '../volume-huffman/.tmp/probe'
$zx0 = '../audio-fidelity/.tmp/bin/zx0.exe'
python -m unittest test_register_fragments test_fast_fragments test_fragment_channels test_pipelined_frame test_generic_converter test_fap3_disk test_static_cache_borders
python toolkit/benchmark_register_fragments.py --raw "$source/volume-1.raw" --states $states --baseline toolkit/carry_huffman_pipeline.json --output toolkit/register_fragments_pipeline.json
python toolkit/profile_inline_matches.py --experiment register_fragments --raw "$source/volume-3.raw" --states $states --zx0 $zx0 --cache .tmp/profile --read-cache ../huffman-byte-peek/.tmp/profile --read-cache ../static-cache-borders/.tmp/profile --report toolkit/register_fragments_frame_cpu.json --ranges 2921:2929,3195:3203,3838:3846 --fast-noop-scan --irq-safe-paging
python toolkit/measure_volume_huffman.py --probe toolkit/volume_huffman_probe.json --partition toolkit/combined_delivery_partition.json --directory $source --states $states --zx0 $zx0 --fuse 'C:/Program Files (x86)/Fuse/fuse.exe' --read-cache ../huffman-byte-peek/.tmp/three/zx0 --read-cache ../combined-delivery/.tmp/rebalance/zx0 --output .tmp/three --report toolkit/register_fragments_fuse.json --fast-noop-scan --irq-safe-paging --inline-matches --deferred-limit 248 --keepalive-fields 64 --frame-service --static-cache-borders --carry-huffman --register-fragments --timeout 300
python toolkit/check_generic_converter.py --output .tmp/generic --ffmpeg ../audio-fidelity/.tmp/bin/ffmpeg.exe --ffprobe ../audio-fidelity/.tmp/bin/ffprobe.exe --zx0 $zx0 --fuse 'C:/Program Files (x86)/Fuse/fuse.exe' --trdos-rom 'C:/Program Files (x86)/Fuse/roms/trdos.rom' --fast-noop-scan --irq-safe-paging --inline-matches --static-cache-borders --carry-huffman --register-fragments --report toolkit/register_fragments_generic.json
python toolkit/summarize_static_cache_borders.py --experiment register_fragments --directory .tmp/three --baseline-directory ../huffman-byte-peek/.tmp/three --cpu toolkit/register_fragments_pipeline.json --generic toolkit/register_fragments_generic.json --evidence toolkit/register_fragments_evidence --output toolkit/register_fragments_summary.json
python toolkit/assess_stage_deadlines.py --cpu toolkit/register_fragments_pipeline.json --output toolkit/register_fragments_deadlines.json
```
