# Переобучение Хаффмана после выбора готовых фрагментов

18–19 сентября 2026. База `6c5c818`: весь age3, 4971 кадр, прежние
пиксели/атрибуты, разрешение, выбранные плитки и AY 50 Гц. Обучение
исключает поправки тех плиток, которые передаются целиком или напрямую.
Сравнены прежнее распределение по контекстам (`fixed`) и новое объединение
в 16 контекстов (`clustered16`). Атрибуты имеют отдельную таблицу.

## Фактический размер

| Поток | Исходные байты | Optimal ZX0 8192 + заголовки | Разница к своей базе |
|---|---:|---:|---:|
| FHF1 база | 3031081 | 2043807 | — |
| FHF1 fixed | 3026940 | 2040815 | −2992 |
| FHF1 clustered16 | 3026816 | **2040549** | **−3258** |
| FHC1 база | 2994638 | 2051444 | — |
| FHC1 fixed | 2990216 | 2046844 | −4600 |
| FHC1 clustered16 | 2989727 | 2046168 | −5276 |

Все четыре варианта независимо восстановили все кадры. Все **1471 блок**
ZX0 проверены отдельным декодером. Лучший FHF1 требует вместе с AY
**2118245 байт**, недостача до предварительного бюджета трёх TRD —
**180581**. Новая раскладка выпускных томов и кода сюда не включена.

Минимизация битов увеличила число дорогих значений с кодом длиннее 8 бит:
FHF1 **59056→72642**, FHC1 **55406→68133** в вариантах clustered16.
У FHF1 кодовые биты **4915019→4881419**; выигрыш всего 33600 бит.
Таблицы помещаются в прежний банк: FHF1 clustered16 **15830** байт вместе
со сдвигами вместо 16208. Бинарный декодер у всех четырёх вариантов
проверен на точное совпадение с соответствующей базой. Структура горячего
пути не меняется; время меняется из-за другого распределения кодов.

## Полный CPU-прогон лучшего FHF1 clustered16

| Измерение | База FHF1 | Новые таблицы | Разница |
|---|---:|---:|---:|
| Восстановление, T | 1127839894 | 1133996268 | +6156374 |
| Максимум кадра, T | 308635 | 319497 | +10862 |
| ZX0 всего потока, T | 157425317 | 157317276 | −108041 |
| Две стадии, T | 1285265211 | 1291313544 | **+6048333** |

Все 4971 кадр, 641 группа и 370 ZX0-блоков этого варианта проверены
исполнением Z80. Худший кадр 4088, кадров реконструкции >425448 — 0.
Стадии, кроме Хаффмана и выравнивания fast-плиток, имеют прежние такты
на каждом кадре. Хаффман +6157164 T; выравнивание −790 T.
Максимум блока ZX0 674461 T. Длительность блока не равна задержке кадра.

Для остальных трёх вариантов полного CPU-прогона не заявляется.
Метаданные, окно, paging, развёртка экрана, IRQ/ULA/ROM и диск исключены
из CPU-сумм. Размер и отдельно измеренная CPU-работа не доказывают плавность.

**Решение:** не заменять базовые таблицы этим вариантом: экономия
3258 байт сопровождается ростом CPU и не закрывает существенный дефицит
места. Сохранить результаты и возможность совместного выбора таблиц по
размеру и тактам. Следующий опыт — раздельные каналы готовых фрагментов
и Хаффмана; PLAYER/TRD в этом опыте прежние.

## Воспроизведение

Из рабочего дерева `three-disk-quality`, с зависимостями в PYTHONPATH:

```text
python toolkit/retune_fragment_contexts.py --input .tmp/unrolled_fast/target_300000.raw --selection .tmp/unrolled_fast/target_300000.npz --motion-cache .tmp/spatial_predictors_cost/iteration_1.npz --cache .tmp/retuned_contexts_fhf --output toolkit/retuned_fragment_contexts_fhf.json
python toolkit/retune_fragment_contexts.py --input .tmp/raw_intra/target_300000.raw --selection .tmp/raw_intra/target_300000.npz --motion-cache .tmp/spatial_predictors_cost/iteration_1.npz --cache .tmp/retuned_contexts_fhc --output toolkit/retuned_fragment_contexts_fhc.json
python toolkit/probe_zx0_storage.py --raw .tmp/retuned_contexts_fhf/clustered16.raw --block-bytes 8192 --zx0 ../audio-fidelity/.tmp/bin/zx0.exe --cache .tmp/retuned_contexts_fhf/zx0_clustered16 --output toolkit/retuned_contexts_fhf_clustered16_zx0.json --jobs 2
python toolkit/benchmark_spatial_tiles.py --fhs .tmp/retuned_contexts_fhf/clustered16.raw --motion-cache .tmp/spatial_predictors_cost/iteration_1.npz --states-sha256 4b9e90d22df2809a70c1cb09890de0a9bb0a23d1b1e357b3f6c29ff830cc9c3b --extended --fast-fragments --unrolled-motion --baseline-commit 6c5c818 --output toolkit/retuned_contexts_fhf_clustered16_cpu.json
python toolkit/benchmark_zx0_storage.py --raw .tmp/retuned_contexts_fhf/clustered16.raw --storage-report toolkit/retuned_contexts_fhf_clustered16_zx0.json --cache .tmp/retuned_contexts_fhf/zx0_clustered16/optimal --output toolkit/retuned_contexts_fhf_clustered16_zx0_cpu.json --baseline-commit 6c5c818
python toolkit/summarize_fragment_tables.py --cpu-report toolkit/retuned_contexts_fhf_clustered16_cpu.json --output toolkit/retuned_fragment_contexts_summary.json
```

Для остальных ZX0-вариантов в команде заменяются `fhf/fhc` и
`fixed/clustered16`; настройки блока/кодера одинаковы.
[Обучение](retune_fragment_contexts.py),
[сводка с проверкой SHA/блоков/кода](retuned_fragment_contexts_summary.json),
[её скрипт](summarize_fragment_tables.py),
[CPU кадров](retuned_contexts_fhf_clustered16_cpu.json),
[CPU ZX0](retuned_contexts_fhf_clustered16_zx0_cpu.json).
