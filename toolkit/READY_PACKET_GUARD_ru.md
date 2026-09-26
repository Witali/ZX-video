# Ограничение необязательного чтения и поиск потерянных IRQ

26 сентября 2026. База `347f995`: те же 4221 кадр, 378 ZX0-блоков,
три самостоятельно загружаемых TRD, прежние разрешение и AY 50 Гц.
Это проверенный эксперимент, **не выпуск с требуемыми сроками**.

## Ограничение предзагрузки

Новый `--ready-packet-guard` разрешает необязательное чтение следующего
пакета только при двух условиях: текущий завершённый слот содержит не
меньше 4705 байтов (максимальное тело 4703 + двухбайтовая длина), и
AY-очередь занята не более чем на 25 записей из 31. Тогда очередные
шесть записей помещаются без ожидания. IRQ может только освобождать
AY-слоты, поэтому устаревшее значение read index делает проверку строже.
При отказе `packet_pending=0`; обязательное чтение и начальная подготовка
остаются прежними. Прерывания разрешены во время всей проверки.

Помощник занимает 60 B в освобождённых `7C31..7C6C`, сразу после
AY-prefetch. Дополнительное вложение стека — 2 B. Память буферов, число
слотов, поток, номинальная сетка и частота AY не меняются.

### Такты Z80

В таблице учтены внешний CALL и два NOP вместо старого `LD A,1`, но
исключены тело/RET parser, общая запись pending, IRQ, ULA, ROM и диск.
Цена CALL/RET самого помощника включена. Каждая его инструкция сверена
с таблицей и исполнением в CPU-тесте.

| Путь | База | Опыт | Разность обвязки |
|---|---:|---:|---:|
| Чтение разрешено | 24 T + parser | 291 T + parser | +267 T |
| Нет завершённого слота | 24 T + parser | 66 T | +42 T, parser отложен |
| Недостаточно готовых байтов | 24 T + parser | 213 T | +189 T, parser отложен |
| Мало свободных AY-записей | 24 T + parser | 271 T | +247 T, parser отложен |

Это ограничение блокирующей работы, а не сокращение тактов самого parser.
Повтор реальных вызовов очереди сохранён в [CPU-отчёте](ready_packet_guard_cpu.json).
Затраты помощника и очереди приведены отдельно в [сводке](ready_packet_guard_summary.json).
Queue + ожидания полной AY-очереди: 289707284→289646116 T, −61168 T.
Сама новая проверка добавила 258552 T на всех выполненных попытках;
эти числа не включают обычные parser/рендер/IRQ и не являются полным CPU фильма.

## Полный результат

| Показатель | Диск 1: база → опыт | Диск 2 | Диск 3 |
|---|---:|---:|---:|
| fps | 8,278923→8,275546 | 7,976366→7,973422 | 7,874636→7,873682 |
| Поздние кадры по счётчику | 984→983 | 843→847 | 1251→1250 |
| Поздние actual OUT, допуск измерения 64 T | 1565→983 | 843→847 | 1251→1250 |
| Недогрузки AY | 83→87 | 343→346 | 473→475 |
| Интервалы вне резервного допуска | 118→127 | 244→243 | 299→318 |
| Разрешённые необязательные чтения / попытки | 258/628 | 169/414 | 6/34 |

Все 4221 кадр до EOF, 25326 точных AY-записей, 7501 сектор ровно один
раз, без retries, прогресс 100%, без debugger-записи RAM. Проверены
80 байтов каждого экрана. Потоки побайтно совпадают с базой; занято
2542/2543/2542 сектора. Cold boot на грязной RAM и смена дисков прошли
с mocked ROM; все три настоящие загрузки/воспроизведения — в Fuse.
Полного сравнения каждого пикселя нового Fuse, другого видео и физического
привода нет. Начальные фазы не выровнены: уменьшение числа поздних OUT
нельзя приписывать только предзагрузке.

11 тестов прошли: четыре слота, границы 4704/4705, AY 25/26, кольцевой
переход, сохранность очереди/стека, потребление IRQ на границах инструкций,
прежние AY и bootstrap. Первые ожидаемые суммы трёх путей были ошибочно
занижены на 1 T; исправлена арифметика теста после поинструкционной сверки.

**Решение:** общий темп не улучшился, недогрузок AY стало 908 вместо 899.
Сумма интервалов публикаций выросла 1855945989→1856513253 T, +567264 T.
Максимальные actual отклонения — 6665355/24888708/34035839 T;
восстановлено 0/3/2 серии по счётчику, последние не восстановились до EOF.
Оставить опцию выключенной. Более точная проверка фактической длины пакета
может разрешить больше чтений, но её выигрыш пока не измерен. Главный срок,
резервный допуск и непрерывный звук не пройдены. Корневой выпуск не заменять.

## Доказанная причина потери прерываний

Отдельный полный прогон базового диска 1 с `--trace-fields` обнаружил два
поля без входа IM2: физические поля 922 и 7885. В первом случае в начале
поля PC=`6094` (`LD HL,fast_irq`), IFF1=IFF2=0; около конца импульса
PC=`609A` (`EI`), прерывание так и не обслужено. Во втором случае начало
импульса попало на `LD (irq_vector),HL` при IFF=0.

Оба случая находятся в `disk_finish`, где после успешного прямого чтения
повторяются DI, настройка I/IM2 и вектора, EI. Последовательность занимает
58 T; после EI ещё одна инструкция выполняется до приёма IRQ. Видеокадр 59
публикуется на физическое поле позже, хотя `late_fields=0`: счётчик потерял
тот же IRQ. AY имеет 85 пропущенных полей между записями при 83 недогрузках.

[Аудит](audit_irq_fields.py), [результат базы](ready_packet_guard_irq_baseline.json)
и [архивы трасс](ready_packet_guard_evidence) сохраняют доказательства.
Следующий шаг: после **успешного прямого чтения** обходить повторную
настройку IM2, предварительно проверить I/IM/вектор на каждом возврате ROM.
Полный C=5 и fallback короткого чтения должны сохранить восстановление IRQ.
Это предложение ещё не реализовано в данном опыте; сроки нельзя исправлять
переносом начала расписания или скрытием пропущенных прерываний.

## Воспроизведение

Из `.worktree/ready-packet-guard`, Python/NumPy, `PYTHONPATH=toolkit`:

```powershell
python -m unittest toolkit.test_ready_packet_guard toolkit.test_audio_wait_prefetch toolkit.test_ay_interrupt toolkit.test_integrated_bootstrap
python toolkit/build_integrated_bootstrap.py --directory ../cached-huffman-byte/.tmp/three --raw-directory ../volume-huffman/.tmp/probe --states ../three-disk-quality/.tmp/no_credits/source/conversion.npz --zx0 ../audio-fidelity/.tmp/bin/zx0.exe --output .tmp/guard --report toolkit/ready_packet_guard_build.json --bank2-zx0 --audio-wait-prefetch --ready-packet-guard
python toolkit/verify_integrated_bootstrap.py --directory .tmp/guard --baseline-directory ../cached-huffman-byte/.tmp/three --raw-directory ../volume-huffman/.tmp/probe --report toolkit/ready_packet_guard_build.json
python toolkit/measure_integrated_bootstrap.py --fuse 'C:/Program Files (x86)/Fuse/fuse.exe' --directory .tmp/guard --raw-directory ../volume-huffman/.tmp/probe --states ../three-disk-quality/.tmp/no_credits/source/conversion.npz --output .tmp/guard-fuse --trace-pipeline --trace-queue-calls --trace-fields
python toolkit/replay_queue_calls.py --directory .tmp/guard --trace-directory .tmp/guard-fuse --output toolkit/ready_packet_guard_cpu.json
python toolkit/measure_fap3_fuse.py --fuse 'C:/Program Files (x86)/Fuse/fuse.exe' --trd ../transfer-cpu-profile/.tmp/prefetch/ZX-video-huffman-preview_part01.trd --metadata ../transfer-cpu-profile/.tmp/prefetch/ZX-video-huffman-preview_part01.json --raw ../volume-huffman/.tmp/probe/volume-1.raw --states ../three-disk-quality/.tmp/no_credits/source/conversion.npz --output .tmp/irqbase/part01.json --timeout 300 --trace-fields --trace-pipeline
python toolkit/audit_irq_fields.py --trace .tmp/irqbase/part01.json --metadata ../transfer-cpu-profile/.tmp/prefetch/ZX-video-huffman-preview_part01.json --output toolkit/ready_packet_guard_irq_baseline.json
python toolkit/summarize_ready_packet_guard.py --fuse .tmp/guard-fuse --directory .tmp/guard --irq-baseline .tmp/irqbase/part01.json
```

Последняя команда без параметров проверяет сохранённые архивы и пересчитывает сводку.
