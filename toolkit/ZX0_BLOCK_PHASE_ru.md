# Эксперимент: смещение границ блоков ZX0

Промежуточный снимок от 25 сентября 2026, база `5bad85f`.
Пакеты FAP3, AY, таблицы и начальные native maps независимых томов
остаются прежними. Меняется только положение границ внешних блоков
ZX0, каждый до 8192 байт. Обычный builder не переключён на эксперимент.

## Сохранённый прогресс

`zx0_block_phase_checkpoint.json` — стабильная копия частичного отчёта,
сделанная для коммита по запросу пользователя. `complete=false`:
сохранены шесть завершённых вариантов первого тома (1624 кадра).
Проверенные смещения: 0, 1024, 2048, 3072, 4096 и 4813.
Лучшее в этом снимке: 640778 вместо 641005 байт (−227 байт).
Число логических секторов прежнее: 2504. Все блоки проверены обратной
распаковкой; пакеты побайтово совпадают. Контрольное смещение 0 также
побайтово воспроизводит исходный сжатый поток из TRD.

Перебор остальных вариантов и томов на момент снимка продолжался.
Рабочий `zx0_block_phase_probe.json` обновляется процессом и не входит
в этот коммит. Программа повторного запуска использует кеши по SHA,
проверяя распаковку каждого полученного блока.

## Воспроизведение

Команды из worktree `.worktree/zx0-block-phase` в PowerShell; пути
относятся к существующим локальным артефактам предыдущих экспериментов.
В новом checkout необходимо предварительно восстановить эти артефакты.
Исходные raw/состояния и компрессор сверяются по хешам в отчёте.

```powershell
$python = 'C:/Users/rudol/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$env:PYTHONPATH = 'toolkit;C:/Work/ZX-video/.worktree/audio-fidelity/.tmp/python_packages'
$env:OPENBLAS_NUM_THREADS = '1'
& $python -m unittest discover -s toolkit -p test_zx0_block_phase.py -v
& $python toolkit/probe_zx0_block_phase.py `
  --raw-directory ../volume-huffman/.tmp/probe `
  --directory ../register-fragments/.tmp/three `
  --states ../three-disk-quality/.tmp/no_credits/source/conversion.npz `
  --zx0 ../audio-fidelity/.tmp/bin/zx0.exe `
  --output .tmp/probe `
  --report .tmp/zx0_block_phase_probe.json `
  --read-cache ../volume-huffman/.tmp/probe/zx0 `
  --read-cache ../fragment-cost-selection/.tmp/probe/zx0 `
  --jobs 4
```

## Что ещё требуется проверить

Завершить перебор всех трёх томов, затем проверить реальную раскладку
дискет с независимым bootstrap. Для выбранных потоков измерить
CPU T-states распаковки/очереди отдельно от ROM и физической задержки
диска; выполнить полное проигрывание с проверкой публикаций и AY.
Новых opcodes нет, но распределение команд ZX0 и число обращений
к блочным границам могут изменить время исполнения. Пока нет
подтверждения ни ускорения, ни точных 25/3 кадра/с, ни нового выпуска.
