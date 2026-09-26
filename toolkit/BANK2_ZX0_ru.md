# ZX0 в фиксированном bank 2

26 сентября 2026. База исходников `19942a9`, сравнение с реальными
интегрированными TRD `b94c9ed`. **Опыт завершён, требования выпуска ещё
не выполнены.** Размеры и сжатые байты прежние, разрешение и AY не менялись.

## Изменение и такты

[Генератор переноса](bank2_zx0.py) оставляет первые 35 байт resumable-входа
в `7C00..7C22`, переносит основной код и состояние (279 байт)
из `7C23..7D39` в `8DF2..8F08`. Это прежнее тело temporal-поправок,
уже обойдённое встроенным Huffman-кодом в bank 6. JP в `8DEF..8DF1`
и RET пустой маски в `8F09` сохранены. Дополнительных банков, переключений
и памяти нет. Приватный стек ZX0 остаётся в `7B70..7BDF`, bank 5.

Изменены абсолютные операнды внутри ZX0 и 22 внешние ссылки на каждый
том: очередь, producer, parser, fatal. Относительные смещения внутри
декодера прежние. Состояние и самомодифицируемые операнды переносим вместе
с кодом; сохранённые возвраты приватного стека формирует уже новый код.

Опкоды и пути инструкций прежние, поэтому цена по таблице Z80 не меняется:
CALL 17→17 T, JP 10→10 T, LD HL/(nn) 16→16 T, ED-обращения к DE 20→20 T;
у всех изменённых внешних операндов в отчёте сохранены абсолютные T и Δ0.
Все 378 реальных блоков, запросы по 256 байт: **201086097→201086097 T**.
Это другой график запросов, чем demand-decode реального плеера; число
нельзя выдавать за полный CPU плеера или вычитать из elapsed Fuse.
Детерминированная Δ самого переноса равна нулю при любом графике запросов.

Выигрыш ожидается от чтения инструкций/состояния без ожидания ULA.
Ни чистый ULA-выигрыш, ни физический дисковод отдельно не измерены.

Режим включается `--bank2-zx0` у экспериментального сборщика. Если inline
Huffman недоступен из-за размера таблиц, остаётся прежний ZX0. Без опции
пересборка всех трёх TRD побайтно совпала с `b94c9ed`.
`decoder_labels` описывает итоговую RAM; `inline_literals` и
`slot_queue_regions` сохраняют сведения предыдущих стадий генерации.
Итоговый перенос записан отдельно в `bank2_zx0`.

## Полное воспроизведение

Все три TRD проверены от самостоятельной загрузки до EOF в Fuse 1.9.0,
без установки кода через debugger. Базовая и новая фазы диска/IRQ не
синхронизированы: таблица показывает результат всего тракта.

| Показатель | Диск 1, было → стало | Диск 2 | Диск 3 |
|---|---:|---:|---:|
| Занято секторов | 2543→2542 | 2543→2543 | 2542→2542 |
| Видео, секторов | 2504→2504 | 2501→2501 | 2496→2496 |
| fps | 8,144320→8,172205 | 7,758621→7,830816 | 7,557598→7,643874 |
| Поздних кадров | 984→984 | 851→843 | 1253→1250 |
| Максимальное опоздание, поля | 226→191 | 576→499 | 825→728 |
| Недогрузок AY | 221→186 | 571→494 | 820→723 |
| Интервалов вне допуска | 294→290 | 362→354 | 505→468 |

Всего 4221 кадр, 25326 точных AY-записей, 7501 сектор прочитан ровно
по одному разу, retries=0, progress=100%. Сумма интервалов от первой
до последней публикации: **1908134283→1893385416 T**, −14748867 T,
**−0,772947%**. Disk read service 232465965→232512372 T, seek service
5187152→5188556 T; это elapsed с CPU, ROM, IRQ, ULA и контроллером,
а не время вращения в отдельности.

Максимальное реальное отклонение OUT: 13614337/35383092/51621031 T.
Восстановленных серий опозданий: 0/2/2. Последние серии 640..1623,
478..1296 и 55..1299 (нумерация от нуля внутри диска) не восстановились
до EOF. Все пропущенные сроки и реальные OUT сохранены в
[сводке](bank2_zx0_summary.json) и [исходных отчётах](bank2_zx0_evidence).
**Основной срок, резервный допуск и AY на каждом поле не пройдены.**

## Охват проверки и следующий шаг

- 12 тестов: точная раскладка, границы/слоты, паузы и продолжение,
  неверная длина входа, AY IRQ между инструкциями, fallback без записи RAM,
  прежний inline decoder и bootstrap.
- [Парный CPU-отчёт](bank2_zx0_cpu.json): все 378 блоков/3083375 байтов,
  проверка каждого префикса, входных/выходных границ и защищённой RAM.
- [Сборка](bank2_zx0_build.json): cold boot с загрязнённой RAM; переходы
  1→2→3, английский промпт и отказ неверному диску проверены с mocked ROM.
- [Проверка ссылок](bank2_zx0_verification.json): 844 операнда, в том числе
  84 относительных перехода на каждом томе; устаревших входов в ZX0 нет.
  Прежний bootstrap и установленный runtime сверены с исходным стендом;
  875 inline Huffman-байтов совпадают с полным CPU-моделированием кадров.
- В новом Fuse проверены 80 байтов каждого кадра. Полного сравнения
  каждого пикселя этого прогона и прогона на физическом Spectrum нет.
  Другой видеофайл целиком с новой опцией не проверен.

[Профиль всех кадров](bank2_zx0_profile.json) сравнивает стадии с полным
профилем `19942a9`. На томе 3 transfer уменьшился 215016→209370 T,
вся работа 466433→460812 T (129,97 мс) при бюджете 425448 T (120 мс).
1269 из 1300 пакетов всё ещё запрашиваются без полностью готового слота.
Готовых минимум за 1000 T до срока, но поздно показанных кадров нет.
Следующий приоритет — разложить transfer на CPU очереди/копирования/ZX0
и чтение диска при фактических запросах. Не считать весь empty-wait
простоем: внутри него идут полезная распаковка и I/O. Затем выбирать
сокращение пересылок и обвязки; дополнительная предзагрузка сама по себе
не устранит устойчивый недостаток скорости третьего тома.

Решение: сохранить перенос как измеренную опцию экспериментального
сборщика, продолжить ускорение. Корневые LFS-образы выпуска не заменены.

## Повторение

Из `.worktree/bank2-zx0`, с Python/NumPy и `PYTHONPATH=toolkit`:

```powershell
python -m unittest toolkit.test_bank2_zx0 toolkit.test_inline_literals toolkit.test_integrated_bootstrap
python toolkit/benchmark_bank2_zx0.py --directory ../integrated-bootstrap/.tmp/three --output toolkit/bank2_zx0_cpu.json
python toolkit/build_integrated_bootstrap.py --directory ../cached-huffman-byte/.tmp/three --raw-directory ../volume-huffman/.tmp/probe --states ../three-disk-quality/.tmp/no_credits/source/conversion.npz --zx0 ../audio-fidelity/.tmp/bin/zx0.exe --output .tmp/three --report toolkit/bank2_zx0_build.json --bank2-zx0
python toolkit/build_integrated_bootstrap.py --directory ../cached-huffman-byte/.tmp/three --raw-directory ../volume-huffman/.tmp/probe --states ../three-disk-quality/.tmp/no_credits/source/conversion.npz --zx0 ../audio-fidelity/.tmp/bin/zx0.exe --output .tmp/default --report .tmp/default_build.json
python toolkit/verify_integrated_bootstrap.py --directory .tmp/three --baseline-directory ../cached-huffman-byte/.tmp/three --raw-directory ../volume-huffman/.tmp/probe --report toolkit/bank2_zx0_build.json
python toolkit/verify_bank2_zx0.py --directory .tmp/three --raw-directory ../volume-huffman/.tmp/probe --default-directory .tmp/default --baseline-directory ../integrated-bootstrap/.tmp/three --output toolkit/bank2_zx0_verification.json
python toolkit/measure_integrated_bootstrap.py --fuse 'C:/Program Files (x86)/Fuse/fuse.exe' --directory .tmp/three --raw-directory ../volume-huffman/.tmp/probe --states ../three-disk-quality/.tmp/no_credits/source/conversion.npz --output .tmp/fuse --trace-pipeline
python toolkit/summarize_integrated_bootstrap.py --fresh .tmp/fuse --directory .tmp/three --build toolkit/bank2_zx0_build.json --baseline toolkit/integrated_bootstrap_evidence --evidence toolkit/bank2_zx0_evidence --output toolkit/bank2_zx0_summary.json
python toolkit/profile_bank2_zx0.py
```

Без повторного Fuse убрать `--fresh` и `--directory` у сводного скрипта:
он проверит SHA сохранённых архивов. Из корня репозитория передать полные
пути входных каталогов. Нормализация окончательных исходников до LF и
повторная сборка в `.tmp/final` дали те же TRD, что измеренный `.tmp/three`.
