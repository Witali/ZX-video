# FAP2: чтение целого кадра и работа с данными на месте

19 сентября 2026, база `a875d18`. Все 4221 кадр без титров, прежние
пиксели age3 и 25326 AY-записей. Это эксперимент общего тракта Z80,
не новый комплект дискет.

## Формат и RAM

`bulk_frame_stream.py` преобразует FAP1 обратимо. После глобального
заголовка FAP2 каждый кадр содержит двухбайтовую длину и единый пакет:
шесть AY-записей, flags/mask_length/coded_length (5 байт), карту кэша
(3), векторы (192), сжатые маски, карту нативного вывода (80), Huffman,
нулевой защитный байт, литералы, ещё один ноль. Длина литералов выводится
из конца пакета. Два защитных байта увеличили вход на 8442 байта:
3097959 → **3106401**. Максимум пакета **3647 байт** помещается в прежние
4704 байта A6A0..B8FF.

Z80 читает длину в BA58..BA59, затем весь пакет одним `reader.take`.
AY, маски и значения потребляются из него. Курсоры, границы, флаги и
защитные байты проверяются. Базовый разборщик занимает **408 байт**
DC00..DD97 (прежний FAP1: 193); банковые мосты прежние, 31 байт.
Обвязка загружает динамический указатель Huffman: LD HL,(nn) **16 T**
вместо LD HL,nn **10 T**; всего **373→379 T**, **+6 T/кадр**.

Второй вариант `--zero-copy` оставляет также векторы и карту вывода
внутри пакета. Его разборщик **212 байт**. Два поля указателей в обвязке
добавляют 4 байта состояния и **12 T/кадр**: всего **391 T**.

| Операция | Копирование, T | Указатель, T | Разница, T |
|---|---:|---:|---:|
| 192 вектора: 12 групп по 16 LDI | 3267 | 37 | −3230 |
| Карта вывода: 80 LDI | 1300 | 37 | −1263 |
| Две загрузки указателей в обвязке | 20 | 32 | +12 |
| **Итого за кадр** | **4587** | **106** | **−4481** |

Подсчёт — таблица Zilog UM0080, списки инструкций и реально исполненные
варианты T в отчётах. Кодировки данных/секторы между двумя FAP2-вариантами
одинаковы. Входной пакет сохраняется неизменным до конца подготовки.

## Полностью измеренный FAP2 с копированием

`bulk_frame_cpu.json`: все кадры, обе экранные страницы, все AY-записи,
курсоры битов/литералов/потока, карты/маски/векторы и защищённые области
совпали. Гистограмма инструкций сходится с суммой стадий.

| Стадия | FAP1, T | FAP2, T | Разница, T |
|---|---:|---:|---:|
| Разбор и мосты | 7357203 | 24307715 | +16950512 |
| Потоковое чтение | 106023939 | 70336349 | −35687590 |
| Банковый ZX0 | 342628971 | 303561027 | −39067944 |
| AY enqueue | 9150603 | 9150603 | 0 |
| Маски | 80531227 | 80531227 | 0 |
| Обвязка | 1574433 | 1599759 | +25326 |
| Реконструкция | 751710764 | 751710764 | 0 |
| Нативный вывод | 405533717 | 405533717 | 0 |
| **Foreground** | **1704510857** | **1646731161** | **−57779696** |

Среднее **390128,207 T**, максимум **864972 T** (кадр 4052).
**1573 кадра** выше 425448 T ещё без IRQ, ULA и диска (FAP1: 1751).
Настоящий ISR при ручной подаче шести прерываний после кадра отдельно
занял **16591971 T**. Ручная подача подтверждает данные, не частоту.

Проекция zero-copy по проверенной постоянной разнице: **1627816860 T**,
среднее **385647,207 T**, максимум **860491 T**, 1512 кадров выше бюджета.
**Полного прогона этого варианта в данном эксперименте нет.** Его короткие
тесты и частичный прогон с настоящим таймером перечислены ниже.

## Размер и расписание

Реальный optimal ZX0 по 8192 байт, независимая обратная распаковка всех
380 блоков: **1935757 байт** с заголовками, против 1928341 FAP1.
Рост **7416 байт / 29 секторов**. От предварительного бюджета трёх дискет
1937664 остаётся всего **1907 байт**. Реальный расход загрузчика, границ
томов и файловой системы пока не подтверждён сборкой. Дополнительные
секторы нельзя считать бесплатными: доставка ROM/диском ещё не измерена.

Два отдельных опыта с периодом 70908 T, настоящим ISR, EI/HALT и
опережающей распаковкой по 256 байт закончились неудачей:

| Вариант | Полностью проверено кадров | Первое опоздание | Максимум | Сбой |
|---|---:|---:|---:|---|
| FAP2 с копированием | 65 | кадр 60 | 5 полей | кадр 65, AY tick 390 |
| FAP2 zero-copy | 66 | кадр 47 | 5 полей | кадр 66, AY tick 396 |

Ускорение меняет попадание в окна опережения; номера первых опозданий
не являются монотонной оценкой быстродействия. Оба опыта непригодны
для выпуска. Бесплатный producer, отсутствие ULA и диска делают эти
условия благоприятнее реальной машины. Таблицы при старте устанавливает
host; общего загрузчика и смены томов ещё нет. Корневые TRD не изменены.

Профиль `frame_control_profile.json` выявил **488407 из 810432 блоков**
(60,26%) с нулевым вектором и пустой bitmap-маской. Счётчик серий
останавливается на каждой полосе из 16 блоков. Это основание следующего
эксперимента; сам анализ ничего не изменяет: **0 байт, 0 T экономии**.

## Проверки и воспроизведение

9 тестов FAP2, прежнего разборщика и таймера прошли. Проверены stored/ZX0,
переход кольца FFFF, пакеты через блоки по 509 байт, повреждённые длины,
флаги/нули и точная разница −4481 T на смешанных кадрах. PC round-trip
всех кадров побайтно возвращает FAP1, включая AY.

```text
python toolkit/bulk_frame_stream.py --source .tmp/frame_packet/stream.raw --output .tmp/bulk_frame/stream.raw --report toolkit/bulk_frame_stream.json
python toolkit/probe_zx0_storage.py --raw .tmp/bulk_frame/stream.raw --block-bytes 8192 --zx0 ../audio-fidelity/.tmp/bin/zx0.exe --cache .tmp/bulk_frame/zx0 --output toolkit/bulk_frame_zx0.json
python -m unittest toolkit/test_bulk_frame_stream.py toolkit/test_bulk_frame_z80.py toolkit/test_frame_stream_z80.py toolkit/test_frame_clock_z80.py
python toolkit/benchmark_frame_stream.py --raw .tmp/bulk_frame/stream.raw --states .tmp/no_credits/source/conversion.npz --storage-report toolkit/bulk_frame_zx0.json --cache .tmp/bulk_frame/zx0/optimal --baseline toolkit/selective_cache_pipeline_cpu.json --output toolkit/bulk_frame_cpu.json
python toolkit/benchmark_frame_stream.py --raw .tmp/bulk_frame/stream.raw --states .tmp/no_credits/source/conversion.npz --storage-report toolkit/bulk_frame_zx0.json --cache .tmp/bulk_frame/zx0/optimal --baseline toolkit/selective_cache_pipeline_cpu.json --output toolkit/bulk_frame_clock_cpu.json --cadence --lookahead --limit 150
python toolkit/benchmark_frame_stream.py --raw .tmp/bulk_frame/stream.raw --states .tmp/no_credits/source/conversion.npz --storage-report toolkit/bulk_frame_zx0.json --cache .tmp/bulk_frame/zx0/optimal --baseline toolkit/selective_cache_pipeline_cpu.json --output toolkit/bulk_frame_zero_copy_clock_cpu.json --cadence --lookahead --zero-copy --limit 150
python toolkit/summarize_bulk_frame.py --baseline toolkit/frame_stream_cpu.json --cpu toolkit/bulk_frame_cpu.json --old-storage toolkit/frame_packet_zx0.json --storage toolkit/bulk_frame_zx0.json --clock toolkit/bulk_frame_clock_cpu.json --zero-copy-clock toolkit/bulk_frame_zero_copy_clock_cpu.json --output toolkit/bulk_frame_summary.json
python toolkit/profile_frame_control.py --cpu toolkit/frame_stream_cpu.json --cells .tmp/raw_attributes_128/cells.raw --output toolkit/frame_control_profile.json
```

**Решение:** сохранить формат и zero-copy как основу дальнейшего ускорения;
рост объёма и расход секторов обязательно перепроверить в сборке. Не
принимать текущее расписание за плавные 25/3 кадра/с или готовые три TRD.
