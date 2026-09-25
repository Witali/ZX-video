# Ускорение Huffman через флаг переноса

25 сентября 2026, база `0cf64be`. Опциональный `--carry-huffman` в сборщике
и универсальном конвертере. Исходные кадры, AY и сжатый поток прежние.
Это сохранённый эксперимент, а не выпуск с подтверждёнными 8⅓ кадра/с.

## Два проверенных варианта

**Чтение одного байта:** сначала проверяем, помещается ли короткий код
целиком в текущем байте. Если да, второй байт не читается. В противном
случае требуется обычный двухбайтовый просмотр после дополнительной
проверки. Эксперимент оставлен только в стенде как `single_byte=True`.

Измеренные изменения примитива: −50 T при успешной однобайтовой ветви,
+58 T для короткого кода на границе, +47 T для длинного кода. Типичный
короткий bitmap-код внутри байта: 168→118 T. Код примитива 235→256 байтов,
таблицы не увеличиваются. На всех символах трёх томов стоимость растёт
**143 755 145→149 564 861 T (+5 809 716)**, замедлены 3762 кадра.
Решение: отклонить для плеера, сохранить воспроизводимый отрицательный результат.

**Перенос:** представлять текущую битовую позицию как F8h..FFh вместо
F0h..F7h. Тогда сложение позиции и длины само устанавливает carry при
пересечении границы байта. `JR NC` заменяет пару `BIT 3,A / JR Z`.
При нормализации позиции используется `OR F8h` вместо `AND F7h`.
Содержимое страниц сдвига не меняется; порядок чтения двух байтов обратный.
Для длинного невыровненного кода добавляется `RES 3,H` перед сдвигом.

## Такты и память

Расчёт по [Zilog UM0080](https://www.zilog.com/docs/z80/um0080.pdf),
проверенный исполнением каждой инструкции. Ниже стоимость примитива
без вызова и внешнего цикла; `a` равен 1 для атрибута, 0 для bitmap.

| Путь | Прежде | С переносом | Разница |
|---|---:|---:|---:|
| Короткий, без перехода в следующий байт | 168−a T | 160−a T | −8 T |
| Короткий, с переходом | 173−a T | 165−a T | −8 T |
| Длинный, начальное смещение 0 | L T | L T | 0 |
| Длинный, начальное смещение 1..7 | L T | L+8 T | +8 T |

Абсолютная прежняя цена длинного кода:
`L = 420 + 53×(length−9) + 32×refills − symbol_carry + 70×(start>0) + 5×(end>0) − a`.
Здесь `refills = ceil(max(0,length−8−available)/8)`,
`available = 8−start` для ненулевого start, иначе 0;
symbol_carry означает перенос при вычислении адреса символа.
Точная формула и исполняемый листинг сохранены в
[стенде](benchmark_prefix_huffman.py) и [отчёте символов](carry_huffman_symbols.json).

Сумма примитива с реальными таблицами каждого тома:
**143 755 145→138 434 657 T (−5 320 488)**. Это подсчёт всех реальных
символов по формулам, проверенным парными Z80-прогонами; сюда не входят
реконструкция, ZX0, вывод, IRQ, ULA и диск. На каждом наборе таблиц
проверено 22 904 пары случаев: каждый используемый символ на восьми смещениях.

Код примитива остаётся **235 байтов**, конец реконструкции **8FE6h**;
до renderer 9000h остаётся 26 байтов. Восемь маркеров перенесены с
BAF0h..BAF7h на BAF8h..BAFFh; таблица позиций BB00h использует новые
значения. Новых буферов, таблиц, копирований и дополнительной глубины
стека нет. Экраны в банках 5/7, Huffman в 6, кольцо диска 64 КиБ
в 0/1/3/4, AY/IRQ и TR-DOS workspace сохраняют прежнее размещение.

## Проверки данных и доставки

- Все коды на восьми битовых смещениях, ненулевой lookahead, все 256
  значений соседнего байта для коротких кодов, фактическое число чтений.
- Настоящий AY IRQ на каждой границе инструкций обоих примитивов;
  два экспериментальных режима одновременно запрещены.
- Полная стадия metadata/reconstruction/rendering для 4221 кадра с
  таблицами тома 1: полные compact и оба native-экрана, защита RAM,
  точная разница тактов каждого кадра относительно сохранённой базы.
  Результат: [полный CPU-отчёт](carry_huffman_pipeline.json).
  Этот стенд получает пакеты от хоста; ZX0/IRQ/диск здесь не исполняются.
  **1 068 194 934→1 063 006 286 T (−5 188 648)**, ни одного замедленного
  кадра. Отличие от суммы символов выше объясняется таблицами тома 1
  на всём фильме вместо отдельных таблиц каждого тома.
- Полный плеер CPU на трёх парных диапазонах по восемь кадров:
  2921..2928 — **4 822 051→4 807 963 T**;
  3195..3202 — **1 058 900→1 057 236 T**;
  3838..3845 — **1 514 014→1 511 320 T**.
  Диск идеальный, ULA отсутствует; 48 исполнений / 288 точных AY.
  Первый диапазон сохраняет три поздних публикации у обеих версий.
- Полный Fuse: три самостоятельных холодных запуска до EOF,
  **4221 публикация / 25 326 точных AY-записей / 6733 точных сектора**,
  без повторов чтения. Все стартовые таблицы точны. Переходы 1→2→3
  и отказ чужим дискам отдельно проверены с подменённой ROM.
  Fuse сверяет 80 байтов экрана на кадр, физический привод не проверен.

| Том | Сектора | FPS до → после | Поздние кадры до → после | Пропущенные поля AY до → после |
|---|---:|---:|---:|---:|
| 1 | 2543 | 8,019790 → 8,028514 | 1065 → 1063 | 380 → 368 |
| 2 | 2544 | 7,428374 → 7,441164 | 1195 → 1194 | 946 → 931 |
| 3 | 2543 | 7,318932 → 7,328012 | 1297 → 1296 | 1104 → 1093 |

Границы 1624/2921/4221 и логические ZX0-потоки прежние, запас 512 байтов.
Время воспроизведения **555,638697→554,896994 с (−0,741703 с)**, без
bootstrap и времени смены дискет. Фактические серии OUT восстановились
5/1/0 раз; на каждом томе одна серия остаётся невосстановленной до EOF.
Максимальные отклонения **7,476837 / 18,712080 / 21,950713 с**.
Очередь AY пуста 368/930/1093 раза, ещё одно поле потеряно вне очереди
на втором томе. Число пропущенных полей отдельно от повторов данных:
все 25 326 AY-записей проиграны побайтно точно, но часть с опозданием.
Цена чтения в Fuse включает ROM, вращение диска, IRQ и ULA; её нельзя
смешивать с детерминированными суммами CPU. Все фактические OUT,
промахи номинальных сроков и восстановление серий сохранены в
[сводке](carry_huffman_summary.json) и [трассах](carry_huffman_evidence/index.json).
Расписание сравнивается с неизменным началом; точность измерения фазы OUT
64 T не заменяет допуск целого поля. Оба критерия плавности провалены.

Прошли 32 теста примитива и регрессий. Универсальный конвертер: шесть
входов / 68 кадров / 408 AY / восемь TRD и два перехода, полный CPU/Fuse.
Пять простых входов выдерживают сроки, шумовой — нет: 492 пропущенных
поля AY и 78 чтений диска. Deferred в этом CLI не используется.
Подробное сравнение кадров/AY: [отчёт](carry_huffman_generic.json).
Решение: сохранить ускорение как
необязательную опцию, продолжать считать точные сроки нерешённой задачей.
Корневые TRD этим экспериментом не заменены.

## Воспроизведение

Из `.worktree/huffman-byte-peek`, с Python/NumPy и `PYTHONPATH=toolkit`:

```powershell
$states = '../three-disk-quality/.tmp/no_credits/source/conversion.npz'
$source = '../volume-huffman/.tmp/probe'
$zx0 = '../audio-fidelity/.tmp/bin/zx0.exe'
python -m unittest test_huffman_peek_variants test_prefix_huffman_z80 test_pipelined_frame test_generic_converter test_fap3_disk test_static_cache_borders
python toolkit/probe_single_byte_huffman.py --variant single_byte --directory $source --states $states --output toolkit/single_byte_huffman_cpu.json
python toolkit/probe_single_byte_huffman.py --variant carry_huffman --directory $source --states $states --output toolkit/carry_huffman_symbols.json
python toolkit/benchmark_carry_huffman.py --raw "$source/volume-1.raw" --states $states --baseline toolkit/static_cache_borders_cpu.json --output toolkit/carry_huffman_pipeline.json
python toolkit/profile_inline_matches.py --experiment carry_huffman --raw "$source/volume-3.raw" --states $states --zx0 $zx0 --cache .tmp/profile --read-cache ../static-cache-borders/.tmp/profile --report toolkit/carry_huffman_frame_cpu.json --ranges 2921:2929,3195:3203,3838:3846 --fast-noop-scan --irq-safe-paging
python toolkit/measure_volume_huffman.py --probe toolkit/volume_huffman_probe.json --partition toolkit/combined_delivery_partition.json --directory $source --states $states --zx0 $zx0 --fuse 'C:/Program Files (x86)/Fuse/fuse.exe' --read-cache ../static-cache-borders/.tmp/three/zx0 --read-cache ../combined-delivery/.tmp/rebalance/zx0 --output .tmp/three --report toolkit/carry_huffman_fuse.json --fast-noop-scan --irq-safe-paging --inline-matches --deferred-limit 248 --keepalive-fields 64 --frame-service --static-cache-borders --carry-huffman --timeout 300
python toolkit/check_generic_converter.py --output .tmp/generic --ffmpeg ../audio-fidelity/.tmp/bin/ffmpeg.exe --ffprobe ../audio-fidelity/.tmp/bin/ffprobe.exe --zx0 $zx0 --fuse 'C:/Program Files (x86)/Fuse/fuse.exe' --trdos-rom 'C:/Program Files (x86)/Fuse/roms/trdos.rom' --fast-noop-scan --irq-safe-paging --inline-matches --static-cache-borders --carry-huffman --report toolkit/carry_huffman_generic.json
python toolkit/summarize_static_cache_borders.py --experiment carry_huffman --directory .tmp/three --baseline-directory ../static-cache-borders/.tmp/three --cpu toolkit/carry_huffman_pipeline.json --generic toolkit/carry_huffman_generic.json --evidence toolkit/carry_huffman_evidence --output toolkit/carry_huffman_summary.json
```
