# LZSA2 и ZX1 на одинаковом потоке FAP2

19 сентября 2026. Выполнен пункт плана
[LOW_COST_CODECS_RESEARCH_ru.md](LOW_COST_CODECS_RESEARCH_ru.md): реальный
замер компрессоров на одних данных. Полный FAP2 без титров: **3106401 байт**,
4221 кадр с прежними пикселями и AY, 380 независимых блоков по 8192 байта
(последний короче). SHA256:
`4ab750e4d93c2638bbbe6cc560ef4f99b1500f9babc53a69c7ec570c20652ecc`.

## Что такое LZSA2

[LZSA](https://github.com/emmanuel-marty/lzsa) — семейство сжатия без потерь
для простой распаковки на 8-битных CPU. Команды передают литералы или
ссылки на уже распакованные последовательности. В варианте LZSA2 длины
и смещения используют байты/полубайты; доступно повторение прежнего
смещения. Автор предоставляет Z80-декодеры. Это возможная замена внешнего
слоя ZX0, а не новый способ квантования изображения или синтеза AY.

[ZX1](https://github.com/einar-saukas/ZX1) — упрощённый родственник ZX0.
Заявленные авторами сравнения скорости не являются измерением нашего
банкового, порционного проигрывателя. В этом опыте скорость Z80 не измеряли.

## Полные результаты

| Кодек | Байты с 4-байтовыми заголовками | Разница с ZX0 | Секторы по 256 байт |
|---|---:|---:|---:|
| ZX0 optimal v2, прежний полный отчёт | 1935757 | 0 | 7562 |
| ZX1 v1.5 optimal | 1971445 | +35688 | 7701 |
| LZSA2 v1.4.1, raw, prefer-ratio | 2010361 | +74604 | 7853 |

В обоих новых опытах **0 блоков меньше ZX0**. Поэтому выбор минимального
размера между ZX0 и каждым новым кодеком оставляет те же 1935757 байт.
Stored-fallback тоже не улучшил новые результаты. Все 380 блоков каждого
формата распакованы авторским PC-декодером и побайтно совпали с оригиналом.
Это не независимый Z80-декодер и не проверка времени воспроизведения.

Предварительный бюджет трёх дискет 1937664 байта: ZX1 превышает его на
**33781**, LZSA2 на **72697**. Этот бюджет всё ещё требует подтверждения
готовой сборкой. Четырёхбайтовые заголовки здесь — одинаковый контейнерный
расход для сравнения; переключение кодеков в Z80 не реализовано.

**Решение:** не заменять весь поток на ZX1/LZSA2 в текущем варианте.
Скорость могла бы представлять интерес для отдельных блоков после
дополнительной экономии объёма, но ускорения здесь не доказано. Код
проигрывателя и TRD не изменены: **0 измеренных T экономии**.

## Источники инструментов и воспроизведение

- ZX1: `https://github.com/einar-saukas/ZX1`, commit
  `11e31cf91047562bb3cdedab1b34bb02ebdc8f83`; авторские `win/zx1.exe`
  и `win/dzx1.exe`, без `-q`.
- LZSA: `https://github.com/emmanuel-marty/lzsa`, commit
  `15ee2dfe118eeb8f7683ca44f64821c3a61ca1e5`; собран MSVC 14.51.36231
  в Visual Studio 2026 18.7.1, `/O2 /MT /DNDEBUG`. Исходники не менялись.
- SHA256 исполняемых файлов, точные флаги, SHA каждого исходного и сжатого
  блока записаны в `bulk_zx1_storage.json` и `bulk_lzsa2_storage.json`.
  Клонированные исходники, двоичные инструменты и кэш лежат в `.tmp`.
  Собственный скрипт сборки/измерений сохранён в Git.

```text
git clone https://github.com/einar-saukas/ZX1.git .tmp/codec_sources/zx1
git -C .tmp/codec_sources/zx1 checkout 11e31cf91047562bb3cdedab1b34bb02ebdc8f83
git clone https://github.com/emmanuel-marty/lzsa.git .tmp/codec_sources/lzsa
git -C .tmp/codec_sources/lzsa checkout 15ee2dfe118eeb8f7683ca44f64821c3a61ca1e5
toolkit\build_lzsa_windows.cmd "C:\Program Files\Microsoft Visual Studio\18\Community" "ABSOLUTE_SOURCE_DIRECTORY" "ABSOLUTE_BUILD_DIRECTORY"
python toolkit/probe_cli_codec_storage.py --raw .tmp/bulk_frame/stream.raw --baseline toolkit/bulk_frame_zx0.json --codec lzsa2 --encoder .tmp/codec_sources/lzsa_build/lzsa.exe --decoder .tmp/codec_sources/lzsa_build/lzsa.exe --revision 15ee2dfe118eeb8f7683ca44f64821c3a61ca1e5 --cache .tmp/codec_storage/lzsa2 --output toolkit/bulk_lzsa2_storage.json
python toolkit/probe_cli_codec_storage.py --raw .tmp/bulk_frame/stream.raw --baseline toolkit/bulk_frame_zx0.json --codec zx1 --encoder .tmp/codec_sources/zx1/win/zx1.exe --decoder .tmp/codec_sources/zx1/win/dzx1.exe --revision 11e31cf91047562bb3cdedab1b34bb02ebdc8f83 --cache .tmp/codec_storage/zx1 --output toolkit/bulk_zx1_storage.json
```

В команде сборки заменить два параметра каталогов абсолютными путями
`.tmp/codec_sources/lzsa` и `.tmp/codec_sources/lzsa_build` своего checkout.
