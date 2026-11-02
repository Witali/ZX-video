// Upstream module: lang/ru.js
var ZX_Lang = {
    ERR_IMAGE_FORMAT_NOT_SUPPORTED: 'Неподдерживаемый формат образа.',
    ERR_FILENAME_NOT_SPECIFIED: 'Не указано имя файла.',
    ERR_UNEXPECTED_END_OF_STREAM: 'Неожиданное окончание потока данных.',
    ERR_ROM_LOADING_ERROR: 'Ошибка загрузки ПЗУ.',
    ERR_INCORRECT_RAM_ADDRESS: 'Некорректный адрес ОЗУ.',
    ERR_SNAPSHOT_FORMAT_NOT_SUPPORTED: 'Неподдерживамый формат снимка.',
    ERR_SNAPSHOT_FILE_LENGTH_NOT_SUPPORTED: 'Неподдерживаемая длина файла снимка.',
    ERR_Z80_SNAPSHOT_SAMROM_NOT_SUPPORTED: 'Снимки SamRom не поддерживаются.',
    ERR_Z80_SNAPSHOT_VERSION_NOT_SUPPORTED: 'Эта версия снимка Z80 не поддерживается. Длина дополнительного заголовка: ',
    ERR_Z80_SNAPSHOT_HARDWARE_NOT_SUPPORTED: 'В настоящее время это оборудование не поддерживается.',
    ERR_Z80_SNAPSHOT_INTERFACE_I_ROM_NOT_SUPPORTED: 'В настоящее время ПЗУ Interface I не поддерживается.',
    ERR_Z80_SNAPSHOT_MGT_ROM_NOT_SUPPORTED: 'В настоящее время ПЗУ MGT не поддерживается.',
    ERR_Z80_SNAPSHOT_MULTIFACE_ROM_NOT_SUPPORTED: 'В настоящее время ПЗУ Multiface не поддерживается.',
    ERR_Z80_SNAPSHOT_RAM_0000_3FFF_NOT_SUPPORTED: 'В настоящее время ОЗУ в области #0000..#3FFF не поддерживается.',
    ERR_Z80_SNAPSHOT_ROM_LOADING_NOT_SUPPORTED: 'В настоящее время загрузка ПЗУ не поддерживается.',
    ERR_Z80_SNAPSHOT_INVALID_RAM_PAGE_FOR_48K: 'Страница памяти не поддерживается для снимка в 48Кб. Код страницы: ',
    ERR_CANNOT_CREATE_CANVAS: 'Не удается создать холст вывода изображения. Вы можете попробовать выбрать другой метод вывода.',
    ERR_WRONG_DATA_BLOCK_SIZE: 'Неверный размер блока данных.',
    ERR_TRD_IMAGE_WRONG_DATA: 'Неверные данные образа TRD.',
    ERR_TRD_IMAGE_UNKNOWN_TYPE: 'Неизвестный тип образа TRD.',
    ERR_SCL_IMAGE_WRONG_DATA: 'Неверные данные образа SCL.',
    ERR_SCL_IMAGE_TOO_MANY_FILES: 'Слишком много файлов для образа SCL.',
    ERR_SCL_IMAGE_WRONG_CRC: 'Неверная контрольная сумма образа SCL. Возможно, образ поврежден.',
    ERR_FDI_IMAGE_WRONG_DATA: 'Неверные данные образа FDI.',
    ERR_TD0_IMAGE_WRONG_DATA: 'Неверные данные образа TD0.',
    ERR_TD0_IMAGE_WRONG_HEADER_CRC: 'Неверная контрольная сумма заголовка образа TD0.',
    ERR_TD0_IMAGE_WRONG_COMMENT_HEADER_CRC: 'Неверная контрольная сумма заголовка комментария образа TD0.',
    ERR_TD0_IMAGE_WRONG_TRACK_HEADER_CRC: 'Неверная контрольная сумма заголовка дорожки образа TD0.',
    ERR_TD0_IMAGE_WRONG_SECTOR_DATA_CRC: 'Неверная контрольная сумма данных сектора образа TD0.',
    ERR_UDI_IMAGE_WRONG_IMAGE_DATA: 'Неверные данные образа UDI.',
    ERR_UDI_IMAGE_VERSION_NOT_SUPPORTED: 'В настоящее время поддерживаются только образы UDI версии 1.0.',
    ERR_UDI_IMAGE_WRONG_CRC: 'Неверная контрольная сумма образа UDI. Возможно, образ поврежден.',
    ERR_DSK_IMAGE_WRONG_DATA: 'Неверные данные образа DSK.',
    ERR_DSK_IMAGE_WRITING_UNSUPPORTED: 'Сохранение в формат DSK не поддерживается.',
    ERR_ROM_WRONG_SIZE: 'Некорректный размер ПЗУ.',
    ERR_AUDIO_NOT_SUPPORTED: 'Звук не поддерживается браузером.',
    ERR_AUDIO_INVALID_RENDERER: 'Указан некорректный способ вывода звука.',
    ERR_AUDIO_INVALID_STATE: 'Некорректное состояние контекста аудио.',
    ERR_LOCAL_STORAGE_NOT_SUPPORTED: 'Локальное хранилище не поддерживается браузером.',
    ERR_LOCAL_STORAGE_HAS_NO_IMAGE: 'Локальное хранилище не содержит образ.',
    ERR_LOCAL_STORAGE_HAS_INVALID_IMAGE: 'Кэш содержит некорректные данные образа.',
    ERR_TAPE_FORMAT_NOT_SUPPORTED : 'Неподдерживаемый формат файла магнитной ленты.',
    ERR_TR_EMPTY: 'Магнитофон пуст.',
    ERR_TR_UNEXPECTED_STREAM_END: 'Неожиданное окончание потока данных.',
    ERR_TR_NOT_SUSPENDED: 'Невозможно возобновить воспроизведение при текущем статусе.',
    ERR_TAPE_BLOCK_OUT_OF_RANGE: 'Индекс блока выходит за допустимые пределы.',
    ERR_TAPE_WRONG_TZX_HEADER: 'Неверный заголовок TZX.',

    VOL_BEEPER: 'Бипер',
    VOL_PSG: 'AY/YM',

    CID_TITLE: 'Укажите параметры нового диска',
    CID_HEAD_COUNT: 'Количество сторон',
    CID_CYL_COUNT: 'Количество дорожек',
    CID_TRDOS_FORMAT: 'Форматирование TR-DOS',
    CID_CREATE_BUTTON: 'Создать',
    CID_CANCEL_BUTTON: 'Отмена',
    CID_INVALID_HEAD_COUNT: 'Количество сторон указано некорректно.',
    CID_INVALID_CYL_COUNT: 'Количество дорожек указано некорректно.',

    SID_TITLE: 'Выберите целевой формат образа',
    SID_FORMAT: 'Формат',
    SID_SAVE: 'Сохранить',
    SID_CANCEL: 'Отмена',
    SID_FORMAT_NOT_SELECTED: 'Не выбран формат образа для сохранения.',

    SB_TITLE: 'Выберите образ TRD, FDI, SCL, UDI, TD0',
    SB_UNEXPECTED_SERVER_RESONSE: 'Неожиданный ответ от сервера.',

    ZB_TITLE: 'Выберите образ',
    ZB_NO_SUITABLE_IMAGES: 'Архив не содержит поддерживаемых образов.',

    DRIVE_EMPTY: '<пусто>',
    DRIVE_MENU_OPEN_FORM_SERVER: 'открыть с сервера...',
    DRIVE_MENU_OPEN_FORM_LOCAL: 'открыть с диска...',
    DRIVE_MENU_SAVE_TO_LOCAL: 'сохранить на диск...',
    DRIVE_MENU_CREATE: 'создать...',
    DRIVE_MENU_EJECT: 'извлечь',
    DRIVE_IS_EMPTY: 'В приводе отсутствует диск.',

    TR_EMPTY: '<пусто>',
    TR_MENU_OPEN_EXTERNAL: 'открыть с ZX-Art...',
    TR_MENU_OPEN_FROM_LOCAL: 'открыть с диска...',
    TR_MENU_EJECT: 'извлечь',
    TR_MENU_SHOW_TAPE_INFO: 'информация о ленте...',
    TR_PLAY: 'Воспроизвести',
    TR_PAUSE: 'Пауза',
    TR_RESUME: 'Возобновить',
    TR_STOP: 'Остановить',

    TOOLBAR_RESET: 'Сброс',
    TOOLBAR_LOAD_SNAPSHOT: 'Загрузить снимок',
    TOOLBAR_SAVE_SNAPSHOT: 'Сохранить снимок',
    TOOLBAR_SETTINGS: 'Настройки',
    TOOLBAR_SOUND: 'Звук',
    TOOLBAR_FULLSCREEN: 'Полноэкранный режим',

    SETTINGS_TITLE: 'Настройки',
    SETTINGS_RESET_BUTTON: 'Сбросить все настройки',
    SETTINGS_APPLY_BUTTON: 'Применить',
    SETTINGS_CANCEL_BUTTON: 'Отмена',
    SETTINGS_SECTION_BUS: 'Шина',
    SETTINGS_SECTION_MEMORY: 'Память',
    SETTINGS_SECTION_DISPLAY: 'Дисплей',
    SETTINGS_SECTION_AUDIO: 'Звук',
    SETTINGS_SECTION_CONTROL: 'Управление',
    SETTINGS_SECTION_TAPE: 'Лента',
    SETTINGS_SECTION_MISC: 'Другое',
    SETTINGS_TSTATES_PER_INTRQ: 'Тактов за прерывание (норма)',
    SETTINGS_TSTATES_PER_INTRQ_TURBO: 'Тактов за прерывание (турбо)',
    SETTINGS_INTRQ_PERIOD: 'Период прерываний (мс)',
    SETTINGS_TURBO_MODE: 'Турбо-режим',
    SETTINGS_EXTENDED_MEMORY: 'Расширенная память',
    SETTINGS_EXTENDED_MEMORY_OFF: 'выключена',
    SETTINGS_EXTENDED_MEMORY_PENTAGON: 'Pentagon 512 КБ',
    SETTINGS_SEMICOLORS: 'Включить полутона',
    SETTINGS_RENDERING: 'Отрисовка',
    SETTINGS_RENDERING_PUTIMAGEDATA: 'метод putImageData',
    SETTINGS_RENDERING_DRAWIMAGE: 'метод drawImage',
    SETTINGS_RENDERING_WEBGL: 'WebGL',
    SETTINGS_SCALE_TYPE: 'Метод масштабирования',
    SETTINGS_SCALE_TYPE_PRE: 'Предварительное',
    SETTINGS_SCALE_TYPE_RENDERING: 'При отрисовке',
    SETTINGS_SCALE_TYPE_POST: 'Последующее',
    SETTINGS_SCALE: 'Масштаб',
    SETTINGS_RAF: 'Отрисовка по событию кадра анимации',
    SETTINGS_AUDIO_RENDERING: 'Способ вывода аудио',
    SETTINGS_AUDIO_RENDERING_UNDEFINED: 'не определен',
    SETTINGS_AUDIO_RENDERING_WLN: 'выделенный поток (WorkletNode)',
    SETTINGS_AUDIO_RENDERING_SPN: 'основной поток (ScriptProcessorNode)',
    SETTINGS_AUDIO_BUFFER_SIZE: 'Размер выходного буфера',
    SETTINGS_AUDIO_BUFFER_SIZE_AUTO: 'автоматически',
    SETTINGS_AUDIO_BUFFER_SIZE_SAMPLES: 'сэмплов',
    SETTINGS_BEEPER: 'Бипер',
    SETTINGS_BEEPER_VOLUME: 'Громкость бипера',
    SETTINGS_PSG: 'Музыкальный сопроцессор',
    SETTINGS_PSG_OFF: 'выключен',
    SETTINGS_PSG_AY_3_891X: 'AY-3-891x',
    SETTINGS_PSG_YM2149: 'YM2149',
    SETTINGS_PSG_TURBO_SOUND: 'Turbo Sound',
    SETTINGS_PSG_TURBO_SOUND_OFF: 'выключен',
    SETTINGS_PSG_TURBO_SOUND_AUTO: 'автоматически',
    SETTINGS_PSG_TURBO_SOUND_NEDO_PC: 'NedoPC',
    SETTINGS_PSG_TURBO_SOUND_POWER_OF_SOUND: 'Power of Sound',
    SETTINGS_PSG_TURBO_SOUND_QUADRO_AY: 'Quadro-AY',
    SETTINGS_PSG_CHANNEL_LAYOUT: 'Распределение каналов',
    SETTINGS_PSG_CLOCK: 'Тактовая частота муз.сопроцессора',
    SETTINGS_PSG_VOLUME: 'Громкость музыкального сопроцессора',
    SETTINGS_PSG_PACKET_SIZE: 'Размер передаваемого в буфер пакета',
    SETTINGS_MOUSE_CAPTURE: 'Захват мыши при клике по дисплею',
    SETTINGS_MOUSE_ENABLE_ACCELERATION: 'Ускорение указателя ОС',
    SETTINGS_MOUSE_SENSITIVITY: 'Чувствительность',
    SETTINGS_GAMEPADS: 'Игровые контролеры',
    SETTINGS_GAMEPADS_DEVICE: 'Устройство',
    SETTINGS_GAMEPADS_MAP: 'Сопоставление',
    SETTINGS_THREADING: 'Многопоточность',
    SETTINGS_THREADING_OFF: 'выключена',
    SETTINGS_THREADING_ON: 'включена',
    SETTINGS_TAPE_PRE_PAUSE_COUNTER_PULSE: 'Контр-импульс перед паузой (мс)',
    SETTINGS_TAPE_DEFAULT_PAUSE: 'Пауза по умолчанию (мс)',
    SETTINGS_TAPE_AUTOPLAY_ON_STANDARD_LOADER: 'Автопроигрывание при стандартном загрузчике',
    SETTINGS_TAPE_AUTOPLAY_ON_CUSTOM_LOADER: 'Автопроигрывание при нестандартном загрузчике (возможны фальш-старты)',
    SETTINGS_TAPE_PAUSE_AFTER_DATA_BLOCK: 'Пауза после каждого блока данных',
    SETTINGS_TAPE_PAUSE_ON_LONG_BLOCK_POST_PAUSE: 'Пауза при длинной пост-паузе блока',
    SETTINGS_TAPE_PAUSE_ON_ZERO_BLOCK_POST_PAUSE: 'Пауза при нулевой пост-паузе блока',
    SETTINGS_TAPE_LONG_PAUSE_DURATION: 'Длительность длинной пост-паузы',
    SETTINGS_TAPE_BOOST_FACTOR: 'Коэффициент ускорения при проигрывании',
    SETTINGS_TAPE_PAUSE_OPT_NO: 'нет',
    SETTINGS_TAPE_PAUSE_OPT_SIMPLE_TAPES: 'только для простых лент',
    SETTINGS_TAPE_PAUSE_OPT_ALL_TAPES: 'для всех лент',
    SETTINGS_TAPE_PAUSE_NOTE: '* паузы не добавляются в группы блоков',
    SETTINGS_TAPE_GLOBAL_AUTOPLAY: 'Автовоспроизведение',
    SETTINGS_TAPE_GLOBAL_AUTOSTOP: 'Автопауза',
    SETTINGS_OPT_ON: 'вкл',
    SETTINGS_OPT_OFF: 'выкл',

    TID_PROP_FILENAME: 'Имя файла',
    TID_PROP_FORMAT: 'Форма',
    TID_PROP_FORMAT_VERSION: 'Версия формата',
    TID_PROP_SIZE: 'Размер',
    TID_PROP_BLOCKS: 'Блоки',
    TID_PROP_INDEX: 'Индекс',
    TID_PROP_ID: 'ИД',
    TID_PROP_INFO: 'Информация',
    TID_PROP_DESCRIPTION: 'Описание',
    TID_PROP_MESSAGE: 'Сообщение',
    TID_PROP_NAME: 'Имя',
    TID_PROP_PAUSE: 'Пауза',
    TID_PROP_POST_PAUSE: 'Пост-пауза',
    TID_PROP_DATA_TYPE: 'Тип данных',
    TID_PROP_DATA_LENGTH: 'Длина данных',
    TID_PROP_PARAM1: 'Параметр 1',
    TID_PROP_PARAM2: 'Параметр 2',
    TID_PROP_HARDWARE: 'Оборудование',
    TID_PROP_HARDWARE_TYPE: 'Тип оборудования',
    TID_PROP_HARDWARE_ID: 'ИД оборудования',
    TID_PROP_HARDWARE_RELATION: 'Отношение',
    TID_UNIT_MS: 'мс',
    TID_PROMPT_GO_TO_THIS_BLOCK: 'Переключиться на этот блок',
    TID_NO_INFO: 'Информация отсутствует',
    TID_BTN_APPLY: 'Применить',
    TID_BTN_CANCEL: 'Закрыть',
    TID_TITLE: 'Информация о ленте',

    TMD_PROP_NUM: 'Номер',
    TMD_PROP_DESCRIPTION: 'Описание',
    TMP_PROP_BLOCK: 'Блок',
    TMD_BTN_APPLY: 'Выбрать',
    TMD_BTN_CANCEL: 'Закрыть',
    TMD_TITLE: 'Меню ленты',

    TMSGD_BTN_CANCEL: 'Закрыть',
    TMSGD_TITLE: 'Сообщение ленты',

    TPINF_PROP_FULL_TITLE: 'Полное название',
    TPINF_PROP_PUBLISHER: 'Издатель ПО',
    TPINF_PROP_AUTHORS: 'Автор(ы)',
    TPINF_PROP_YEAR: 'Год публикации',
    TPINF_PROP_LANGUANGE: 'Язык',
    TPINF_PROP_PROD_TYPE: 'Тип игры/утилиты',
    TPINF_PROP_PRICE: 'Цена',
    TPINF_PROP_LOADER: 'Загрузчик/защита',
    TPINF_PROP_ORIGIN: 'Происхождение',
    TPINF_PROP_COMMENTS: 'Комментарии',
    TPINF_HW_COMPUTER: 'Компьютеры',
    TPINF_HW_EXT_STORAGE: 'Внешние устройства хранения',
    TPINF_HW_ROMRAM: 'Дополнения ПЗУ/ОЗУ',
    TPINF_HW_SOUND: 'Звуковые устройства',
    TPINF_HW_JOYSTICK: 'Джойстики',
    TPINF_HW_MOUSE: 'Мыши',
    TPINF_HW_CONTROLLER: 'Другие контролеры',
    TPINF_HW_SERIAL_PORT: 'Последовательный порты',
    TPINF_HW_PARALLEL_PORT: 'Параллельные порты',
    TPINF_HW_PRINTER: 'Принтеры',
    TPINF_HW_MODEM: 'Модемы',
    TPINF_HW_DIGITIZER: 'Дигитайзеры',
    TPINF_HW_NETWORK_ADAPTER: 'Сетевые адаптеры',
    TPINF_HW_KEYBOARD: 'Клавиатуры',
    TPINF_HW_AD_DA: 'АЦП/ЦАП',
    TPINF_HW_EPROM_PROGRAMMER: 'Программаторы EPROM',
    TPINF_HW_GRAPHICS: 'Графика',
    TPINF_HWREL_RUNS_AND_MAY_USE: 'Запускается и может использовать возможности',
    TPINF_HWREL_RUNS_AND_USES: 'Запускается и использует возможности',
    TPINF_HWREL_RUNS_AND_DOES_NOT_USE: 'Запускается и не использует возможности',
    TPINF_HWREL_DOES_NOT_RUN: 'Не запускается',
    TPINF_HDR_PROGRAM: 'Программа',
    TPINF_HDR_NUMBER_ARRAY: 'Массив чисел',
    TPINF_HDR_CHARACTER_ARRAY: 'Массив символов',
    TPINF_HDR_CODE: 'Код',
    TPINF_BLK_STANDARD: 'Стандарт',
    TPINF_BLK_TURBO: 'Турбо',
    TPINF_BLK_PURE_TONE: 'Чистый тон',
    TPINF_BLK_PULSE_SEQUENCE: 'Последовательность импульсов',
    TPINF_BLK_PURE_DATA: 'Чистые данные',
    TPINF_BLK_DIRECT_RECORDING: 'Прямая запись',
    TPINF_BLK_COMMODORE_64_STANDARD: 'Commodore 64 стандарт',
    TPINF_BLK_COMMODORE_64_TURBO: 'Commodore 64 турбо',
    TPINF_BLK_CSW: 'CSW',
    TPINF_BLK_GENERALIZED_DATA: 'Обобщенные данные',
    TPINF_BLK_PAUSE: 'Пауза',
    TPINF_BLK_GROUP_START: 'Начало группы',
    TPINF_BLK_GROUP_END: 'Окончание группы',
    TPINF_BLK_JUMP: 'Прыжок',
    TPINF_BLK_LOOP_START: 'Начало цикла',
    TPINF_BLK_LOOP_END: 'Окончание цикла',
    TPINF_BLK_CALL: 'Вызов',
    TPINF_BLK_RETURN: 'Возврат',
    TPINF_BLK_SELECTION_MENU: 'Меню выбора',
    TPINF_BLK_STOP_48: 'Остановка, если 48K',
    TPINF_BLK_LEVEL: 'Указанный уровень',
    TPINF_BLK_TEXT_DESCRIPTION: 'Текстовое описание',
    TPINF_BLK_MESSAGE: 'Сообщение',
    TPINF_BLK_ARCHIVE_INFO: 'Архивная информация',
    TPINF_BLK_HARDWARE_TYPE: 'Тип оборудования',
    TPINF_BLK_EMULATION_INFO: 'Информация об эмуляции',
    TPINF_BLK_CUSTOM_INFO: 'Пользовательская информация',
    TPINF_BLK_SNAPSHOT: 'Данные снимка',
    TPINF_BLK_GLUE: 'Склейка',

    WORKSPACE_LOG: 'Журнал',

    RESET_MODE_SOS128: 'SOS 128',
    RESET_MODE_SOS48: 'SOS 48',
    RESET_MODE_TRDOS: 'TR-DOS',
    RESET_MODE_EXT: 'Расширение',

    AUDIO_WORKLET_JS: '/js/spectrum_audio.js',
    WORKER_JS: '/js/spectrum_hw.js'
};

// Upstream module: spectrum/common.js
var OPT_TSTATES_PER_INTRQ = "TSTATES_PER_INTRQ";
var OPT_INTRQ_PERIOD = "INTRQ_PERIOD";
var OPT_EXTENDED_MEMORY = "EXTENDED_MEMORY";
var OPT_SEMICOLORS = "SEMICOLORS";
var OPT_RENDERING_PARAMS = "RENDERING_PARAMS";
var OPT_TAPE_BOOST_FACTOR = "TAPE_BOOST_FACTOR";

var VAL_EXTENDED_MEMORY_OFF = 0;
var VAL_EXTENDED_MEMORY_PENTAGON = 1;

var VAL_SCALE_METHOD_UNDEFINED = 0;
var VAL_SCALE_METHOD_PRE = 1; // scaling samples
var VAL_SCALE_METHOD_RENDER = 2;
var VAL_SCALE_METHOD_POST = 3; // scaling by CSS

var VAL_RENDERER_UNDEFINED = 0;
var VAL_RENDERER_PUT_IMAGE_DATA = 1;
var VAL_RENDERER_DRAW_IMAGE = 2;
var VAL_RENDERER_WEB_GL = 3;

var VAL_AUDIO_RENDERER_UNDEFINED = 0;
var VAL_AUDIO_RENDERER_SPN = 1;
var VAL_AUDIO_RENDERER_WLN = 2;

var VAL_PSG_OFF = 0;
var VAL_PSG_AY_3_891X = 1;
var VAL_PSG_YM_2149 = 2;

var VAL_TS_OFF = 0;
var VAL_TS_NEDO_PC = 1;
var VAL_TS_POWER_OF_SOUND = 2;
var VAL_TS_QUADRO_AY = 3;
var VAL_TS_AUTO = 4;

var VAL_CHANNELS_ABC = 0;
var VAL_CHANNELS_ACB = 1;

var VAL_THREADING_SINGLE = 0;
var VAL_THREADING_MULTIPLE = 1;

var VAL_TR_EMPTY = 0;
var VAL_TR_INITIALIZED = 1;
var VAL_TR_SUSPENDED = 2;
var VAL_TR_PLAYBACK = 3;
var VAL_TR_FINISHED = 4;

var VAL_TAPACT_NO = 1;
var VAL_TAPACT_SIMPLE_TAPES = 2;
var VAL_TAPACT_ALL_TAPES = 3;

var RESET_MODE_SOS128 = 0;
var RESET_MODE_SOS48 = 1;
var RESET_MODE_TRDOS = 2;
var RESET_MODE_EXT = 3;

var GAMEPAD_BUTTONS = {
	RC_BOTTOM: 0,
	RC_RIGHT: 1,
	RC_LEFT: 2,
	RC_TOP: 3,
	F_TOP_LEFT: 4,
	F_TOP_RIGHT: 5,
	F_BOTTOM_LEFT: 6,
	F_BOTTOM_RIGHT: 7,
	CC_LEFT: 8,
	CC_RIGHT: 9,
	LC_STICK: 10,
	RC_STICK: 11,
	LC_TOP: 12,
	LC_BOTTOM: 13,
	LC_LEFT: 14,
	LC_RIGHT: 15,
	CC_CENTER: 16
};

var GAMEPAD_AXES = {
	LC_HOR: 0,
	LC_VER: 1,
	RC_HOR: 2,
	RC_VER: 3
};

var KEMPSTON_KEY = {
	RIGHT: 0,
	LEFT: 1,
	DOWN: 2,
	UP: 3,
	FIRE: 4,
	EXT1: 5,
	EXT2: 6,
	EXT3: 7
};

var GAMEPAD_MAP_DEVICE = {
	KEMPSTON: 0,
	KEYBOARD: 1
};

function JSONSerializer() {
	this.__type = 'JSONSerializer';
}
Object.assign(JSONSerializer, {
	__types: {},
	registerType: function (name, type) {
		this.__types[name] = type;
	},
	serialize: function (obj) {
		return JSON.stringify(obj);
	},
	deserialize: function (value) {
		return JSON.parse(value, function (key, value) {
			var Type = value && value.__type && JSONSerializer.__types[value.__type];
			if (Type) {
				var obj = new Type();
				Object.assign(obj, value);
				return obj;
			}
			return value;
		});
	}
});

function GamepadMap() {
	this.__type = 'GamepadMap';
	this.name = 'CUSTOM';
	this.buttons = [];
	this.axes = [];
	this.threshold = 0.5;
}
Object.assign(GamepadMap.prototype, {
	tryCreateButtonEntry: function (buttonCount, button, key) {
		if (button < buttonCount)
			this.buttons[button] = key;
	},
	tryCreateAxisEntry: function (axisCount, axis, key1, key2) {
		if (axis < axisCount)
			this.axes[axis] = [key1, key2];
	}
});
Object.assign(GamepadMap, {
	createKempstonMap: function (buttonCount, axisCount) {
		var map = new GamepadMap();
		map.name = 'KEMPSTON';
		map.threshold = 0.5;
		map.buttons = Array(buttonCount).fill(null);
		map.axes = Array(axisCount).fill(null);
		map.tryCreateButtonEntry(buttonCount, GAMEPAD_BUTTONS.LC_LEFT, 'KEMPSTON:LEFT');
		map.tryCreateButtonEntry(buttonCount, GAMEPAD_BUTTONS.LC_RIGHT,'KEMPSTON:RIGHT');
		map.tryCreateButtonEntry(buttonCount, GAMEPAD_BUTTONS.LC_TOP, 'KEMPSTON:UP');
		map.tryCreateButtonEntry(buttonCount, GAMEPAD_BUTTONS.LC_BOTTOM, 'KEMPSTON:DOWN');
		map.tryCreateButtonEntry(buttonCount, GAMEPAD_BUTTONS.F_TOP_LEFT, 'KEMPSTON:LEFT');
		map.tryCreateButtonEntry(buttonCount, GAMEPAD_BUTTONS.F_TOP_RIGHT, 'KEMPSTON:RIGHT');
		map.tryCreateButtonEntry(buttonCount, GAMEPAD_BUTTONS.RC_BOTTOM, 'KEMPSTON:FIRE');
		map.tryCreateButtonEntry(buttonCount, GAMEPAD_BUTTONS.RC_RIGHT, 'KEMPSTON:EXT1');
		map.tryCreateButtonEntry(buttonCount, GAMEPAD_BUTTONS.RC_LEFT, 'KEMPSTON:EXT2');
		map.tryCreateButtonEntry(buttonCount, GAMEPAD_BUTTONS.RC_TOP, 'KEMPSTON:EXT3');
		map.tryCreateAxisEntry(axisCount, GAMEPAD_AXES.LC_HOR, 'KEMPSTON:LEFT', 'KEMPSTON:RIGHT');
		map.tryCreateAxisEntry(axisCount, GAMEPAD_AXES.LC_VER, 'KEMPSTON:UP', 'KEMPSTON:DOWN');
		return map;
	},
	createSinclair1Map: function (buttonCount, axisCount) {
		var map = new GamepadMap();
		map.name = 'SINCLAIR1';
		map.threshold = 0.5;
		map.buttons = Array(buttonCount).fill(null);
		map.axes = Array(axisCount).fill(null);
		map.tryCreateButtonEntry(buttonCount, GAMEPAD_BUTTONS.LC_LEFT, 'KEYBOARD:4,4');
		map.tryCreateButtonEntry(buttonCount, GAMEPAD_BUTTONS.LC_RIGHT, 'KEYBOARD:4,3');
		map.tryCreateButtonEntry(buttonCount, GAMEPAD_BUTTONS.LC_TOP, 'KEYBOARD:4,1');
		map.tryCreateButtonEntry(buttonCount, GAMEPAD_BUTTONS.LC_BOTTOM, 'KEYBOARD:4,2');
		map.tryCreateButtonEntry(buttonCount, GAMEPAD_BUTTONS.F_TOP_LEFT, 'KEYBOARD:4,4');
		map.tryCreateButtonEntry(buttonCount, GAMEPAD_BUTTONS.F_TOP_RIGHT, 'KEYBOARD:4,3');
		map.tryCreateButtonEntry(buttonCount, GAMEPAD_BUTTONS.RC_BOTTOM, 'KEYBOARD:4,0');
		map.tryCreateAxisEntry(axisCount, GAMEPAD_AXES.LC_HOR, 'KEYBOARD:4,4', 'KEYBOARD:4,3');
		map.tryCreateAxisEntry(axisCount, GAMEPAD_AXES.LC_VER, 'KEYBOARD:4,1', 'KEYBOARD:4,2');
		return map;
	},
	createSinclair2Map: function (buttonCount, axisCount) {
		var map = new GamepadMap();
		map.name = 'SINCLAIR2';
		map.threshold = 0.5;
		map.buttons = Array(buttonCount).fill(null);
		map.axes = Array(axisCount).fill(null);
		map.tryCreateButtonEntry(buttonCount, GAMEPAD_BUTTONS.LC_LEFT, 'KEYBOARD:3,0');
		map.tryCreateButtonEntry(buttonCount, GAMEPAD_BUTTONS.LC_RIGHT, 'KEYBOARD:3,1');
		map.tryCreateButtonEntry(buttonCount, GAMEPAD_BUTTONS.LC_TOP, 'KEYBOARD:3,3');
		map.tryCreateButtonEntry(buttonCount, GAMEPAD_BUTTONS.LC_BOTTOM, 'KEYBOARD:3,2');
		map.tryCreateButtonEntry(buttonCount, GAMEPAD_BUTTONS.F_TOP_RIGHT, 'KEYBOARD:3,1');
		map.tryCreateButtonEntry(buttonCount, GAMEPAD_BUTTONS.RC_BOTTOM, 'KEYBOARD:3,4');
		map.tryCreateAxisEntry(axisCount, GAMEPAD_AXES.LC_HOR, 'KEYBOARD:3,0', 'KEYBOARD:3,1');
		map.tryCreateAxisEntry(axisCount, GAMEPAD_AXES.LC_VER, 'KEYBOARD:3,3', 'KEYBOARD:3,2');
		return map;
	},
	createCursorMap: function (buttonCount, axisCount) {
		var map = new GamepadMap();
		map.name = 'CURSOR';
		map.threshold = 0.5;
		map.buttons = Array(buttonCount).fill(null);
		map.axes = Array(axisCount).fill(null);
		map.tryCreateButtonEntry(buttonCount, GAMEPAD_BUTTONS.LC_LEFT, 'KEYBOARD:3,4');
		map.tryCreateButtonEntry(buttonCount, GAMEPAD_BUTTONS.LC_RIGHT, 'KEYBOARD:4,2');
		map.tryCreateButtonEntry(buttonCount, GAMEPAD_BUTTONS.LC_TOP, 'KEYBOARD:4,3');
		map.tryCreateButtonEntry(buttonCount, GAMEPAD_BUTTONS.LC_BOTTOM, 'KEYBOARD:4,4');
		map.tryCreateButtonEntry(buttonCount, GAMEPAD_BUTTONS.F_TOP_LEFT, 'KEYBOARD:3,4');
		map.tryCreateButtonEntry(buttonCount, GAMEPAD_BUTTONS.F_TOP_RIGHT, 'KEYBOARD:4,2');
		map.tryCreateButtonEntry(buttonCount, GAMEPAD_BUTTONS.RC_BOTTOM, 'KEYBOARD:4,0');
		map.tryCreateAxisEntry(axisCount, GAMEPAD_AXES.LC_HOR, 'KEYBOARD:3,4', 'KEYBOARD:4,2');
		map.tryCreateAxisEntry(axisCount, GAMEPAD_AXES.LC_VER, 'KEYBOARD:4,3', 'KEYBOARD:4,4');
		return map;
	},
	createQAOPMMap: function (buttonCount, axisCount) {
		var map = new GamepadMap();
		map.name = 'QAOPM';
		map.threshold = 0.5;
		map.buttons = Array(buttonCount).fill(null);
		map.axes = Array(axisCount).fill(null);
		map.tryCreateButtonEntry(buttonCount, GAMEPAD_BUTTONS.LC_LEFT, 'KEYBOARD:5,1');
		map.tryCreateButtonEntry(buttonCount, GAMEPAD_BUTTONS.LC_RIGHT, 'KEYBOARD:5,0');
		map.tryCreateButtonEntry(buttonCount, GAMEPAD_BUTTONS.LC_TOP, 'KEYBOARD:2,0');
		map.tryCreateButtonEntry(buttonCount, GAMEPAD_BUTTONS.LC_BOTTOM, 'KEYBOARD:1,0');
		map.tryCreateButtonEntry(buttonCount, GAMEPAD_BUTTONS.F_TOP_LEFT, 'KEYBOARD:5,1');
		map.tryCreateButtonEntry(buttonCount, GAMEPAD_BUTTONS.F_TOP_RIGHT, 'KEYBOARD:5,0');
		map.tryCreateButtonEntry(buttonCount, GAMEPAD_BUTTONS.RC_BOTTOM, 'KEYBOARD:7,2');
		map.tryCreateAxisEntry(axisCount, GAMEPAD_AXES.LC_HOR, 'KEYBOARD:5,1', 'KEYBOARD:5,0');
		map.tryCreateAxisEntry(axisCount, GAMEPAD_AXES.LC_VER, 'KEYBOARD:2,0', 'KEYBOARD:1,0');
		return map;
	},
	createQAOPSpaceMap: function (buttonCount, axisCount) {
		var map = new GamepadMap();
		map.name = 'QAOPSPACE';
		map.threshold = 0.5;
		map.buttons = Array(buttonCount).fill(null);
		map.axes = Array(axisCount).fill(null);
		map.tryCreateButtonEntry(buttonCount, GAMEPAD_BUTTONS.LC_LEFT, 'KEYBOARD:5,1');
		map.tryCreateButtonEntry(buttonCount, GAMEPAD_BUTTONS.LC_RIGHT, 'KEYBOARD:5,0');
		map.tryCreateButtonEntry(buttonCount, GAMEPAD_BUTTONS.LC_TOP, 'KEYBOARD:2,0');
		map.tryCreateButtonEntry(buttonCount, GAMEPAD_BUTTONS.LC_BOTTOM, 'KEYBOARD:1,0');
		map.tryCreateButtonEntry(buttonCount, GAMEPAD_BUTTONS.F_TOP_LEFT, 'KEYBOARD:5,1');
		map.tryCreateButtonEntry(buttonCount, GAMEPAD_BUTTONS.F_TOP_RIGHT, 'KEYBOARD:5,0');
		map.tryCreateButtonEntry(buttonCount, GAMEPAD_BUTTONS.RC_BOTTOM, 'KEYBOARD:7,0');
		map.tryCreateAxisEntry(axisCount, GAMEPAD_AXES.LC_HOR, 'KEYBOARD:5,1', 'KEYBOARD:5,0');
		map.tryCreateAxisEntry(axisCount, GAMEPAD_AXES.LC_VER, 'KEYBOARD:2,0', 'KEYBOARD:1,0');
		return map;
	}
});
JSONSerializer.registerType('GamepadMap', GamepadMap);

var DiskImageFormat = {
	FDI: 'FDI',
	TRD: 'TRD',
	SCL: 'SCL',
	TD0: 'TD0',
	UDI: 'UDI',
	DSK: 'DSK',

	getFromFileName: function(filename) {
		var match = (/^[^\\\/]*\.(TRD|FDI|SCL|TD0|UDI|DSK)$/i).exec(filename);
		if (!match)
			throw new Error(ZX_Lang.ERR_IMAGE_FORMAT_NOT_SUPPORTED);
		return match[1].toUpperCase();
	}
};

var TapeFormat = {
	TAP: 'TAP',
	SPC: 'SPC',
	STA: 'STA',
	LTP: 'LTP',
	ZXT: 'ZXT',
	TZX: 'TZX',

	getFromFileName: function(filename) {
		var match = (/^[^\\\/]*\.(TAP|SPC|STA|LTP|ZXT|TZX)$/i).exec(filename);
		if (!match)
			throw new Error(ZX_Lang.ERR_TAPE_FORMAT_NOT_SUPPORTED);
		return match[1].toUpperCase();
	}
}

function extend(Child, Parent) {
	var F = function() { };
	F.prototype = Parent.prototype;
	Child.prototype = new F();
	Child.prototype.constructor = Child;
	Child.superclass = Parent.prototype;
}

function ZX_Event() {
	var _self = this;
	var _handlers = [];
	var _index = -1;

	function compile(args) {
		if (_index < 0) {
			_index = ZX_Event.next++;
		}
		var codeLines = [];
		ZX_Event.g[_index] = {};
		for (var i = 0; i < _handlers.length; i++) {
			ZX_Event.g[_index][i] = _handlers[i];
			codeLines.push('ZX_Event.g[' + _index + '][' + i + '](args);')
		}
		_self.emit = new Function('args', codeLines.join('\n'));
		_self.emit(args);
	}

	function isEmpty() {
		return _handlers.length === 0;
	}

	this.emit = compile;
	this.pub = {
		subscribe: function (handler) {
			if (!(typeof handler === 'function'))
				throw new Error('Argument error: Handler must be a function.');
	
			_handlers.push(handler);
			_self.emit = compile;
		},
		
		unsubscribe: function (handler) {
			for (var i = 0; i < _handlers.length; i++) {
				if (_handlers[i] === handler) {
					_handlers.splice(i, 1);
					_self.emit = compile;
					break;
				}
			}
		}
	},
	this.isEmpty = isEmpty;
}
ZX_Event.g = {};
ZX_Event.next = 0;

function stringToBytes( str ) {
  	var ch;
  	var stack;
  	var bytes = [];
  	var len = str.length;
  	for (var i = 0; i < len; i++ ) {
	    ch = str.charCodeAt(i);  // get char  
	    stack = [];                 // set up "stack" 
	    do { 
	      stack.push( ch & 0xff );  // push byte to stack 
	      ch = ch >> 8;          // shift value down by 1 byte 
	    }   
	    while ( ch ); 
	    // add stack contents to result 
	    // done because chars have "wrong" endianness 
	    while ( stack.length ) {
	    	bytes.push( stack.pop() );
	    }
	} 
	// return an array of bytes 
	return bytes;
}

function base64Encode( data ) {
	var abc = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
	var res = '';

	var i = 0;
	while ( i < data.length ) {
		var count = 0;
		var buf = 0;

		buf |= ( data[i] << 16 );
		count += 2;
		i++;

		if ( i < data.length ) {
			buf |= ( data[i] << 8 );
			count += 1;
			i++;

			if ( i < data.length ) {
				buf |= ( data[i] << 0 );
				count += 1;
				i++;
			}
		}

		for ( var c = 0; c < count; c++ ) {
			res += abc.charAt(( buf >> (( 3 - c ) * 6 )) & 0x3f );
		}
	}

	res += '=';

	return res;
}

function base64Decode( str ) {
	var abc = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
	var res = [];

	var buf;
	var stage = 0;
	var i = 0;
	while ( i < str.length ) {
		var ch = str.charAt(i);
		var bits = abc.indexOf(ch);
		if ( bits == -1 ) {
			break;
		}

		switch ( stage ) {
			case 0: buf = bits; break;
			case 1: res.push(( buf << 2 ) | ( bits >> 4 )); buf = ( bits & 0x0f ); break;
			case 2: res.push(( buf << 4 ) | ( bits >> 2 )); buf = ( bits & 0x03 ); break;
			case 3: res.push(( buf << 6 ) | ( bits >> 0 )); break;
		}

		stage = ( stage + 1 ) & 3;
		i++;
	}

	return res;
}

function getDateTimeString(timeStamp) {
	var dt = new Date(timeStamp);
	return (
		dt.getFullYear() 
		+ '.' + ('0' + (dt.getMonth() + 1)).substr(-2)
		+ '.' + ('0' + dt.getDate()).substr(-2)
		+ ' ' + ('0' + dt.getHours()).substr(-2)
		+ ':' + ('0' + dt.getMinutes()).substr(-2)
		+ ':' + ('0' + dt.getSeconds()).substr(-2)
	);
}

function getTimeString(timeStamp) {
	var dt = new Date(timeStamp);
	return (
		('0' + dt.getHours()).substr(-2)
		+ ':' + ('0' + dt.getMinutes()).substr(-2)
		+ ':' + ('0' + dt.getSeconds()).substr(-2)
	);
}

function getErrorOutput() {
	if (!window.ZXContext) {
		window.ZXContext = {};
	}
	if (!window.errorOutput) {
		window.errorOutput = [];
	}
	return window.errorOutput;
}

function renderErrors() {
	var errorOutput = getErrorOutput();
	var errorsDiv = document.getElementById('errors');
	var errorsListDiv = document.getElementById('errorList');
	if (errorsDiv && errorsListDiv) {
		var fragment = document.createDocumentFragment();
		for ( var i = 0; i < errorOutput.length; i++ ) {
			if (errorOutput[i].rendered)
				continue;
			var record = document.createElement('div');
			var recordTimestamp = document.createElement('span');
			var recordMessage = document.createElement('span');
			recordTimestamp.textContent = getTimeString(errorOutput[i].timeStamp),
			recordMessage.textContent = errorOutput[i].error;
			record.classList.add('error');
			recordTimestamp.classList.add('timestamp');
			recordMessage.classList.add('message');
			record.appendChild(recordTimestamp);
			record.appendChild(recordMessage);
			fragment.appendChild(record);
			errorOutput[i].rendered = true;
		}
		errorsListDiv.appendChild(fragment);
		if (!errorsDiv.classList.contains('-expanded')) {
			errorsDiv.classList.add('-expanded');
		}
		errorsListDiv.scrollTop = errorsListDiv.scrollHeight;
	}
	else {
		var lastError = errorOutput.length > 0 ? errorOutput[errorOutput.length - 1] : null;
		alert(lastError);
	}
}

function handleError(error) {
	if (typeof window !== 'undefined') {
		var errorOutput = getErrorOutput();
		errorOutput.push({
			timeStamp: Date.now(),
			error: error,
			rendered: false
		});
		if (errorOutput.length > 100) {
			errorOutput.splice(0, errorOutput.length - 100);
		}
		window.console && console.log && console.log(error);
		renderErrors();
	}
	else throw error;
}

function doRequest(options) {
	return new Promise(function (resolve, reject) {
		var req = new XMLHttpRequest();
		req.onreadystatechange = function () {
			if (req.readyState === XMLHttpRequest.DONE) {
				if (req.status === 200) {
					var response = req.response;
					// HACK for IE11
					if (options.responseType === 'json' && typeof response === 'string') {
						response = JSON.parse(response);
					}
					resolve(response);
				}
				else 
					reject(req.statusText);
			}
		}
		req.onerror = function (event) {
			reject('Unspecified error.');
		}
		req.open(options.method || 'GET', options.url, !options.sync);
		// 'responseType' and 'timeout' properties should be set after calling 'open' method.
		// Otherwise, 'Invalid state error' is produced in IE11.
		req.responseType = options.responseType || '';
		req.send(options.data || undefined);
	});
}

function loadLocalFile(fileinput) {
	return new Promise(function (resolve, reject) {
		try {
			if (!fileinput)
				throw new Error('A file input element is not specified.');
			if (typeof File !== 'undefined' && typeof FileReader !== 'undefined') {
				// загрузка с диска напрямую
				var reader = new FileReader();
				reader.onload = function(e) { 
					var data = stringToBytes(e ? e.target.result : reader.content);
					resolve(data); 
				}
				reader.onerror = function(e) { 
					reject(e); 
				}
				reader.readAsBinaryString(fileinput.files[0]);
			}
			else {
				// загрузка с диска через сервер
				if (!fileinput.name) {
					fileinput.name = 'clientFile';
				}
				var iframe = document.createElement('iframe');
				iframe.id = 'file_load_frame';
				iframe.name = 'file_load_frame';
				iframe.style.display = 'none';

				var form = document.createElement('form');
				form.action = '/get_base64.php?input=' + encodeURIComponent(fileinput.name);
				form.method = 'POST';
				form.enctype = 'multipart/form-data';
				form.target = 'file_load_frame';
				form.appendChild(fileinput);

				iframe.addEventListener('load', function (e) {
					if (!iframe.contentWindow.location.host)
						return;
					var base64 = (iframe.contentDocument.documentElement.textContent || '').replace(/^\s+|\s+$/g, '');
					var data = base64Decode(base64);
					iframe.remove();
					form.remove();
					resolve(data);
				});
				iframe.addEventListener('error', function (e) {
					reject(e);
				});

				document.body.appendChild(iframe);
				document.body.appendChild(form);
				form.submit();
			}
		}
		catch (error) {
			reject(error);
		}
	});
}

function loadServerFile(filename) {
	return new Promise(function (resolve, reject) {
		if (!filename) {
			reject(ZX_Lang.ERR_FILENAME_NOT_SPECIFIED);
			return;
		}
		var typeMatch = (/\.([^\.\\\/]+)$/).exec(filename);
		var type = typeMatch && typeMatch[1] || '';

		doRequest({
			url: '/get_base64.php?type=' + encodeURIComponent(type) + '&name=' + encodeURIComponent(filename),
			responseType: 'text'
		}).then(function (base64_data) {
			var data = base64Decode(base64_data);
			resolve(data);
		}).catch(function (error) {
			reject(error);
		});
	});
}

function downloadText(text, filename) {
	text = text || '';
	filename = filename || 'data.txt';
	var data = new Array(text.length);
	for ( var i = 0; i < text.length; i++ ) {
		data[i] = text.charCodeAt(i);
	}
	downloadBinaryData(data, filename);
}

function downloadBinaryData(data, filename) {
	filename = filename || 'data.bin';
	if (window.URL && URL.createObjectURL && window.Blob) {
		var typedData = new Uint8Array(data);
		var file = new Blob([typedData], { type: 'application/octet-stream' });
		if (window.navigator.msSaveBlob) {
			// works in IE11
			window.navigator.msSaveBlob(file, filename);
		}
		else {
			// works in other browsers
			var link = document.createElement('a');
			link.href = URL.createObjectURL(file);
			link.download = filename;
			link.click();
			URL.revokeObjectURL(link.href);
		}
	}
	else {
		var base64_data = base64Encode(data);
		var action_url = 'get_bin.php?input=data&name=' + filename;
		var $form = $('<form action="' + action_url + '" method="post" target="_blank" style="display: none;" />').appendTo(document.body);
		var $i_data = $('<input type="hidden" name="data" />').appendTo($form);
		$i_data.val(base64_data);
		$form.submit();
	}
}

function isWebGLSupported() {
	try { 
		if (!!document.createElement('canvas').getContext('webgl'))
			return true;
	} catch (e) { }
	try {
		if (!!document.createElement('canvas').getContext('experimental-webgl'))
			return true;
	} catch (e) { }
	return false;
}

function isAudioContextSupported() {
	return !!(typeof AudioContext !== 'undefined' || typeof webkitAudioContext !== 'undefined' || typeof audioContext !== 'undefined');
}

function areWebWorkersSupported() {
	return typeof Worker !== 'undefined' && !isIE11();
}

function isAudioWorkletNodeSupported() {
	return typeof AudioWorkletNode !== 'undefined';
}

function isScriptProcessorNodeSupported() {
	return typeof ScriptProcessorNode !== 'undefined';
}

function isIE11() {
	return typeof MSInputMethodContext !== 'undefined' && (typeof document === 'undefined' || !!document.documentMode);
}

function CRC16GEN(poly, init) {
	this._init = init;
	this._poly = poly;
	this._value = init;

	this.get_value = function () {
		return this._value;
	}
	this.reset = function () {
		this._value = this._init;
	}
	this.preset = function(value) {
		this._value = value & 0xFFFF;
	}
	this.add = function (next) {
		this._value ^= ( next << 8 );
		for ( var i = 0; i < 8; i++ ) {
			this._value = (( this._value & 0x8000 ) ? (( this._value << 1 ) ^ this._poly ) : ( this._value << 1 )) & 0xFFFF;
		}
	}
	this.addArray = function (arr, begin, length) {
		if (typeof begin === 'undefined') {
			begin = 0;
		}
		var end = arr.length;
		if (typeof length !== 'undefined') {
			end = begin + length;
		}
		while (begin < end) {
			this.add(arr[begin++]);
		}
	}
}
CRC16GEN.poly_1021 = function() { return new CRC16GEN(0x1021, 0xFFFF); }
CRC16GEN.poly_A097 = function() { return new CRC16GEN(0xA097, 0x0000); }

function CRC32GEN(poly, init) {
	this._init = init;
	this._poly = poly;
	this._value = init;

	this.get_value = function () {
		return this._value;
	}
	this.reset = function () {
		this._value = this._init;
	}
	this.preset = function(value) {
		this._value = value & 0xFFFFFFFF;
	}
	this.add = function (next) {
		this._value ^= -1 ^ next;
		for ( var i = 0; i < 8; i++ ) {
			var temp = -(this._value & 1);
			this._value >>= 1;
			this._value ^= this._poly & temp;
		}
		this._value ^= -1;
	}
	this.addArray = function (arr, begin, length) {
		if (typeof begin === 'undefined') {
			begin = 0;
		}
		var end = arr.length;
		if (typeof length !== 'undefined') {
			end = begin + length;
		}
		while (begin < end) {
			this.add(arr[begin++]);
		}
	}
}
CRC32GEN.poly_edb88320 = function() { return new CRC32GEN(0xEDB88320, 0xFFFFFFFF); }

function CRC16TD() {
	// CRC16 TELEDISK
	// Poly: 0xA097

	this.value = 0x0000;
	this.add = function (next) {
		this.value ^= ( next << 8 );
		for ( var i = 0; i < 8; i++ ) {
			this.value = (( this.value & 0x8000 ) ? (( this.value << 1 ) ^ 0xA097 ) : ( this.value << 1 )) & 0xFFFF;
		}
	}
	this.addArray = function (arr, begin, length) {
		if (typeof begin === 'undefined') {
			begin = 0;
		}
		var end = arr.length;
		if (typeof length !== 'undefined') {
			end = begin + length;
		}
		while (begin < end) {
			this.add(arr[begin++]);
		}
	}
}

function CRC16() {
	// CRC16 CCITT
	// Poly: 0x1021		x^16 + x^12 + x^5 + 1

	this.value = 0xFFFF;
	this.add = function (next) {
		this.value = ((this.value << 8) ^ CRC16.table[(this.value >> 8) ^ (next & 0xFF)]) & 0xFFFF;
	}
	this.addArray = function (arr, begin, length) {
		if (typeof begin === 'undefined') {
			begin = 0;
		}
		var end = arr.length;
		if (typeof length !== 'undefined') {
			end = begin + length;
		}
		while (begin < end) {
			this.add(arr[begin++]);
		}
	}
}
CRC16.table = [
	0x0000, 0x1021, 0x2042, 0x3063, 0x4084, 0x50A5, 0x60C6, 0x70E7, 0x8108, 0x9129, 0xA14A, 0xB16B, 0xC18C, 0xD1AD, 0xE1CE, 0xF1EF,
	0x1231, 0x0210, 0x3273, 0x2252, 0x52B5, 0x4294, 0x72F7, 0x62D6, 0x9339, 0x8318, 0xB37B, 0xA35A, 0xD3BD, 0xC39C, 0xF3FF, 0xE3DE,
	0x2462, 0x3443, 0x0420, 0x1401, 0x64E6, 0x74C7, 0x44A4, 0x5485, 0xA56A, 0xB54B, 0x8528, 0x9509, 0xE5EE, 0xF5CF, 0xC5AC, 0xD58D,
	0x3653, 0x2672, 0x1611, 0x0630, 0x76D7, 0x66F6, 0x5695, 0x46B4, 0xB75B, 0xA77A, 0x9719, 0x8738, 0xF7DF, 0xE7FE, 0xD79D, 0xC7BC,
	0x48C4, 0x58E5, 0x6886, 0x78A7, 0x0840, 0x1861, 0x2802, 0x3823, 0xC9CC, 0xD9ED, 0xE98E, 0xF9AF, 0x8948, 0x9969, 0xA90A, 0xB92B,
	0x5AF5, 0x4AD4, 0x7AB7, 0x6A96, 0x1A71, 0x0A50, 0x3A33, 0x2A12, 0xDBFD, 0xCBDC, 0xFBBF, 0xEB9E, 0x9B79, 0x8B58, 0xBB3B, 0xAB1A,
	0x6CA6, 0x7C87, 0x4CE4, 0x5CC5, 0x2C22, 0x3C03, 0x0C60, 0x1C41, 0xEDAE, 0xFD8F, 0xCDEC, 0xDDCD, 0xAD2A, 0xBD0B, 0x8D68, 0x9D49,
	0x7E97, 0x6EB6, 0x5ED5, 0x4EF4, 0x3E13, 0x2E32, 0x1E51, 0x0E70, 0xFF9F, 0xEFBE, 0xDFDD, 0xCFFC, 0xBF1B, 0xAF3A, 0x9F59, 0x8F78,
	0x9188, 0x81A9, 0xB1CA, 0xA1EB, 0xD10C, 0xC12D, 0xF14E, 0xE16F, 0x1080, 0x00A1, 0x30C2, 0x20E3, 0x5004, 0x4025, 0x7046, 0x6067,
	0x83B9, 0x9398, 0xA3FB, 0xB3DA, 0xC33D, 0xD31C, 0xE37F, 0xF35E, 0x02B1, 0x1290, 0x22F3, 0x32D2, 0x4235, 0x5214, 0x6277, 0x7256,
	0xB5EA, 0xA5CB, 0x95A8, 0x8589, 0xF56E, 0xE54F, 0xD52C, 0xC50D, 0x34E2, 0x24C3, 0x14A0, 0x0481, 0x7466, 0x6447, 0x5424, 0x4405,
	0xA7DB, 0xB7FA, 0x8799, 0x97B8, 0xE75F, 0xF77E, 0xC71D, 0xD73C, 0x26D3, 0x36F2, 0x0691, 0x16B0, 0x6657, 0x7676, 0x4615, 0x5634,
	0xD94C, 0xC96D, 0xF90E, 0xE92F, 0x99C8, 0x89E9, 0xB98A, 0xA9AB, 0x5844, 0x4865, 0x7806, 0x6827, 0x18C0, 0x08E1, 0x3882, 0x28A3,
	0xCB7D, 0xDB5C, 0xEB3F, 0xFB1E, 0x8BF9, 0x9BD8, 0xABBB, 0xBB9A, 0x4A75, 0x5A54, 0x6A37, 0x7A16, 0x0AF1, 0x1AD0, 0x2AB3, 0x3A92,
	0xFD2E, 0xED0F, 0xDD6C, 0xCD4D, 0xBDAA, 0xAD8B, 0x9DE8, 0x8DC9, 0x7C26, 0x6C07, 0x5C64, 0x4C45, 0x3CA2, 0x2C83, 0x1CE0, 0x0CC1,
	0xEF1F, 0xFF3E, 0xCF5D, 0xDF7C, 0xAF9B, 0xBFBA, 0x8FD9, 0x9FF8, 0x6E17, 0x7E36, 0x4E55, 0x5E74, 0x2E93, 0x3EB2, 0x0ED1, 0x1EF0
];


var SeekOrigin = {
	begin: 0,
	current: 1,
	end: 2
};
function MemoryStream(data) {
	var _position = 0;

	this.get_buffer = function () {
		return data;
	}
	this.get_position = function () {
		return _position;
	}
	this.get_length = function () {
		return data.length;
	}
	this.seek = function (offset, origin) {
		offset = offset !== undefined ? offset : 0;
		origin = origin !== undefined ? origin : SeekOrigin.begin;
		var basePosition;
		switch (origin) {
			case SeekOrigin.current: basePosition = _position; break;
			case SeekOrigin.end: basePosition = data.length; break;
			default: basePosition = 0; break;
		}
		var position = basePosition + offset;
		while (position < 0 && data.length > 0) position += data.length;
		if (position < 0) position = 0;
		if (position > data.length) position = data.length;
		_position = position;
	}
	this.write = function (value) {
		if (_position < data.length) {
			data[_position++] = value;
		}
		else {
			data.push(value);
			_position++;
		}
	}
	this.read = function () {
		if (_position < data.length) {
			return data[_position++];
		}
		else {
			return -1;
		}
	}
	this.writeMultiple = function (elements) {
		for (var i = 0; i < elements.length; i++, _position++) {
			if (_position < data.length) {
				data[_position] = elements[i];
			}
			else {
				data.push(elements[i]);
			}
		}
	}
	this.readMultuple = function (count) {
		var begin = _position;
		var end = _position + count;
		if (end > data.length) {
			end = data.length;
		}
		_position = end;
		return data.slice(begin, end);
	}
}

function BitReader(data, bitCount) {
	var _position = 0;
	var _bit = 0;
	var _bitsMask = [0x00, 0x01, 0x03, 0x07, 0x0F, 0x1F, 0x3F, 0x7F, 0xFF];
	var _count = bitCount !== undefined ? bitCount : data.length * 8;

	this.get_position = function () {
		return _position * 8 + _bit;
	}
	this.get_length = function () {
		return _count;
	}
	this.read = function(n) {
		var value = 0;
		while (n && _position < data.length) {
			var k = Math.min(n, 8 - _bit);
			value = (value << k) | (data[_position] >> (8 - _bit - k)) & _bitsMask[k];
			n -= k;
			_bit = (_bit + k) & 0x07;
			if (!_bit) {
				_position++;
			}
		}
		if (!n)
			return value;
		return -1;
	}
}

function CRCWrapper(stream, crc) {
	this._stream = stream;
	this._crc = crc;
	this.writeNoCrc = this._stream.write.bind(this._stream);
	this.readNoCrc = this._stream.read.bind(this._stream);
	this.writeMultipleNoCrc = this._stream.writeMultiple.bind(this._stream);
	this.readMultupleNoCrc = this._stream.readMultuple.bind(this._stream);

	this.get_stream = function () {
		return this._stream;
	}

	this.get_crc = function () {
		return this._crc;
	}

	this.get_buffer = function () {
		return this._stream.get_buffer();
	}

	this.seek = function(offset, origin) {
		return this._stream.seek(offset, origin);
	}
	
	this.get_length = function() {
		return this._stream.get_length();
	}

	this.write = function (value) {
		this._crc.add(value);
		this.writeNoCrc(value);
	}

	this.read = function () {
		var value = this.readNoCrc();
		if (value >= 0) {
			this._crc.add(value);
		}
		return value;
	}

	this.writeMultiple = function (elements) {
		this._crc.addArray(elements);
		this.writeMultipleNoCrc(elements);
	}

	this.readMultuple = function (count) {
		var elements = this.readMultupleNoCrc(count);
		this._crc.addArray(elements);
		return elements;
	}
}

/*
 * При реализации следующего класса частично были использованы (с предварительной переработкой)
 * исходные коды Miodrag Milanovic (https://git.redump.net/mame/tree/src/lib/formats/td0_dsk.cpp)
 * и Flat Rock Software (https://github.com/CatacombGames/CatacombApocalypse/blob/master/LZHUF.C),
 * распространяемые под свободными лицензиями (BSD-3-Clause, GNU).
 */
function LZSSDecompressionStream(underlyingStream) {
	var _underlyingStream = underlyingStream;

	var STR_BUF_SIZE = 4096; // Size of string buffer
	var FWD_BUF_SIZE = 60; // Size of look-ahead buffer
	var THRESHOLD = 2;
	var buffer = new Array(STR_BUF_SIZE + FWD_BUF_SIZE - 1);
	var bufferBegin = 0;
	var bufferCount = 0;
	var bufferIndex = 0;
	var bufferRIndex = 0;

	// 0..255 - ordinary characters
	// 256..313 - sequences
	var DICT_SIZE = (256 - THRESHOLD + FWD_BUF_SIZE);
	// nodes + root (627)
	var TABLE_SIZE = (DICT_SIZE * 2 - 1);
	// root position (626)
	var ROOT_POS = (TABLE_SIZE - 1); 
	// update when cumulative frequency reaches this value
	var MAX_FREQ = 0x8000; 
	// cumulative freq table (short[])
	// freq[TABLE_SIZE] = 0xFFFF - barricade
	var freq = new Array(TABLE_SIZE + 1); 
	// [0..R] - parent nodes references
	// [TABLE_SIZE..(TABLE_SIZE + DICT_SIZE - 1)] - pointers for leaves
	var prnt = new Array(TABLE_SIZE + DICT_SIZE);
	// pointing children nodes (son[], son[] + 1)
	var son = new Array(TABLE_SIZE);
	
	var bitsBuf = 0;
	var bitsPos = 8;
	var bitsMask = [0x00, 0x01, 0x03, 0x07, 0x0F, 0x1F, 0x3F, 0x7F, 0xFF];

	/*
	 * Tables for encoding/decoding upper 6 bits of
	 * sliding dictionary pointer
	 */

	// decoder table
	var d_code = [
		0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
		0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
		0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
		0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
		0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01,
		0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01,
		0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02,
		0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x02,
		0x03, 0x03, 0x03, 0x03, 0x03, 0x03, 0x03, 0x03,
		0x03, 0x03, 0x03, 0x03, 0x03, 0x03, 0x03, 0x03,
		0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04,
		0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x05,
		0x06, 0x06, 0x06, 0x06, 0x06, 0x06, 0x06, 0x06,
		0x07, 0x07, 0x07, 0x07, 0x07, 0x07, 0x07, 0x07,
		0x08, 0x08, 0x08, 0x08, 0x08, 0x08, 0x08, 0x08,
		0x09, 0x09, 0x09, 0x09, 0x09, 0x09, 0x09, 0x09,
		0x0A, 0x0A, 0x0A, 0x0A, 0x0A, 0x0A, 0x0A, 0x0A,
		0x0B, 0x0B, 0x0B, 0x0B, 0x0B, 0x0B, 0x0B, 0x0B,
		0x0C, 0x0C, 0x0C, 0x0C, 0x0D, 0x0D, 0x0D, 0x0D,
		0x0E, 0x0E, 0x0E, 0x0E, 0x0F, 0x0F, 0x0F, 0x0F,
		0x10, 0x10, 0x10, 0x10, 0x11, 0x11, 0x11, 0x11,
		0x12, 0x12, 0x12, 0x12, 0x13, 0x13, 0x13, 0x13,
		0x14, 0x14, 0x14, 0x14, 0x15, 0x15, 0x15, 0x15,
		0x16, 0x16, 0x16, 0x16, 0x17, 0x17, 0x17, 0x17,
		0x18, 0x18, 0x19, 0x19, 0x1A, 0x1A, 0x1B, 0x1B,
		0x1C, 0x1C, 0x1D, 0x1D, 0x1E, 0x1E, 0x1F, 0x1F,
		0x20, 0x20, 0x21, 0x21, 0x22, 0x22, 0x23, 0x23,
		0x24, 0x24, 0x25, 0x25, 0x26, 0x26, 0x27, 0x27,
		0x28, 0x28, 0x29, 0x29, 0x2A, 0x2A, 0x2B, 0x2B,
		0x2C, 0x2C, 0x2D, 0x2D, 0x2E, 0x2E, 0x2F, 0x2F,
		0x30, 0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37,
		0x38, 0x39, 0x3A, 0x3B, 0x3C, 0x3D, 0x3E, 0x3F
	];

	var d_len = [
		0x03, 0x03, 0x03, 0x03, 0x03, 0x03, 0x03, 0x03,
		0x03, 0x03, 0x03, 0x03, 0x03, 0x03, 0x03, 0x03,
		0x03, 0x03, 0x03, 0x03, 0x03, 0x03, 0x03, 0x03,
		0x03, 0x03, 0x03, 0x03, 0x03, 0x03, 0x03, 0x03,
		0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04,
		0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04,
		0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04,
		0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04,
		0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04,
		0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04,
		0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x05,
		0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x05,
		0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x05,
		0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x05,
		0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x05,
		0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x05,
		0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x05,
		0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x05, 0x05,
		0x06, 0x06, 0x06, 0x06, 0x06, 0x06, 0x06, 0x06,
		0x06, 0x06, 0x06, 0x06, 0x06, 0x06, 0x06, 0x06,
		0x06, 0x06, 0x06, 0x06, 0x06, 0x06, 0x06, 0x06,
		0x06, 0x06, 0x06, 0x06, 0x06, 0x06, 0x06, 0x06,
		0x06, 0x06, 0x06, 0x06, 0x06, 0x06, 0x06, 0x06,
		0x06, 0x06, 0x06, 0x06, 0x06, 0x06, 0x06, 0x06,
		0x07, 0x07, 0x07, 0x07, 0x07, 0x07, 0x07, 0x07,
		0x07, 0x07, 0x07, 0x07, 0x07, 0x07, 0x07, 0x07,
		0x07, 0x07, 0x07, 0x07, 0x07, 0x07, 0x07, 0x07,
		0x07, 0x07, 0x07, 0x07, 0x07, 0x07, 0x07, 0x07,
		0x07, 0x07, 0x07, 0x07, 0x07, 0x07, 0x07, 0x07,
		0x07, 0x07, 0x07, 0x07, 0x07, 0x07, 0x07, 0x07,
		0x08, 0x08, 0x08, 0x08, 0x08, 0x08, 0x08, 0x08,
		0x08, 0x08, 0x08, 0x08, 0x08, 0x08, 0x08, 0x08
	];

	function init() {
		// init freqiencies, children and parents
		for ( var i = 0; i < DICT_SIZE; i++ ) {
			freq[i] = 1;
			son[i] = i + TABLE_SIZE;
			prnt[i + TABLE_SIZE] = i;
		}
		for ( var i = DICT_SIZE, j = 0; i < TABLE_SIZE; i++, j += 2 ) {
			freq[i] = (freq[j] + freq[j + 1]) & 0xFFFF;
			son[i] = j;
			prnt[j] = i;
			prnt[j + 1] = i;
		}
		freq[TABLE_SIZE] = 0xFFFF;
		prnt[ROOT_POS] = 0;
		// init buffer
		var bufferEnd = STR_BUF_SIZE - FWD_BUF_SIZE;
		for ( var i = 0; i < bufferEnd; i++ ) {
			buffer[i] = 0x20;
		}
		bufferRIndex = bufferEnd;
	}

	function readBits(count) {
		var nFromBuffer = Math.min(8 - bitsPos, count);
		var nFromStream = count - nFromBuffer;
		var value = (bitsBuf >> (8 - bitsPos - nFromBuffer)) & bitsMask[nFromBuffer];
		if (nFromStream > 0) {
			var bitsRead = 0;
			do {
				bitsBuf = _underlyingStream.read();
				if (bitsBuf < 0)
					throw new Error(ZX_Lang.ERR_UNEXPECTED_END_OF_STREAM);
				var bitsRead = Math.min(nFromStream, 8);
				value = (value << bitsRead) | (bitsBuf >> (8 - bitsRead) & bitsMask[bitsRead]);
				nFromStream -= bitsRead;
			}
			while (nFromStream > 0);
			bitsPos = bitsRead;
		}
		else {
			bitsPos += nFromBuffer;
		}
		return value;
	}


	// reconstruct freq tree
	function reconst() {
		// halven cumulative req for leaf nodes
		var j = 0;
		for ( var i = 0; i < TABLE_SIZE; i++ ) {
			if (son[i] >= TABLE_SIZE) {
				freq[j] = (freq[i] + 1) >> 1;
				son[j] = son[i];
				j++;
			}
		}
		// make a tree : first, connect children nodes
		for ( var i = DICT_SIZE, j = 0; i < TABLE_SIZE; i++, j += 2 ) {
			var f = freq[i] = (freq[j] + freq[j + 1]) & 0xFFFF;
			for (var k = i; f < freq[k - 1]; k--) { }
			var len = i - k;
			move(freq, k + 1, k, len);
			freq[k] = f;
			move(son, k + 1, k, len);
			son[k] = j;
		}
		// connect parent nodes
		for ( var i = 0; i < TABLE_SIZE; i++ ) {
			var j = son[i];
			if (j >= TABLE_SIZE) {
				prnt[j] = i
			}
			else {
				prnt[j] = i;
				prnt[j + 1] = i;
			}
		}
	}

	// update freq tree
	function update(c) {
		if (freq[ROOT_POS] == MAX_FREQ) {
			reconst();
		}
		c = prnt[c + TABLE_SIZE];
		do {
			var k = freq[c] = (freq[c] + 1) & 0xFFFF;
			// swap nodes to keep the tree freq-ordered
			var l;
			if (k > freq[l = c + 1]) {
				while (k > freq[++l]) {}
				l--;
				freq[c] = freq[l];
				freq[l] = k;

				var i = son[c];
				prnt[i] = l;
				if (i < TABLE_SIZE) prnt[i + 1] = l;

				var j = son[l];
				son[l] = i;

				prnt[j] = c;
				if (j < TABLE_SIZE) prnt[j + 1] = c;
				son[c] = j;

				c = l;
			}
		}
		while ((c = prnt[c]) != 0) // do it until reaching the root
	}

	function move(arr, di, si, len) {
		if (di > si) {
			di += len;
			si += len;
			while (len--) {
				arr[--di] = arr[--si];
			}
		}
		else {
			while (len--) {
				arr[di++] = arr[si++];
			}
		}
	}

	function decodeChar() {
		var c = son[ROOT_POS];
		/*
		 * start searching tree from the root to leaves.
		 * choose node #(son[]) if input bit == 0
		 * else choose #(son[]+1) (input bit == 1)
		 */	
		while (c < TABLE_SIZE) {
			c += readBits(1);
			c = son[c];
		}
		c -= TABLE_SIZE;
		update(c);
		return c;
	}

	function decodePosition() {
		var i = readBits(8);
		var upperBits = d_code[i];
		var len = d_len[i] - 2;
		var lowerBits = readBits(len);
		i = (i << len) | lowerBits;
		return (upperBits << 6) | (i & 0x3F);
	}

	// Decoding/Uncompressing
	function decode() {
		if (bufferCount > 0)
			return getFromBuffer();

		var c = decodeChar();
		if (c < 256) {
			buffer[bufferRIndex++] = c;
			bufferRIndex &= (STR_BUF_SIZE - 1);
			return c;
		}
		// put to buffer
		var pos = decodePosition();
		bufferBegin = (bufferRIndex - pos - 1) & (STR_BUF_SIZE - 1);
		bufferCount = c - 255 + THRESHOLD;
		bufferIndex = 0;
		return getFromBuffer();
	}

	function getFromBuffer() {
		// assert bufferIndex < bufferCount
		var c = buffer[(bufferBegin + bufferIndex) & (STR_BUF_SIZE - 1)];
		buffer[bufferRIndex++] = c;
		bufferRIndex &= (STR_BUF_SIZE - 1);
		bufferIndex++;
		if (bufferIndex >= bufferCount) {
			bufferIndex = bufferCount = 0;
		}
		return c;
	}

	function read() {
		return decode();
	} 

	function readMultuple(count) {
		var result = new Array(count);
		for ( var i = 0; i < count; i++) {
			result[i] = decode();
		}
		return result;
	}

	this.get_buffer = function () {
		throw new Error('Unsupported exception.');
	}
	this.get_position = function () {
		throw new Error('Unsupported exception.');
	}
	this.get_length = function () {
		throw new Error('Unsupported exception.');
	}
	this.seek = function (offset, origin) {
		throw new Error('Unsupported exception.');
	}
	this.read = read;
	this.readMultuple = readMultuple;
	this.write = function () {
		throw new Error('Unsupported exception');
	}
	this.writeMultiple = function (elemenets) {
		throw new Error('Unsupported exception');
	}

	init();
}

var TAPE_EVENT = {
	SELECTION: 1,
	DESCRIPTION: 2,
	MESSAGE: 3,
	ARCHIVE_INFO: 4,
	HARDWARE_INFO: 5,
	CUSTOM_INFO: 6,
	SNAPSHOT_RESTORATION: 7
};

function TapeInfo() {
	this.__classes = ['TypeInfo'];
	this.format = null;
	this.formatVersion = null;
	this.size = null;
	this.blocks = [];
	this.currentIndex = null;
}

function TapeBlockInfo() {
	this.__classes = ['TypeBlockInfo'];
	this.index = null;
	this.id = null;
	this.idDescription = null;
	this.size = null;
}

function TapeDataBlockInfo() {
	TapeDataBlockInfo.superclass.constructor.apply(this, arguments);
	this.__classes.push('TapeDataBlockInfo');
	this.postPause = null;
}
extend(TapeDataBlockInfo, TapeBlockInfo);

function TapeHeaderBlockInfo() {
	TapeHeaderBlockInfo.superclass.constructor.apply(this, arguments);
	this.__classes.push('TapeHeaderBlockInfo');
	this.type = null;
	this.typeDescription = null;
	this.filename = null;
	this.binLength = null;
	this.param1 = null;
	this.param2 = null;
}
extend(TapeHeaderBlockInfo, TapeDataBlockInfo);

function TapeGroupBlockInfo() {
	TapeGroupBlockInfo.superclass.constructor.apply(this, arguments);
	this.__classes.push('TapeGroupBlockInfo');
	this.name = null;
}
extend(TapeGroupBlockInfo, TapeBlockInfo);

function TapeDescriptionBlockInfo() {
	TapeDescriptionBlockInfo.superclass.constructor.apply(this, arguments);
	this.__classes.push('TapeDescriptionBlockInfo');
	this.description = null;
}
extend(TapeDescriptionBlockInfo, TapeBlockInfo);

function TapeHardwareTypeBlockInfo() {
	TapeHardwareTypeBlockInfo.superclass.constructor.apply(this, arguments);
	this.__classes.push('TapeHardwareTypeBlockInfo');
	this.records = [];
}
extend(TapeHardwareTypeBlockInfo, TapeBlockInfo);

function TapeHardwareTypeBlockInfoRecord() {
	this.__classes = ['TapeHardwareTypeBlockInfoRecord'];
	this.type = null;
	this.typeDescription = null;
	this.id = null;
	this.idDescription = null;
	this.relation = null;
	this.relationDescription = null;
}

function TapeArchiveBlockInfo() {
	TapeArchiveBlockInfo.superclass.constructor.apply(this, arguments);
	this.__classes.push('TapeArchiveBlockInfo');
	this.records = [];
}
extend(TapeArchiveBlockInfo, TapeBlockInfo);

function TapeArchiveBlockInfoRecord() {
	this.__classes = ['TapeArchiveBlockInfoRecord'];
	this.infoId = null;
	this.infoIdDescription = null;
	this.infoText = null;
}

function TapeMessageBlockInfo() {
	TapeMessageBlockInfo.superclass.constructor.apply(this, arguments);
	this.__classes.push('TapeMessageBlockInfo');
	this.message = null;
	this.duration = null;
}
extend(TapeMessageBlockInfo, TapeBlockInfo);

function TapePauseBlockInfo() {
	TapePauseBlockInfo.superclass.constructor.apply(this, arguments);
	this.__classes.push('TapePauseBlockInfo');
	this.duration = null;
}
extend(TapePauseBlockInfo, TapeBlockInfo);

function TapeSelectBlockInfo() {
	TapeSelectBlockInfo.superclass.constructor.apply(this, arguments);
	this.__classes.push('TapeSelectBlockInfo');
	this.options = [];
}
extend(TapeSelectBlockInfo, TapeBlockInfo);

function TapeSelectBlockInfoOption() {
	this.__classes = ['TapeSelectBlockInfoOption'];
	this.blockIndex = null;
	this.description = null;
}

function TapeSnapshotBlockInfo() {
	TapeSnapshotBlockInfo.superclass.constructor.apply(this, arguments);
	this.__classes.push('TapeSnapshotBlockInfo');
	this.format = null;
}
extend(TapeSnapshotBlockInfo, TapeBlockInfo);
// Upstream module: hardware/hw_state.js
function HWState() {
    var _onPerformance = new ZX_Event();

    this.perfomance = { frequency: 0, fps: 0 };

    this.get_onPerformance = function () {
        return _onPerformance.pub;
    }

    this.updatePerformance = function (data) {
        this.perfomance = data;
        _onPerformance.emit(data);
    }
}
Object.assign(HWState, {
    _instance: null,
    get_instance: function () {
        if (!this._instance) {
            this._instance = new HWState();
        }
        return this._instance;
    }
});

// Upstream module: hardware/z80.js
function ZX_Z80 () {
    'use strict';
   
    var _bus;

    // счетчик тактов
    var ts_cnt = 0;

    // регистры процессора
    var pc = 0;
    var sp = 0xffff;
    var ix = 0;
    var iy = 0;
    
    var i = 0;
    var r = 0;
    
    var iff = 0;
    var imf = 0;

    var a = 0xff;
    var f = new Flags();
    var regs = new RegSet();
    
    var a_ = 0xff;
    var f_ = new Flags();
    var regs_ = new RegSet();

    var q = 0;
    var memptr = 0;

    function Flags() {
        var self = this;

        self.s = 1;
        self.z = 1;
        self.y = 1;
        self.h = 1;
        self.x = 1;
        self.p = 1;
        self.n = 1;
        self.c = 1;

        self.get = function() {
            return (
                ( self.s ? 0x80 : 0 ) |
                ( self.z ? 0x40 : 0 ) |
                ( self.y ? 0x20 : 0 ) |
                ( self.h ? 0x10 : 0 ) |
                ( self.x ? 0x08 : 0 ) |
                ( self.p ? 0x04 : 0 ) |
                ( self.n ? 0x02 : 0 ) |
                ( self.c ? 0x01 : 0 )
            );
        }

        self.set = function( value ) {
            self.s = ( value & 0x80 );
            self.z = ( value & 0x40 );
            self.y = ( value & 0x20 );
            self.h = ( value & 0x10 );
            self.x = ( value & 0x08 );
            self.p = ( value & 0x04 );
            self.n = ( value & 0x02 );
            self.c = ( value & 0x01 );
        }
    }

    function RegSet() {
        var self = this;

        self.b = 0;
        self.c = 0;
        self.d = 0;
        self.e = 0;
        self.h = 0;
        self.l = 0;
    }

    // префиксы расширенных команд
    var prefix_ix = false;
    var prefix_iy = false;
    var prefix_ext = false;
    var prefix_bit = false;

    var index_offset_cache = 0;

    // запросы на прерывания
    var nmi_request = 0;
    var int_request = 0;
    var int_request_data = 0xFF;
    var int_request_force = 0;
    var int_lock = 0;

    /////////////////////////////////////
    // фуикции чтения/записи регистров //
    /////////////////////////////////////

    function set_af( value ) {
        a = ( value >> 8 );
        f.set( value & 0xff );
    }
    function get_af() { return ( a << 8 ) | f.get(); }
    
    function set_bc( value ) {
        regs.b = ( value >> 8 );
        regs.c = ( value & 0xff );
    }
    function get_bc() { return ( regs.b << 8 ) | regs.c; }

    function set_de( value ) {
        regs.d = ( value >> 8 );
        regs.e = ( value & 0xff );
    }
    function get_de() { return ( regs.d << 8 ) | regs.e; }

    function set_hl( value ) {
        regs.h = ( value >> 8 );
        regs.l = ( value & 0xff );
    }
    function get_hl() { return ( regs.h << 8 ) | regs.l; }

    function set_ix_h( value ) { ix = ( ix & 0x00ff ) | ( value << 8 ); }
    function get_ix_h() { return ( ix >> 8 ); }

    function set_ix_l( value ) { ix = ( ix & 0xff00 ) | value; }
    function get_ix_l() { return ( ix & 0xff ); }

    function set_iy_h( value ) { iy = ( iy & 0x00ff ) | ( value << 8 ); }
    function get_iy_h() { return ( iy >> 8 ); }

    function set_iy_l( value ) { iy = ( iy & 0xff00 ) | value; }
    function get_iy_l() { return ( iy & 0xff ); }

    ////////////////////////////////////////
    // фуикции чтения/записи спец. флагов //
    ////////////////////////////////////////

	function get_iff1() {
		return !!(iff & 0x02);
	}

	function set_iff1(value) {
		if (value) {
			iff |= 0x02;
		}
		else {
			iff &= 0xfd;
		}
	}

	function get_iff2() {
		return !!(iff & 0x01);
	}

	function set_iff2(value) {
		if (value) {
			iff |= 0x01;
		}
		else {
			iff &= 0xfe;
		}
	}
	
	function get_imfa() {
		return !!(imf & 0x02);
	}

	function set_imfa(value) {
		if (value) {
			imf |= 0x02;
		}
		else {
			imf &= 0xfd;
		}
	}

	function get_imfb() {
		return !!(imf & 0x01);
	}

	function set_imfb(value) {
		if (value) {
			imf |= 0x01;
		}
		else {
			imf &= 0xfe;
		}
	}

    ///////////////////////////////////////////////////////////
    // функции обращения к памяти и устройствам ввода/вывода //
    ///////////////////////////////////////////////////////////

    function read_opcode() {
        var v8 = _bus.instruction_read(pc);
        pc = ( pc + 1 ) & 0xffff;
        r = ( r & 0x80 ) | (( r + 1 ) & 0x7f );
        ts_cnt += 4;
        return v8;
    }

    function read_operand_byte() {
        var v8 = _bus.instruction_read(pc);
        pc = ( pc + 1 ) & 0xffff;
        ts_cnt += 3;
        return v8;
    }

    function read_operand_word() {
        var low_byte = read_operand_byte();
        var high_byte = read_operand_byte();
        return low_byte | ( high_byte << 8 );
    }

    function read_mem_byte(address) {
        var v8 = _bus.mem_read(address);
        ts_cnt += 3;
        return v8;
    }

    function write_mem_byte(address, value) {
        _bus.mem_write(address, value);
        ts_cnt += 3;
    }

    function read_mem_word(address) {
        var low_byte = read_mem_byte(address);
        var high_byte = read_mem_byte(( address + 1 ) & 0xffff);
        return low_byte | ( high_byte << 8 );
    }
    
    function write_mem_word(address, value) {
        write_mem_byte(address, value & 0xff);
        write_mem_byte(( address + 1 ) & 0xffff, value >> 8);
    }

    function read_io_byte(port) {
        var v8 = _bus.io_read(port);
        ts_cnt += 4;
        return v8;
    }

    function write_io_byte(port, value) {
        _bus.io_write(port, value);
        ts_cnt += 4;
    }

    function is_halt() {
        return _bus.instruction_read(pc) == 0x76;
    }

    ///////////////////////////////////////////
    // функции обработки команд и прерываний //
    ///////////////////////////////////////////

    function process() {
        // Если выполняется команда с данными префиксами,
        // то не обрабатываем поступившие прерывания, 
        // а ждем завершения чтения и выполнения команды.
        // Кроме того, маскируемое прерывание не выполняется 
        // сразу после выполнения инструкций EI, DI (флаг int_lock).
        if (!prefix_bit && !prefix_ext) {
            // проверка на запрос немаскируемого прерывания
            if (nmi_request && process_nmi_request())
                return;
            // проверка на запрос маскируемого прерывания
            if (int_request && !int_lock && process_int_request()) 
                return;
        }

        int_lock = 0;

        // считываем очередной код
        // DD/FD CB's final opcode is a non-M1 operand fetch: 3 T, no R increment.
        var opcode = (prefix_bit && (prefix_ix || prefix_iy)) ? read_operand_byte() : read_opcode();

        // проверка на префиксы

        // если предыдущий код был префиксом 0xED или 0xCB
        // то следующий код должен быть командой, поэтому
        // проверка осуществляется, только если это не так.
        if ( !prefix_bit && !prefix_ext ) {
            // 11x11101
            if (( opcode & 0xdf ) == 0xdd ) {
                // IX
                // IY
                prefix_ix = !(opcode & 0x20);
                prefix_iy = !prefix_ix;
                prefix_ext = false;
                prefix_bit = false;
                return;
            }

            if ( opcode == 0xed ) {
                // 0xED
                prefix_ix = false;
                prefix_iy = false;
                prefix_ext = true;
                prefix_bit = false;
                return;
            }

            if ( opcode == 0xcb ) {
                // 0xCB
                prefix_ext = false;
                prefix_bit = true;

                // надо сразу прочитать смещение, если были индексные префиксы
                if (prefix_ix || prefix_iy) {
                    index_offset_cache = byte_to_svalue(read_operand_byte());
                }                
                return;                
            }
        }

        do_operation(opcode);

        prefix_ix = false;
        prefix_iy = false;
        prefix_ext = false;
        prefix_bit = false;
    }

    function process_nmi_request() {
        nmi_request = 0;

        // total: + 11 t-states
        set_iff1(false);

        r = ( r & 0x80 ) | (( r + 1 ) & 0x7f );

        if ( is_halt() ) {
            pc = ( pc + 1 ) & 0xffff;
        }                
        else if ( prefix_iy || prefix_ix ) {
            // если включен какой-то из индексных префиксов,
            // то после прерывания надо заново его включить,
            // поэтому адрес возврата делаем на единицу меньше
            pc = ( pc - 1 ) & 0xffff;
        }

        prefix_iy = false;
        prefix_ix = false;

        sp = ( sp - 2 ) & 0xffff;
        write_mem_word(sp, pc);
        pc = 0x0066;
        memptr = pc;

        q = 0;
        ts_cnt += 5;

        return true;
    }

    function process_int_request() {
        // если маскируемые прерывания выключены
        // прерывание не обрабатывается
        if (!get_iff1() && !int_request_force)
            return false;

        int_request_force = 0;
        set_iff1(false);
        set_iff2(false);

        /*
            Команды LD A, I и LD A, R по спецификации должны копировать флаг
            прерываний iff2 во флаг четности. Однако в реальном Z80 существует
            баг, что если в этот момент поступит сигнал прерывания, то во флаг
            четности запишется значение уже сброшенного флага.

            Мы уже сбросили флаги выше. Проверяем, что следующая команда - одна
            из перечисленных и, если так, даем ей выполниться со сброшенным флагом
            iff2. После выполнения команды прерывание будет выполнено по условиям 
            int_request и int_request_force.
        */

        var emulate_iff2_copy_bug = false;
        var next_opcode = _bus.instruction_read(pc);
        if ( next_opcode == 0xED ) {
            next_opcode = _bus.instruction_read((pc + 1) & 0xFFFF);
            emulate_iff2_copy_bug = ( next_opcode & 0xF7 ) == 0x57;
        }

        if (emulate_iff2_copy_bug) {
            int_request_force = 1;
            return false;
        }

        // выполняем прерывание
        r = ( r & 0x80 ) | (( r + 1 ) & 0x7f );

        if ( is_halt() ) {
            pc = ( pc + 1 ) & 0xffff;
        }   
        else if ( prefix_iy || prefix_ix ) {
            // если включен какой-то из индексных префиксов,
            // то после прерывания надо заново его включить,
            // поэтому адрес возврата делаем на единицу меньше
            pc = ( pc - 1 ) & 0xffff;
        }

        prefix_iy = false;
        prefix_ix = false;

        ts_cnt += 2 + 4;

        switch (imf) {
            case 0x00:
            case 0x01:
                // IM 0
                // total: + 13 t-states
                do_operation(int_request_data);
                break;

            case 0x02:
                // IM 1
                // total: + 13 t-states
                do_operation(0xff); // RST #38
                break;

            case 0x03:
                // IM 2
                // total: + 19 t-states
                var ref_addr = ( i << 8 ) | int_request_data;
                var hnd_addr = read_mem_word(ref_addr);

                sp = ( sp - 2 ) & 0xffff;
                write_mem_word(sp, pc);
                pc = hnd_addr;
                memptr = pc;

                q = 0;
                ts_cnt += 1;

                break;
        }
        return true;
    }

    function do_operation(opcode) {
        if (prefix_ext) {

            // 010xx111
            if ( ( opcode & 0xe7 ) == 0x47 ) {
                // LD A, I      ( 4 + 4 ) + 1
                // LD A, R      -//-
                // LD I, A
                // LD R, A
                var subcode = (opcode >> 3) & 0x03;
                switch (subcode) {
                    case 0x00: 
                        i = a; 
                        q = 0;
                        break;

                    case 0x01: 
                        r = a; 
                        q = 0;
                        break;

                    case 0x02: 
                        a = i;
                        f.s = a & 0x80;
                        f.z = !a;
                        f.y = a & 0x20;
                        f.h = 0;
                        f.x = a & 0x08;
                        f.p = get_iff2();
                        f.n = 0;
                        q = 1;
                        break;

                    case 0x03: 
                        a = r;
                        f.s = a & 0x80;
                        f.z = !a;
                        f.y = a & 0x20;
                        f.h = 0;
                        f.x = a & 0x08;
                        f.p = get_iff2();
                        f.n = 0;
                        q = 1;
                        break;
                }

                ts_cnt += 1;

                return;
            }

            // 01xxx011
            if ( (opcode & 0xc7 ) == 0x43 ) {
                // LD dd, (nn)  ( 4 + 4 + 3 + 3 + 3 + 3 )
                // LD (nn), dd  -//-

                var addr = read_operand_word();

                var to_reg = !!(opcode & 0x08);
                var dd = (opcode >> 4) & 0x03;

                if (to_reg) {
                    var value = read_mem_word(addr);
                    switch (dd) {
                        case 0x00: set_bc(value); break;
                        case 0x01: set_de(value); break;
                        case 0x02: set_hl(value); break;
                        case 0x03: sp = value; break;
                    }
                }
                else { // to_mem
                    var value;
                    switch (dd) {
                        case 0x00: value = get_bc(); break;
                        case 0x01: value = get_de(); break;
                        case 0x02: value = get_hl(); break;
                        case 0x03: value = sp; break;
                    }
                    write_mem_word(addr, value);
                }
                q = 0;
                memptr = (addr + 1) & 0xFFFF;
                return;
            }

            // 101xx000
            if ( (opcode & 0xe7 ) == 0xa0 ) {
                // LDI      ( 4 + 4 + 3 + 3 ) + 2
                // LDIR     ( 4 + 4 + 3 + 3 ) + 2 + 5?
                // LDD      ( 4 + 4 + 3 + 3 ) + 2
                // LDDR     ( 4 + 4 + 3 + 3 ) + 2 + 5?

                var increment = !(opcode & 0x08);
                var repeat = !!(opcode & 0x10);

                var cur_hl = get_hl();
                var cur_de = get_de();
                var cur_bc = get_bc();

                var data = read_mem_byte(cur_hl);
                write_mem_byte(cur_de, data);

                if (increment) {
                    cur_hl = (cur_hl + 1) & 0xffff;
                    cur_de = (cur_de + 1) & 0xffff;
                }
                else {
                    cur_hl = (cur_hl - 1) & 0xffff;
                    cur_de = (cur_de - 1) & 0xffff;
                }

                cur_bc = (cur_bc - 1) & 0xffff;

                set_hl(cur_hl);
                set_de(cur_de);
                set_bc(cur_bc);

                var _undoc_support = a + data;
                f.y = ( _undoc_support & 0x02 );
                f.h = 0;
                f.x = ( _undoc_support & 0x08 );
                f.p = cur_bc; // != 0
                f.n = 0;
                q = 1;

                ts_cnt += 2;

                if ( repeat && cur_bc ) {
                    pc = ( pc - 2 ) & 0xffff;
                    // https://spectrumcomputing.co.uk/forums/viewtopic.php?t=6102
                    // https://github.com/hoglet67/Z80Decoder/wiki/Undocumented-Flags
                    f.y = pc & 0x2000;
                    f.x = pc & 0x0800;
                    memptr = (pc + 1) & 0xFFFF;
                    ts_cnt += 5;
                }

                return;
            }

            // 101xx001
            if ( (opcode & 0xe7 ) == 0xa1 ) {
                // CPI          ( 4 + 4 + 3 ) + 5
                // CPIR         ( 4 + 4 + 3 ) + 5 + 5?
                // CPD          ( 4 + 4 + 3 ) + 5
                // CPDR         ( 4 + 4 + 3 ) + 5 + 5?

                var increment = !(opcode & 0x08);
                var repeat = !!(opcode & 0x10);

                var cur_hl = get_hl();
                var cur_bc = get_bc();

                var data = read_mem_byte(cur_hl);
                var cmp_res = (a - data) & 0xff;
                var cmp_half = ((a & 0x0f) - (data & 0x0f)) < 0;

                if (increment) {
                    cur_hl = (cur_hl + 1) & 0xffff;
                    memptr = (memptr + 1) & 0xFFFF;
                }
                else {
                    cur_hl = (cur_hl - 1) & 0xffff;
                    memptr = (memptr - 1) & 0xFFFF;
                }

                cur_bc = (cur_bc - 1) & 0xffff;

                set_hl(cur_hl);
                set_bc(cur_bc);
                
                var _undoc_support = ( cmp_res - ( cmp_half ? 1 : 0 )) & 0xff;
                f.s = cmp_res & 0x80;
                f.z = !cmp_res;
                f.y = ( _undoc_support & 0x02 );
                f.h = cmp_half;
                f.x = ( _undoc_support & 0x08 );
                f.p = cur_bc; // != 0
                f.n = 1;
                q = 1;

                ts_cnt += 5;

                if ( repeat && cur_bc && cmp_res ) {
                    pc = ( pc - 2 ) & 0xffff;
                    // https://spectrumcomputing.co.uk/forums/viewtopic.php?t=6102
                    // https://github.com/hoglet67/Z80Decoder/wiki/Undocumented-Flags
                    f.y = pc & 0x2000;
                    f.x = pc & 0x0800;
                    memptr = (pc + 1) & 0xFFFF;
                    ts_cnt += 5;
                }

                return;
            }

            // 01xxx100
            if (( opcode & 0xc7 ) == 0x44 ) {
                // NEG          ( 4 + 4 )
                // * включая все недокументированные варианты опкодов

                var old_a = a;
                a = ( 0x100 - a ) & 0xff;

                f.s = a & 0x80;
                f.z = !a;
                f.y = a & 0x20;
                f.h = ( old_a & 0x0f ); // 0 - ( old_a & 0x0f ) < 0
                f.x = a & 0x08;
                f.p = old_a == 0x80;
                f.n = 1;
                f.c = !!old_a;
                q = 1;

                return;
            }

            // 01xxx110
            if ( ( opcode & 0xc7 ) == 0x46 ) {
                // IM 0         ( 4 + 4 )
                // IM 1         -//-
                // IM 2
                // * включая все недокументированные варианты опкодов

                set_imfa(!!(opcode & 0x10));
                set_imfb(!!(opcode & 0x08));
                q = 0;
                return;
            }

            // 01xxx010
            if ( (opcode & 0xc7 ) == 0x42 ) {
                // ADC HL, ss       ( 4 + 4 ) + 7
                // SBC HL, ss       ( 4 + 4 ) + 7

                var addition = !!(opcode & 0x08);
                var ss = (opcode >> 4) & 0x03;

                var operand;
                switch (ss) {
                    case 0x00: operand = get_bc(); break; // BC
                    case 0x01: operand = get_de(); break; // DE
                    case 0x02: operand = get_hl(); break; // HL
                    case 0x03: operand = sp; break; // SP
                }
                if ( f.c ) {
                    operand++;
                }

                var current = get_hl();

                if (addition) {
                    // addition
                    var result = current + operand;
                    var care = result & 0x10000;
                    result &= 0xffff;

                    set_hl(result);
                    f.s = result & 0x8000;
                    f.z = !result;
                    f.y = result & 0x2000;
                    f.h = ((current & 0x0fff) + (operand & 0x0fff)) & 0x1000;
                    f.x = result & 0x0800;
                    f.p = get_word_sum_overflow(current, operand, result);
                    f.n = 0;
                    f.c = care;
                }
                else { 
                    // subtraction
                    var result = current - operand;
                    var borrow = result < 0;
                    result &= 0xffff;

                    set_hl(result);
                    f.s = result & 0x8000;
                    f.z = !result;
                    f.y = result & 0x2000;
                    f.h = ((current & 0x0fff) - (operand & 0x0fff)) < 0;
                    f.x = result & 0x0800;
                    f.p = get_word_diff_overflow(current, operand, result);
                    f.n = 1;
                    f.c = borrow;
                }
                q = 1;
                memptr = (current + 1) & 0xFFFF;

                ts_cnt += 7;

                return;
            }

            // 0110x111
            if ( (opcode & 0xf7 ) == 0x67 ) {
                // RLD          ( 4 + 4 + 3 + 3 ) + 4
                // RRD          ( 4 + 4 + 3 + 3 ) + 4

                var left = !!(opcode & 0x08);
                var cur_mem = read_mem_byte(get_hl());

                if (left) {
                    var temp = cur_mem >> 4;
                    cur_mem = (( cur_mem << 4 ) & 0xf0 ) | ( a & 0x0f );
                    a = ( a & 0xf0 ) | temp;
                }
                else {
                    var temp = cur_mem & 0x0f;
                    cur_mem = (( a << 4 ) & 0xf0 ) | ( cur_mem >> 4 );
                    a = ( a & 0xf0 ) | temp;
                }

                var addr = get_hl();
                write_mem_byte(addr, cur_mem);
                f.s = a & 0x80;
                f.z = !a;
                f.y = a & 0x20;
                f.h = 0;
                f.x = a & 0x08;
                f.p = get_parity(a);
                f.n = 0;

                q = 1;
                memptr = (addr + 1) & 0xFFFF;
                ts_cnt += 4;

                return;
            }

            // 01xxx101
            if ( (opcode & 0xc7 ) == 0x45 ) {
                // RETI         ( 4 + 4 + 3 + 3 )
                // RETN         ( 4 + 4 + 3 + 3 )
                // * включая все недокументированные варианты опкодов

                pc = read_mem_word(sp);
                sp = ( sp + 2 ) & 0xffff;
                set_iff1(get_iff2()); // RETN and RETI aliases both restore IFF1 from IFF2.
                q = 0;
                memptr = pc;
                return;
            }

            // 01xxx00x
            if ( ( opcode & 0xc6 ) == 0x40 ) {
                // IN r, (C)        ( 4 + 4 + 4 )
                // OUT (C), r       -//-
                // * IN 0, (C)
                // * OUT (C), 0

                var r1 = (opcode >> 3) & 0x07;
                var cmd_in = !(opcode & 0x01);

                var addr = get_bc();
                if (cmd_in) {
                    // IN
                    var value = read_io_byte(addr);
                    switch (r1) {
                        case 0x00: regs.b = value; break;
                        case 0x01: regs.c = value; break;
                        case 0x02: regs.d = value; break;
                        case 0x03: regs.e = value; break;
                        case 0x04: regs.h = value; break;
                        case 0x05: regs.l = value; break;
                        case 0x07: a = value; break;
                    }

                    f.s = value & 0x80;
                    f.z = !value;
                    f.y = value & 0x20;
                    f.h = 0;
                    f.x = value & 0x08;
                    f.p = get_parity(value);
                    f.n = 0;
                    q = 1;
                }
                else {
                    // OUT
                    var value = 0;
                    switch (r1) {
                        case 0x00: value = regs.b; break;
                        case 0x01: value = regs.c; break;
                        case 0x02: value = regs.d; break;
                        case 0x03: value = regs.e; break;
                        case 0x04: value = regs.h; break;
                        case 0x05: value = regs.l; break;
                        case 0x07: value = a; break;
                    }

                    write_io_byte(addr, value);
                    q = 0;
                }
                memptr = (addr + 1) & 0xFFFF;

                return;
            }

            // 101xx01x
            if ( (opcode & 0xe6 ) == 0xa2 ) {
                // INI              ( 4 + 4 + 4 + 3 ) + 1 + 5?
                // INIR             -//-
                // IND
                // INDR
                // OUTI
                // OTIR
                // OUTD
                // OTDR

                var repeat = !!(opcode & 0x10);
                var increment = !(opcode & 0x08);
                var cmd_in = !(opcode & 0x01);

                var cur_hl = get_hl();

                var old_b = regs.b;
                var new_b = ( regs.b - 1 ) & 0xff;

                var data;
                if (cmd_in) {
                    data = read_io_byte(( old_b << 8 ) | regs.c ); // INI/IND reads before decrementing B.
                    write_mem_byte(cur_hl, data);
                    memptr = (((old_b << 8) | regs.c) + (increment ? 1 : -1)) & 0xFFFF;
                }
                else {
                    data = read_mem_byte(cur_hl);
                    write_io_byte(( new_b << 8 ) | regs.c, data); // OUTI/OUTD decrements B before the port write.
                    memptr = (((new_b << 8) | regs.c) + (increment ? 1 : -1)) & 0xFFFF;
                }

                regs.b = new_b;

                var new_hl = ( increment ? ( cur_hl + 1 ) : ( cur_hl - 1 )) & 0xffff;
                set_hl(new_hl);

                f.s = regs.b & 0x80;
                f.z = !regs.b;
                f.y = regs.b & 0x20;
                f.x = regs.b & 0x08;
                f.n = data & 0x80;

                var temp;
                if ( cmd_in ) {
                    temp = data + (( regs.c + ( increment ? 1 : -1 )) & 0xFF);
                }
                else {
                    temp = data + ( new_hl & 0xFF );
                }
                f.h = temp > 255;
                f.c = temp > 255;
                var pv = ( temp & 7 ) ^ regs.b;
                f.p = get_parity(pv);

                q = 1;
                ts_cnt += 1;

                if ( repeat && regs.b ) {
                    pc = ( pc - 2 ) & 0xffff;
                    // https://spectrumcomputing.co.uk/forums/viewtopic.php?t=6102
                    // https://github.com/hoglet67/Z80Decoder/wiki/Undocumented-Flags
                    f.y = pc & 0x2000;
                    f.x = pc & 0x0800;
                    var temp2 = regs.b;
                    if (f.c) {
                        temp2 = (temp2 + (f.n ? -1 : 1)) & 0xFF;
                        f.h = (temp2 ^ regs.b) & 0x10;
                    }
                    pv ^= (temp2 & 7);
                    f.p = get_parity(pv);
                    ts_cnt += 5;
                }

                return;
            }

            return;

        } // endif (prefix_ext)

        if (prefix_bit) {
            // 00xxxxxx
            if ( (opcode & 0xc0 ) == 0x00 ) {
                // RLC r                ( 4 + 4 )
                // RLC (HL)             ( 4 + 4 + 3 + 3 ) + 1
                // RLC (IX + d)         ( 4 + 4 + 3 + 3 + 3 ) + 6
                // RLC (IY + d)         ( 4 + 4 + 3 + 3 + 3 ) + 6
                // * RLC (IX + d), r    ??? ( 4 + 4 + 3 + 3 + 3 ) + 6 ???
                // * RLC (IY + d), r    ??? ( 4 + 4 + 3 + 3 + 3 ) + 6 ???
                // RL r                 -//-
                // RL (HL)
                // RL (IX + d)
                // RL (IY + d)
                // * RL (IX + d), r
                // * RL (IY + d), r
                // RRC r
                // RRC (HL)
                // RRC (IX + d)
                // RRC (IY + d)
                // * RRC (IX + d), r
                // * RRC (IY + d), r
                // RR r
                // RR (HL)
                // RR (IX + d)
                // RR (IY + d)
                // * RR (IX + d), r
                // * RR (IY + d), r
                // SLA r
                // SLA (HL)
                // SLA (IX + d)
                // SLA (IY + d)
                // * SLA (IX + d), r
                // * SLA (IY + d), r
                // * SLL r
                // * SLL (HL)
                // * SLL (IX + d)
                // * SLL (IY + d)                
                // * SLL (IX + d), r
                // * SLL (IY + d), r
                // SRA r
                // SRA (HL)
                // SRA (IX + d)
                // SRA (IY + d)
                // * SRA (IX + d), r
                // * SRA (IY + d), r
                // SRL r
                // SRL (HL)
                // SRL (IX + d)
                // SRL (IY + d)
                // * SRL (IX + d), r
                // * SRL (IY + d), r

                var cmd_shift = !!(opcode & 0x20);
                var left = !(opcode & 0x08);
                var without_c = !(opcode & 0x10); // постфикс C при ротации, означает, что флаг C не участвует в ротации!
                var r1 = opcode & 0x07;

                var current;
                if (prefix_ix) {
                    current = read_mem_byte(( ix + index_offset_cache ) & 0xffff);
                }
                else if (prefix_iy) {
                    current = read_mem_byte(( iy + index_offset_cache ) & 0xffff);
                }
                else {
                    switch (r1) {
                        case 0x00: current = regs.b; break;
                        case 0x01: current = regs.c; break;
                        case 0x02: current = regs.d; break;
                        case 0x03: current = regs.e; break;
                        case 0x04: current = regs.h; break;
                        case 0x05: current = regs.l; break;
                        case 0x06: current = read_mem_byte(get_hl()); break;
                        case 0x07: current = a; break;
                    }
                }

                var extra;
                var result;
                if (left) {
                    // left
                    extra = !!(current & 0x80);
                    result = (current << 1) & 0xff;
                    if (cmd_shift) {
                        if ( without_c ) {
                            // SLA
                            // здесь дополнительных действий не требуется
                        }
                        else {
                            // SLL (не документирована)
                            result |= 0x01;
                        }
                        
                        
                    }
                    else {
                        // rotate
                        if ((!without_c && f.c) || (without_c && extra)) {
                            result |= 0x01;
                        }
                    }
                }
                else {
                    // right
                    extra = !!(current & 0x01);
                    result = (current >> 1);
                    if (cmd_shift) {
                        if (without_c) {
                            // SRA
                            // восстанавливаем значение 7-го бита
                            if (current & 0x80) {
                                result |= 0x80;
                            }
                        }
                        else {
                            // SRL
                            // здесь дополнительных действий не требуется
                        }
                    }
                    else {
                        // rotate
                        if ((!without_c && f.c) || (without_c && extra)) {
                            result |= 0x80;
                        }
                    }
                }

                if (prefix_ix) {
                    var index_address = (ix + index_offset_cache) & 0xFFFF;
                    write_mem_byte(index_address, result);
                    memptr = index_address;
                    ts_cnt += 3; // Indexed CB internal cycles; opcode fetch is counted separately.
                }
                else if (prefix_iy) {
                    var index_address = (iy + index_offset_cache) & 0xFFFF;
                    write_mem_byte(index_address, result);   
                    memptr = index_address;
                    ts_cnt += 3; // Indexed CB internal cycles; opcode fetch is counted separately.
                }

                switch (r1) {
                    case 0x00: regs.b = result; break;
                    case 0x01: regs.c = result; break;
                    case 0x02: regs.d = result; break;
                    case 0x03: regs.e = result; break;
                    case 0x04: regs.h = result; break;
                    case 0x05: regs.l = result; break;
                    case 0x06:
                        if (!prefix_ix && !prefix_iy) {
                            write_mem_byte(get_hl(), result);

                            ts_cnt += 1;
                        }
                        break;

                    case 0x07: a = result; break;
                }

                f.s = result & 0x80;
                f.z = !result;
                f.y = result & 0x20;
                f.h = 0;
                f.x = result & 0x08;
                f.p = get_parity(result);
                f.n = 0;
                f.c = extra;
                q = 1;

                return;
            }

            // 01xxxxxx
            if ( (opcode & 0xc0 ) == 0x40 ) {
                // BIT b, r             ( 4 + 4 )
                // BIT b, (HL)          ( 4 + 4 + 3 ) + 1
                // BIT b, (IX + d)      ( 4 + 4 + 3 + 3 ) + 6
                // BIT b, (IY + d)      ( 4 + 4 + 3 + 3 ) + 6

                var r_dst = opcode & 0x07;

                var value;
                var index_address;
                if (prefix_ix) {
                    index_address = ( ix + index_offset_cache ) & 0xFFFF;
                    value = read_mem_byte(index_address);
                    memptr = index_address;
                    ts_cnt += 3; // Indexed CB internal cycles; opcode fetch is counted separately.
                }
                else if (prefix_iy) {
                    index_address = ( iy + index_offset_cache ) & 0xFFFF;
                    value = read_mem_byte(index_address);
                    memptr = index_address;
                    ts_cnt += 3; // Indexed CB internal cycles; opcode fetch is counted separately.
                }
                else {
                    switch (r_dst) {
                        case 0x00: value = regs.b; break;
                        case 0x01: value = regs.c; break;
                        case 0x02: value = regs.d; break;
                        case 0x03: value = regs.e; break;
                        case 0x04: value = regs.h; break;
                        case 0x05: value = regs.l; break;
                        case 0x06: 
                            value = read_mem_byte(get_hl()); 
                            ts_cnt += 1;
                            break;

                        case 0x07: value = a; break;
                    }
                }

                var bit = (opcode >> 3) & 0x07;
                var mask = 0x01 << bit;
                var res = value & mask;

                f.s = (res & 0x80);
                f.z = !res; 
                f.h = 1;    
                f.p = !res; 
                f.n = 0;    
                if ( prefix_ix || prefix_iy ) {
                    f.y = index_address & 0x2000;
                    f.x = index_address & 0x0800;
                }
                else if (r_dst == 0x06) {
                    f.y = memptr & 0x2000;
                    f.x = memptr & 0x0800;
                }
                else {
                    f.y = value & 0x20;
                    f.x = value & 0x08;
                }
                q = 1;

                return;
            }

            // 1xxxxxxx
            if ( (opcode & 0x80 ) == 0x80 ) {
                // SET b, r                 ( 4 + 4 )
                // SET b, (HL)              ( 4 + 4 + 3 + 3 ) + 1
                // SET b, (IX + d)          ( 4 + 4 + 3 + 3 + 3 ) + 6
                // SET b, (IY + d)          ( 4 + 4 + 3 + 3 + 3 ) + 6
                // * SET b, (IX + d), r     ??? ( 4 + 4 + 3 + 3 + 3 ) + 6 ???
                // * SET b, (IY + d), r     ??? ( 4 + 4 + 3 + 3 + 3 ) + 6 ???
                // RES b, r                 -//-
                // RES b, (HL)
                // RES b, (IX + d)
                // RES b, (IY + d)
                // * RES b, (IX + d), r
                // * RES b, (IY + d), r

                var r_dst = opcode & 0x07;

                var value;
                if (prefix_ix) {
                    value = read_mem_byte(( ix + index_offset_cache ) & 0xffff);
                }
                else if (prefix_iy) {
                    value = read_mem_byte(( iy + index_offset_cache ) & 0xffff);
                }
                else {
                    switch (r_dst) {
                        case 0x00: value = regs.b; break;
                        case 0x01: value = regs.c; break;
                        case 0x02: value = regs.d; break;
                        case 0x03: value = regs.e; break;
                        case 0x04: value = regs.h; break;
                        case 0x05: value = regs.l; break;
                        case 0x06: value = read_mem_byte(get_hl()); break;
                        case 0x07: value = a; break;
                    }
                }

                var bit = (opcode >> 3) & 0x07;
                var mask = 0x01 << bit;
                var cmd_set = !!(opcode & 0x40);
                if (cmd_set) {
                    value |= mask;
                }
                else {
                    value &= (mask ^ 0xff);
                }

                if (prefix_ix) {
                    var index_address = ( ix + index_offset_cache ) & 0xFFFF;
                    write_mem_byte(index_address, value);
                    memptr = index_address;
                    ts_cnt += 3; // Indexed CB internal cycles; opcode fetch is counted separately.
                }
                else if (prefix_iy) {
                    var index_address = ( iy + index_offset_cache ) & 0xFFFF;
                    write_mem_byte(index_address, value);
                    memptr = index_address;
                    ts_cnt += 3; // Indexed CB internal cycles; opcode fetch is counted separately.
                }

                switch (r_dst) {
                    case 0x00: regs.b = value; break;
                    case 0x01: regs.c = value; break;
                    case 0x02: regs.d = value; break;
                    case 0x03: regs.e = value; break;
                    case 0x04: regs.h = value; break;
                    case 0x05: regs.l = value; break;
                    case 0x06:
                        if (!prefix_ix && !prefix_iy) {
                            write_mem_byte(get_hl(), value);

                            ts_cnt += 1;
                        }
                        break;

                    case 0x07: a = value; break;
                }
                q = 0;
                return;
            }

            return;

        } // endif (prefix_bit)

        if (opcode == 0) {
            // NOP                  ( 4 )
            q = 0;
            return;
        }

        // 01xxxxxx
        if ( ( opcode & 0xc0 ) == 0x40 ) {
            // LD r, r'             ( 4 )
            // LD r, (HL)           ( 7 )
            // LD (HL), r           ( 7 )
            // LD r, (IX + d)       ( 4 + 4 + 3 + 3 ) + 5
            // LD r, (IY + d)       ( 4 + 4 + 3 + 3 ) + 5
            // LD (IX + d), r       ( 4 + 4 + 3 + 3 ) + 5
            // LD (IY + d), r       ( 4 + 4 + 3 + 3 ) + 5
            // HALT                 ( 4 )
            // + недокументированные

            var r_dst = (opcode >> 3) & 0x07;
            var r_src = opcode & 0x07;    

            if ( r_src == 0x06 && r_dst == 0x06 ) {
                // HALT
                pc = ( pc - 1 ) & 0xffff;

                // ( 4 )
                q = 0;
                return;
            }

            var value;
            switch (r_src) {
                case 0x00: value = regs.b; break;
                case 0x01: value = regs.c; break;
                case 0x02: value = regs.d; break;
                case 0x03: value = regs.e; break;
                case 0x04: 
                    if (prefix_ix && r_dst != 0x06) {
                        value = get_ix_h();
                    }
                    else if (prefix_iy && r_dst != 0x06) {
                        value = get_iy_h();
                    }
                    else {
                        value = regs.h; 
                    }
                    break;

                case 0x05: 
                    if (prefix_ix && r_dst != 0x06) {
                        value = get_ix_l();
                    }
                    else if (prefix_iy && r_dst != 0x06) {
                        value = get_iy_l();
                    }
                    else {
                        value = regs.l; 
                    }
                    break;

                case 0x06:
                    var addr;
                    if (prefix_ix) {
                        var offset = byte_to_svalue(read_operand_byte());
                        addr = (ix + offset) & 0xffff;
                        memptr = addr;
                        ts_cnt += 5;
                    }
                    else if (prefix_iy) {
                        var offset = byte_to_svalue(read_operand_byte());
                        addr = (iy + offset) & 0xffff;
                        memptr = addr;
                        ts_cnt += 5;
                    }
                    else {
                        addr = get_hl();
                    }
                    value = read_mem_byte(addr); 
                    break;

                case 0x07: value = a; break;
            }

            switch (r_dst) {
                case 0x00: regs.b = value; break;
                case 0x01: regs.c = value; break;
                case 0x02: regs.d = value; break;
                case 0x03: regs.e = value; break;
                case 0x04: 
                    if (prefix_ix && r_src != 0x06) {
                        set_ix_h(value);
                    }
                    else if (prefix_iy && r_src != 0x06) {
                        set_iy_h(value);
                    }
                    else {
                        regs.h = value;
                    }
                    break;

                case 0x05: 
                    if (prefix_ix && r_src != 0x06) {
                        set_ix_l(value);
                    }
                    else if (prefix_iy && r_src != 0x06) {
                        set_iy_l(value);
                    }
                    else {
                        regs.l = value;
                    }
                    break;

                case 0x06: 
                    var addr;
                    if (prefix_ix) {
                        var offset = byte_to_svalue(read_operand_byte());
                        addr = (ix + offset) & 0xffff;
                        memptr = addr;
                        ts_cnt += 5;
                    }
                    else if (prefix_iy) {
                        var offset = byte_to_svalue(read_operand_byte());
                        addr = (iy + offset) & 0xffff;
                        memptr = addr;
                        ts_cnt += 5;
                    }
                    else {
                        addr = get_hl();
                    }
                    write_mem_byte(addr, value);
                    break;

                case 0x07: a = value; break;
            }
            q = 0;
            return;
        }

        // 00xxx110
        if ( ( opcode & 0xc7 ) == 0x06 ) {
            // LD r, n              ( 4 + 3 )
            // LD (HL), n           ( 4 + 3 + 3 )
            // LD (IX + d), n       ( 4 + 4 + 3 + 3 ) + 5
            // LD (IY + d), n       ( 4 + 4 + 3 + 3 ) + 5
            // + недокументированные

            var r_dst = (opcode >> 3) & 0x07;

            switch (r_dst) {
                case 0x00: regs.b = read_operand_byte(); break;
                case 0x01: regs.c = read_operand_byte(); break;
                case 0x02: regs.d = read_operand_byte(); break;
                case 0x03: regs.e = read_operand_byte(); break;
                case 0x04: 
                    if (prefix_ix) {
                        set_ix_h(read_operand_byte());
                    }
                    else if (prefix_iy) {
                        set_iy_h(read_operand_byte());
                    }
                    else {
                       regs.h = read_operand_byte();
                    }
                    break;

                case 0x05: 
                    if (prefix_ix) {
                        set_ix_l(read_operand_byte()); 
                    }
                    else if (prefix_iy) {
                        set_iy_l(read_operand_byte()); 
                    }
                    else {
                        regs.l = read_operand_byte();
                    }
                    break;

                case 0x06: 
                    var addr;
                    if (prefix_ix) {
                        var offset = byte_to_svalue(read_operand_byte());
                        addr = (ix + offset) & 0xffff;
                        memptr = addr;
                        ts_cnt += 2; // LD (IX/IY+d),n totals 19 T, including both operands.
                    }
                    else if (prefix_iy) {
                        var offset = byte_to_svalue(read_operand_byte());
                        addr = (iy + offset) & 0xffff;
                        memptr = addr;
                        ts_cnt += 2; // LD (IX/IY+d),n totals 19 T, including both operands.
                    }
                    else {
                        addr = get_hl();
                    }                    
                    write_mem_byte(addr, read_operand_byte()); 
                    break;

                case 0x07: a = read_operand_byte(); break;
            }
            q = 0;
            return;
        }

        // 00xxx010
        if ( (opcode & 0xc7 ) == 0x02 ) {
            // LD A, (BC)           ( 4 + 3 )
            // LD A, (DE)           ( 4 + 3 )
            // LD A, (nn)           ( 4 + 3 + 3 + 3 )
            // LD HL, (nn)          ( 4 + 3 + 3 + 3 + 3 )
            // LD IX, (nn)          ( 4 + 4 + 3 + 3 + 3 + 3 )
            // LD IY, (nn)          ( 4 + 4 + 3 + 3 + 3 + 3 )

            // LD (BC), A           ( 4 + 3 )
            // LD (DE), A           ( 4 + 3 )
            // LD (nn), A           ( 4 + 3 + 3 + 3 )
            // LD (nn), HL          ( 4 + 3 + 3 + 3 + 3 )
            // LD (nn), IX          ( 4 + 4 + 3 + 3 + 3 + 3 )
            // LD (nn), IY          ( 4 + 4 + 3 + 3 + 3 + 3 )

            var to_reg = !!(opcode & 0x08);
            var r_code = (opcode >> 4) & 0x03;

            if (to_reg) {
                var addr;
                switch (r_code) {
                    case 0x00: 
                        // A, (BC)
                        addr = get_bc();
                        a = read_mem_byte(addr);
                        break;

                    case 0x01:
                        // A, (DE)
                        addr = get_de();
                        a = read_mem_byte(addr);
                        break;

                    case 0x02:
                        // HL, (nn)
                        addr = read_operand_word();
                        var value = read_mem_word(addr);
                        if (prefix_ix) {
                            ix = value;
                        }
                        else if (prefix_iy) {
                            iy = value;
                        }
                        else {
                            set_hl(value);
                        }
                        break;

                    case 0x03:
                        // A, (nn)
                        addr = read_operand_word();
                        a = read_mem_byte(addr);
                        break;
                }
                memptr = (addr + 1) & 0xFFFF;
            }
            else {
                switch (r_code) {
                    case 0x00:
                        // (BC), A
                        var addr = get_bc();
                        write_mem_byte(addr, a);
                        memptr = (a << 8) | ((addr + 1) & 0xFF);
                        break;

                    case 0x01:
                        // (DE), A
                        var addr = get_de();
                        write_mem_byte(addr, a);
                        memptr = (a << 8) | ((addr + 1) & 0xFF);
                        break;

                    case 0x02:
                        // (nn), HL
                        var value;
                        if (prefix_ix) {
                            value = ix;
                        }
                        else if (prefix_iy) {
                            value = iy;
                        }
                        else {
                            value = get_hl();
                        }

                        var addr = read_operand_word();
                        write_mem_word(addr, value);
                        memptr = (addr + 1) & 0xFFFF;
                        break;

                    case 0x03:
                        // (nn), A
                        var addr = read_operand_word();
                        write_mem_byte(addr, a);
                        memptr = (a << 8) | ((addr + 1) & 0xFF);
                        break;
                }
            }
            q = 0;
            return;
        }

        // 00xx0001
        if ( ( opcode & 0xcf ) == 0x01 ) {
            // LD dd, nn        ( 4 + 3 + 3 )
            // LD IX, nn        ( 4 + 4 + 3 + 3 )
            // LD IY, nn        ( 4 + 4 + 3 + 3 )

            var value = read_operand_word();

            var dd = (opcode >> 4) & 0x03;
            switch (dd) {
                case 0x00: set_bc(value); break;
                case 0x01: set_de(value); break;
                case 0x02: 
                    if (prefix_ix) {
                        ix = value;
                    }
                    else if (prefix_iy) {
                        iy = value;
                    }
                    else {
                        set_hl(value); 
                    }
                    break;

                case 0x03: sp = value; break;
            }
            q = 0;
            return;
        }

        // 11xx0x01
        if ( (opcode & 0xcb) == 0xc1 ) {
            // PUSH qq          ( 4 + 3 + 3 ) + 1
            // PUSH IX          ( 4 + 4 + 3 + 3 ) + 1
            // PUSH IY          ( 4 + 4 + 3 + 3 ) + 1
            // POP qq           ( 4 + 3 + 3 )
            // POP IX           ( 4 + 4 + 3 + 3 )
            // POP IY           ( 4 + 4 + 3 + 3 )

            var to_reg = !(opcode & 0x04);
            var qq = (opcode >> 4) & 0x03;


            if (to_reg) {
                var value = read_mem_word(sp);
                sp = ( sp + 2 ) & 0xffff;

                switch (qq) {
                    case 0x00: set_bc(value); break;
                    case 0x01: set_de(value); break;
                    case 0x02:
                        if (prefix_ix) {
                            ix = value;
                        }
                        else if (prefix_iy) {
                            iy = value;
                        }
                        else {
                            set_hl(value);
                        }
                        break;

                    case 0x03: set_af(value); break;
                }
            }
            else {
                var value;
                switch (qq) {
                    case 0x00: value = get_bc(); break;
                    case 0x01: value = get_de(); break;
                    case 0x02:
                        if (prefix_ix) {
                            value = ix;
                        }
                        else if (prefix_iy) {
                            value = iy;
                        }
                        else {
                            value = get_hl();
                        }
                        break;

                    case 0x03:
                        value = get_af();
                        break;
                }

                sp = ( sp - 2 ) & 0xffff;
                write_mem_word(sp, value);

                ts_cnt += 1;
            }
            q = 0;
            return;
        }

        // 11111001
        if ( opcode == 0xf9 ) {
            // LD SP, HL        ( 4 ) + 2
            // LD SP, IX        ( 4 + 4 ) + 2
            // LD SP, IY        ( 4 + 4 ) + 2

            if (prefix_ix) {
                sp = ix;
            }
            else if (prefix_iy) {
                sp = iy;
            }
            else {
                sp = get_hl();
            }

            ts_cnt += 2;
            q = 0;
            return;
        }

        if ( opcode == 0xeb ) {
            // EX DE, HL        ( 4 )
            var value = get_hl();
            set_hl(get_de());
            set_de(value);
            q = 0;
            return;
        }

        if ( opcode == 0x08 ) {
            // EX AF, AF'       ( 4 )
            var t = a;
            a = a_;
            a_ = t;

            t = f;
            f = f_;
            f_ = t;
            q = 0;
            return;
        }

        if ( opcode == 0xd9 ) {
            // EXX              ( 4 )
            var t = regs;
            regs = regs_;
            regs_ = t;
            q = 0;
            return;
        }

        if ( opcode == 0xe3 ) {
            // EX (SP), HL      ( 4 + 3 + 3 + 3 + 3 ) + 3
            // EX (SP), IX      ( 4 + 4 + 3 + 3 + 3 + 3 ) + 3
            // EX (SP), IY      ( 4 + 4 + 3 + 3 + 3 + 3 ) + 3

            var value = read_mem_word(sp);
            if (prefix_ix) {
                write_mem_word(sp, ix);
                ix = value;
            }
            else if (prefix_iy) {
                write_mem_word(sp, iy);
                iy = value;
            }
            else {
                write_mem_word(sp, get_hl());
                set_hl(value);
            }

            q = 0;
            memptr = value;
            ts_cnt += 3;

            return;
        }

        // 10xxxxxx and 11xxx110
        if ( ( opcode & 0xc0 ) == 0x80 || ( opcode & 0xc7 ) == 0xc6 ) {
            // ADD A, r         ( 4 )
            // ADD A, n         ( 4 + 3 )
            // ADD A, (HL)      ( 4 + 3 )
            // ADD A, (IX + d)  ( 4 + 4 + 3 + 3 ) + 5
            // ADD A, (IY + d)  ( 4 + 4 + 3 + 3 ) + 5
            // ADC A, r         -//-
            // ADC A, n
            // ADC A, (HL)
            // ADC A, (IX + d)
            // ADC A, (IY + d)
            // SUB r
            // SUB n
            // SUB (HL)
            // SUB (IX + d)
            // SUB (IY + d)
            // SBC A, r
            // SBC A, n
            // SBC A, (HL)
            // SBC A, (IX + d)
            // SBC A, (IY + d)
            // AND r
            // AND n
            // AND (HL)
            // AND (IX + d)
            // AND (IY + d)
            // OR r
            // OR n
            // OR (HL)
            // OR (IX + d)
            // OR (IY + d)
            // XOR r
            // XOR n
            // XOR (HL)
            // XOR (IX + d)
            // XOR (IY + d)                
            // CP r
            // CP n
            // CP (HL)
            // CP (IX + d)
            // CP (IY + d)
            // + недокументированные

            var operand;

            var explicit_operand = !!(opcode & 0x40);
            if (explicit_operand) {
                operand = read_operand_byte(); // n
            }
            else {
                var r1 = opcode & 0x07;
                switch (r1) {
                    case 0x00: operand = regs.b; break; // B
                    case 0x01: operand = regs.c; break; // C
                    case 0x02: operand = regs.d; break; // D
                    case 0x03: operand = regs.e; break; // E
                    case 0x04: 
                        if (prefix_ix) {
                            operand = get_ix_h(); // IXh
                        }
                        else if (prefix_iy) {
                            operand = get_iy_h(); // IYh
                        }
                        else {
                            operand = regs.h; // H
                        }
                        break;

                    case 0x05: 
                        if (prefix_ix) {    
                            operand = get_ix_l(); // IXl
                        }
                        else if (prefix_iy) {
                            operand = get_iy_l(); // IYl
                        }
                        else {
                            operand = regs.l; // L
                        }
                        break;

                    case 0x06:
                        if (prefix_ix) {
                            var offset = byte_to_svalue(read_operand_byte()); // (IX + d)
                            var index_address = (ix + offset) & 0xFFFF;
                            operand = read_mem_byte(index_address);
                            memptr = index_address;
                            ts_cnt += 5;
                        }
                        else if (prefix_iy) {
                            var offset = byte_to_svalue(read_operand_byte()); // (IY + d)
                            var index_address = (iy + offset) & 0xFFFF;
                            operand = read_mem_byte(index_address);
                            memptr = index_address;
                            ts_cnt += 5;
                        }
                        else {
                            operand = read_mem_byte(get_hl()); // (HL)
                        }
                        break;

                    case 0x07: operand = a; break; // A
                }
            }

            var logic = !!(opcode & 0x20);
            if (logic) { // logic
                var subcode = (opcode >> 3) & 0x03;

                switch (subcode) {
                    case 0x00:
                        // AND
                        a &= operand;
                        f.s = a & 0x80;
                        f.z = !a;
                        f.y = a & 0x20;
                        f.h = 1;
                        f.x = a & 0x08;
                        f.p = get_parity(a);
                        f.n = 0;
                        f.c = 0;
                        break;

                    case 0x01:
                        // XOR
                        a ^= operand;
                        f.s = a & 0x80;
                        f.z = !a;
                        f.y = a & 0x20;
                        f.h = 0;
                        f.x = a & 0x08;
                        f.p = get_parity(a);
                        f.n = 0;
                        f.c = 0;
                        break;

                    case 0x02:
                        // OR
                        a |= operand;
                        f.s = a & 0x80;
                        f.z = !a;
                        f.y = a & 0x20;
                        f.h = 0;
                        f.x = a & 0x08;
                        f.p = get_parity(a);
                        f.n = 0;
                        f.c = 0;
                        break;

                    case 0x03:
                        // CP
                        var diff = a - operand;
                        var borrow = diff < 0;
                        diff &= 0xff;

                        // при выполнении CP флаги X и Y устанавливаются на основе аргумента, а не результата
                        f.s = diff & 0x80;
                        f.z = !diff;
                        f.y = operand & 0x20;
                        f.h = (a & 0x0f) - (operand & 0x0f) < 0;
                        f.x = operand & 0x08;
                        f.p = get_byte_diff_overflow(a, operand, diff);
                        f.n = 1;
                        f.c = borrow;
                        break;
                }
            }
            else { // arithmetic
                var carry_op = !!(opcode & 0x08);
                var add_op = !(opcode & 0x10);
                var carry_value = carry_op && f.c ? 1 : 0;
                var old_a = a;

                if (add_op) {
                    a += (operand + carry_value);
                    var care = a & 0x100;
                    a &= 0xff;

                    f.s = a & 0x80;
                    f.z = !a;
                    f.y = a & 0x20;
                    f.h = ((old_a & 0x0f) + (operand & 0x0f) + carry_value) & 0x10;
                    f.x = a & 0x08;
                    f.p = get_byte_sum_overflow(old_a, operand, a);
                    f.n = 0;
                    f.c = care;
                }
                else { // subtraction
                    a -= (operand + carry_value);
                    var borrow = a < 0;
                    a &= 0xff;

                    f.s = a & 0x80;
                    f.z = !a;
                    f.y = a & 0x20;
                    f.h = (old_a & 0x0f) - (operand & 0x0f) - carry_value < 0;
                    f.x = a & 0x08;
                    f.p = get_byte_diff_overflow(old_a, operand, a);
                    f.n = 1;
                    f.c = borrow;
                }
            }

            q = 1;
            return;
        }

        // 00xxx10x
        if ( (opcode & 0xc6 ) == 0x04 ) {
            // INC r            ( 4 )
            // INC (HL)         ( 4 + 3 + 3 ) + 1
            // INC (IX + d)     ( 4 + 4 + 3 + 3 + 3 ) + 6
            // INC (IY + d)     ( 4 + 4 + 3 + 3 + 3 ) + 6
            // DEC r            -//-
            // DEC (HL)
            // DEC (IX + d)
            // DEC (IY + d)
            // + недокументированные

            var r1 = (opcode >> 3) & 0x07;
            var cmd_inc = !(opcode & 0x01);
            if (cmd_inc) {
                var operand;
                var result;
                switch (r1) {
                    case 0x00:
                        // B
                        operand = regs.b;
                        result = (operand + 1) & 0xff;
                        regs.b = result;
                        break;

                    case 0x01:
                        // C
                        operand = regs.c;
                        result = (operand + 1) & 0xff;
                        regs.c = result;
                        break;

                    case 0x02:
                        // D
                        operand = regs.d;
                        result = (operand + 1) & 0xff;
                        regs.d = result;
                        break;

                    case 0x03:
                        // E
                        operand = regs.e;
                        result = (operand + 1) & 0xff;
                        regs.e = result;
                        break;

                    case 0x04:
                        if (prefix_ix) {
                            // IXh
                            operand = get_ix_h();
                            result = (operand + 1) & 0xff;
                            set_ix_h(result);
                        }
                        else if (prefix_iy) {
                            // IYh
                            operand = get_iy_h();
                            result = (operand + 1) & 0xff;
                            set_iy_h(result);
                        }
                        else {
                            // H
                            operand = regs.h;
                            result = (operand + 1) & 0xff;
                            regs.h = result;
                        }
                        break;

                    case 0x05:
                        if (prefix_ix) {
                            // IXl
                            operand = get_ix_l();
                            result = (operand + 1) & 0xff;
                            set_ix_l(result);
                        }
                        else if (prefix_iy) {
                            // IYl
                            operand = get_iy_l();
                            result = (operand + 1) & 0xff;
                            set_iy_l(result);
                        }
                        else {
                            // L
                            operand = regs.l;
                            result = (operand + 1) & 0xff;
                            regs.l = result;
                        }
                        break;   

                    case 0x06:
                        var addr;
                        if (prefix_ix) {
                            // (IX + d)
                            addr = ( ix + byte_to_svalue(read_operand_byte()) ) & 0xffff;
                            memptr = addr;
                            ts_cnt += 6;
                        }
                        else if (prefix_iy) {
                            // (IY + d)
                            addr = ( iy + byte_to_svalue(read_operand_byte()) ) & 0xffff;
                            memptr = addr;
                            ts_cnt += 6;
                        }
                        else {
                            // (HL)
                            addr = get_hl();

                            ts_cnt += 1;
                        }

                        operand = read_mem_byte(addr);
                        result = (operand + 1) & 0xff;
                        write_mem_byte(addr, result);
                        break;

                    case 0x07:
                        // A
                        operand = a;
                        result = (operand + 1) & 0xff;
                        a = result;
                        break;                            
                }

                f.s = result & 0x80;
                f.z = !result;
                f.y = result & 0x20;
                f.h = (operand & 0x0f) == 0x0f;
                f.x = result & 0x08;
                f.p = operand == 0x7f;
                f.n = 0;
            }
            else {
                var operand;
                var result;
                switch (r1) {
                    case 0x00:
                        // B
                        operand = regs.b;
                        result = (operand - 1) & 0xff;
                        regs.b = result;
                        break;

                    case 0x01:
                        // C
                        operand = regs.c;
                        result = (operand - 1) & 0xff;
                        regs.c = result;
                        break;

                    case 0x02:
                        // D
                        operand = regs.d;
                        result = (operand - 1) & 0xff;
                        regs.d = result;
                        break;

                    case 0x03:
                        // E
                        operand = regs.e;
                        result = (operand - 1) & 0xff;
                        regs.e = result;
                        break;

                    case 0x04:
                        if (prefix_ix) {
                            // IXh
                            operand = get_ix_h();
                            result = (operand - 1) & 0xff;
                            set_ix_h(result);
                        }
                        else if (prefix_iy) {
                            // IYh
                            operand = get_iy_h();
                            result = (operand - 1) & 0xff;
                            set_iy_h(result);
                        }
                        else {
                            // H
                            operand = regs.h;
                            result = (operand - 1) & 0xff;
                            regs.h = result;
                        }
                        break;

                    case 0x05:
                        if (prefix_ix) {
                            // IXl
                            operand = get_ix_l();
                            result = (operand - 1) & 0xff;
                            set_ix_l(result);
                        }
                        else if (prefix_iy) {
                            // IYl
                            operand = get_iy_l();
                            result = (operand - 1) & 0xff;
                            set_iy_l(result);
                        }
                        else {
                            // L
                            operand = regs.l;
                            result = (operand - 1) & 0xff;
                            regs.l = result;
                        }
                        break;   

                    case 0x06:
                        var addr;
                        if (prefix_ix) {
                            // (IX + d)
                            addr = ( ix + byte_to_svalue(read_operand_byte()) ) & 0xffff;
                            memptr = addr;
                            ts_cnt += 6;
                        }
                        else if (prefix_iy) {
                            // (IY + d)
                            addr = ( iy + byte_to_svalue(read_operand_byte()) ) & 0xffff;
                            memptr = addr;
                            ts_cnt += 6;
                        }
                        else {
                            // (HL)
                            addr = get_hl();

                            ts_cnt += 1;
                        }      
                        
                        operand = read_mem_byte(addr);
                        result = (operand - 1) & 0xff;
                        write_mem_byte(addr, result);                                      
                        break;

                    case 0x07:
                        // A
                        operand = a;
                        result = (operand - 1) & 0xff;
                        a = result;
                        break;                            
                }

                f.s = result & 0x80;
                f.z = !result;
                f.y = result & 0x20;
                f.h = !(operand & 0x0f);
                f.x = result & 0x08;
                f.p = operand == 0x80;
                f.n = 1;
            }
            q = 1;
            return;
        }

        // 1111x011
        if ( (opcode & 0xf7 ) == 0xf3 ) {
            // DI           ( 4 )
            // EI           ( 4 )

            var allow_int = !!(opcode & 0x08);
            set_iff1(allow_int);
            set_iff2(allow_int);
            int_lock = 1;
            q = 0;
            return;
        }

        // 00100111
        if ( opcode == 0x27 ) {
            // DAA          ( 4 )
            // https://stackoverflow.com/questions/8119577/z80-daa-instruction/57837042#57837042
            
            var t = 0;
            if (f.h || (a & 0x0F) > 0x09) {
                t++;
            }
            if (f.c || a > 0x99) {
                t += 2;
                f.c = 1;
            }

            if (f.n && !f.h) {
                f.h = 0;
            }
            else if (f.n && f.h) {
                f.h = (a & 0x0F) < 0x06;
            }
            else {
                f.h = (a & 0x0F) > 0x09;
            }

            switch (t) {
                case 1: a = (a + (f.n ? 0xFA : 0x06)) & 0xFF; break;
                case 2: a = (a + (f.n ? 0xA0 : 0x60)) & 0xFF; break;
                case 3: a = (a + (f.n ? 0x9A : 0x66)) & 0xFF; break;
            }

            f.s = a & 0x80;
            f.z = !a;
            f.y = a & 0x20;
            f.x = a & 0x08;
            f.p = get_parity(a);
            q = 1;
            return;
        }
        
        // 00101111
        if ( opcode == 0x2f ) {
            // CPL          ( 4 )

            a ^= 0xff;
            f.y = a & 0x20;
            f.h = 1;
            f.x = a & 0x08;
            f.n = 1;
            q = 1;
            return;
        }

        // 00111111
        if ( opcode == 0x3f ) {
            // CCF          ( 4 )

            f.h = f.c;
            f.n = 0;
            f.c = !f.c;
            if (q) {
                f.y = a & 0x20;
                f.x = a & 0x08;
            }
            else {
                f.y |= a & 0x20;
                f.x |= a & 0x08;
            }
            q = 1;
            return;
        }

        // 00110111
        if ( opcode == 0x37 ) {
            // SCF          ( 4 )

            f.h = 0;
            f.n = 0;
            f.c = 1;
            if (q) {
                f.y = a & 0x20;
                f.x = a & 0x08;
            }
            else {
                f.y |= a & 0x20;
                f.x |= a & 0x08;
            }
            q = 1;
            return;
        }

        // 00xx1001
        if ( ( opcode & 0xcf ) == 0x09 ) {
            // ADD HL, ss   ( 4 ) + 7
            // ADD IX, pp   ( 4 + 4 ) + 7
            // ADD IY, rr   ( 4 + 4 ) + 7

            var ss = (opcode >> 4) & 0x03;
            var operand;
            switch (ss) {
                case 0x00: operand = get_bc(); break; // BC
                case 0x01: operand = get_de(); break; // DE
                case 0x02:
                    if (prefix_ix) {
                        operand = ix; // IX
                    }
                    else if (prefix_iy) {
                        operand = iy; // IY
                    }
                    else {
                        operand = get_hl(); // HL
                    }
                    break;

                case 0x03: operand = sp; break; // SP
            }

            var current;
            if (prefix_ix) {
                current = ix;
            }
            else if (prefix_iy) {
                current = iy;
            }
            else {
                current = get_hl();
            }

            var result = current + operand;
            var care = result & 0x10000;
            result &= 0xffff;

            if (prefix_ix) {
                ix = result;
            }
            else if (prefix_iy) {
                iy = result;
            }
            else {
                set_hl(result);
            }

            f.y = result & 0x2000;
            f.h = ((current & 0x0fff) + (operand & 0x0fff)) & 0x1000;
            f.x = result & 0x0800;
            f.n = 0;
            f.c = care;
            q = 1;
            memptr = (current + 1) & 0xFFFF;

            ts_cnt += 7;

            return;
        }

        // 00xxx011
        if ( (opcode & 0xc7 ) == 0x03 ) {
            // INC ss       ( 4 ) + 2
            // INC IX       ( 4 + 4 ) + 2
            // INC IY       ( 4 + 4 ) + 2
            // DEC ss       -//-
            // DEC IX
            // DEC IY

            var cmd_inc = !(opcode & 0x08);
            var ss = (opcode >> 4) & 0x03;

            if (cmd_inc) {
                switch (ss) {
                    case 0x00: set_bc(( get_bc() + 1 ) & 0xffff ); break; // BC
                    case 0x01: set_de(( get_de() + 1 ) & 0xffff ); break; // DE
                    case 0x02:
                        if (prefix_ix) {
                            ix = ( ix + 1 ) & 0xffff; // IX
                        }
                        else if (prefix_iy) {
                            iy = ( iy + 1 ) & 0xffff; // IY
                        }
                        else {
                            set_hl(( get_hl() + 1 ) & 0xffff ); // HL
                        }
                        break;

                    case 0x03: sp = ( sp + 1 ) & 0xffff; break; // SP
                }
            }
            else {
                switch (ss) {
                    case 0x00: set_bc(( get_bc() - 1 ) & 0xffff ); break; // BC
                    case 0x01: set_de(( get_de() - 1 ) & 0xffff ); break; // DE
                    case 0x02:
                        if (prefix_ix) {
                            ix = ( ix - 1 ) & 0xffff; // IX
                        }
                        else if (prefix_iy) {
                            iy = ( iy - 1 ) & 0xffff; // IY
                        }
                        else {
                            set_hl(( get_hl() - 1 ) & 0xffff ); // HL
                        }
                        break;

                    case 0x03: sp = ( sp - 1 ) & 0xffff; break; // SP
                }
            }

            q = 0;
            ts_cnt += 2;
            return;
        }

        // 000xx111
        if ( (opcode & 0xe7 ) == 0x07 ) {
            // RLCA         ( 4 )
            // RLA          ( 4 )
            // RRCA         ( 4 )
            // RRA          ( 4 )

            var left = !(opcode & 0x08);
            var without_c = !(opcode & 0x10); // постфикс C указывает, что флаг C не участвует в ротации!

            var extra;
            if (left) {
                extra = !!(a & 0x80);
                a = ( a << 1 ) & 0xff;
                if ((!without_c && f.c) || (without_c && extra)) {
                    a |= 0x01;
                }
            }
            else {
                extra = !!(a & 0x01);
                a = ( a >> 1 );
                if ((!without_c && f.c) || (without_c && extra)) {
                    a |= 0x80;
                }
            }

            f.y = a & 0x20;
            f.h = 0;
            f.x = a & 0x08;
            f.n = 0;
            f.c = extra;
            q = 1;

            return;
        }

        // 11000011
        if ( opcode == 0xc3 ) {
            // JP nn        ( 4 + 3 + 3 )

            var addr = read_operand_word();
            pc = addr;
            q = 0;
            memptr = pc;
            return;
        }

        // 11xxx010
        if ( ( opcode & 0xc7 ) == 0xc2 ) {
            // JP cc, nn    ( 4 + 3 + 3 )

            var condition_code = (opcode >> 3) & 0x07;

            var condition;
            switch (condition_code) {
                case 0x00: condition = !f.z; break; // NZ
                case 0x01: condition = f.z; break; // Z
                case 0x02: condition = !f.c; break; // NC
                case 0x03: condition = f.c; break; // C
                case 0x04: condition = !f.p; break; // PO
                case 0x05: condition = f.p; break; // PE
                case 0x06: condition = !f.s; break; // P
                case 0x07: condition = f.s; break; // M
            }

            var addr = read_operand_word();
            if ( condition ) {
                pc = addr;
            }
            q = 0;
            memptr = addr;
            return;
        }

        // 00xxx000 where xxx >= 010
        if ( ( opcode & 0xc7 ) == 0x00 && ( opcode & 0x38 ) >= 0x10 ) {
            // JR e         ( 4 + 3 ) + 5
            // JR C, e      ( 4 + 3 ) + 5?
            // JR NC, e     ( 4 + 3 ) + 5?
            // JR Z, e      ( 4 + 3 ) + 5?
            // JR NZ, e     ( 4 + 3 ) + 5?
            // DJNZ e       ( 4 + 3 ) + 1 + 5?

            var condition_code = (opcode >> 3) & 0x07;

            var condition;
            switch (condition_code) {
                case 0x02:
                    // DJNZ e
                    regs.b = ( regs.b - 1 ) & 0xff;
                    condition = !!regs.b; // B != 0

                    ts_cnt += 1;
                    break;

                case 0x03: condition = true; break; // JR e
                case 0x04: condition = !f.z; break; // JR NZ, e
                case 0x05: condition = f.z; break; // JR Z, e
                case 0x06: condition = !f.c; break; // JR NC, e
                case 0x07: condition = f.c; break; // JR C, e
            }

            var offset = byte_to_svalue(read_operand_byte());
            if ( condition ) {
                pc = ( pc + offset ) & 0xffff;
                memptr = pc;
                ts_cnt += 5;
            }
            q = 0;
            return;
        }

        // 11101001
        if ( opcode == 0xe9 ) {
            // JP (HL)      ( 4 )
            // JP (IX)      ( 4 + 4 )
            // JP (IY)      ( 4 + 4 )
            // * это не косвенная адресация, читать мнемонику без скобок!

            if (prefix_ix) {
                pc = ix;
            }
            else if (prefix_iy) {
                pc = iy;
            }
            else {
                pc = get_hl();
            }
            q = 0;
            return;
        }

        // 11001101
        if ( opcode == 0xcd ) {
            // CALL nn      ( 4 + 3 + 3 + 3 + 3 ) + 1

            var addr = read_operand_word();

            sp = ( sp - 2 ) & 0xffff;
            write_mem_word(sp, pc);
            pc = addr;

            q = 0;
            memptr = pc;
            ts_cnt += 1;
            return;
        }

        // 11xxx100
        if ( ( opcode & 0xc7 ) == 0xc4 ) {
            // CALL cc, nn  ( 4 + 3 + 3 + 3? + 3? ) + 1?

            var condition_code = (opcode >> 3) & 0x07;

            var condition;
            switch (condition_code) {
                case 0x00: condition = !f.z; break; // NZ
                case 0x01: condition = f.z; break; // Z
                case 0x02: condition = !f.c; break; // NC
                case 0x03: condition = f.c; break; // C
                case 0x04: condition = !f.p; break; // PO
                case 0x05: condition = f.p; break; // PE
                case 0x06: condition = !f.s; break; // P
                case 0x07: condition = f.s; break; // M
            }

            var addr = read_operand_word();

            if ( condition ) {
                sp = ( sp - 2 ) & 0xffff;
                write_mem_word(sp, pc);
                pc = addr;

                ts_cnt += 1;
            }
            q = 0;
            memptr = addr;
            return;
        }

        // 11001001
        if ( opcode == 0xc9 ) {
            // RET          ( 4 + 3 + 3 )

            pc = read_mem_word(sp);
            sp = ( sp + 2 ) & 0xffff;
            q = 0;
            memptr = pc;
            return;
        }

        // 11xxx000
        if ( ( opcode & 0xc7 ) == 0xc0 ) {
            // RET cc       ( 4 + 3? + 3? ) + 1

            var condition_code = (opcode >> 3) & 0x07;

            var condition;
            switch (condition_code) {
                case 0x00: condition = !f.z; break; // NZ
                case 0x01: condition = f.z; break; // Z
                case 0x02: condition = !f.c; break; // NC
                case 0x03: condition = f.c; break; // C
                case 0x04: condition = !f.p; break; // PO
                case 0x05: condition = f.p; break; // PE
                case 0x06: condition = !f.s; break; // P
                case 0x07: condition = f.s; break; // M
            }

            if ( condition ) {
                pc = read_mem_word(sp);
                sp = ( sp + 2 ) & 0xffff;
                memptr = pc;
            }
            q = 0;
            ts_cnt += 1;
            return;
        }

        // 11xxx111
        if ( (opcode & 0xc7 ) == 0xc7 ) {
            // RST p        ( 4 + 3 + 3 ) + 1

            var rst_code = (opcode >> 3) & 0x07;
            var addr = rst_code << 3; // code * 8

            sp = ( sp - 2 ) & 0xffff;
            write_mem_word(sp, pc);
            pc = addr;
            q = 0;
            memptr = pc;
            ts_cnt += 1;
            return;
        }

        // 1101x011
        if ( ( opcode & 0xf7 ) == 0xd3 ) {
            // IN A, (n)    ( 4 + 3 + 4 )
            // OUT (n), A   ( 4 + 3 + 4 )

            var port_low = read_operand_byte();
            var port_high = a;
            var port = (port_high << 8) | port_low;

            var cmd_in = !!(opcode & 0x08);
            if (cmd_in) {
                // IN
                memptr = ((a << 8) + port_low + 1) & 0xFFFF;
                a = read_io_byte(port);
            }
            else {
                // OUT
                write_io_byte(port, a);
                memptr = (a << 8) | ((port_low + 1) & 0xFF);
            }
            q = 0;
            return;
        }        
    }

    /////////////////////////////
    // вспомогательные функции //
    /////////////////////////////

    function byte_to_svalue( value ) {
        if ( value & 0x80 ) {
            return -((value ^ 0xff) + 1);
        }
        else {
            return value;
        }
    }

    function get_parity(value) {
        var half = (value >> 4) ^ (value & 0x0F);
        var quarter = (half >> 2) ^ (half & 0x03);
        return !((quarter >> 1) ^ (quarter & 0x01));
    }

    function get_byte_sum_overflow(op1, op2, sum) {
        if ((op1 ^ op2) & 0x80) {
            return false;
        }
        else {
            if ((op1 ^ sum) & 0x80) {
                return true;
            }
            else {
                return false;
            }
        }
    }

    function get_byte_diff_overflow(op1, op2, diff) {
        if ((op1 ^ op2) & 0x80) {
            if ((op1 ^ diff) & 0x80) {
                return true;
            }
            else {
                return false;
            }
        }
        else {
            return false;
        }
    }

    function get_word_sum_overflow(op1, op2, sum) {
        if ((op1 ^ op2) & 0x8000) {
            return false;
        }
        else {
            if ((op1 ^ sum) & 0x8000) {
                return true;
            }
            else {
                return false;
            }
        }        
    }

    function get_word_diff_overflow(op1, op2, diff) {
        if ((op1 ^ op2) & 0x8000) {
            if ((op1 ^ diff) & 0x8000) {
                return true;
            }
            else {
                return false;
            }
        }
        else {
            return false;
        }
    }

    ////////////////////////////////
    // функции запроса прерываний //
    ////////////////////////////////

    // Ставит запрос на немаскируемое прерывание, 
    // который будет обработан при следующем (или
    // после следующем) вызове метода process()
    function nmirq() {
        nmi_request = 1;
    }  

    // intrq(active);
    // Переводит линию intrq в активное или неактивное
    // состояние. Прерывание будет обработано только в
    // том случае, если во время активности линии у
    // процессора будет включена обработка маскируемых
    // прерываний, а также, если этому не будут
    // препятствовать выполняемые в настоящий момент
    // инструкции. 
    function intrq(active) {
        int_request = active;
    }

    ////////////////////
    // функция сброса //
    ////////////////////

    // reset();
    // Заново инициализирует процессор. После
    // сброса устанавливается режим прерываний 0,
    // запрещаются маскируемые прерывания, ре-
    // гистры AF и SP устанавливаются в 0xFFFF,
    // регистры IR и PC устанавливаются в 0x0000.
    // Значение остальных регистров не определено.
    function reset() {
        set_iff1(false);
        set_iff2(false);
        int_request = 0;
        nmi_request = 0;
        pc = 0x0000;
        i = 0;
        r = 0;
        imf = 0x00; // IM 0
        sp = 0xffff;
        a = 0xff;
        f.set(0xff);
        a_ = 0xff;
        f_.set(0xff);
        prefix_ix = false;
        prefix_iy = false;
        prefix_ext = false;
        prefix_bit = false;
    }

    ///////////////////////////////////
    // функции для отладки и снимков //
    ///////////////////////////////////

    function get_state() {
        var state = {};

        state.af_ = ( a_ << 8 ) | f_.get();
        state.bc_ = ( regs_.b << 8 ) | regs_.c;
        state.de_ = ( regs_.d << 8 ) | regs_.e;
        state.hl_ = ( regs_.h << 8 ) | regs_.l;

        state.af = ( a << 8 ) | f.get();
        state.bc = ( regs.b << 8 ) | regs.c;
        state.de = ( regs.d << 8 ) | regs.e;
        state.hl = ( regs.h << 8 ) | regs.l;

        state.ix = ix;
        state.iy = iy;

        state.sp = sp;
        state.pc = pc;

        state.r = r;
        state.i = i;

        state.memptr = memptr;
        state.q = q;
        state.imf = imf;
        state.iff = iff;

        state.prefix_dd = prefix_ix;
        state.prefix_fd = prefix_iy;
        state.prefix_ed = prefix_ext;
        state.prefix_cb = prefix_bit;

        return state;        
    }

    function set_state( state ) {
        a_ = ( state.af_ >> 8 );
        f_.set( state.af_ & 0xff );
        regs_.b = ( state.bc_ >> 8 );
        regs_.c = ( state.bc_ & 0xff );
        regs_.d = ( state.de_ >> 8 );
        regs_.e = ( state.de_ & 0xff );
        regs_.h = ( state.hl_ >> 8 );
        regs_.l = ( state.hl_ & 0xff );

        a = ( state.af >> 8 );
        f.set( state.af & 0xff );
        regs.b = ( state.bc >> 8 );
        regs.c = ( state.bc & 0xff );
        regs.d = ( state.de >> 8 );
        regs.e = ( state.de & 0xff );
        regs.h = ( state.hl >> 8 );
        regs.l = ( state.hl & 0xff );

        ix = state.ix;
        iy = state.iy;

        sp = state.sp;
        pc = state.pc;

        r = state.r;
        i = state.i;

        memptr = state.memptr ?? 0;
        q = state.q ?? 0;
        imf = state.imf;
        iff = state.iff;

        prefix_ix = state.prefix_dd;
        prefix_iy = state.prefix_fd;
        prefix_ext = state.prefix_ed;
        prefix_bit = state.prefix_cb;
    }

    ///////////////////////
    // внешний интерфейс //
    ///////////////////////

    // process();
    // Считывает очередную инструкцию из памяти и
    // либо выполняет команду, либо устанавливает
    // флаг какого-то из командных префиксов.
    // Также при поступлении запроса на прерывание,
    // выполняется проверка возможности его удовле-
    // творить, и, в случае успеха, выполняется
    // переход в процедуру обработки.
    this.process = process;

    // get_state();
    // Возвращает объект с внутренним состоянием
    // регистров и триггеров процессора
    this.get_state = get_state;

    // set_state( state );
    // Устанавливает внутреннее состояние процессора
    // в соответствии с переданным объектом state:
    // {
    //    af_: ...,
    //    bc_: ...,
    //    de_: ...,
    //    hl_: ...,
    //
    //    af: ...,
    //    bc: ...,
    //    de: ...,
    //    hl: ...,
    //
    //    ix: ...,
    //    iy: ...,
    //
    //    sp: ...,
    //    pc: ...,
    //
    //    r: ...,
    //    i: ...,
    //
    //    imf: ...,
    //    iff: ...,
    //
    //    prefix_dd: ...,
    //    prefix_fd: ...,
    //    prefix_ed: ...,
    //    prefix_cb: ...    
    // }
    this.set_state = set_state;

    this.get_tstates = function() { return ts_cnt; }
    this.set_tstates = function( value ) { ts_cnt = value; }

    this.connect = function (bus) {
        _bus = bus;
        _bus.on_reset(reset);
        _bus.on_var_write(function () { nmirq(); }, 'nmirq');
        _bus.on_var_write(function (name, value) { intrq(value); }, 'intrq');
    }
}
// Upstream module: hardware/bus.js
function ZX_Bus() {
	'use strict';

	var instruction_read_handlers = [];
	var memReadHandlers = [];
	var memWriteHandlers = [];
	var ioReadHandlers = [];
	var ioWriteHandlers = [];
	var varReadHandlers = [];
	var varWriteHandlers = [];
	var namedVarReadHandlers = {};
	var namedVarWriteHandlers = {};
	var resetHandlers = [];
	var optHandlers = [];
	var namedOptHandlers = [];

	function registerHandler(collection, fn) {
		collection.push(fn);
	}

	function onInstructionRead(fn, filter) {
		registerHandler(instruction_read_handlers, { fn: fn, filter: filter });
	}

	function onMemRead(fn, filter) {
		registerHandler(memReadHandlers, { fn: fn, filter: filter });
	}

	function onMemWrite(fn, filter) {
		registerHandler(memWriteHandlers, { fn: fn, filter: filter });
	}

	function onIoRead(fn, filter) {
		registerHandler(ioReadHandlers, { fn: fn, filter: filter });
	}

	function onIoWrite(fn, filter) {
		registerHandler(ioWriteHandlers, { fn: fn, filter: filter });
	}

	function onVarRead(fn, name) {
		var handlers = varReadHandlers;
		if (!!name) {
			handlers = namedVarReadHandlers[name] || (namedVarReadHandlers[name] = []);
		}
		registerHandler(handlers, fn);
	}

	function onVarWrite(fn, name) {
		var handlers = varWriteHandlers;
		if (!!name) {
			handlers = namedVarWriteHandlers[name] || (namedVarWriteHandlers[name] = []);
		}
		registerHandler(handlers, fn);
	}

	function onReset(fn) {
		registerHandler(resetHandlers, fn);
	}

	function onOpt(fn, name) {
		var handlers = optHandlers;
		if (!!name) {
			handlers = namedOptHandlers[name] || (namedOptHandlers[name] = []);
		}
		registerHandler(handlers, fn);
	}

	function instructionRead(address) {
		var result;
		for ( var i = 0; i < instruction_read_handlers.length; i++ ) {
			var hndInfo = instruction_read_handlers[i];
			var process = !hndInfo.filter
				|| hndInfo.filter.range && hndInfo.filter.range.begin <= address && address <= hndInfo.filter.range.end
				|| (hndInfo.filter.mask !== undefined) && (address & hndInfo.filter.mask) == hndInfo.filter.value;
			if (process) {
				var subresult = hndInfo.fn(address);
				if (subresult !== undefined) {
					result = subresult;
				}
			}
		}
		return result;
	}

	function memRead(address) {
		var result = 0xff;
		for ( var i = 0; i < memReadHandlers.length; i++ ) {
			var hndInfo = memReadHandlers[i];
			var process = !hndInfo.filter
				|| hndInfo.filter.range && hndInfo.filter.range.begin <= address && address <= hndInfo.filter.range.end
				|| (hndInfo.filter.mask !== undefined) && (address & hndInfo.filter.mask) == hndInfo.filter.value;
			if (process) {
				var subresult = hndInfo.fn(address);
				if (subresult !== undefined) {
					result = subresult;
				}
			}
		}
		return result;
	}

	function memWrite(address, data) {
		for ( var i = 0; i < memWriteHandlers.length; i++ ) {
			var hndInfo = memWriteHandlers[i];
			var process = !hndInfo.filter
				|| hndInfo.filter.range && hndInfo.filter.range.begin <= address && address <= hndInfo.filter.range.end
				|| (hndInfo.filter.mask !== undefined) && (address & hndInfo.filter.mask) == hndInfo.filter.value;
			if (process) {
				hndInfo.fn(address, data);
			}
		}
	}

	function ioRead(address) {
		var result = 0xFF;
		for ( var i = 0; i < ioReadHandlers.length; i++ ) {
			var hndInfo = ioReadHandlers[i];
			var process = !hndInfo.filter
				|| (hndInfo.filter.mask !== undefined) && (address & hndInfo.filter.mask) == hndInfo.filter.value
				|| hndInfo.filter.range && hndInfo.filter.range.begin <= address && address <= hndInfo.filter.range.end;
			if (process) {
				var subresult = hndInfo.fn(address);
				if (subresult !== undefined) {
					result &= subresult;
				}
			}
		}
		return result;
	}

	function ioWrite(address, data) {
		for ( var i = 0; i < ioWriteHandlers.length; i++ ) {
			var hndInfo = ioWriteHandlers[i];
			var process = !hndInfo.filter
				|| (hndInfo.filter.mask !== undefined) && (address & hndInfo.filter.mask) == hndInfo.filter.value
				|| hndInfo.filter.range && hndInfo.filter.range.begin <= address && address <= hndInfo.filter.range.end;
			if (process) {
				hndInfo.fn(address, data);
			}
		}
	}

	function varRead(name) {
		var result;
		var namedHandlers = namedVarReadHandlers[name] || [];
		for ( var i = 0; i < namedHandlers.length; i++ ) {
			var subresult = namedHandlers[i](name);
			if (subresult !== undefined) {
				result = subresult;
			}
		}
		for ( var i = 0; i < varReadHandlers.length; i++ ) {
			var subresult = varReadHandlers[i](name);
			if (subresult !== undefined) {
				result = subresult;
			}
		}
		return result;
	}

	function varWrite(name, value) {
		var namedHandlers = namedVarWriteHandlers[name] || [];
		for ( var i = 0; i < namedHandlers.length; i++ ) {
			namedHandlers[i](name, value);
		}
		for ( var i = 0; i < varWriteHandlers.length; i++ ) {
			varWriteHandlers[i](name, value);
		}
	}

	function reset(mode) {
		mode = mode || RESET_MODE_SOS128;
		for ( var i = 0; i < resetHandlers.length; i++ ) {
			resetHandlers[i](mode);
		}
	}


	function opt(name, value) {
		var namedHandlers = namedOptHandlers[name] || [];
		for ( var i = 0; i < namedHandlers.length; i++ ) {
			namedHandlers[i](name, value);
		}
		for ( var i = 0; i < optHandlers.length; i++ ) {
			optHandlers[i](name, value);
		}
	}

	this.on_instruction_read = onInstructionRead;
	this.on_mem_read = onMemRead;
	this.on_mem_write = onMemWrite;
	this.on_io_read = onIoRead;
	this.on_io_write = onIoWrite;
	this.on_var_read = onVarRead;
	this.on_var_write = onVarWrite;
	this.on_reset = onReset;
	this.on_opt = onOpt;
	this.instruction_read = instructionRead;
	this.mem_read = memRead;
	this.mem_write = memWrite;
	this.var_read = varRead;
	this.var_write = varWrite;
	this.io_read = ioRead;
	this.io_write = ioWrite;
	this.reset = reset;
	this.opt = opt;
}

// Upstream module: hardware/port_fe.js
function ZX_PortFE() {
	'use strict';

	var _bus;
	var port_value = 0x00;

	function io_write_fe(address, data) {
		_bus.var_write('port_fe_value', data);
	}

	function var_write_port_fe_value(name, value) {
		port_value = value;
	}

	function var_read_port_fe_value(name) {
		return port_value;
	}

	function reset() {
		_bus.var_write('port_fe_value', 0x00);
	}

	this.connect = function (bus) {
		_bus = bus;
		// в Pentagon128 проверка доступа к порту
		// осуществляется только по линии A0
		bus.on_io_write(io_write_fe, { mask: 0x01, value: 0x00 });
		bus.on_var_write(var_write_port_fe_value, 'port_fe_value');
		bus.on_var_read(var_read_port_fe_value, 'port_fe_value');
		bus.on_reset(reset);
	}
}
// Upstream module: hardware/port_7ffd.js
function ZX_Port7FFD() {
	'use strict';

	var _bus;
	var port_value = 0x00;

	function io_write_7ffd(address, data) {
		// if bit 5 is on, the port is locked
		if (!(port_value & 0x20)) {
			_bus.var_write('port_7ffd_value', data);
		}
	}

	function var_write_port_7ffd_value(name, value) {
		port_value = value;
	}

	function var_read_port_7ffd_value(name) {
		return port_value;
	}

	function reset(mode) {
		var value = (mode === RESET_MODE_SOS48 ? 0x20 : 0x00)
			| (mode === RESET_MODE_SOS128 ? 0x00 : 0x10);

		_bus.var_write('port_7ffd_value', value);
	}

	this.connect = function (bus) {
		_bus = bus;
		// в Pentagon128 проверка доступа к порту 
		// идет только по линиям A1, A15
		bus.on_io_write(io_write_7ffd, { mask: 0x8002, value: 0x0000 });
		bus.on_var_write(var_write_port_7ffd_value, 'port_7ffd_value');
		bus.on_var_read(var_read_port_7ffd_value, 'port_7ffd_value');
		bus.on_reset(reset);
	}
}
// Upstream module: hardware/rom.js
function ZX_ROM() {
	"use strict";
	
	var ROM_SIZE = 0x4000;

	var _bus;
	var _memory = {};
	var _rom_trdos = false;
	var _rom_turbo = false;
	var _port_7ffd_value = 0x00;

	var roms = [
		{ key: 'sos', name: '48.rom' },
		{ key: 'turbo', name: '48turbo.rom' },
		{ key: 'sos128', name: '128tr.rom' },
		{ key: 'trdos', name: 'tr5_04t.rom' }
	];

	var ready$ = Promise.all([
		get_rom(roms[0]),
		get_rom(roms[1]),
		get_rom(roms[2]),
		get_rom(roms[3])
	]);

	function get_rom(rom) {
		return loadServerFile(rom.name).then(function (data) {
			if (data.length != ROM_SIZE)
				throw new Error(ZX_Lang.ERR_ROM_WRONG_SIZE + '(' + rom.key + ')');

			_memory[rom.key] = new Uint8Array(data);
		});
	}

	function readByte(address) {
		if (_rom_trdos) {
			return _memory.trdos[address];
		}
		else if (_port_7ffd_value & 0x10) {
			return _rom_turbo ? _memory.turbo[address] : _memory.sos[address];
		}
		else {
			return _memory.sos128[address];
		}
	}	

	function readInstruction(address) {
		var data;

		if (( address & 0xff00 ) == 0x3d00 && (_port_7ffd_value & 0x10) && !_rom_trdos) {
			_bus.var_write('rom_trdos', true);
		}

		if ( address < 0x4000 ) {
			// readByte(address) function is inlined for the sake of performance
			// readByte begin
			if (_rom_trdos) {
				data = _memory.trdos[address];
			}
			else if (_port_7ffd_value & 0x10) {
				data = _rom_turbo ? _memory.turbo[address] : _memory.sos[address];
			}
			else {
				data = _memory.sos128[address];
			}
			// readByte end
		}

		if (( address & 0xc000 ) && _rom_trdos) {
			_bus.var_write('rom_trdos', false);
		}

		return data;
	}

	function var_write_port_7ffd_value(name, value) {
		_port_7ffd_value = value;
	}

	function var_write_rom_trdos(name, value) {
		_rom_trdos = value;
	}

	function var_write_rom_turbo(name, value) {
		_rom_turbo = value;
	}

	function var_read_rom_trdos(name) {
		return _rom_trdos;
	}

	function var_read_rom_turbo(name) {
		return _rom_turbo;
	}

	function reset(mode) {
		_bus.var_write('rom_trdos', mode === RESET_MODE_TRDOS);
		_bus.var_write('rom_turbo', mode === RESET_MODE_EXT);
	}

	this.get_ready$ = function () { 
		return ready$; 
	};

	this.connect = function(bus) {
		_bus = bus;
		bus.on_instruction_read(readInstruction);
		bus.on_mem_read(readByte, { range: { begin: 0x0000, end: 0x3FFF } });
		bus.on_var_write(var_write_port_7ffd_value, 'port_7ffd_value');
		bus.on_var_write(var_write_rom_trdos, 'rom_trdos');
		bus.on_var_write(var_write_rom_turbo, 'rom_turbo');
		bus.on_var_read(var_read_rom_trdos, 'rom_trdos');
		bus.on_var_read(var_read_rom_turbo, 'rom_turbo');
		bus.on_reset(reset);
	}
}
// Upstream module: hardware/ram.js
function ZX_RAM() {
	"use strict";

	var PAGE_SIZE = 0x4000;
	var PAGE_COUNT = 32;
	
	var _bus;
	var _memory = null;
	var _extendedMemory = VAL_EXTENDED_MEMORY_OFF;
	var _port_7ffd_value = 0x00;

	// инициализация памяти 512 кб
	initMemory();

	function initMemory() {
		_memory = [];
		var buffer = new ArrayBuffer(PAGE_SIZE * PAGE_COUNT);
		for ( var page = 0; page < PAGE_COUNT; page++ ) {
			_memory[page] = new Uint8Array(buffer, page * PAGE_SIZE, PAGE_SIZE);
		}
	}

	function readByte(address) {
		if (address >= 0x4000 && address < 0x8000) {
			return _memory[5][address & 0x3FFF];
		}
		if (address >= 0x8000 && address < 0xC000) {
			return _memory[2][address & 0x3FFF];
		}
		if (address >= 0xC000) {
			var page = (_extendedMemory == VAL_EXTENDED_MEMORY_PENTAGON)
				? (( _port_7ffd_value & 0xc0 ) >> 3 ) | ( _port_7ffd_value & 0x07 )
				: ( _port_7ffd_value & 0x07 );
			return _memory[page][address & 0x3FFF];
		}
	}

	function writeByte(address, data) {
		if (address >= 0x4000 && address < 0x8000) {
			_memory[5][address & 0x3FFF] = data;
		}
		else if (address >= 0x8000 && address < 0xC000) {
			_memory[2][address & 0x3FFF] = data;
		}
		else if (address >= 0xC000) {
			var page = (_extendedMemory == VAL_EXTENDED_MEMORY_PENTAGON)
				? (( _port_7ffd_value & 0xc0 ) >> 3 ) | ( _port_7ffd_value & 0x07 )
				: ( _port_7ffd_value & 0x07 );
			_memory[page][address & 0x3FFF] = data;
		}
	}

	function var_write_port_7ffd_value(name, value) {
		_port_7ffd_value = value;
	}

	function opt_extendedMemory(name, value) {
		_extendedMemory = value;
	}

	this.connect = function(bus) {
		_bus = bus;
		bus.on_instruction_read(readByte, { range: { begin: 0x4000, end: 0xFFFF } });
		bus.on_mem_read(readByte, { range: { begin: 0x4000, end: 0xFFFF } });
		bus.on_mem_write(writeByte, { range: { begin: 0x4000, end: 0xFFFF } });
		bus.on_var_write(var_write_port_7ffd_value, 'port_7ffd_value');
		bus.on_opt(opt_extendedMemory, OPT_EXTENDED_MEMORY);
	}
}
// Upstream module: hardware/display.js
// экран 256 x 192
// 6144 (0x1800) байт под пикселы
// 768 (0x300) байт под цвета знакомест
// 6912 (0x1b00) байт всего

// соответствие координат и памяти экрана:

// address: 010p pyyy rrrx xxxx
// point.y: pprr ryyy
// point.x: xxxx xbbb

// pp (0-2) - часть экрана (верхняя, средняя, нижняя)
// rrr (0-7) - вертикальное знакоместо относительно части экрана
// yyy (0-7) - номер строки относительно знакоместа
// xxxxx (0-31) - байт в строке
// bbb (0-7) - бит в байте (начиная со старшего!)

function ZX_Display () {
	'use strict';
	
	var _threading = VAL_THREADING_SINGLE;
	var _borderWidth = 16;
	var _scale = 2;
	var _scaleType = VAL_SCALE_METHOD_RENDER;
	var _rendererType = VAL_RENDERER_UNDEFINED;
	var _semicolors = false;
	var _flashInversion = false;
	var _flashInterval = 512;
	var _renderOnAnimationFrame = false;

	var _bus = null;
	var _clock = null;
	var _port_7ffd_value = 0x00;
	var _port_fe_value = 0x00;
	var _borderChanged = false;
	var _extendedMemory = VAL_EXTENDED_MEMORY_OFF;

	var _renderer = new NullRenderer();
	var _screen5Data = new Uint8Array(0x1B00);
	var _screen5Dirty = new Uint8Array(0x1800);
	var _screen7Data = new Uint8Array(0x1B00);
	var _screen7Dirty = new Uint8Array(0x1800);
	var _deferredData = new Uint8Array(0x1B00);
	var _deferredDirty = new Uint8Array(0x1800);

	function initRenderer() {
		switch ( _rendererType ) {
			case VAL_RENDERER_PUT_IMAGE_DATA: _renderer = new PutImageDataRenderer(_borderWidth, _scale, _scaleType); break;
			case VAL_RENDERER_DRAW_IMAGE: _renderer = new DrawImageRenderer(_borderWidth, _scale, _scaleType); break;
			case VAL_RENDERER_WEB_GL: _renderer = new WebGLRenderer(_borderWidth, _scale, _scaleType); break;
			default: _renderer = new NullRenderer(_borderWidth, _scale, _scaleType); break;
		}
		_renderer.set_threading(_threading);
	}

	function bind(canvases) {
		_renderer && _renderer.bind(canvases);
		_borderChanged = true;
		_screen5Dirty.fill(1);
		_screen7Dirty.fill(1);
	}

	function flashLoop() {
		_flashInversion = !_flashInversion;
		for (var address = 0x1800; address < 0x1B00; address++) {
			if (_screen5Data[address] & 0x80) {
				var topLeftAddress = ((address << 3) & 0x1800) | (address & 0x00FF);
				_screen5Dirty[topLeftAddress + 0x0000] = 1;
				_screen5Dirty[topLeftAddress + 0x0100] = 1;
				_screen5Dirty[topLeftAddress + 0x0200] = 1;
				_screen5Dirty[topLeftAddress + 0x0300] = 1;
				_screen5Dirty[topLeftAddress + 0x0400] = 1;
				_screen5Dirty[topLeftAddress + 0x0500] = 1;
				_screen5Dirty[topLeftAddress + 0x0600] = 1;
				_screen5Dirty[topLeftAddress + 0x0700] = 1;
			}
			if (_screen7Data[address] & 0x80) {
				var topLeftAddress = ((address << 3) & 0x1800) | (address & 0x00FF);
				_screen7Dirty[topLeftAddress + 0x0000] = 1;
				_screen7Dirty[topLeftAddress + 0x0100] = 1;
				_screen7Dirty[topLeftAddress + 0x0200] = 1;
				_screen7Dirty[topLeftAddress + 0x0300] = 1;
				_screen7Dirty[topLeftAddress + 0x0400] = 1;
				_screen7Dirty[topLeftAddress + 0x0500] = 1;
				_screen7Dirty[topLeftAddress + 0x0600] = 1;
				_screen7Dirty[topLeftAddress + 0x0700] = 1;
			}
		}
	}

	function scheduleRedraw(intrqVar, intrqActive) {
		if (!intrqActive)
			return;
		// Probable renering windows:
		// Spectrum 48: 	4.096 - 24.064
		// Spectrum 128:	4.104 - 24.364
		// Pentagon 48/128: 5.12  - 25.6
		//
		// static rendering delay as a temporary solution for Arkanoid :)
		_clock.setTimeout(beginRedraw, 6.6); 
	}

	function beginRedraw() {
		var layer = +!!(_port_7ffd_value & 0x08);
		var data = layer ? _screen7Data : _screen5Data;
		var dirty = layer ? _screen7Dirty : _screen5Dirty;

		if (_threading == VAL_THREADING_SINGLE) {
			if (_renderOnAnimationFrame) {
				// (копирование буферов понижает производительность)
				_deferredData.set(data);
				_deferredDirty.set(dirty);
				requestAnimationFrame(function () {
					endRedrawInMainThread(layer, _deferredData, _deferredDirty, _flashInversion, _semicolors);
				});
			}
			else {
				endRedrawInMainThread(layer, data, dirty, _flashInversion, _semicolors);
			}
		}
		else {
			_renderer.drawData(layer, data, dirty, _flashInversion, _semicolors);
			if (_renderOnAnimationFrame) {
				requestAnimationFrame(function () {
					endRedrawInDedicatedThread(layer);
				});
			}
			else {
				endRedrawInDedicatedThread(layer);
			}
		}
	}

	function endRedrawInMainThread(layer, data, dirty, flashInversion, semicolors) {
		_renderer.drawData(layer, data, dirty, flashInversion, semicolors);
		_renderer.displayLayer(layer);
		if (_borderChanged) {
			_borderChanged = false;
			var 
				attrs = _port_fe_value & 0x07,
				borderColor = ZX_Display.getColor(!_semicolors, attrs & 0x02, attrs & 0x04, attrs & 0x01);

			_renderer.drawBorder(borderColor);
		}
	}

	function endRedrawInDedicatedThread(layer) {
		_renderer.copyLayerToScreen(layer);
		if (_borderChanged) {
			_borderChanged = false;
			var 
				attrs = _port_fe_value & 0x07,
				borderColor = ZX_Display.getColor(!_semicolors, attrs & 0x02, attrs & 0x04, attrs & 0x01);

			_renderer.drawBorder(borderColor);
		}
	}

	function write(address, data) {
		var page = -1;
		if (address >= 0x4000 && address < 0x8000) {
			page = 5;
		}
		else if (address >= 0xC000) {
			page = (_extendedMemory == VAL_EXTENDED_MEMORY_PENTAGON)
				? ((_port_7ffd_value & 0xC0) >> 3) | (_port_7ffd_value & 0x07)
				: _port_7ffd_value & 0x07;
		}
		address &= 0x3FFF;
		if (address >= 0x1B00 || page != 5 && page != 7)
			return;

		var screenData, screenDirty;
		if (page == 5) {
			screenData = _screen5Data;
			screenDirty = _screen5Dirty;
		}
		else {
			screenData = _screen7Data;
			screenDirty = _screen7Dirty;
		}
		if (screenData[address] == data)
			return;

		screenData[address] = data;
		if (address < 0x1800) {
			screenDirty[address] = 1;
		}
		else {
			var topLeftAddress = ((address << 3) & 0x1800) | (address & 0x00FF);
			screenDirty[topLeftAddress + 0x0000] = 1;
			screenDirty[topLeftAddress + 0x0100] = 1;
			screenDirty[topLeftAddress + 0x0200] = 1;
			screenDirty[topLeftAddress + 0x0300] = 1;
			screenDirty[topLeftAddress + 0x0400] = 1;
			screenDirty[topLeftAddress + 0x0500] = 1;
			screenDirty[topLeftAddress + 0x0600] = 1;
			screenDirty[topLeftAddress + 0x0700] = 1;						
		}
	}

	function var_write_port_7ffd_value(name, value) {
		_port_7ffd_value = value;
	}

	function var_write_port_fe_value(name, value) {
		_borderChanged = _borderChanged || (( _port_fe_value ^ value ) & 0x07 );
		_port_fe_value = value;
	}

	this.force_redraw = beginRedraw;

	function opt_extendedMemory(name, value) {
		if ( _extendedMemory !== value ) {
			_extendedMemory = value;
		}
	}

	function opt_renderingParams(name, value) {
		var recreateRenderer = !_renderer 
			|| _scale != value.scale 
			|| _scaleType != value.scaleType 
			|| _rendererType != value.rendererType;

		_scale = value.scale;
		_scaleType = value.scaleType;
		_rendererType = value.rendererType;
		_renderOnAnimationFrame = value.renderOnAnimationFrame;
		if (recreateRenderer) {
			initRenderer();
		}
	}

	function opt_semicolors(name, value) {
		if (_semicolors != value) {
			_semicolors = value;
			_borderChanged = true;
			_screen5Dirty.fill(1);
			_screen7Dirty.fill(1);
		}
	}

	this.connect = function (bus, clock) {
		_bus = bus;
		_clock = clock;
		bus.on_mem_write(write, { range: { begin: 0x4000, end: 0x5AFF } });
		bus.on_mem_write(write, { range: { begin: 0xC000, end: 0xDAFF } });
		bus.on_var_write(var_write_port_7ffd_value, 'port_7ffd_value');
		bus.on_var_write(var_write_port_fe_value, 'port_fe_value');
		bus.on_var_write(scheduleRedraw, 'intrq');
		bus.on_opt(opt_extendedMemory, OPT_EXTENDED_MEMORY);
		bus.on_opt(opt_renderingParams, OPT_RENDERING_PARAMS);
		bus.on_opt(opt_semicolors, OPT_SEMICOLORS);
		_clock.setInterval(flashLoop, _flashInterval, 0);
		initRenderer();
	}

	this.bind = bind;
	this.get_threading = function () {
		return _threading;
	}
	this.set_threading = function (value) {
		_threading = value;
	}
}
Object.assign(ZX_Display, {
	getColor: function (bright, r, g, b) {
		return [
			r ? ( bright ? 0xff : 0xbf ) : 0x00,
			g ? ( bright ? 0xff : 0xbf ) : 0x00,
			b ? ( bright ? 0xff : 0xbf ) : 0x00,
			0xff
		];
	},
	getColorsByAttrs: function (attrs) {
		return {
			forecolor: ZX_Display.getColor(attrs & 0x40, attrs & 0x02, attrs & 0x04, attrs & 0x01),
			backcolor: ZX_Display.getColor(attrs & 0x40, attrs & 0x10, attrs & 0x20, attrs & 0x08)
		};
	},
	inversionTable: (function () {
		var it = new Uint8Array(0x100);
		for ( var attrs = 0; attrs <= 0xFF; attrs++ ) {
			it[attrs] = (attrs & 0x80)
				? (attrs & 0x40) | ((attrs << 3) & 0x38) | ((attrs >> 3) & 0x07)
				: attrs;
		}
		return it;
	})()
});

/*
	Renderer interface:

	methods:
		void bind( Array canvases )
			Binds output canvases to the renderer. There can be either 2 or 3 canvases depending on the mode activated at the moment.
			For code which is performing in the main ui thread there will be three canvases: border, screen5, screen7.
			For code which is performing in the dedicated worker thread it will be only two offscreen canvases: border and screen.

		void drawBorder( vec4 color )
			Fills the border with the specific color.

		void drawData( Number layer, Uint8Array data, Uint8Array dirty, Boolean flashInversion, Boolean semicolors)
			Renders data which has been changed from the last rendering on the corresponding canvas (it can be output canvas or
			intermediate offscreen canvas).

		void displayLayer( Number layer )
			Adjusts visibility of canvases of screen5 and screen7 depending on the layer parameter. (For main UI thread.)

		void copyLayerToScreen( Number layer )
			Renders intermediate layer canvas on the output screen canvas. (For dedicated worker thread.)
*/

function RendererBase(borderWidth, scale, scaleType) {
	this._threading = VAL_THREADING_SINGLE;
	this._scale = scale;
	this._scaleType = scaleType;
	this._borderWidth = borderWidth;
	this._lastBorderColor = [0, 0, 0, 255];
	this._lastBorderTextWidth = 0;
	this._border = null;
	this._screen = null;
	this._layer0 = null;
	this._layer1 = null;
	this._borderCtx = null;
	this._screenCtx = null;
	this._buildSamples();
}
Object.assign(RendererBase.prototype, {
	get_threading: function () {
		return this._threading;
	},
	set_threading: function (value) {
		this._threading = value;
	},
	_createCanvas: function (width, height) {
		if (typeof OffscreenCanvas !== 'undefined') {
			return new OffscreenCanvas(width, height);
		}
		else if (typeof window !== 'undefined') {
			var canvas = document.createElement('canvas');
			canvas.width = width;
			canvas.height = height;
			return canvas;
		}
		else
			throw new Error(ZX_Lang.ERR_CANNOT_CREATE_CANVAS);
	},
	_buildSamples: function () {

	},
	bind: function (canvases) {
		this._border = canvases[0];
		this._borderCtx = this._border.getContext('2d', { alpha: false });
		if (this._threading === VAL_THREADING_MULTIPLE) {
			this._screen = canvases[1];
			this._screenCtx = this._screen.getContext('2d', { alpha: false });
			this._layer0 = this._createCanvas(this._screen.width, this._screen.height);
			this._layer1 = this._createCanvas(this._screen.width, this._screen.height);
		}
		else {
			this._layer0 = canvases[1];
			this._layer1 = canvases[2];
		}
	},
	drawBorder: function (color) {
		if ( !this._borderCtx )
			return;

		var 
			scale = this._scale,
			ctx = this._borderCtx,
			bw = this._borderWidth * scale,
			sw = 256 * scale,
			sh = 192 * scale;

		ctx.fillStyle = 'rgba(' + color.join(',') + ')';
		ctx.beginPath();
		ctx.rect(0, 0, bw + sw + bw, bw);
		ctx.rect(0, bw, bw, sh);
		ctx.rect(bw + sw, bw, bw, sh);
		ctx.rect(0, bw + sh, bw + sw + bw, bw);
		ctx.closePath();
		ctx.fill();

		this._lastBorderColor = color.slice(0, 4);
	},
	drawData: function (layer, data, dirty, flashInversion, semicolors) {
	},
	displayLayer: function (layer) {
		this._layer1 && (this._layer1.style.opacity = layer ? 1.0 : 0.0);
	},
	copyLayerToScreen: function (layer) {
		this._screenCtx && this._screenCtx.drawImage(layer ? this._layer1 : this._layer0, 0, 0);
	}
});

function NullRenderer() {
	NullRenderer.superclass.constructor.apply(this, arguments);
}
extend(NullRenderer, RendererBase);

function PutImageDataRenderer() {
	this._samples = [];
    this._nativeLayers = [];
    this._nativeContexts = [];
    this._frames = [];
	this._layer0Ctx = null;
	this._layer1Ctx = null;
	PutImageDataRenderer.superclass.constructor.apply(this, arguments);
}
extend(PutImageDataRenderer, RendererBase);
Object.assign(PutImageDataRenderer.prototype, {
	_buildSamples: function() {
		var 
			samples = [],
			scale = 1, // Samples and frame storage always use the native 256 x 192 raster.
			sampleWidth = 8 * scale,
			sampleHeight = 1 * scale;

		var sampleCanvas = this._createCanvas(0x100 * sampleWidth, 0x80 * sampleHeight);
		var sampleContext = sampleCanvas.getContext('2d', { alpha: false });

		/* very very slow in IE */
		for ( var attrs = 0; attrs < 0x80; attrs++ ) {
			var colors = ZX_Display.getColorsByAttrs(attrs);
			for ( var bits = 0; bits < 0x100; bits++ ) {
				var sample = sampleContext.createImageData(sampleWidth, sampleHeight);
				var dataIndex = 0;

				for ( var y = 0; y < scale; y++ ) {
					for ( var bit = 0; bit < 8; bit++ ) {
						var color = ( bits & ( 0x80 >> bit )) ? colors.forecolor : colors.backcolor;

						for ( var x = 0; x < scale; x++ ) {
							sample.data[dataIndex++] = color[0];
							sample.data[dataIndex++] = color[1];
							sample.data[dataIndex++] = color[2];
							sample.data[dataIndex++] = color[3];
						}
					}					
				}

				samples[( attrs << 8 ) | bits] = sample;
			}
		}

		this._samples = samples;
	},
	bind: function (canvases) {
		PutImageDataRenderer.superclass.bind.call(this, canvases);
		this._layer0Ctx = this._layer0.getContext('2d', { alpha: false });
		this._layer1Ctx = this._layer1.getContext('2d', { alpha: false });
        for (var layer = 0; layer < 2; layer++) {
            var native = this._createCanvas(256, 192);
            var context = native.getContext('2d', { alpha: false });
            this._nativeLayers[layer] = native;
            this._nativeContexts[layer] = context;
            this._frames[layer] = context.createImageData(256, 192);
        }
        this._layer0Ctx.imageSmoothingEnabled = false;
        this._layer1Ctx.imageSmoothingEnabled = false;
	},
	drawData: function (layer, data, dirty, flashInversion, semicolors) {
		var 
			sampleScale = 1,
			semicolorsMask = semicolors ? 0x00 : 0x40,
			flashInversionMask = flashInversion ? 0xFF : 0x7F,
			ctx = layer ? this._layer1Ctx : this._layer0Ctx;

		if (ctx) {
            var changed = false;
            var frame = this._frames[layer];
			for (var address = 0; address < 0x1800; address++) {
				if (dirty[address]) {
					var 
						x = (address & 0x1F) << 3, // 0, 8, 16, ..., 240
						y = ((address >> 5) & 0xC0) | ((address >> 2) & 0x38) | ((address >> 8) & 0x07), // 0, 1, 2, ..., 191
						attr = ZX_Display.inversionTable[data[0x1800 | ((address >> 3) & 0x0300) | (address & 0xFF)] & flashInversionMask | semicolorsMask],
						dx = x * sampleScale, 
						dy = y * sampleScale, 
						sampleIndex = (attr << 8) | data[address];

					// Eight adjacent native pixels; Spectrum memory is not row-major.
                    frame.data.set(this._samples[sampleIndex].data, (dy * 256 + dx) * 4);
                    changed = true;
					dirty[address] = 0;
				}
            }
            if (changed) {
                this._nativeContexts[layer].putImageData(frame, 0, 0);
                ctx.drawImage(this._nativeLayers[layer], 0, 0, 256, 192,
                    0, 0, ctx.canvas.width, ctx.canvas.height);
            }
        }
    }
});

function DrawImageRenderer() {
	this._samples = null;
	this._sampleParams = {
		width: 8,
		height: 1,
		stepX: 10,
		stepY: 3
	};
	this._layer0Ctx = null;
	this._layer1Ctx = null;
	DrawImageRenderer.superclass.constructor.apply(this, arguments);
}
extend(DrawImageRenderer, RendererBase);
Object.assign(DrawImageRenderer.prototype, {
	_buildSamples: function () {
		/*
			All browsers except Google Chrome calculate pixel color basing on neighbor pixels
			so we need to dublicate boundary pixels in order to get correct colors.

			x         x         x         x
			0         10        20        30

		y0	******************************...
			*sample00**sample01**sample02*...
			******************************...
		y3	******************************...
			*sample10**sample11**sample12*...
			******************************...
		y4	.................................

		*/
		var sampleScale = ( this._scaleType == VAL_SCALE_METHOD_PRE ) ? this._scale : 1;
		var sampleParams = {
			width: 8 * sampleScale,
			height: 1 * sampleScale,
			stepX: 8 * sampleScale + 2, // 8 точек сэмпла и 2 обрамляющих точки
			stepY: 1 * sampleScale + 2 // 1 точка сэмпла и 2 обрамляющих точки
		};

		var samples = this._createCanvas(0x100 * sampleParams.stepX, 0x80 * sampleParams.stepY);
		var samplesContext = samples.getContext('2d', { alpha: false });
		var samplesData = samplesContext.createImageData(samples.width, samples.height);

		var state = {
			data: samplesData.data,
			dataIndex: 0,
			attrs: 0
		};
		for ( state.attrs = 0; state.attrs < 0x80; state.attrs++ ) {
			generateSampleLine(state);
			for ( var i = 0; i < sampleScale; i++ ) {
				generateSampleLine(state);
			}
			generateSampleLine(state);
		}
		samplesContext.putImageData(samplesData, 0, 0);

		this._samples = samples;
		this._sampleParams = sampleParams;

		function generateSampleLine( state ) {
			var colors = ZX_Display.getColorsByAttrs(state.attrs);
			for ( var pixels = 0; pixels < 0x100; pixels++ ) {
				for ( var pixel = 0; pixel < 8; pixel++ ) {
					var color = ( pixels & ( 0x80 >> pixel )) ? colors.forecolor : colors.backcolor;

					if ( pixel == 0 ) {
						state.data[state.dataIndex++] = color[0];
						state.data[state.dataIndex++] = color[1];
						state.data[state.dataIndex++] = color[2];
						state.data[state.dataIndex++] = color[3];
					}

					for ( var i = 0; i < sampleScale; i++ ) {
						state.data[state.dataIndex++] = color[0];
						state.data[state.dataIndex++] = color[1];
						state.data[state.dataIndex++] = color[2];
						state.data[state.dataIndex++] = color[3];
					}

					if ( pixel == 7 ) {
						state.data[state.dataIndex++] = color[0];
						state.data[state.dataIndex++] = color[1];
						state.data[state.dataIndex++] = color[2];
						state.data[state.dataIndex++] = color[3];
					}
				}
			}
		}
	},
	_initImageData: function (context, width, height) {
		var data = context.createImageData(width, height);
		context.putImageData(data, 0, 0);
	},
	bind: function (canvases) {
		DrawImageRenderer.superclass.bind.call(this, canvases);
		this._layer0Ctx = this._layer0.getContext('2d', { alpha: false });
		this._layer1Ctx = this._layer1.getContext('2d', { alpha: false });
		this._initImageData(this._borderCtx, this._border.width, this._border.height);
		this._initImageData(this._layer0Ctx, this._layer0.width, this._layer0.height);
		this._initImageData(this._layer1Ctx, this._layer1.width, this._layer1.height);
	},
	drawData: function (layer, data, dirty, flashInversion, semicolors) {
		var 
			renderScale = ( this._scaleType == VAL_SCALE_METHOD_PRE || this._scaleType == VAL_SCALE_METHOD_RENDER ) ? this._scale : 1,
			sampleParams = this._sampleParams,
			w = 8 * renderScale,
			h = 1 * renderScale,
			semicolorsMask = semicolors ? 0x00 : 0x40,
			flashInversionMask = flashInversion ? 0xFF : 0x7F,
			ctx = layer ? this._layer1Ctx : this._layer0Ctx;
			
		if (ctx) {
			for (var address = 0; address < 0x1800; address++) {
				if (dirty[address]) {
					var 
						x = (address & 0x1F) << 3, // 0, 8, 16, ..., 240
						y = ((address >> 5) & 0xC0) | ((address >> 2) & 0x38) | ((address >> 8) & 0x07), // 0, 1, 2, ..., 191
						attr = ZX_Display.inversionTable[data[0x1800 | ((address >> 3) & 0x0300) | (address & 0xFF)] & flashInversionMask | semicolorsMask],
						dx = x * renderScale, 
						dy = y * renderScale, 
						sx = data[address] * sampleParams.stepX + 1,
						sy = attr * sampleParams.stepY + 1;
						
					ctx.drawImage(this._samples, sx, sy, sampleParams.width, sampleParams.height, dx, dy, w, h);
					dirty[address] = 0;
				}
			}
		}
	}
});

function WebGLRenderer() {
	this._samples = null;
	this._sampleParams = {
		width: 8,
		height: 1
	};
	this._glBuffer = new Float32Array(0x1800 * 24);
	this._copyTexture = null;
	WebGLRenderer.superclass.constructor.apply(this, arguments);
}
extend(WebGLRenderer, RendererBase);
Object.assign(WebGLRenderer.prototype, {
	_glGetContext: function (canvas, options) {
		var names = [ "webgl2", "webgl", "experimental-webgl" ];
		var glContext = null;
		for ( var i = 0; i < names.length && !glContext; i++ ) {
			try {
				glContext = canvas.getContext(names[i], options);
			}
			catch (e) {}
		}
		return glContext;
	},
	_glCreateShader: function ( glContext, shaderType, shaderSource ) {
		var shader = glContext.createShader(shaderType);
		glContext.shaderSource(shader, shaderSource);
		glContext.compileShader(shader);

		var compiled = glContext.getShaderParameter(shader, glContext.COMPILE_STATUS);
		if ( !compiled ) {
			var error = glContext.getShaderInfoLog(shader);
			glContext.deleteShader(shader);
			throw new Error(error);
		}

		return shader;
	},
	_glCreateAndLinkProgram: function ( glContext, shaders ) {
		var program = glContext.createProgram();
		for ( var i = 0; i < shaders.length; i++ ) {
			glContext.attachShader(program, shaders[i]);
		}

		glContext.linkProgram(program);

		var linked = glContext.getProgramParameter(program, glContext.LINK_STATUS);
		if ( !linked ) {
			var error = glContext.getProgramInfoLog(program);
			glContext.deleteProgram(program);
			throw new Error(error);
		}

		return program;
	},
	_copyVertexShaderSource: [
		'attribute vec2 a_position;',
		'varying vec2 v_coords;',

		'void main() {',
		'	vec2 clipCoords = (a_position * 2.0 - 1.0) * vec2(1.0, -1.0);',
		'	gl_Position = vec4(clipCoords, 0.0, 1.0);',
		'	v_coords = a_position;',
		'}'
	].join('\r\n'),
	_copyFragmentShaderSource: [
		'precision lowp float;',
		'uniform sampler2D u_source;',
		'varying vec2 v_coords;',

		'void main() {',
		'	gl_FragColor = texture2D(u_source, v_coords);',
		'}'
	].join('\r\n'),
	_renderVertexShaderSource: [
		"attribute vec4 a_params;",
		"attribute vec2 a_sampleDimensions;",
		"attribute float a_renderScale;",
		"attribute float a_sampleScale;",
		"attribute vec2 a_canvasResolution;",
		"attribute vec2 a_samplesResolution;",
		"varying vec2 v_sampleCoords;",

		"void main() {",
		"   vec2 xy = a_params.xy * a_sampleDimensions * a_renderScale / a_canvasResolution;",
		"   vec2 pq = a_params.pq * a_sampleDimensions * a_sampleScale / a_samplesResolution;",
		"	vec2 clipCoords = (xy * 2.0 - 1.0) * vec2(1.0, -1.0);",
		"	gl_Position = vec4(clipCoords, 0.0, 1.0);",
		"	v_sampleCoords = pq;",
		"}"
	].join('\r\n'),
	_renderFragmentShaderSource: [
	    "precision lowp float;",
        "uniform sampler2D u_samples;",
        "varying vec2 v_sampleCoords;",
	    
	    "void main() {",
	    "	gl_FragColor = texture2D(u_samples, v_sampleCoords);",
	    "}"
	].join('\r\n'),
	_glInitWebGLContext: function ( glContext ) {
		var vertexShader = this._glCreateShader(glContext, glContext.VERTEX_SHADER, this._renderVertexShaderSource);
		var fragmentShader = this._glCreateShader(glContext, glContext.FRAGMENT_SHADER, this._renderFragmentShaderSource);
		var program = this._glCreateAndLinkProgram(glContext, [vertexShader, fragmentShader]);
		glContext.useProgram(program);

	    var buffer = glContext.createBuffer();
	    glContext.bindBuffer(glContext.ARRAY_BUFFER, buffer);

		glContext.bindAttribLocation(program, 0, 'a_params');
		var paramsLocation = glContext.getAttribLocation(program, 'a_params');
		glContext.enableVertexAttribArray(paramsLocation);
		glContext.vertexAttribPointer(paramsLocation, 4, glContext.FLOAT, false, 0, 0);

		var sampleDimensionsLocation = glContext.getAttribLocation(program, "a_sampleDimensions");
		glContext.vertexAttrib2f(sampleDimensionsLocation, 8, 1);

		var renderScaleLocation = glContext.getAttribLocation(program, 'a_renderScale');
		var renderScale = ( this._scaleType == VAL_SCALE_METHOD_PRE || this._scaleType == VAL_SCALE_METHOD_RENDER ) ? this._scale : 1;
		glContext.vertexAttrib1f(renderScaleLocation, renderScale);

		var sampleScaleLocation = glContext.getAttribLocation(program, "a_sampleScale");
		var sampleScale = ( this._scaleType == VAL_SCALE_METHOD_PRE ) ? this._scale : 1;
		glContext.vertexAttrib1f(sampleScaleLocation, sampleScale);

		var canvasResolutionLocation = glContext.getAttribLocation(program, 'a_canvasResolution');
		glContext.vertexAttrib2f(canvasResolutionLocation, glContext.canvas.width, glContext.canvas.height);

		var samplesResolutionLocation = glContext.getAttribLocation(program, 'a_samplesResolution');
		glContext.vertexAttrib2f(samplesResolutionLocation, this._samples.width, this._samples.height);

	    var texture = glContext.createTexture();
		glContext.activeTexture(glContext.TEXTURE0);
	    glContext.bindTexture(glContext.TEXTURE_2D, texture);
	    glContext.texParameteri(glContext.TEXTURE_2D, glContext.TEXTURE_WRAP_S, glContext.CLAMP_TO_EDGE);
	    glContext.texParameteri(glContext.TEXTURE_2D, glContext.TEXTURE_WRAP_T, glContext.CLAMP_TO_EDGE);    
	    glContext.texParameteri(glContext.TEXTURE_2D, glContext.TEXTURE_MIN_FILTER, glContext.NEAREST);
	    glContext.texParameteri(glContext.TEXTURE_2D, glContext.TEXTURE_MAG_FILTER, glContext.NEAREST);
	    glContext.texImage2D(glContext.TEXTURE_2D, 0, glContext.RGBA, glContext.RGBA, glContext.UNSIGNED_BYTE, this._samples);
	},
	_buildSamples: function () {
		/*
			x       x       x       x
			0       8       16      24

		y0	sample00sample01sample02...
		y1	sample10sample11sample12...
		y2	...........................

		*/
		var sampleScale = ( this._scaleType == VAL_SCALE_METHOD_PRE ) ? this._scale : 1;
		var sampleParams = {
			width: 8 * sampleScale,
			height: 1 * sampleScale
		}

		var samples = this._createCanvas(0x100 * sampleParams.width, 0x80 * sampleParams.height);
		var samplesContext = samples.getContext('2d', { alpha: false });
		var samplesData = samplesContext.createImageData(samples.width, samples.height);

		var state = {
			data: samplesData.data,
			dataIndex: 0,
			attrs: 0
		};
		for ( state.attrs = 0; state.attrs < 0x80; state.attrs++ ) {
			for ( var i = 0; i < sampleScale; i++ ) {
				generateSampleLine(state);
			}
		}

		samplesContext.putImageData(samplesData, 0, 0);

		this._samples = samples;
		this._sampleParams = sampleParams;

		function generateSampleLine( state ) {
			var colors = ZX_Display.getColorsByAttrs(state.attrs);
			for ( var pixels = 0; pixels < 0x100; pixels++ ) {
				for ( var pixel = 0; pixel < 8; pixel++ ) {
					var color = ( pixels & ( 0x80 >> pixel )) ? colors.forecolor : colors.backcolor;

					for ( var i = 0; i < sampleScale; i++ ) {
						state.data[state.dataIndex++] = color[0];
						state.data[state.dataIndex++] = color[1];
						state.data[state.dataIndex++] = color[2];
						state.data[state.dataIndex++] = color[3];
					}
				}
			}
		}		
	},
	bind: function (canvases) {
		if (this._threading === VAL_THREADING_MULTIPLE) {
			this._border = canvases[0];
			this._borderCtx = this._border.getContext('2d', { alpha: false });

			this._screen = canvases[1];
			this._screenCtx = this._glGetContext(this._screen, { alpha: false });
			var gl = this._screenCtx;
			var copyVertexShader = this._glCreateShader(gl, gl.VERTEX_SHADER, this._copyVertexShaderSource);
			var copyFragmentShader = this._glCreateShader(gl, gl.FRAGMENT_SHADER, this._copyFragmentShaderSource);
			var copyProgram = this._glCreateAndLinkProgram(gl, [copyVertexShader, copyFragmentShader]);
			gl.useProgram(copyProgram);

			var positionBuffer = gl.createBuffer();
			gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
			gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([1.0, 1.0, -1.0, 1.0, 1.0, -1.0, -1.0, -1.0]), gl.STATIC_DRAW);

			gl.bindAttribLocation(copyProgram, 0, 'a_position');
			gl.enableVertexAttribArray(0);
			gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);

			this._copyTexture = gl.createTexture();
			gl.activeTexture(gl.TEXTURE0);
			gl.bindTexture(gl.TEXTURE_2D, this._copyTexture);
			gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
			gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);    
			gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
			gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);

			this._layer0 = this._createCanvas(this._screen.width, this._screen.height);
			this._layer1 = this._createCanvas(this._screen.width, this._screen.height);
		}
		else {
			WebGLRenderer.superclass.bind.call(this, canvases);
		}
		this._layer0Ctx = this._glGetContext(this._layer0, { preserveDrawingBuffer: true, alpha: false });
		this._layer1Ctx = this._glGetContext(this._layer1, { preserveDrawingBuffer: true, alpha: false });
		if ( !this._layer0Ctx || !this._layer1Ctx )
			throw new Error(ZX_Lang.ERR_CANNOT_CREATE_CANVAS);

		this._glInitWebGLContext(this._layer0Ctx);
		this._glInitWebGLContext(this._layer1Ctx);
	},
	drawData: function (layer, data, dirty, flashInversion, semicolors) {
		var 
			semicolorsMask = semicolors ? 0x00 : 0x40,
			flashInversionMask = flashInversion ? 0xFF : 0x7F,
			ctx = layer ? this._layer1Ctx : this._layer0Ctx;

		if (ctx) {
			var glBufferIndex = 0;
			for (var address = 0; address < 0x1800; address++) {
				if (dirty[address]) {
					var 
						x = (address & 0x1F), // 0, 1, 2, ..., 31
						y = ((address >> 5) & 0xC0) | ((address >> 2) & 0x38) | ((address >> 8) & 0x07), // 0, 1, 2, ..., 191
						attr = ZX_Display.inversionTable[data[0x1800 | ((address >> 3) & 0x0300) | (address & 0xFF)] & flashInversionMask | semicolorsMask],
						p = x+1,
						q = y+1,
						sx = data[address],
						sp = sx+1,
						sy = attr,
						sq = sy+1,
						glData = [
							x, y, sx, sy,
							p, y, sp, sy,
							p, q, sp, sq,
							x, y, sx, sy,
							x, q, sx, sq,
							p, q, sp, sq
						];

					this._glBuffer.set(glData, glBufferIndex);
					glData.length = 0;
					glBufferIndex += 24;
					dirty[address] = 0;
				}
			}
			if (glBufferIndex) {
				ctx.bufferData(ctx.ARRAY_BUFFER, this._glBuffer, ctx.STATIC_DRAW);
				ctx.drawArrays(ctx.TRIANGLES, 0, glBufferIndex >> 2);
				ctx.flush();
				ctx.finish();
			}
		}
	},
	copyLayerToScreen: function (layer) {
		var gl = this._screenCtx;
		gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, layer ? this._layer1 : this._layer0);
		gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
	}
});

// Upstream module: hardware/keyboard.js
function ZX_Keyboard() {
	"use strict";
	
	var _keyStates = [ 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF ];
	var _onKeysStateChanged = new ZX_Event();

	function switchKeys(keys, pressed) {
		for ( var i = 0; i < keys.length; i++ ) {
			if ( pressed ) {
				_keyStates[keys[i].index] &= ((0x01 << keys[i].bit) ^ 0xFF);
			}
			else {
				_keyStates[keys[i].index] |= (0x01 << keys[i].bit);
			}
		}

		_onKeysStateChanged.emit({
			keys: keys,
			pressed: pressed
		});
	}


	function io_read_fe(address) {
		var data = 0xFF;
		!(address & 0x0100) && (data &= _keyStates[0]);
		!(address & 0x0200) && (data &= _keyStates[1]);
		!(address & 0x0400) && (data &= _keyStates[2]);
		!(address & 0x0800) && (data &= _keyStates[3]);
		!(address & 0x1000) && (data &= _keyStates[4]);
		!(address & 0x2000) && (data &= _keyStates[5]);
		!(address & 0x4000) && (data &= _keyStates[6]);
		!(address & 0x8000) && (data &= _keyStates[7]);
		return data;
	}
	
	function connect(bus) {
		bus.on_io_read(io_read_fe, { mask: 0xFF, value: 0xFE });
	}

	this.get_onKeysStateChanged = function () {
		return _onKeysStateChanged.pub;
	}
	this.switchKeys = switchKeys;
	this.connect = connect;
}

// Upstream module: hardware/betadisk.html

function ZX_BetaDisk() {
	this.connect = connect;
	this.get_state = get_state;

	if (ZXContext.debugMode) {
		this.startLogging = startLogging;
		this.stopLogging = stopLogging;
	}

	var _bus;
	var _clock;
	var _drives = [];
	var _rom_trdos = false;

	var _drive = 0;
	var _head = 0; // 0 - нижняя головка, 1 - верхняя
	var _vg93;
	var _headReady = 0;
	var _doubleDensity = 0;
	var _debugLog = null;
	var _intervalsDependOnFrequency = false; // Drive rotation stays at 300 rpm independently of CPU frequency.
	var _tstatesPerIntrq = 71680;
	var _intrqPeriod = 20.48;

	function connect(bus, clock, drives) {
		// В Pentagon дешифрация портов ВГ93 осуществляется по
		// линиям A0, A1, A5, A6, A7;
		// дешифрация систменого порта - по линиям A0, A1, A7
		_bus = bus;
		_clock = clock;
		_drives.push.apply(_drives, drives);
		if (ZXContext.debugMode) {
			_bus.on_io_read(dbg_io_read_vg93, { mask: 0x83, value: 0x03 });
			_bus.on_io_read(dbg_io_read_ff, { mask: 0x83, value: 0x83 });
			_bus.on_io_write(dbg_io_write_vg93, { mask: 0x83, value: 0x03 });
			_bus.on_io_write(dbg_io_write_ff, { mask: 0x83, value: 0x83 });
		}
		else {
			_bus.on_io_read(io_read_vg93, { mask: 0x83, value: 0x03 });
			_bus.on_io_read(io_read_ff, { mask: 0x83, value: 0x83 });
			_bus.on_io_write(io_write_vg93, { mask: 0x83, value: 0x03 });
			_bus.on_io_write(io_write_ff, { mask: 0x83, value: 0x83 });
		}
		_bus.on_var_write(var_write_rom_trdos, 'rom_trdos');
		_bus.on_opt(function (name, value) {
			_tstatesPerIntrq = value;
			updateTimeFactor();
		}, OPT_TSTATES_PER_INTRQ);
		_bus.on_opt(function (name, value) {
			_intrqPeriod = value;
			updateTimeFactor();
		}, OPT_INTRQ_PERIOD);
		_vg93 = new VG93(clock);
		_vg93.set_floppy(_drives[0]);
		_vg93.masterReset();
	}

	function get_state() {
		var state = {
			vg93: _vg93.get_state(),
			drive: _drive,
			head: _head,
			headReady: _headReady,
			doubleDensity: _doubleDensity
		};
		return state;
	}

	function io_write_vg93(address, value) {
		if (_rom_trdos) {
			_vg93.write((address >> 5) & 0x03, value);
		}
	}

	function io_write_ff(address, value) {
		if (_rom_trdos) {
			var drive = value & 0x03;
			if (_drive != drive) {
				_drive = drive;
				_vg93.set_floppy(_drives[drive]);
			}
			_headReady = +!!(value & 0x08);
			_vg93.set_headReady(_headReady);
			_doubleDensity = !(value & 0x40);
			_vg93.set_doubleDensity(_doubleDensity);
			var head = +!(value & 0x10);
			if (_head != head) {
				_head = head;
				for (var i = 0; i < _drives.length; i++) {
					_drives[i].set_head(head);
				}
			}
			
			if (!(value & 0x04)) {
				_vg93.masterReset();
			}
		}
	}

	function io_read_vg93(address) {
		if (_rom_trdos) {
			return _vg93.read((address >> 5) & 0x03);
		}
	}

	function io_read_ff(address) {
		if (_rom_trdos) {
			return (_vg93.get_intrq() << 7)
				| (_vg93.get_drq() << 6)
				| 0x00;
		}
	}

	function startLogging() {
		if (!_debugLog) {
			_debugLog = [];
		}
	}

	function stopLogging() {
		var log = _debugLog;
		_debugLog = null;
		return log;
	}

	function dbg_io_write_vg93(address, value) {
		if (_rom_trdos && _debugLog) {
			_debugLog.push({ 
				ts: _clock.get_ms(),
				op: 'o',
				port: address & 0xFF,
				value: value
			});
		}
		io_write_vg93(address, value);
	}

	function dbg_io_write_ff(address, value) {
		if (_rom_trdos && _debugLog) {
			_debugLog.push({ 
				ts: _clock.get_ms(),
				op: 'o',
				port: address & 0xFF,
				value: value
			});
		}
		io_write_ff(address, value);
	}

	function dbg_io_read_vg93(address) {
		var result = io_read_vg93(address);
		if (_rom_trdos && _debugLog) {
			_debugLog.push({
				ts: _clock.get_ms(),
				op: 'i',
				port: address & 0xFF,
				value: result
			});
		}
		return result;
	}

	function dbg_io_read_ff(address) {
		var result = io_read_ff(address);
		if (_rom_trdos && _debugLog) {
			_debugLog.push({
				ts: _clock.get_ms(),
				op: 'i',
				port: address & 0xFF,
				value: result
			});
		}
		return result;
	}

	function var_write_rom_trdos(name, value) {
		_rom_trdos = value;
	}

	function updateTimeFactor() {
		var timeFactor = _intervalsDependOnFrequency
			? (3500 * _intrqPeriod / _tstatesPerIntrq)
			: 1;
			_vg93.set_timeFactor(timeFactor);
	}
}

// Upstream module: hardware/floppy.js
function ZX_Floppy() {
    var SEC_LENGTH_0x0080 = 0;
    var SEC_LENGTH_0x0100 = 1;
    var SEC_LENGTH_0x0200 = 2;
    var SEC_LENGTH_0x0400 = 3;

	var _isReady = false;
	var _cylinders = [];
	var _headCount = 0;
	var _isWriteProtected = true;
	var _isDoubleDensity = false;
    var _cyl = 0;
    var _head = 0;
    var _motor = 0;
    var _stateChangedEvent = new ZX_Event();

    this._debug_getRaw = function() {
        return _cylinders;
    }

    function onStateChanged() {
        _stateChangedEvent.emit({
            cyl: _cyl,
            head: _head,
            motor: !!_motor
        });
    }

    function createTrDosSector(cyl, sec, sectorSize, data, dataOffset) {
        if (typeof dataOffset === 'undefined') {
            dataOffset = 0;
        }

        var raw = [];
        raw.push(
            0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 
            0x4E, 0x4E); // GAP I
        raw.push(
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
            0x00, 0x00, 0x00, 0x00); // SYNC
        raw.push(
            0x1A1, 0x1A1, 0x1A1, // MFM Marker
            0xFE, // Address Marker
            cyl, // Track number
            0, // Side/Head. For TR-DOS is always 0, no matter what the actual value is.
            sec + 1, // Sector number is 1-based.
            SEC_LENGTH_0x0100);
        var crc = new CRC16();
        crc.addArray(raw, raw.length - 8); // Starting with MFM Marker
        raw.push(crc.value >> 8, crc.value & 0xFF);
        raw.push(
            0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E,
            0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E,
            0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E); // GAP II
        raw.push(
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
            0x00, 0x00, 0x00, 0x00); // SYNC
        raw.push(
            0x1A1, 0x1A1, 0x1A1, // MFM Marker
            0xFB // Data Marker
        );
        if (data.length - dataOffset < sectorSize)
            throw new Error(ZX_Lang.ERR_WRONG_DATA_BLOCK_SIZE + ' ' + sectorSize + ' <> ' + (data.length - dataOffset) + '.');
        raw.push.apply(raw, data.slice(dataOffset, dataOffset + sectorSize));
        crc = new CRC16();
        crc.addArray(raw, raw.length - sectorSize - 4); // Starting with MFM Marker
        raw.push(crc.value >> 8, crc.value & 0xFF);
        raw.push(
            0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E,
            0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E,
            0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E,
            0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E,
            0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E,
            0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E,
            0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E,
            0x4E, 0x4E, 0x4E, 0x4E); // GAP III
        return raw;
    }

	this.get_isReady = function() { return _isReady; }
	this.get_isWriteProtected = function() { return _isWriteProtected; }
    this.get_isDoubleDensity = function () { return _isDoubleDensity; }
	this.get_cylCount = function () { return _cylinders.length; }
	this.get_headCount = function () { return _headCount; }
    this.get_cylinder = function () { return _cyl; }
    this.set_head = function (value) { _head = value; onStateChanged(); }
    this.get_head = function () { return _head }
    this.set_motor = function (value) { _motor = +!!value; onStateChanged(); }
    this.get_motor = function () { return !!_motor; }
    this.get_onStateChanged = function () {
        return _stateChangedEvent.pub;
    }

    this.stepIn = function () {
        if (_cyl < _cylinders.length - 1) {
            _cyl++;
            onStateChanged();
        }
    }
    this.stepOut = function () {
        if (_cyl > 0) {
            _cyl--;
            onStateChanged();
        }
    }
    this.openStream = function() {
        var data;
        if (_cyl >= 0 && _cyl < _cylinders.length && _head >= 0 && _head < _headCount) {
            data = _cylinders[_cyl][_head];
        }
        else {
            data = [];
        }
        return new MemoryStream(data);
    }

    this.insertTRD = function (bin) {
        // UNDONE: имя диска из служебного сектора можно использовать как комментарий
        if ( !bin || !bin.length )
            throw new Error(ZX_Lang.ERR_TRD_IMAGE_WRONG_DATA);

        var cylCount = 0;
        var headCount = 0;
        // определяем конфигурацию диска из служебной информации
        switch ( bin[0x08e3] ) {
            case 0x16: cylCount = 80; headCount = 2; break;
            case 0x17: cylCount = 40; headCount = 2; break;
            case 0x18: cylCount = 80; headCount = 1; break;
            case 0x19: cylCount = 40; headCount = 1; break;
            // если служебная информация некорректная, то пытаемся определить
            // конфигурацию исходя из размера файла
            default:
                switch ( bin.length ) {
                    case 655360: cylCount = 80; headCount = 2; break;
                    case 327680: cylCount = 80; headCount = 1; break;
                    case 163840: cylCount = 40; headCount = 1; break;

                    // если и размер нестандартный, то бросаем исключение
                    default: throw new Error(ZX_Lang.ERR_TRD_IMAGE_UNKNOWN_TYPE);
                }
                break;
        }

        var cylinders = new Array(cylCount);
        var index = 0;
        for ( var cylIndex = 0; cylIndex < cylCount; cylIndex++ )
        for ( var headIndex = 0; headIndex < headCount; headIndex++ ) {
            var cyl = (cylinders[cylIndex] || (cylinders[cylIndex] = []));
            var track = (cyl[headIndex] || (cyl[headIndex] = []));
            var trackStream = new MemoryStream(track);
            var sectorSize = (0x0080 << SEC_LENGTH_0x0100);
            // Canonical TR-DOS MFM track, matching Fuse's INTERLEAVE_2 layout:
            // one 10-byte initial gap; physical IDs 1,9,2,10,...,8,16;
            // 378 bytes per sector including ID/data marks, CRCs and gaps;
            // 192 final gap bytes complete 6250 bytes at 250 kbit/s, 300 rpm.
            trackStream.writeMultiple(new Array(10).fill(0x4E));
            for (var physical = 0; physical < 16; physical++) {
                var sec = (physical >> 1) + ((physical & 1) ? 8 : 0);
                var offset = index + sec * sectorSize;
                var payload = offset < bin.length ? bin : new Array(sectorSize).fill(0);
                var payloadOffset = offset < bin.length ? offset : 0;
                trackStream.writeMultiple(createTrDosSector(cylIndex, sec, sectorSize, payload, payloadOffset).slice(10));
            }
            trackStream.writeMultiple(new Array(6250 - trackStream.get_length()).fill(0x4E));
            index += 16 * sectorSize;
        }

        _cylinders = cylinders;
        _headCount = headCount;
        _isDoubleDensity = true;
        _isWriteProtected = false;
        _isReady = true;
        onStateChanged();
    }

    this.insertSCL = function (bin) {
        var sclCatStream = new MemoryStream(bin);
        if (String.fromCharCode.apply(String, sclCatStream.readMultuple(8)) != 'SINCLAIR')
            throw new Error(ZX_Lang.ERR_SCL_IMAGE_WRONG_DATA);
            
        var fileCount = sclCatStream.read();
        if (fileCount < 0)
            throw new Error(ZX_Lang.ERR_SCL_IMAGE_WRONG_DATA);

        var sclStream = new MemoryStream(bin);
        sclStream.seek(9 + fileCount * 14, SeekOrigin.begin);

        var trdData = new Array(160 << 12); // 160 tracks; 16 sectors per track; 256 bytes per sector.
        for (var i = 0; i < trdData.length; i++) {
            trdData[i] = 0;
        }
        var trdCatStream = new MemoryStream(trdData);
        var trdStream = new MemoryStream(trdData);
        trdStream.seek(16 * 256, SeekOrigin.begin);

        for (var fileIndex = 0; fileIndex < fileCount; fileIndex++) {
            if (sclCatStream.get_position() >= (8 << 8))
                throw new Error(ZX_Lang.ERR_SCL_IMAGE_TOO_MANY_FILES);
            var fileHeader = sclCatStream.readMultuple(14);
            if (fileHeader.length != 14)
                throw new Error(ZX_Lang.ERR_SCL_IMAGE_WRONG_DATA);
            var fileSecCount = fileHeader[13];
            var trkIndex = trdStream.get_position() >> 12;
            var secIndex = (trdStream.get_position() - (trkIndex << 12)) >> 8;
            trdCatStream.writeMultiple(fileHeader);
            trdCatStream.write(secIndex);
            trdCatStream.write(trkIndex);
            trdStream.writeMultiple(sclStream.readMultuple(fileSecCount << 8));
        }
        var freeTrkIndex = trdStream.get_position() >> 12;
        var freeSecIndex = (trdStream.get_position() - (trkIndex << 12)) >> 8;
        var freeSecCount = (trdStream.get_length() - trdStream.get_position()) >> 8;
        trdCatStream.seek(8 << 8, SeekOrigin.begin);
        trdCatStream.write(0x00); // признак конца каталога
        trdCatStream.seek((8 << 8) + 0xE1, SeekOrigin.begin);
        trdCatStream.writeMultiple([
            freeSecIndex,
            freeTrkIndex,
            0x16, // дискета с 80-ю цилиндрами и двумя сторонами
            fileCount,
            freeSecCount & 0xFF,
            freeSecCount >> 8,
            0x10 // код TR-DOS'а
        ]);
        trdCatStream.seek((8 << 8) + 0xF4, SeekOrigin.begin);
        trdCatStream.writeMultiple([
            0x00, // количество удаленных файлов
            0x20, 0x20, 0x20, 0x20, 0x20, 0x20, 0x20, 0x20, 0x20, 0x20, 0x20 // имя диска
        ]);
        
        var crc = 0;
        var i = bin.length - 4;
        while (--i >= 0) {
            crc = (crc + bin[i]) & 0xFFFFFFFF;
        }
        var storedCrc = 
            (bin[bin.length - 1] << 24)
            | (bin[bin.length - 2] << 16)
            | (bin[bin.length - 3] << 8)
            | (bin[bin.length - 4]);
        if (crc != storedCrc) {
            handleError(ZX_Lang.ERR_SCL_IMAGE_WRONG_CRC);
        }

        this.insertTRD(trdStream.get_buffer());
    }

    this.insertFDI = function (bin) {
        if ( !bin || bin.length < 14 || bin[0] != 0x46 /*F*/ || bin[1] != 0x44 /*D*/ || bin[2] != 0x49 /*I*/ ) {
            throw new Error(ZX_Lang.ERR_FDI_IMAGE_WRONG_DATA);
        }
    
        var isWriteProtected = ( bin[3] != 0 );
        var cylCount = (( bin[5] << 8 ) | bin[4] );
        var headCount = (( bin[7] << 8 ) | bin[6] );
        var commentOffset = (( bin[9] << 8 ) | bin[8] );
        var dataOffset = (( bin[11] << 8 ) | bin[10] );
        var extraHeaderLength = (( bin[13] << 8 ) | bin[12] );
        var extraHeaderOffset = 14;
        var trackHeaderOffset = ( extraHeaderOffset + extraHeaderLength );
    
        var comment = '';
        while ( commentOffset < bin.length && bin[commentOffset] != 0 ) {
            comment += String.fromCharCode(bin[commentOffset]);
            commentOffset++;
        }
    
        var cylinders = [];
        for ( var cylIndex = 0; cylIndex < cylCount; cylIndex++ ) {
            var cyl = [];
            cylinders.push(cyl);
            for ( var headIndex = 0; headIndex < headCount; headIndex++ ) {
                var track = [];
                cyl.push(track);

                var trackDataOffset = (
                    dataOffset + 
                    (bin[trackHeaderOffset + 3] << 24) +
                    (bin[trackHeaderOffset + 2] << 16) +
                    (bin[trackHeaderOffset + 1] << 8) +
                    (bin[trackHeaderOffset + 0] << 0)
                );
    
                var secCount = bin[trackHeaderOffset + 6];
                for ( var secIndex = 0; secIndex < secCount; secIndex++ ) {
                    var secHeaderOffset = trackHeaderOffset + 7 + ( secIndex * 7 );
    
                    var cylByte = bin[secHeaderOffset + 0];
                    var headByte = bin[secHeaderOffset + 1];
                    var secByte = bin[secHeaderOffset + 2];
                    var sizeByte = bin[secHeaderOffset + 3];
                    var flags = bin[secHeaderOffset + 4];
    
                    var secDataOffset = ( 
                        trackDataOffset + 
                        ( bin[ secHeaderOffset + 6 ] << 8 ) +
                        bin[ secHeaderOffset + 5 ]
                    );
    
                    var secSize = ( 0x0080 << sizeByte );

                    track.push(
                        0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 
                        0x4E, 0x4E); // GAP I                    
                    track.push(
                        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
                        0x00, 0x00, 0x00, 0x00); // SYNC
                    track.push(
                        0x1A1, 0x1A1, 0x1A1, // MFM Marker
                        0xFE, // Address Marker
                        cylByte, // Track number
                        headByte, // Side/Head
                        secByte, // Sector number
                        sizeByte);
                    var crc = new CRC16();
                    crc.addArray(track, track.length - 8); // Starting with MFM Marker
                    track.push(crc.value >> 8, crc.value & 0xFF);
                    track.push(
                        0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E,
                        0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E,
                        0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E); // GAP II
                    track.push(
                        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
                        0x00, 0x00, 0x00, 0x00); // SYNC
                    track.push(
                        0x1A1, 0x1A1, 0x1A1 // MFM Marker
                    );
                    track.push(
                        (flags & 0x80) ? 0xF8 : 0xFB // Data Marker
                    );
                    for (var i = 0; i < secSize; i++) {
                        track.push(bin[secDataOffset++]);
                    }
                    var crcCalcSize = 0;
                    if ((flags & 0x01) && secSize >= 128) crcCalcSize = 128;
                    if ((flags & 0x02) && secSize >= 256) crcCalcSize = 256;
                    if ((flags & 0x04) && secSize >= 512) crcCalcSize = 512;
                    if ((flags & 0x08) && secSize >= 1024) crcCalcSize = 1024;
                    if ((flags & 0x10) && secSize >= 2048) crcCalcSize = 2048;
                    if ((flags & 0x20) && secSize >= 4096) crcCalcSize = 4096;
                    var crc = new CRC16();
                    crc.addArray(track, track.length - crcCalcSize - 4); // Starting with MFM Marker
                    track.push(crc.value >> 8, crc.value & 0xFF);
                    track.push(
                        0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E,
                        0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E,
                        0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E,
                        0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E,
                        0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E,
                        0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E,
                        0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E,
                        0x4E, 0x4E, 0x4E, 0x4E); // GAP III
                }
    
                // передвигаем смещение на следующий заголовок дорожки
                trackHeaderOffset += ( 7 + ( 7 * secCount ));
            }
        }
    
        _cylinders = cylinders
        _headCount = headCount;
        _isDoubleDensity = true;
        _isWriteProtected = isWriteProtected;
        _isReady = true;
        onStateChanged();
    }

    this.insertTD0 = function (bin) {
        var td0Stream = new MemoryStream(bin);
        bin = null;
        var td0CrcStream = new CRCWrapper(td0Stream, CRC16GEN.poly_A097());
        var signature = String.fromCharCode.apply(String, td0CrcStream.readMultuple(2));
        if (signature != 'TD' && signature != 'td')
            throw new Error(ZX_Lang.ERR_TD0_IMAGE_WRONG_DATA);
        var sequence = td0CrcStream.read();
        if (sequence != 0x00)
            throw new Error(ZX_Lang.ERR_TD0_IMAGE_WRONG_DATA);
        var checkSequence = td0CrcStream.read();
        var tekediskVersion = td0CrcStream.read();
        var dataParams = td0CrcStream.read();
        var dataRate = dataParams & 0x03; // 0: 250kbps; 1: 300kbps; 2: 500kbps.
        var doubleDensity = !(dataParams & 0x80);
        var driveType = td0CrcStream.read(); // 1: 360k; 2: 1.2M; 3: 720k; 4: 1.44M.
        // Drive Type experimentations:
        // 0 = 5.25 96 tpi disk in 48 tpi drive
        // 1 = 5.25
        // 2 = 5.25 48-tpi
        // 3 = 3.5
        // 4 = 3.5
        // 5 = 8-inch
        // 6 = 3.5
        var stepping = td0CrcStream.read(); // 0: Single-Step; 1: Double-Step; 2: Even-only step (96 tpi disk in 48 tpi drive)
        var dosAllocation = td0CrcStream.read();
        var headCount = td0CrcStream.read() == 1 ? 1 : 2;
        var crc = td0CrcStream.readNoCrc() | (td0CrcStream.readNoCrc() << 8);
        if (crc != td0CrcStream.get_crc().get_value())
            throw new Error(ZX_Lang.ERR_TD0_IMAGE_WRONG_HEADER_CRC);

        var compressed = signature == 'td';
        var formatStream;
        if (compressed) {
            formatStream = new LZSSDecompressionStream(td0Stream);
        }
        else {
            formatStream = td0Stream;
        }
        var formatCrcStream = new CRCWrapper(formatStream, CRC16GEN.poly_A097());

        var dataOffset = 0;
        // The comment block presence is indicated by the high bit of 'Stepping' field.
        if (stepping & 0x80) {
            var cmtCrc = formatCrcStream.readNoCrc() | (formatCrcStream.readNoCrc() << 8);
            formatCrcStream.get_crc().reset();
            var cmtLength = formatCrcStream.read() | (formatCrcStream.read() << 8);
            var cmtYear = formatCrcStream.read(); // 1900-based
            var cmtMonth = formatCrcStream.read(); // 0-based
            var cmtDay = formatCrcStream.read(); // 1-based
            var cmtHour = formatCrcStream.read();
            var cmtMinute = formatCrcStream.read();
            var cmtSecond = formatCrcStream.read();
            var cmtLines = [];
            var commentLine = ''
            for (var i = 0; i < cmtLength; i++) {
                var charCode = formatCrcStream.read();
                if (charCode) {
                    commentLine += String.fromCharCode(charCode);
                }
                if (!charCode || i == cmtLength - 1) {
                    cmtLines.push(commentLine);
                    commentLine = '';
                }
            }
            if (cmtCrc != formatCrcStream.get_crc().get_value())
                throw new Error(ZX_Lang.ERR_TD0_IMAGE_WRONG_COMMENT_HEADER_CRC);
        }

        // init floppy cylinders
        var cylinders = [];

        // Data block
        while (true) { 
            formatCrcStream.get_crc().reset();
            var secCount = formatCrcStream.read();
            if (secCount == 0xFF) // FF means the end of the track list.
                break;
            var cylIndex = formatCrcStream.read();
            var headAndDensity = formatCrcStream.read();
            var headIndex = headAndDensity & 0x01;
            var trackDoubleDensity = !(headAndDensity & 0x80);
            var trackHeadrCrcLowByte = formatCrcStream.readNoCrc();
            if (trackHeadrCrcLowByte != (formatCrcStream.get_crc().get_value() & 0xFF))
                throw new Error(ZX_Lang.ERR_TD0_IMAGE_WRONG_TRACK_HEADER_CRC);

            // init floppy track
            var cyl = (cylinders[cylIndex] || (cylinders[cylIndex] = []));
            var track = (cyl[headIndex] || (cyl[headIndex] = []));
            var trackStream = new MemoryStream(track);
            var trackCrcStream = new CRCWrapper(trackStream, CRC16GEN.poly_1021());

            for (var secIndex = 0; secIndex < secCount; secIndex++) {
                var idCyl = formatStream.read();
                var idHead = formatStream.read();
                var idSecNum = formatStream.read();
                var idSecSizeByte = formatStream.read();
                var idFlags = formatStream.read();
                var sectorDataCrcLowByte = formatStream.read();

                //var sectorBogusSector = idSecNum >= 100;
                var sectorLength = (0x0080 << idSecSizeByte);
                var sectorDuplicated = !!(idFlags & 0x01);
                var sectorCrcError = !!(idFlags & 0x02);
                var sectorDeletedRecordType = !!(idFlags & 0x04);
                var sectorDataIsSkipped = !!(idFlags & 0x10); // (no data block)
                var sectorNoData = !!(idFlags & 0x20); // (no data block)
                var sectorNoHeader = !!(idFlags & 0x40); // (bogus header)


                var sectorData = [];
                if (!sectorDataIsSkipped && !sectorNoData) {
                    var sectorDataBlockSize = formatStream.read() | (formatStream.read()<< 8); // size of the data + encoding method byte
                    var sectorDataBlockEncodingMethod = formatStream.read(); // 0: raw data; 1: repeatedly two 16-bit values: count and pattern; 2: RLE.

                    switch (sectorDataBlockEncodingMethod) {
                        case 0: 
                            sectorData = formatStream.readMultuple(sectorLength);
                            break;
                        case 1:
                            while (sectorData.length < sectorLength) {
                                var count = formatStream.read() | (formatStream.read() << 8);
                                var value1 = formatStream.read(), value2 = formatStream.read();
                                while (count--) {
                                    sectorData.push(value1, value2);
                                }
                            }
                            break;
                        case 2: 
                            while (sectorData.length < sectorLength) {
                                var startValue = formatStream.read();
                                if (!startValue) {
                                    var len = formatStream.read();
                                    sectorData.push.apply(sectorData, formatStream.readMultuple(len));
                                }
                                else {
                                    var len = 2 * startValue;
                                    var repeats = formatStream.read();
                                    var sequence = formatStream.readMultuple(len);
                                    while (repeats--) {
                                        sectorData.push.apply(sectorData, sequence);
                                    }
                                }
                            }
                            break;
                    }
                    var calcCrc = CRC16GEN.poly_A097();
                    calcCrc.addArray(sectorData);
                    if (sectorDataCrcLowByte != (calcCrc.get_value() & 0xFF))
                        throw new Error(ZX_Lang.ERR_TD0_IMAGE_WRONG_SECTOR_DATA_CRC);
                }

                // GAP I
                if (trackDoubleDensity) {
                    trackStream.writeMultiple([
                        0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 
                        0x4E, 0x4E]);
                }
                else {
                    trackStream.writeMultiple([
                        0xFF, 0xFF, 0xFF, 0xFF, 0xFF]);
                }
                // SYNC + IDAM
                if (!sectorNoHeader) {
                    if (trackDoubleDensity) {
                        trackStream.writeMultiple([
                            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
                            0x00, 0x00, 0x00, 0x00]);
                    }
                    else {
                        trackStream.writeMultiple([
                            0x00, 0x00, 0x00, 0x00, 0x00, 0x00]);
                    }
                    trackCrcStream.get_crc().reset();
                    if (trackDoubleDensity) {
                        trackCrcStream.writeMultiple([
                            0x1A1, 0x1A1, 0x1A1, 0xFE]);
                    }
                    else {
                        trackCrcStream.write(0x1FE);
                    }
                    trackCrcStream.writeMultiple([
                        idCyl, idHead, idSecNum, idSecSizeByte]);
                    var idCrc = trackCrcStream.get_crc().get_value();
                    trackStream.writeMultiple([
                        idCrc >> 8, idCrc & 0xFF]);
                }
                // GAP II + SYNC + DAM + DATA
                if (!sectorDataIsSkipped && !sectorNoData) {
                    if (trackDoubleDensity) {
                        trackStream.writeMultiple([
                            0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E,
                            0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E,
                            0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x00, 0x00,
                            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
                            0x00, 0x00]);
                    }
                    else {
                        trackStream.writeMultiple([
                            0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 
                            0xFF, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 
                            0x00]);
                    }
                    trackCrcStream.get_crc().reset();
                    if (trackDoubleDensity) {
                        trackCrcStream.writeMultiple([
                            0x1A1, 0x1A1, 0x1A1, (sectorDeletedRecordType ? 0xF8 : 0xFB)]);
                    }
                    else{
                        trackCrcStream.write(sectorDeletedRecordType ? 0x1F8 : 0x1FB);
                    }

                    trackCrcStream.writeMultiple(sectorData);
                    var dataCrc = trackCrcStream.get_crc().get_value();
                    if (!sectorCrcError) {
                        trackStream.writeMultiple([
                            dataCrc >> 8, dataCrc & 0xFF]);
                    }
                    else {
                        trackStream.writeMultiple([
                            dataCrc & 0xFF, dataCrc >> 8]);
                    }
                }
                // GAP III
                if (trackDoubleDensity) {
                    trackStream.writeMultiple([
                        0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E,
                        0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E,
                        0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E,
                        0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E,
                        0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E,
                        0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E,
                        0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E,
                        0x4E, 0x4E, 0x4E, 0x4E]);
                }
                else {
                    trackStream.writeMultiple([
                        0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
                        0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
                        0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
                        0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]);
                }
            }
        }

        _cylinders = cylinders;
        _headCount = headCount;
        _isDoubleDensity = doubleDensity;
        _isWriteProtected = false;
        _isReady = true;
        onStateChanged();
    }

    this.insertUDI = function (bin) {
        var udiRawStream = new MemoryStream(bin);
        var udiStream = new CRCWrapper(udiRawStream, CRC32GEN.poly_edb88320());
        bin = null;
        var signature = String.fromCharCode.apply(String, udiStream.readMultuple(4));
        if (signature != 'UDI!')
            throw new Error(ZX_Lang.ERR_UDI_IMAGE_WRONG_IMAGE_DATA);
        var fileSize = udiStream.read() | (udiStream.read() << 8) | (udiStream.read() << 16) | (udiStream.read() << 24);
        var version = udiStream.read();
        if (version != 0) 
            throw new Error(ZX_Lang.ERR_UDI_IMAGE_VERSION_NOT_SUPPORTED);
        var cylCount = udiStream.read() + 1;
        var headCount = udiStream.read() + 1;
        var zero = udiStream.read();
        var extHdrSize = udiStream.read() | (udiStream.read() << 8) | (udiStream.read() << 16) | (udiStream.read() << 24);
        var extHdr = udiStream.readMultuple(extHdrSize);
        // init cylinders
        var cylinders = [];
        for (var cylIndex = 0; cylIndex < cylCount; cylIndex++) {
            var cyl = (cylinders[cylIndex] || (cylinders[cylIndex] = []));
            for (var headIndex = 0; headIndex < headCount; headIndex++) {
                var track = (cyl[headIndex] || (cyl[headIndex] = []));
                var type = udiStream.read(); // 0 = MFM
                var size = udiStream.read() | (udiStream.read() << 8);
                var data = udiStream.readMultuple(size);
                var cmsize = (size >> 3) + (((size & 7) + 7) >> 3);
                for (var i = 0; i < cmsize; i++) {
                    var bits = udiStream.read();
                    if (!bits)
                        continue;
                    for (var j = 0; j < 8; j++, bits >>= 1) {
                        if (bits & 1) {
                            data[(i << 3) + j] |= 0x0100;
                        }
                    }
                }
                for (var i = 0; i < data.length; i++) {
                    track.push(data[i]);
                }
            }
        }
        var crc32 = udiRawStream.read() | (udiRawStream.read() << 8) | (udiRawStream.read() << 16) | (udiRawStream.read() << 24)
        if (crc32 != udiStream.get_crc().get_value()) {
            handleError(ZX_Lang.ERR_UDI_IMAGE_WRONG_CRC);
        }

        _cylinders = cylinders;
        _headCount = headCount;
        _isDoubleDensity = type == 0x00;
        _isWriteProtected = false;
        _isReady = true;
        onStateChanged();
    }

    this.insertDSK = function (bin) {
        // TODO: support weak data
        // TODO: support partly readable sectors
        var dskStream = new MemoryStream(bin);
        bin = null;
        var signature = String.fromCharCode.apply(String, dskStream.readMultuple(23));
        var extendedFormat = false;
        switch (signature) {
            case 'MV - CPCEMU Disk-File\r\n': extendedFormat = false; break;
            case 'EXTENDED CPC DSK File\r\n': extendedFormat = true; break;
            default: throw new Error(ZX_Lang.ERR_DSK_IMAGE_WRONG_DATA);
        }
        var signature2 = String.fromCharCode.apply(String, dskStream.readMultuple(11));
        if (signature2 != 'Disk-Info\r\n')
            throw new Error(ZX_Lang.ERR_DSK_IMAGE_WRONG_DATA);
        var creatorName = String.fromCharCode.apply(String, dskStream.readMultuple(14));
        var cylCount = dskStream.read();
        var headCount = dskStream.read();

        var cylinders = [];
        var wholeDiskIsInFM = true;
        if (extendedFormat) {
            dskStream.seek(2, SeekOrigin.current);
            var trackCount = cylCount * headCount;
            var trackAllocationTable = new Array(trackCount);
            for (var trackIndex = 0, offset = 0x0100; trackIndex < trackCount; trackIndex++) {
                var size = dskStream.read() << 8;
                trackAllocationTable[trackIndex] = [offset, size];
                offset += size;
            }
            for (var cylIndex = 0; cylIndex < cylCount; cylIndex++) {
                var cyl = cylinders[cylIndex] || (cylinders[cylIndex] = []);
                for (var headIndex = 0; headIndex < headCount; headIndex++) {
                    var track = cyl[headIndex] || (cyl[headIndex] = []);
                    var trackIndex = cylIndex * headCount + headIndex;
                    var trackDataSize = trackAllocationTable[trackIndex][1];
                    if (!trackDataSize)
                        continue;
                    var trackRawStream = new MemoryStream(track);
                    var trackStream = new CRCWrapper(trackRawStream, CRC16GEN.poly_1021());
                    var trackOffset = trackAllocationTable[trackIndex][0];
                    dskStream.seek(trackOffset, SeekOrigin.begin);
                    var trackSignature = String.fromCharCode.apply(String, dskStream.readMultuple(12));
                    if (trackSignature != 'Track-Info\r\n')
                        throw new Error(ZX_Lang.ERR_DSK_IMAGE_WRONG_DATA);
                    dskStream.seek(4, SeekOrigin.current);
                    var trCylNum = dskStream.read();
                    var trHeadNum = dskStream.read();
                    var dataRate = dskStream.read();
                    var recordingMode = dskStream.read();
                    var recordingModeIsFM = recordingMode == 1;
                    if (!recordingModeIsFM) {
                        wholeDiskIsInFM = false;
                    }
                    var spacePerSectorAllocated = (0x0080 << dskStream.read());
                    var secCount = dskStream.read();
                    var gapIIISize = dskStream.read();
                    var fillerByte = dskStream.read();
                    var sectorInfoOffset = dskStream.get_position();
                    var sectorDataOffset = trackOffset + 0x0100;
                    for (var secIndex = 0; secIndex < secCount; secIndex++) {
                        dskStream.seek(sectorInfoOffset, SeekOrigin.begin);
                        var secCylNum = dskStream.read();
                        var secHeadNum = dskStream.read();
                        var secSecNum = dskStream.read();
                        var secSizeByte = dskStream.read();
                        var secSize = (0x0080 << secSizeByte);
                        var fdcStatus1 = dskStream.read();
                        var fdcStatus2 = dskStream.read();
                        // secDataSize < secSize: controller reads only secDataSize bytes, and raises the error from fdsStatus1, fdsStatus2
                        // secDataSize == secSize: normal sector
                        // secDataSize == secSize * n: n variants of weak/random sector data
                        var secDataSize = dskStream.read() | (dskStream.read() << 8);
                        if (recordingModeIsFM) {
                            trackStream.writeMultiple([
                                0xFF, 0xFF, 0xFF, 0xFF, 0xFF, // GAP I
                                0x00, 0x00, 0x00, 0x00, 0x00, 0x00]); // SYNC
                            trackStream.get_crc().preset(0xFFFF);
                            trackStream.write(0x1FE); // IDAM
                        }
                        else {
                            trackStream.writeMultiple([
                                0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 
                                0x4E, 0x4E, // GAP I
                                0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
                                0x00, 0x00, 0x00, 0x00, // SYNC
                                0x1A1, 0x1A1, 0x1A1]); // MFM MARKER
                            trackStream.get_crc().preset(0xCDB4);
                            trackStream.write(0xFE); // IDAM
                        }
                        trackStream.writeMultiple([secCylNum, secHeadNum, secSecNum, secSizeByte]); // ID
                        trackStream.writeMultiple([trackStream.get_crc().get_value() >> 8, trackStream.get_crc().get_value() & 0xFF]); // ID CRC
                        if (recordingModeIsFM) {
                            trackStream.writeMultiple([
                                0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 
                                0xFF, 0xFF, 0xFF, // GAP II
                                0x00, 0x00, 0x00, 0x00, 0x00, 0x00]); // SYNC
                            trackStream.get_crc().preset(0xFFFF);
                            trackStream.write(0x1FB); // DAM
                        }
                        else {
                            trackStream.writeMultiple([
                                0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E,
                                0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E,
                                0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, // GAP II
                                0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
                                0x00, 0x00, 0x00, 0x00, // SYNC
                                0x1A1, 0x1A1, 0x1A1]); // MFM MARKER
                            trackStream.get_crc().preset(0xCDB4);
                            trackStream.write(0xFB); // DAM
                        }
                        sectorInfoOffset = dskStream.get_position();
                        dskStream.seek(sectorDataOffset, SeekOrigin.begin);
                        trackStream.writeMultiple(dskStream.readMultuple(secSize)); // DATA
                        trackStream.writeMultiple([trackStream.get_crc().get_value() >> 8, trackStream.get_crc().get_value() & 0xFF]); // DATA CRC
                        for (var i = 0; i < gapIIISize; i++) {
                            trackStream.write(recordingModeIsFM ? 0xFF : 0x4E); // GAP III
                        }
                        sectorDataOffset += secDataSize;                  
                    }
                }
            }
        }
        else {
            var spacePerTrackAllocated = dskStream.read() | (dskStream.read << 8);
            for (var cylIndex = 0; cylIndex < cylCount; cylIndex++) {
                var cyl = cylinders[cylIndex] || (cylinders[cylIndex] = []);
                for (var headIndex = 0; headIndex < headCount; headIndex++) {
                    var track = cyl[headIndex] || (cyl[headIndex] = []);
                    var trackRawStream = new MemoryStream(track);
                    var trackStream = new CRCWrapper(trackRawStream, CRC16GEN.poly_1021());
                    var trackIndex = cylIndex * headCount + headIndex;
                    var trackOffset = 0x0100 + trackIndex * spacePerTrackAllocated;
                    dskStream.seek(trackOffset, SeekOrigin.begin);
                    var trackSignature = String.fromCharCode.apply(String, dskStream.readMultuple(12));
                    if (trackSignature != 'Track-Info\r\n')
                        throw new Error(ZX_Lang.ERR_DSK_IMAGE_WRONG_DATA);
                    dskStream.seek(4, SeekOrigin.current);
                    var trCylNum = dskStream.read();
                    var trHeadNum = dskStream.read();
                    dskStream.seek(2, SeekOrigin.current);
                    var spacePerSectorAllocated = (0x0080 << dskStream.read());
                    var secCount = dskStream.read();
                    var gapIIISize = dskStream.read();
                    var fillerByte = dskStream.read();
                    for (var secIndex = 0; secIndex < secCount; secIndex++) {
                        var sectorOffset = trackOffset + 0x0100 + secIndex * spacePerSectorAllocated;
                        var secCylNum = dskStream.read();
                        var secHeadNum = dskStream.read();
                        var secSecNum = dskStream.read();
                        var secSizeByte = dskStream.read();
                        var secSize = (0x0080 << secSizeByte);
                        var fdcStatus1 = dskStream.read();
                        var fdcStatus2 = dskStream.read();
                        dskStream.seek(2, SeekOrigin.current);
                        trackStream.writeMultiple([
                            0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 
                            0x4E, 0x4E, // GAP I
                            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
                            0x00, 0x00, 0x00, 0x00, // SYNC
                            0x1A1, 0x1A1, 0x1A1]); // MFM MARKER
                        trackStream.get_crc().preset(0xCDB4);
                        trackStream.writeMultiple([0xFE, secCylNum, secHeadNum, secSecNum, secSizeByte]); // IDAM + ID
                        trackStream.writeMultiple([trackStream.get_crc().get_value() >> 8, trackStream.get_crc().get_value() & 0xFF]); // ID CRC
                        trackStream.writeMultiple([
                            0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E,
                            0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E,
                            0x4E, 0x4E, 0x4E, 0x4E, 0x4E, 0x4E, // GAP II
                            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
                            0x00, 0x00, 0x00, 0x00, // SYNC
                            0x1A1, 0x1A1, 0x1A1]); // MFM MARKER
                        trackStream.get_crc().preset(0xCDB4);
                        trackStream.write(0xFB); // DAM
                        var currentOffset = dskStream.get_position();
                        dskStream.seek(sectorOffset, SeekOrigin.begin);
                        trackStream.writeMultiple(dskStream.readMultuple(secSize)); // DATA
                        dskStream.seek(currentOffset, SeekOrigin.begin);
                        trackStream.writeMultiple([trackStream.get_crc().get_value() >> 8, trackStream.get_crc().get_value() & 0xFF]); // DATA CRC
                        for (var i = 0; i < gapIIISize; i++) {
                            trackStream.write(0x4E); // GAP III
                        }
                    }
                }
            }
        }

        _cylinders = cylinders;
        _headCount = headCount;
        _isDoubleDensity = !wholeDiskIsInFM;
        _isWriteProtected = false;
        _isReady = true;
        onStateChanged();
    }

    this.create = function (cylCount, headCount, trdosFormat) {
        var cylinders = [];
        for (var cylIndex = 0; cylIndex < cylCount; cylIndex++)
        for (var headIndex = 0; headIndex < headCount; headIndex++) {            
            var cyl = cylinders[cylIndex] || (cylinders[cylIndex] = []);
            var track = cyl[headIndex] || (cyl[headIndex] = []);
            if (trdosFormat) {
                var trackStream = new MemoryStream(track);
                for (var secIndex = 0; secIndex < 16; secIndex++) {
                    if (cylIndex == 0 && headIndex == 0 && secIndex == 8) {
                        var diskType = (cylCount < 80) ? (headCount == 2 ? 0x17 : 0x19) : (headCount == 2 ? 0x16 : 0x18);
                        var freeSecCount = (cylCount * headCount - 1) * 16;
                        trackStream.writeMultiple(createTrDosSector(cylIndex, secIndex, 0x0100, [
                            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                            0, 0x00, 0x01, diskType, 0x00, freeSecCount & 0xFF, freeSecCount >> 8, 0x10, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0x00, 0x20, 0x20, 0x20, 0x20, 0x20, 0x20, 0x20, 0x20, 0x20, 0x20, 0x20
                        ]));
                    }
                    else {
                        trackStream.writeMultiple(createTrDosSector(cylIndex, secIndex, 0x0100, [
                            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
                        ]));
                    }
                }
            }
        
        }

        _cylinders = cylinders;
        _headCount = headCount;
        _isDoubleDensity = true;
        _isWriteProtected = false;
        _isReady = true;
        onStateChanged();
    }

    this.eject = function () {
        _isReady = false;
        _cylinders = [];
        _headCount = 0;
        _isDoubleDensity = false;
        _isWriteProtected = false;
    }

    this.getCompatibleFormats = function() {
        var formats = [];
        if (_isReady) {
            formats.push('UDI', 'TD0', 'FDI');
            if (_isDoubleDensity) {
                var sclCompatible = true;
                for (var cylIndex = 0; cylIndex < _cylinders.length; cylIndex++)
                for (var headIndex = 0; headIndex < _headCount; headIndex++) {
                    var track = _cylinders[cylIndex][headIndex];
                    var trackRawStream = new MemoryStream(track);
                    var trackStream = new CRCWrapper(trackRawStream, CRC16GEN.poly_1021());
                    var sectors = new Array(16);
                    var amDetector = new VG93AMDetector(_isDoubleDensity);
                    while (sclCompatible) {
                        var next;
                        do {
                            next = trackStream.read();
                            if (_isDoubleDensity && (next & 0x1FF) == 0x1A1) {
                                trackStream.get_crc().preset(0xCDB4);
                            }
                            else if (!_isDoubleDensity && ((next & 0x1FC) == 0x1F8 || (next & 0x1FF) == 0x1FC || (next ^ 0x1FF) == 0x1FE)) {
                                trackStream.get_crc().preset(0xFFFF);
                                trackStream.get_crc().add(next);
                            }
                            amDetector.analyseNext(next);
                        }
                        while (next >= 0 && !amDetector.get_marker());
                        if (next < 0)
                            break;
                        if (amDetector.get_marker() != 0xFE) {
                            sclCompatible = false;
                            break;
                        }
                        var idCyl = trackStream.read();
                        var idHead = trackStream.read();
                        var idSec = trackStream.read();
                        var idSize = trackStream.read();
                        if (idCyl != cylIndex 
                            || idHead != 0 
                            || idSec < 1 
                            || idSec > 16
                            || sectors[idSec-1]
                            || idSize != 1) {

                            sclCompatible = false;
                            break;
                        }
                        var idCrc = (trackStream.get_stream().read() << 8) | trackStream.get_stream().read();
                        if (idCrc != trackStream.get_crc().get_value()) {
                            sclCompatible = false;
                            break;
                        }
                        do {
                            next = trackStream.read();
                            if (_isDoubleDensity && (next & 0x1FF) == 0x1A1) {
                                trackStream.get_crc().preset(0xCDB4);
                            }
                            else if (!_isDoubleDensity && ((next & 0x1FC) == 0x1F8 || (next & 0x1FF) == 0x1FC || (next ^ 0x1FF) == 0x1FE)) {
                                trackStream.get_crc().preset(0xFFFF);
                                trackStream.get_crc().add(next);
                            }
                            amDetector.analyseNext(next);
                        }
                        while (next >= 0 && !amDetector.get_marker());
                        if (next < 0)
                            break;
                        if ((amDetector.get_marker() & 0xFC) != 0xF8) {
                            sclCompatible = false;
                            break;
                        }
                        trackStream.readMultuple(256);
                        var dataCrc = trackStream.get_stream().read() << 8 | trackStream.get_stream().read();
                        if (dataCrc != trackStream.get_crc().get_value()) {
                            sclCompatible = false;
                            break;
                        }
                        sectors[idSec-1] = true;
                    }
                    for (var i = 0; i < sectors.length; i++) {
                        if (!sectors[i]) {
                            sclCompatible = false;
                            break;
                        }
                    }
                }
                if (sclCompatible) {
                    formats.push('SCL');
                    if (_cylinders.length == 40 || _cylinders.length == 80) {
                        formats.push('TRD');
                    }
                }
            }
        }
        return formats;
    }

    this.saveToTRD = function () {
        var trdStream = new MemoryStream([]);
        for (var cylIndex = 0; cylIndex < _cylinders.length; cylIndex++)
        for (var headIndex = 0; headIndex < _headCount; headIndex++) {
            var sectors = new Array(16);
            var trackStream = new MemoryStream(_cylinders[cylIndex][headIndex]);
            var next;
            while ((next = trackStream.read()) >= 0) {
                while (next >= 0 && (next & 0x1FF) != 0x1A1) {
                    next = trackStream.read();
                }
                while (next >= 0 && next != 0xFE ) {
                    next = trackStream.read();
                }
                trackStream.seek(2, SeekOrigin.current); // skip cylinder and head number
                var sectorIndex = trackStream.read() - 1;
                trackStream.seek(3, SeekOrigin.current); // skip sector size and crc
                while (next >= 0 && (next & 0x1FF) != 0x1A1) {
                    next = trackStream.read();
                }
                while (next >= 0 && (next & 0xFC) != 0xF8) {
                    next = trackStream.read();
                }
                sectors[sectorIndex] = trackStream.readMultuple(256);
                trackStream.seek(2, SeekOrigin.current); // skip crc
            }
            for (var secIndex = 0; secIndex < sectors.length; secIndex++) {
                var data = sectors[secIndex] || [
                    0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                    0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                    0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                    0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                    0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
                    0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
                ];
                trdStream.writeMultiple(data);
            }
        }
        return trdStream.get_buffer();
    }

    this.saveToSCL = function () {
        var trdStream = new MemoryStream(this.saveToTRD());
        var files = [];
        while (trdStream.get_position() < 0x800) {
            var fileRec = trdStream.readMultuple(16);
            if (fileRec.length != 16 || !fileRec[0])
                break;
            if (fileRec[0] != 0x01) {
                var currentPosition = trdStream.get_position();
                var file = {
                    header: fileRec.slice(0, 14),
                    data: []
                };
                var fileStream = new MemoryStream(file.data);
                var secCount = fileRec[13];
                var secIndex = fileRec[14];
                var trkIndex = fileRec[15];
                trdStream.seek(0x1000 * trkIndex + 0x0100 * secIndex)
                fileStream.writeMultiple(trdStream.readMultuple(0x0100 * secCount));
                files.push(file);
                trdStream.seek(currentPosition, SeekOrigin.begin);
            }
        }

        var sclStream = new MemoryStream([]);
        sclStream.writeMultiple([0x53, 0x49, 0x4E, 0x43, 0x4C, 0x41, 0x49, 0x52]); // SINCLAIR
        sclStream.write(files.length);
        for (var i = 0; i < files.length; i++) {
            sclStream.writeMultiple(files[i].header);
        }
        for (var i = 0; i < files.length; i++) {
            sclStream.writeMultiple(files[i].data);
        }
        var crcLo = 0x0000;
        var crcHi = 0x0000;
        sclStream.seek(0, SeekOrigin.begin);
        var next;
        while ((next = sclStream.read()) >= 0) {
            crcLo += next;
            if (crcLo & 0x10000) {
                crcLo &= 0xFFFF;
                crcHi = (crcHi + 1) & 0xFFFF;
            }
        }
        sclStream.writeMultiple([
            crcLo & 0xFF, crcLo >> 8,
            crcHi & 0xFF, crcHi >> 8
        ]);
        return sclStream.get_buffer();
    }

    this.saveToFDI = function () {
        // EXTRACT DATA
        var tracks = [];
        for (var cylIndex = 0; cylIndex < _cylinders.length; cylIndex++)
        for (var headIndex = 0; headIndex < _headCount; headIndex++) {
            var sectors = [];
            var trackRawStream = new MemoryStream(_cylinders[cylIndex][headIndex]);
            var trackStream = new CRCWrapper(trackRawStream, CRC16GEN.poly_1021());
            var amDetector = new VG93AMDetector(_isDoubleDensity);
            var next;
            while (true) {
                var next;
                do {
                    next = trackStream.read();
                    if (_isDoubleDensity && (next & 0x1FF) == 0x1A1) {
                        trackStream.get_crc().preset(0xCDB4);
                    }
                    else if (!_isDoubleDensity && ((next & 0x1FC) == 0x1F8 || (next & 0x1FF) == 0x1FC || (next ^ 0x1FF) == 0x1FE)) {
                        trackStream.get_crc().preset(0xFFFF);
                        trackStream.get_crc().add(next);
                    }
                    amDetector.analyseNext(next);
                }
                while (next >= 0 && amDetector.get_marker() != 0xFE);
                if (next < 0)
                    break;
                // read ID
                var idCyl = trackStream.read();
                var idHead = trackStream.read();
                var idSec = trackStream.read();
                var idSize = trackStream.read();
                do {
                    next = trackStream.read();
                    if (_isDoubleDensity && (next & 0x1FF) == 0x1A1) {
                        trackStream.get_crc().preset(0xCDB4);
                    }
                    else if (!_isDoubleDensity && ((next & 0x1FC) == 0x1F8 || (next & 0x1FF) == 0x1FC || (next ^ 0x1FF) == 0x1FE)) {
                        trackStream.get_crc().preset(0xFFFF);
                        trackStream.get_crc().add(next);
                    }
                    amDetector.analyseNext(next);
                }
                while (next >= 0 && !amDetector.get_marker());
                if (next < 0)
                    break;
                if ((amDetector.get_marker() & 0xFC) != 0xF8) {
                    trackStream.seek(
                        _isDoubleDensity ? -2 : -1,
                        SeekOrigin.current
                    );
                    continue;
                }
                var flags = (next & 0xFE) == 0xF8 ? 0x80 : 0x00;
                var data = trackStream.readMultuple(0x0080 << idSize);
                if (data.length != (0x0080 << idSize))
                    break;
                var dataCrc = trackStream.get_crc().get_value();
                var realDataCrc = (trackStream.get_stream().read() << 8) | trackStream.get_stream().read();
                if (dataCrc == realDataCrc) {
                    flags |= (0x01 << idSize);
                }
                sectors.push({
                    id: [idCyl, idHead, idSec, idSize, flags],
                    data: data
                });
            }
            tracks.push(sectors);
        }
        // WRITE TO IMAGE
        var fdiStream = new MemoryStream([]);
        fdiStream.writeMultiple([0x46, 0x44, 0x49]); // FDI
        fdiStream.writeMultiple([
            _isWriteProtected ? 1 : 0,
            _cylinders.length & 0xFF,
            _cylinders.length >> 8,
            _headCount & 0xFF,
            _headCount >> 8
        ]);
        fdiStream.writeMultiple([
            0x00, 0x00, // Смещение тексте (LH)
            0x00, 0x00, // Смещение данных (LH)
            0x00, 0x00  // Длина расширенного заголовка (LH)
        ]);
        var trackOffset = 0x00000000;
        for (var trkIndex = 0; trkIndex < tracks.length; trkIndex++) {
            var track = tracks[trkIndex];
            fdiStream.writeMultiple([
                (trackOffset >> 0) & 0xFF,
                (trackOffset >> 8) & 0xFF,
                (trackOffset >> 16) & 0xFF,
                (trackOffset >> 24) & 0xFF,
                0,
                0
            ]);
            fdiStream.write(track.length);
            var sectorOffset = 0x0000;
            for (var secIndex = 0; secIndex < track.length; secIndex++) {
                fdiStream.writeMultiple(track[secIndex].id);
                fdiStream.writeMultiple([
                    (sectorOffset >> 0) & 0xFF,
                    (sectorOffset >> 8) & 0xFF
                ]);
                sectorOffset += (0x0080 << track[secIndex].id[3]);
            }
            trackOffset += sectorOffset;
        }
        // сохраняем смещение текста
        var currentPosition = fdiStream.get_position();
        fdiStream.seek(0x08, SeekOrigin.begin);
        fdiStream.writeMultiple([
            (currentPosition >> 0) & 0xFF,
            (currentPosition >> 8) & 0xFF
        ]);
        fdiStream.seek(currentPosition, SeekOrigin.begin);
        var desc = '\0';
        var descData = stringToBytes(desc);
        fdiStream.writeMultiple(descData);
        // сохраняем смещение данных
        currentPosition = fdiStream.get_position();
        fdiStream.seek(0x0A, SeekOrigin.begin);
        fdiStream.writeMultiple([
            (currentPosition >> 0) & 0xFF,
            (currentPosition >> 8) & 0xFF
        ]);
        fdiStream.seek(currentPosition, SeekOrigin.begin);
        // записываем данные секторов
        for (var trkIndex = 0; trkIndex < tracks.length; trkIndex++) {
            var track = tracks[trkIndex];
            for (var secIndex = 0; secIndex < track.length; secIndex++) {
                var sector = track[secIndex];
                fdiStream.writeMultiple(sector.data);
            }
        }
        
        return fdiStream.get_buffer();
    }

    this.saveToUDI = function() {
        var udiStream = new MemoryStream([]);
        udiStream.writeMultiple([0x55, 0x44, 0x49, 0x21]); // UDI!
        udiStream.writeMultiple([0x00, 0x00, 0x00, 0x00]); // File size
        udiStream.write(0x00); // Version
        udiStream.write(_cylinders.length - 1);
        udiStream.write(_headCount - 1);
        udiStream.write(0x00); // Unused
        udiStream.writeMultiple([0x00, 0x00, 0x00, 0x00]); // Extended header length
        for (var cylIndex = 0; cylIndex < _cylinders.length; cylIndex++)
        for (var headIndex = 0; headIndex < _headCount; headIndex++) {
            var track = _cylinders[cylIndex][headIndex];
            var trackStream = new MemoryStream(track);
            udiStream.write(_isDoubleDensity ? 0x00 : 0x01);
            udiStream.writeMultiple([track.length & 0xFF, track.length >> 8]);
            var next;
            while ((next = trackStream.read()) >= 0) {
                udiStream.write(next & 0xFF);
            }
            trackStream.seek(0, SeekOrigin.begin);
            var cmsize = (track.length >> 3) + (((track.length & 7) + 7) >> 3);
            for (var i = 0; i < cmsize; i++) {
                var bytes = trackStream.readMultuple(8);
                var bits = 0x00;
                for (var j = 0, mask = 1; j < bytes.length; j++, mask <<= 1) {
                    if (bytes[j] & 0x0100) {
                        bits |= mask;
                    }
                }
                udiStream.write(bits);
            }
        }
        udiStream.seek(4, SeekOrigin.begin);
        udiStream.writeMultiple([
            (udiStream.get_length() >> 0) & 0xFF,
            (udiStream.get_length() >> 8) & 0xFF,
            (udiStream.get_length() >> 16) & 0xFF,
            (udiStream.get_length() >> 24) & 0xFF
        ]);
        var crc = CRC32GEN.poly_edb88320();
        crc.addArray(udiStream.get_buffer());
        udiStream.seek(0, SeekOrigin.end);
        udiStream.writeMultiple([
            (crc.get_value() >> 0) & 0xFF,
            (crc.get_value() >> 8) & 0xFF,
            (crc.get_value() >> 16) & 0xFF,
            (crc.get_value() >> 24) & 0xFF
        ]);
        return udiStream.get_buffer();
    };

    this.saveToTD0 = function () {
        var td0RawStream = new MemoryStream([]);
        var td0Stream = new CRCWrapper(td0RawStream, CRC16GEN.poly_A097());
        td0Stream.writeMultiple([0x54, 0x44]); // TD
        td0Stream.write(0); // Sequence
        td0Stream.write(0); // Check sequence
        td0Stream.write(0x15); // Version 1.5
        td0Stream.write(_isDoubleDensity ? 0x00 : 0x80); // Single density flag & Data rate code
        td0Stream.write(0x04); // Drive type (3.5'' 1.44MB)
        td0Stream.write(0x00); // Comment block flag & Stepping code
        td0Stream.write(0x00); // DOS allocation flag
        td0Stream.write(_headCount);
        td0Stream.get_stream().writeMultiple([
            td0Stream.get_crc().get_value() & 0xFF,
            td0Stream.get_crc().get_value() >> 8
        ]);

        for (var cylIndex = 0; cylIndex < _cylinders.length; cylIndex++)
        for (var headIndex = 0; headIndex < _headCount; headIndex++) {
            var track = _cylinders[cylIndex][headIndex];
            var trackRawStream = new MemoryStream(track);
            var trackStream = new CRCWrapper(trackRawStream, CRC16GEN.poly_1021());
            
            var sectorInfoArr = [];
            var sectorInfo = null;
            var nextBogusSectorIndex = 100;
            var amDetector = new VG93AMDetector(_isDoubleDensity);
            while (true) {
                var next;
                do {
                    next = trackStream.read();
                    if (_isDoubleDensity && (next & 0x1FF) == 0x1A1) {
                        trackStream.get_crc().preset(0xCDB4);
                    }
                    else if (!_isDoubleDensity && ((next & 0x1FC) == 0x1F8 || (next & 0x1FF) == 0x1FC || (next ^ 0x1FF) == 0x1FE)) {
                        trackStream.get_crc().preset(0xFFFF);
                        trackStream.get_crc().add(next);
                    }
                    amDetector.analyseNext(next);
                }
                while (next >= 0 && !amDetector.get_marker());
                if (next < 0)
                    break;
                switch (amDetector.get_marker()) {
                    case 0xFE:
                        if (sectorInfo) {
                            // HEADER WITHOUT DATA
                            sectorInfoArr.push(sectorInfo);
                        }
                        var id = trackStream.readMultuple(4);
                        var crcCalculated = trackStream.get_crc().get_value();
                        var crcPresented = (trackStream.read() << 8) | trackStream.read();
                        sectorInfo = {
                            cyl: id[0],
                            head: id[1],
                            sec: id[2],
                            size: id[3],
                            crc1: crcPresented,
                            crc1Calc: crcCalculated
                        };
                        break;
                    case 0xF8:
                    case 0xF9:
                    case 0xFA:
                    case 0xFB:
                        if (!sectorInfo) {
                            // DATA WITHOUT ID
                            sectorInfo = {
                                cyl: cylIndex,
                                head: headIndex,
                                sec: nextBogusSectorIndex++,
                                size: -1
                            };
                        }
                        sectorInfo.dataAM = amDetector.get_marker();
                        if (sectorInfo.size >= 0) {
                            // NORMAL DATA
                            var secLen = 0x0080 << sectorInfo.size;
                            var secData = trackStream.readMultuple(secLen);
                            if (secData.length == secLen) {
                                sectorInfo.data = secData;
                                sectorInfo.crc2Calc = trackStream.get_crc().get_value();
                                sectorInfo.crc2 = (trackStream.read() << 8) | trackStream.read();
                            }
                        }
                        else {
                            // DATA WITHOUT ID
                            // get all the data till the next address marker
                            var amDetector2 = new VG93AMDetector(_isDoubleDensity);
                            var sectorDataBeginPos = trackStream.get_position();
                            var sectorDataBeginCrc = trackStream.get_crc().get_value();
                            var sectorData = [];
                            do {
                                next = trackStream.read();
                                if (_isDoubleDensity && (next & 0x1FF) == 0x1A1) {
                                    trackStream.get_crc().preset(0xCDB4);
                                }
                                else if (!_isDoubleDensity && ((next & 0x1FC) == 0x1F8 || (next & 0x1FF) == 0x1FC || (next ^ 0x1FF) == 0x1FE)) {
                                    trackStream.get_crc().preset(0xFFFF);
                                    trackStream.get_crc().add(next);
                                }
                                amDetector2.analyseNext(next);
                                if (next >= 0 && !amDetector2.get_marker()) {
                                    sectorData.push(next);
                                }
                            }
                            while (next >= 0 && !amDetector2.get_marker());
                            // try to guess sector length by looking for correct crc
                            var sectorLen = 0x2000;
                            while ((sectorData.length + 2) < sectorLen) {
                                sectorLen >>= 1;
                            }
                            while (sectorLen >= 0x0080) {
                                var crc = CRC16GEN.poly_1021();
                                crc.preset(sectorDataBeginCrc);
                                crc.addArray(sectorData, 0, sectorLen);
                                var postCrc = (sectorData[sectorLen + 1] << 8) || sectorData[sectorLen];
                                if (crc.get_value() == postCrc) {
                                    sectorInfo.data = sectorData.slice(0, sectorLen);
                                    sectorInfo.crc2 = postCrc;
                                    sectorInfo.crc2Calc = crc.get_value();
                                    var s = 0;
                                    for (var l = sectorLen; l > 0x0080; l >>= 1) {
                                        s++;
                                    }
                                    sectorInfo.size = s;
                                    break;
                                }
                            }
                            // if it failed then take the maximum possible sector size with wrong crc
                            if (!sectorInfo.data) {
                                sectorLen = 0x2000;
                                while ((sectorData.length + 2) < sectorLen) {
                                    sectorLen >>= 1;
                                }
                                if (sectorLen >= 0x0080) {
                                    var crc = CRC16GEN.poly_1021();
                                    crc.preset(sectorDataBeginCrc);
                                    crc.addArray(sectorData, 0, sectorLen);
                                    sectorInfo.data = sectorData.slice(0, sectorLen);
                                    sectorInfo.crc2 = (sectorData[sectorLen + 1] << 8) | sectorData[sectorLen];
                                    sectorInfo.crc2Calc = crc.get_value();
                                    var s = 0;
                                    for (var l = sectorLen; l > 0x0080; l >>= 1) {
                                        s++;
                                    }
                                    sectorInfo.size = s;
                                }
                            }
                            // set stream position just after the sector data block (if it exists)
                            trackStream.seek(sectorDataBeginPos, SeekOrigin.begin);
                            trackStream.get_crc().preset(sectorDataBeginCrc);
                            if (sectorInfo.size >= 0) {
                                trackStream.seek((0x0080 << sectorInfo.size) + 2, SeekOrigin.current);
                                trackStream.get_crc().addArray(sectorInfo.data);
                                trackStream.get_crc().add(sectorInfo.crc2 >> 8);
                                trackStream.get_crc().add(sectorInfo.crc2 & 0xFF);
                            }
                        }
                        sectorInfoArr.push(sectorInfo);
                        sectorInfo = null;
                        break;
                }
            }
            if (sectorInfo) {
                sectorInfoArr.push(sectorInfo);
                sectorInfo = null;
            }

            td0Stream.get_crc().preset(0);
            td0Stream.write(sectorInfoArr.length);
            td0Stream.write(cylIndex);
            td0Stream.write(headIndex);
            td0Stream.write(td0Stream.get_crc().get_value() & 0xFF);
            for (var secIndex = 0; secIndex < sectorInfoArr.length; secIndex++) {
                var sectorInfo = sectorInfoArr[secIndex];
                td0Stream.write(sectorInfo.cyl);
                td0Stream.write(sectorInfo.head);
                td0Stream.write(sectorInfo.sec);
                td0Stream.write(Math.max(sectorInfo.size, 0));
                var secFlags = 
                    ((!!sectorInfo.data && sectorInfo.crc2 != sectorInfo.crc2Calc) << 1)
                    | (((sectorInfo.dataAM & 0xFE) == 0xF8) << 2)
                    | ((!sectorInfo.data) << 5)
                    | ((sectorInfo.sec >= 100) << 6);
                td0Stream.write(secFlags);
                if (sectorInfo.data) {
                    var crc = CRC16GEN.poly_A097();
                    crc.addArray(sectorInfo.data);
                    td0Stream.write(crc.get_value() & 0xFF);
                    // UNDONE: analyze data and use different encoding methods to preserve space
                    var l = sectorInfo.data.length + 1;
                    td0Stream.write(l & 0xFF);
                    td0Stream.write(l >> 8);
                    td0Stream.write(0);
                    td0Stream.writeMultiple(sectorInfo.data);
                }
                else {
                    td0Stream.write(0); // lo(crc)
                }
            }
        }
        td0Stream.write(0xFF);

        return td0Stream.get_buffer();
    };
}

// Upstream module: hardware/vg93.js
/* 
    В TR-DOS'е с режимом MFM типичной длиной дорожки 
    считается 6250 байт (6208...6464 байт), для FM - 3125 байт.
    FM - Фазовая модуляция (Одинарная плотность записи)
    MFM - Модифицированная фазовая модуляция (Двойная плотность записи)
*/

function VG93(clock) {
    this.masterReset = masterReset;
    this.write = write;
    this.read = read;
    this.get_intrq = get_intrq;
    this.get_drq = get_drq;
    this.get_headLoad = get_headLoad;
    this.get_dirc = get_dirc;
    this.set_doubleDensity = set_doubleDensity;
    this.set_headReady = set_headReady;
    this.get_floppy = get_floppy;
    this.set_floppy = set_floppy;
    this.get_timeFactor = get_timeFactor;
    this.set_timeFactor = set_timeFactor;
    this.get_state = get_state;

	// Тактовый генератор.
	// Дает возможность измерять эмулируемое время для вычисления задержек.
    var _clock = clock;
    var _floppy;
  
    var BYTES_PER_TRACK_MFM = 6250; // 6250
    var BYTES_PER_TRACK_FM = 3125; // 3125

    var _timeFactor = 1;
    var _baseIntervals = {
        REVOLUTION_INTERVAL: 200, // (частота вращения = 300 об/минуту)
        INDEX_PULSE_DURATION: 4, // 2?
        STEP_DELAYS: [6, 12, 20, 30],
        HEAD_ENGAGE_DURATION: 15
    };
    // приод оборота (и появления индексного импульса)
    var REVOLUTION_INTERVAL = 200;
	// продолжительность индексного импульса (ms)
    var INDEX_PULSE_DURATION = 4;
    var HEAD_ENGAGE_DURATION = 15;
    var STEP_DELAYS = [6, 12, 20, 30];

    // in
    var _doubleDensity = 0; // MFM
    var _headReady = 0; // HRDY
    var _ready = 0; // RDY
    // out
    var _intrq = 0;
    var _drq = 0;
    var _headLoad = 0;
    var _dirc = 1;
    // internal
    var _track = 0;
    var _sector = 1;
    var _command = 0x03;
    var _data = 0;
    var _busy = 0;
    var _intrqLocked = 0;
    var _onHeadReady = new Trigger();
    var _onReadyOn = new Trigger();
    var _onReadyOff = new Trigger();
    var _commandInstance = null;
    var _revolutionState = new RevolutionState();

    var _notBusyIndexPulseCounter = 0;

    function Trigger() {
        var handlers = [];

        this.add = function (handler) {
            handlers.push(handler);
        }
        this.remove = function (handler) {
            var i = handlers.indexOf(handler);
            if (i >= 0) {
                handlers.splice(i, 1);
            }
        }
        this.fire = function () {
            var pending = handlers.splice(0);
            for (var i = 0; i < pending.length; i++) {
                pending[i]();
            }
        }
    }

    function RevolutionState() {
        var _rotation = false;
        var _lastRevolutionBegin = 0;
        var _revolutionProgress = 0;

        var _onIndexPulse = new Trigger();
        var _indexPulse = false;
        var _indexPulseBeginTask = null;
        var _indexPulseEndTask = null;

        this.get_rotation = get_rotation;
        this.set_rotation = set_rotation;
        this.get_indexPulse = get_indexPulse;
        this.get_revolutionProgressPercent = get_revolutionProgressPercent;
        this.onIndexPulse = _onIndexPulse;

        function get_rotation() {
            return _rotation; 
        }

        function set_rotation(value) {
            if (value == _rotation)
                return;
            _rotation = value;
            if (_rotation) {
                set_indexPulse(_revolutionProgress < INDEX_PULSE_DURATION);
                _indexPulseBeginTask = _clock.setInterval(function () { set_indexPulse(true);  _lastRevolutionBegin = _clock.get_ms(); }, REVOLUTION_INTERVAL, 0, REVOLUTION_INTERVAL - _revolutionProgress);
                _indexPulseEndTask = _clock.setInterval(function () { set_indexPulse(false); }, REVOLUTION_INTERVAL, 0, _revolutionProgress < INDEX_PULSE_DURATION ? INDEX_PULSE_DURATION - _revolutionProgress : REVOLUTION_INTERVAL + INDEX_PULSE_DURATION - _revolutionProgress);
            }
            else {
                set_indexPulse(false);
                _indexPulseBeginTask.cancelled = true;
                _indexPulseEndTask.cancelled = true;
                _revolutionProgress = (_clock.get_ms() - _lastRevolutionBegin) % REVOLUTION_INTERVAL;
            }
        }

        function get_indexPulse() { 
            return _indexPulse; 
        }

        function set_indexPulse(value) {
            if (value == _indexPulse)
                return;
            _indexPulse = value;
            if (_indexPulse) {
                _onIndexPulse.fire();
            }
        }

        function get_revolutionProgressPercent() {
            if (_rotation) {
                return ((_clock.get_ms() - _lastRevolutionBegin) % REVOLUTION_INTERVAL) / REVOLUTION_INTERVAL;
            }
            else {
                return _revolutionProgress / REVOLUTION_INTERVAL;
            }
        }
    }

    function get_state() {
        var state = {
            track: _track,
            sector: _sector,
            data: _data,
            command: _command,
            status: _commandInstance.get_status(),
            intrq: _intrq,
            drq: get_drq()
        };
        return state;
    }

    function masterReset() {
        _intrqLocked = 0;
        _sector = 1;
        set_ready(1);
        _command = 0x03;
        processCommand();
    }

    function calcDiskAngle() {
        return _revolutionState.get_revolutionProgressPercent();
    }

    function get_headReady() {
        return _headReady;
    }

    function set_headReady(value) {
        if (_headReady != value) {
            _headReady = value;
            if (value) {
                _onHeadReady.fire();
            }
        }
    }

    function get_ready() {
        return _ready;
    }

    function set_ready(value) {
        value = +value;
        if (_ready != value) {
            _ready = value;
            if (value) {
                _onReadyOn.fire();
            }
            else {
                _onReadyOff.fire();
            }
        }
    }

    function get_headLoad() {
        return _headLoad;
    }

    function set_headLoad(value) {
        if (_headLoad != value) {
            _headLoad = value;
            _revolutionState.set_rotation(value);
            _floppy.set_motor(value);
        }
        set_ready(value); // In Beta Disk Interface HLD pin is directly connected to RDY pin.
    }

    function get_intrq() {
        return _intrq;
    }

    function get_drq() {
        return _drq;
    }

    function get_dirc() {
        return _dirc;
    }

    function set_doubleDensity(value) {
        _doubleDensity = +!!value;
    }

    function get_floppy() {
        return _floppy;
    }

    function set_floppy(value) {
        _floppy = value;
    }

    function get_timeFactor() {
        return _timeFactor;
    }

    function set_timeFactor(value) {
        if (_timeFactor != value) {
            _timeFactor = value;
            REVOLUTION_INTERVAL = _baseIntervals.REVOLUTION_INTERVAL * _timeFactor;
            INDEX_PULSE_DURATION = _baseIntervals.INDEX_PULSE_DURATION * _timeFactor;
            for (var i = 0; i < _baseIntervals.STEP_DELAYS.length; i++) {
                STEP_DELAYS[i] = _baseIntervals.STEP_DELAYS[i] * _timeFactor;
            }
            HEAD_ENGAGE_DURATION = _baseIntervals.HEAD_ENGAGE_DURATION * _timeFactor;
        }
    }

    function get_busy() {
        return _busy;
    }

    function set_busy(value) {
        if (_busy != value) {
            _busy = value;
            if (value) {
                _revolutionState.onIndexPulse.remove(notBusyIndexPulseHandler);
            }
            else {
                _notBusyIndexPulseCounter = 0;
                _revolutionState.onIndexPulse.add(notBusyIndexPulseHandler);
            }
        }
    }

    function notBusyIndexPulseHandler() {
        if (++_notBusyIndexPulseCounter >= 15) {
            set_headLoad(0);
        }
        else {
            _revolutionState.onIndexPulse.add(notBusyIndexPulseHandler);
        }
    }

    // Таймаут чтения или записи группы байт (ms).
    function calculateReadWriteTimeout(byteCount)  {
        return (byteCount * REVOLUTION_INTERVAL / (_doubleDensity ? BYTES_PER_TRACK_MFM : BYTES_PER_TRACK_FM)); 
    }

    function read(address) {
        switch (address) {
            case 0x00: 
                var status = _commandInstance.get_status();
                if (!_intrqLocked) {
                    _intrq = 0;
                }
                return status;
            case 0x01: return _track;
            case 0x02: return _sector;
            case 0x03: 
                var data = _data;
                var reading = get_busy()
                    && (
                        _commandInstance instanceof ReadSectorCommand
                        || _commandInstance instanceof ReadAddressCommand
                        || _commandInstance instanceof ReadTrackCommand
                    );
                if (reading) {
                    _drq = 0;
                }
                return data;
            }
    }

    function write(address, value) {
        switch (address) {
            case 0x00: _command = value; processCommand(); break;
            case 0x01: _track = value; break;
            case 0x02: _sector = value; break;
            // NOTE: unclear if we should check busy state.
            // case 0x01: if (!get_busy()) { _track = value; } break;
            // case 0x02: if (!get_busy()) { _sector = value; } break;
            case 0x03:
                _data = value;
                var writing = get_busy()
                    && (
                        _commandInstance instanceof WriteSectorCommand
                        || _commandInstance instanceof WriteTrackCommand
                    );
                if (writing) {
                    _drq = 0;
                }
                break;
        }
    }

    function processCommand() {
        var instance = null;
        if ((_command & 0xF0) == 0xD0) {
            instance = new InterruptCommand(_command, _commandInstance);
        }
        else if (!get_busy()) {
            if (!(_command & 0x80)) {
                if (_command & 0x60) {
                    instance = new StepCommand(_command);
                }
                else {
                    instance = new SeekRestoreCommand(_command);
                }
            }
            else if (!(_command & 0x40)) {
                switch (_command & 0xE0) {
                    case 0x80: instance = new ReadSectorCommand(_command); break;
                    case 0xA0: instance = new WriteSectorCommand(_command); break;
                }
            }
            else {
                switch (_command & 0xF0) {
                    case 0xC0: instance = new ReadAddressCommand(_command); break;
                    case 0xE0: instance = new ReadTrackCommand(_command); break;
                    case 0xF0: instance = new WriteTrackCommand(_command); break;
                }
            }
        }
        if (instance) {
            // should it be like that?
            if (_commandInstance instanceof InterruptCommand) {
                _commandInstance.terminate();
            }
            _commandInstance = instance;
            _commandInstance.execute();
        }
    }

    function InterruptCommand(code, lastCommand) {
        this.execute = execute;
        this.terminate = terminate;
        this.get_status = get_status;

        var _fOnReadyOn = !!(code & 0x01);
        var _fOnReadyOff = !!(code & 0x02);
        var _fOnIndexPulse = !!(code & 0x04);
        var _fImmediate = !!(code & 0x08);
        var _fNoInterrupt = !(code & 0x0F);
        var _lastCommand = lastCommand;
        var _commandTerminated = false;

        function get_status() {
            if (_commandTerminated) {
                return _lastCommand.get_status();
            }
            else {
                return (!get_ready() << 7)
                    | (_floppy.get_isWriteProtected() << 6)
                    | (get_headLoad() << 5)
                    | (!_floppy.get_cylinder() << 2)
                    | (_revolutionState.get_indexPulse() << 1)
                    | get_busy();

            }
        }

        function execute() {
            if (get_busy()) {
                set_busy(0);
                _lastCommand.terminate();
                _commandTerminated = true;
            }
            if (_fOnReadyOn) {
                _onReadyOn.add(deferredInterrupt);
            }
            if (_fOnReadyOff) {
                _onReadyOff.add(deferredInterrupt);
            }
            if (_fOnIndexPulse) {
                _revolutionState.onIndexPulse.add(deferredInterrupt);
            }
            if (_fImmediate) {
                _intrq = 1;
            }
            // NOTE 1: It seems that we should not lock INTRQ once we get
            // 'Immediate' flag mixed with any other conditinal flag.
            // In this case 'CAT' command in TR-DOS fails on the
            // second time.
            // NOTE 2: It also seems that if we ever lock INTRQ we get
            // some undesired behavior sometimes. Particullary, FORMAT command
            // in TR-DOS does not work properly, if we have peformed, for example,
            // LIST command before it. So it's commented for a while.
            // if (_fImmediate && !_fOnReadyOn && !_fOnReadyOff && !_fOnIndexPulse) {
            //     _intrqLocked = 1;
            // }
            // if (_fNoInterrupt) {
            //     _intrqLocked = 0;
            // }
        }

        function deferredInterrupt() {
            _intrq = 1;
            // UNDONE: should interrupt occur on EVERY index pulse?
            // if (_fOnIndexPulse) {
            //     _onIndexPulse.add(deferredInterrupt);
            // }
        }

        function terminate() {
            _onReadyOn.remove(deferredInterrupt);
            _onReadyOff.remove(deferredInterrupt);
            _revolutionState.onIndexPulse.remove(deferredInterrupt);
        }
    }

    function WriteTrackCommand(code) {
        this.execute = execute;
        this.terminate = terminate;
        this.get_status = get_status;

        var _fDelay = !!(code & 0x04);
        var _stream = null;
        var _crc = new CRC16();
        var _crcBytesWritten = 0;
        var _dataLostError = 0;
        var _writeError = 0;
        var _headEngagementTask = null;
        var _drqServiceWaitingTask = null;
        var _processTask = null;

        function get_status() {
            return (!get_ready() << 7)
                | (_floppy.get_isWriteProtected() << 6)
                | (_writeError << 5)
                | (_dataLostError << 2)
                | (_drq << 1)
                | get_busy();
        }
        
        function execute() {
            set_busy(1);
            _drq = 0;
            if (!_intrqLocked) {
                _intrq = 0;
            }
            _dataLostError = 0;
            _writeError = 0;
            if (_floppy.get_isReady()) {
                set_headLoad(1);
                if (_fDelay) {
                    _headEngagementTask = _clock.setTimeout(onHeadEngaged, HEAD_ENGAGE_DURATION);
                }
                else {
                    onHeadEngaged();
                }
            }
            else {
                onCompleted();
            }
        }

        function onHeadEngaged() {
            if (_headReady) {
                checkForWriteProtection();
            }
            else {
                _onHeadReady.add(checkForWriteProtection);
            }
        }

        function checkForWriteProtection() {
            if (!_floppy.get_isWriteProtected()) {
                _drq = 1;
                _drqServiceWaitingTask = _clock.setTimeout(waitDrqIsServiced, calculateReadWriteTimeout(3));
            }
            else {
                onCompleted();
            }
        }

        function waitDrqIsServiced() {
            if (!_drq) {
                _revolutionState.onIndexPulse.add(writeTrack);
            }
            else {
                _dataLostError = 1;
                onCompleted();
            }
        }

        function writeTrack() {
            _revolutionState.onIndexPulse.add(onCompleted);
            _stream = _floppy.openStream();
            _processTask = _clock.setInterval(processNext, calculateReadWriteTimeout(1), 0, 0);
        }

        function processNext() {
            if (_drq) {
                // drq has not been serviced
                _dataLostError = 1;
                _stream.write(0x00);
                _crc.add(0x00);
            }
            else if (_crcBytesWritten) {
                switch (_crcBytesWritten) {
                    case 1:
                        _stream.write(_crc.value & 0xFF);
                        _crcBytesWritten++
                        break;
                    case 2:
                        // Real controller has a bug here.
                        // After crc has just been transferred to a
                        // disk, the next byte is being interpreted
                        // as an ordinary value to be stored, but 
                        // not a command.
                        _stream.write(_data);
                        _crcBytesWritten = 0;
                        _drq = 1;
                        break;
                }
            }
            else if (_doubleDensity) {
                switch (_data) {
                    case 0xF5: 
                        _stream.write(0x1A1);
                        // This is the real logiс.
                        // We preset CRC16(A1, A1, A1) every time we get F5.
                        _crc.value = 0xCDB4; 
                        break;
                    case 0xF6: 
                        _stream.write(0x1C2); 
                        _crc.add(0xC2);
                        break;
                    case 0xF7: 
                        _stream.write(_crc.value >> 8); 
                        _crcBytesWritten++;
                        break;
                    default: 
                        _stream.write(_data);
                        _crc.add(_data);
                        break;
                }
                _drq = 1;
            }
            else {
                switch (_data) {
                    case 0xF7: 
                        _stream.write(_crc.value >> 8); 
                        _crcBytesWritten++;
                        break;
                    case 0xF8:
                    case 0xF9:
                    case 0xFA:
                    case 0xFB:
                    case 0xFE: 
                        _crc.value = 0xFFFF;
                        _stream.write(_data | 0x100);
                        _crc.add(_data);
                        break;
                    case 0xFC:
                        _stream.write(_data | 0x100);
                        _crc.add(_data);
                        break;
                    default: 
                        _stream.write(_data);
                        _crc.add(_data);
                        break;
                }
                _drq = 1;
            }
        }

        function onCompleted() {
            _processTask && (_processTask.cancelled = true);
            _intrq = 1;
            set_busy(0);
        }

        function terminate() {
            _headEngagementTask && (_headEngagementTask.cancelled = true);
            _onHeadReady.remove(checkForWriteProtection);
            _drqServiceWaitingTask && (_drqServiceWaitingTask.cancelled = true);
            _revolutionState.onIndexPulse.remove(writeTrack);
            _revolutionState.onIndexPulse.remove(onCompleted);
            _processTask && (_processTask.cancelled = true);
        }
    }

    function ReadTrackCommand(code) {
        this.execute = execute;
        this.terminate = terminate;
        this.get_status = get_status;

        var _fDelay = !!(code & 0x04);
        var _stream = null;
        var _dataLostError = 0;
        var _headEngagementTask = null;
        var _readTask = null;

        function get_status() {
            return (!get_ready() << 7)
                | (_dataLostError << 2)
                | (_drq << 1)
                | get_busy();
        }

        function execute() {
            set_busy(1);
            _drq = 0;
            if (!_intrqLocked) {
                _intrq = 0;
            }
            _dataLostError = 0;

            if (_floppy.get_isReady()) {
                set_headLoad(1);
                if (_fDelay) {
                    _headEngagementTask = _clock.setTimeout(onHeadEngaged, HEAD_ENGAGE_DURATION);
                }
                else {
                    onHeadEngaged();
                }
            }
            else {
                onCompleted();
            }
        }

        function onHeadEngaged() {
            if (_headReady) {
                waitForTrackBegin();
            }
            else {
                _onHeadReady.add(waitForTrackBegin);
            }
        }

        function waitForTrackBegin() {
            _revolutionState.onIndexPulse.add(readTrack);
        }

        function readTrack() {
            _stream = _floppy.openStream();
            _revolutionState.onIndexPulse.add(onCompleted);
            _readTask = _clock.setInterval(processNext, calculateReadWriteTimeout(1), 0);
        }

        function processNext() {
            if (_drq) { 
                _dataLostError = 1;
            }

            var nextValue = _stream.read();
            if (nextValue < 0) {
                nextValue = _doubleDensity ? 0x4E : 0xFF;
            }
            _data = nextValue & 0xFF;
            _drq = 1;
        }

        function onCompleted() {
            _readTask && (_readTask.cancelled = true);
            _intrq = 1;
            set_busy(0);
        }

        function terminate() {
            _headEngagementTask && (_headEngagementTask.cancelled = true);
            _onHeadReady.remove(waitForTrackBegin);
            _revolutionState.onIndexPulse.remove(readTrack);
            _revolutionState.onIndexPulse.remove(onCompleted);
            _readTask && (_readTask.cancelled = true);
        }
    }

    function ReadAddressCommand(code) {
        this.execute = execute;
        this.terminate = terminate;
        this.get_status = get_status;

        var _fDelay = !!(code & 0x04);
        var _stream = null;
        var _amDetector = null;
        var _idDetected = 0;
        var _bytesCounter = 0;
        var _idTrack = null;
        var _idCrc = null;
        var _indexPulsesEncountered = 0;

        var _crc = null;
        var _notFoundError = 0;
        var _crcError = 0;
        var _dataLostError = 0;

        var _headEngagementTask = null;
        var _readTask = null;

        function get_status() {
            return (!get_ready() << 7) 
                | (_notFoundError << 4)
                | (_crcError << 3)
                | (_dataLostError << 2)
                | (_drq << 1)
                | get_busy();
        }

        function execute() {
            set_busy(1);
            _drq = 0;
            if (!_intrqLocked) {
                _intrq = 0;
            }
            _dataLostError = 0;
            _notFoundError = 0;

            if (_floppy.get_isReady()) {
                set_headLoad(1);
                if (_fDelay) {
                    _headEngagementTask = _clock.setTimeout(onHeadEngaged, HEAD_ENGAGE_DURATION);
                }
                else {
                    onHeadEngaged();
                }
            }
            else {
                onCompleted();
            }
        }

        function onHeadEngaged() {
            if (_headReady) {
                initReading();
            }
            else {
                _onHeadReady.add(initReading);
            }
        }

        function initReading() {
            var bytesPerTrack = _doubleDensity ? BYTES_PER_TRACK_MFM : BYTES_PER_TRACK_FM;
            var startIndex = (bytesPerTrack * calcDiskAngle()) | 0;
            _stream = _floppy.openStream();
            _stream.seek(Math.min(startIndex, _stream.get_length()));
            _indexPulsesEncountered = 0;
            _amDetector = new VG93AMDetector(_doubleDensity);
            _readTask = _clock.setInterval(processNext, calculateReadWriteTimeout(1), 0);
            _revolutionState.onIndexPulse.add(onIndexPulse);
        }
        
        function processNext() {
            var nextValue = _stream.read();
            if (nextValue < 0) {
                nextValue = _doubleDensity ? 0x4E : 0xFF;
            }
            var nextByte = nextValue & 0xFF;
            _amDetector.analyseNext(nextValue);

            if (!_idDetected) {
                var marker = _amDetector.get_marker();
                if (marker && marker >= 0xFC && marker <= 0xFF) {
                    _idDetected = 1;
                    _bytesCounter = 0;
                    _crc = new CRC16();
                    if (_doubleDensity) {
                        _crc.addArray([0xA1, 0xA1, 0xA1]);
                    }
                    _crc.add(nextByte);
                }
            }
            else {
                if (_drq) {
                    _dataLostError = 1;
                }
                if (_bytesCounter < 4) {
                    _crc.add(nextByte);
                }
                if (_bytesCounter < 6) {
                    switch (_bytesCounter) {
                        case 0: _idTrack = nextByte; break;
                        case 4: _idCrc = nextByte << 8; break;
                        case 5: _idCrc |= nextByte; break;
                    }
                    _data = nextByte;
                    _drq = 1;
                    _bytesCounter++
                }
                else {
                    _sector = _idTrack;
                    if (_idCrc != _crc.value) {
                        _crcError = 1;
                    }
                    _readTask.cancelled = true;
                    _revolutionState.onIndexPulse.remove(onIndexPulse);
                    _amDetector = null;
                    _stream = null;
                    onCompleted();
                }
            }
        }

        function onIndexPulse() {
            _stream.seek(0);
            if (++_indexPulsesEncountered > 1) {
                _readTask.cancelled = true;
                _notFoundError = 1;
                _amDetector = null;
                _stream = null;
                onCompleted();
            }
            else {
                _revolutionState.onIndexPulse.add(onIndexPulse);
            }
        }

        function onCompleted() {
            _intrq = 1;
            set_busy(0);
        }

        function terminate() {
            _headEngagementTask && (_headEngagementTask.cancelled = true);
            _onHeadReady.remove(initReading);
            _readTask && (_readTask.cancelled = true);
            _revolutionState.onIndexPulse.remove(onIndexPulse);
            _amDetector = null;
            _stream = null;
        }
    }

    function ReadSectorCommand(code) {
        this.execute = execute;
        this.terminate = terminate;
        this.get_status = get_status;

        var OP_STAGE = {
            DETECT_IDAM: 1,
            READ_ID: 2,
            DETECT_DAM: 3,
            READ_DATA: 4,
            READ_CRC: 5
        };

        var _fMultuple = !!(code & 0x10);
        var _fDelay = !!(code & 0x04);
        var _fHeadCompare = !!(code & 0x02);
        var _head = +!!(code & 0x08);
        var _stream = null;
        var _amDetector = null;
        var _opStage = null;
        var _idCrc = null;
        var _rwCounter = 0;
        var _crc = null;
        var _dataMarkerMaxDistance = null;
        var _dataBytesLength = 0;
        var _dataCrc = null;
        var _indexPulsesEncountered = 0;

        var _crcError = 0;
        var _notFoundError = 0;
        var _dataLostError = 0;
        var _recordType = 0;

        var _headEngagementTask = null;
        var _readTask = null;

        function get_status() {
            return (!get_ready() << 7)
                | (_recordType << 5)
                | (_notFoundError << 4)
                | (_crcError << 3)
                | (_dataLostError << 2)
                | (_drq << 1)
                | get_busy();
        }

        function execute() {
            set_busy(1);
            _drq = 0;
            _dataLostError = 0;
            _notFoundError = 0;
            _recordType = 0;
            _crcError = 0;
            if (!_intrqLocked) {
                _intrq = 0;
            }
            var ready = _floppy.get_isReady();
            if (ready) {
                set_headLoad(1);
                if (_fDelay) {
                    _headEngagementTask = _clock.setTimeout(onHeadEngaged, HEAD_ENGAGE_DURATION);
                }
                else {
                    onHeadEngaged();
                }
            }
            else {
                onCompleted();
            }
        }

        function onHeadEngaged() {
            _headEngagementTask = null;
            if (_headReady) {
                initReading();
            }
            else {
                _onHeadReady.add(initReading);
            }
        }

        function initReading() {
            var bytesPerTrack = _doubleDensity ? BYTES_PER_TRACK_MFM : BYTES_PER_TRACK_FM;
            var startIndex = (bytesPerTrack * calcDiskAngle()) | 0;
            _stream = _floppy.openStream();
            _stream.seek(Math.min(startIndex, _stream.get_length()));
            _amDetector = new VG93AMDetector(_doubleDensity);
            _opStage = OP_STAGE.DETECT_IDAM;
            _dataMarkerMaxDistance = _doubleDensity ? 43 : 30;
            _readTask = _clock.setInterval(processNext, calculateReadWriteTimeout(1), 0);
            _revolutionState.onIndexPulse.add(onIndexPulse);
        }

        function processNext() {
            var nextValue = _stream.read();
            if (nextValue < 0) {
                nextValue = _doubleDensity ? 0x4E : 0xFF;
            }
            var nextByte = nextValue & 0xFF;
            _amDetector.analyseNext(nextValue);
            
            switch (_opStage) {
                case OP_STAGE.DETECT_IDAM: 
                    var marker = _amDetector.get_marker();
                    if (marker && marker >= 0xFC && marker <= 0xFF) {
                        _opStage = OP_STAGE.READ_ID;
                        _rwCounter = 0;
                        _crc = new CRC16();
                        _doubleDensity && _crc.addArray([0xA1, 0xA1, 0xA1]);
                        _crc.add(nextByte);
                    }
                    break;
                case OP_STAGE.READ_ID:
                    if (_rwCounter < 4) {
                        _crc.add(nextByte);
                    }
                    switch (_rwCounter) {
                        case 0: if (nextByte != _track) _opStage = OP_STAGE.DETECT_IDAM; break;
                        case 1: if (_fHeadCompare && nextByte != _head) _opStage = OP_STAGE.DETECT_IDAM; break;
                        case 2: if (nextByte != _sector) _opStage = OP_STAGE.DETECT_IDAM; break;
                        case 3: _dataBytesLength = (0x0080 << nextByte); break;
                        case 4: _idCrc = nextByte << 8; break;
                        case 5: _idCrc |= nextByte; break;
                    }
                    if (++_rwCounter == 6) {
                        _rwCounter = 0;
                        _crcError = (_idCrc != _crc.value);
                        _opStage = _crcError ? OP_STAGE.DETECT_IDAM : OP_STAGE.DETECT_DAM;
                    }
                    break;
                case OP_STAGE.DETECT_DAM:
                    var marker = _amDetector.get_marker();
                    if (marker && marker >= 0xF8 && marker <= 0xFB) {
                        _recordType = +(marker == 0xF8 || marker == 0xF9);
                        _crc = new CRC16();
                        _doubleDensity && _crc.addArray([0xA1, 0xA1, 0xA1]);
                        _crc.add(nextByte);
                        _rwCounter = 0;
                        _opStage = OP_STAGE.READ_DATA;
                    }
                    else if (++_rwCounter == _dataMarkerMaxDistance) {
                        _opStage = OP_STAGE.DETECT_IDAM;
                    }
                    break;
                case OP_STAGE.READ_DATA:
                    if (_drq) {
                        _dataLostError = 1;
                    }
                    _crc.add(nextByte);
                    _data = nextByte;
                    _drq = 1;
                    if (++_rwCounter == _dataBytesLength) {
                        _rwCounter = 0;
                        _opStage = OP_STAGE.READ_CRC
                    }
                    break;
                case OP_STAGE.READ_CRC:
                    if (_drq) {
                        _dataLostError = 1;
                    }
                    switch (_rwCounter) {
                        case 0: _dataCrc = nextByte << 8; break;
                        case 1: _dataCrc |= nextByte; break;
                    }
                    if (++_rwCounter == 2) {
                        if (_dataCrc != _crc.value) {
                            _crcError = 1;
                        }
                        if (_fMultuple && !_crcError) {
                            _sector++;
                            _indexPulsesEncountered = 0;
                            _rwCounter = 0;
                            _opStage = OP_STAGE.DETECT_IDAM;
                        }
                        else {
                            _readTask.cancelled = true;
                            _revolutionState.onIndexPulse.remove(onIndexPulse);
                            _amDetector = null;
                            _stream = null;
                            onCompleted();
                        }
                    }
                    break;
            }
        }

        function onIndexPulse() {
            _stream.seek(0);
            if (++_indexPulsesEncountered > 1) {
                _readTask.cancelled = true;
                _notFoundError = 1;
                _amDetector = null;
                _stream = null;
                onCompleted();
            }
            else {
                _revolutionState.onIndexPulse.add(onIndexPulse);
            }
        }

        function onCompleted() {
            _intrq = 1;
            set_busy(0);
        }

        function terminate() {
            _headEngagementTask && (_headEngagementTask.cancelled = true);
            _onHeadReady.remove(initReading);
            _readTask && (_readTask.cancelled = true);
            _revolutionState.onIndexPulse.remove(onIndexPulse);
            _amDetector = null;
            _stream = null;
        }
    }

    function WriteSectorCommand(code) {
        this.execute = execute;
        this.terminate = terminate;
        this.get_status = get_status;

        var OP_STAGE = {
            DETECT_IDAM: 1,
            READ_ID: 2,
            DELAY: 3,
            WRITE_SYNC_AND_DAM: 4,
            WRITE_DATA: 5,
            WRITE_CRC: 6
        };

        var _fMultuple = !!(code & 0x10);
        var _fDelay = !!(code & 0x04);
        var _fHeadCompare = !!(code & 0x02);
        var _recordType = !!(code & 0x01);
        var _head = +!!(code & 0x08);
        var _stream = null;
        var _amDetector = null;
        var _opStage = null;
        var _idCrc = null;
        var _rwCounter = 0;
        var _crc = null;
        var _dataBytesLength = 0;
        var _indexPulsesEncountered = 0;
        var _fmSync = [0x00, 0x00, 0x00, 0x00, 0x00, 0x00];
        var _mfmSync = [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x1A1, 0x1A1, 0x1A1];

        var _crcError = 0;
        var _notFoundError = 0;
        var _dataLostError = 0;
        var _writeError = 0;

        var _headEngagementTask = null;
        var _writeTask = null;

        function get_status() {
            return (!get_ready() << 7)
                | (_floppy.get_isWriteProtected() << 6)
                | (_writeError << 5)
                | (_notFoundError << 4)
                | (_crcError << 3)
                | (_dataLostError << 2)
                | (_drq << 1)
                | get_busy();
        }

        function execute() {
            set_busy(1);
            _drq = 0;
            _dataLostError = 0;
            _notFoundError = 0;
            _recordType = 0;
            _writeError = 0;
            _crcError = 0;
            if (!_intrqLocked) {
                _intrq = 0;
            }
            var ready = _floppy.get_isReady();
            if (ready) {
                set_headLoad(1);
                if (_fDelay) {
                    _headEngagementTask = _clock.setTimeout(onHeadEngaged, HEAD_ENGAGE_DURATION);
                }
                else {
                    onHeadEngaged();
                }
            }
            else {
                onCompleted();
            }
        }

        function onHeadEngaged() {
            if (_headReady) {
                checkForWriteProtection();
            }
            else {
                _onHeadReady.add(checkForWriteProtection);
            }
        }

        function checkForWriteProtection() {
            if (!_floppy.get_isWriteProtected()) {
                initWriting();
            }
            else {
                onCompleted();
            }
        }

        function initWriting() {
            var bytesPerTrack = _doubleDensity ? BYTES_PER_TRACK_MFM : BYTES_PER_TRACK_FM;
            var startIndex = (bytesPerTrack * calcDiskAngle()) | 0;
            _stream = _floppy.openStream();
            _stream.seek(Math.min(startIndex, _stream.get_length()));
            _amDetector = new VG93AMDetector(_doubleDensity);
            _opStage = OP_STAGE.DETECT_IDAM;
            _writeTask = _clock.setInterval(processNext, calculateReadWriteTimeout(1), 0);
            _revolutionState.onIndexPulse.add(onIndexPulse);
        }
        
        function processNext() {
            if (_opStage != OP_STAGE.WRITE_SYNC_AND_DAM && _opStage != OP_STAGE.WRITE_DATA && _opStage != OP_STAGE.WRITE_CRC) {
                var nextValue = _stream.read();
                if (nextValue < 0) {
                    nextValue = _doubleDensity ? 0x4E : 0xFF;
                }
                var nextByte = nextValue & 0xFF;
                _amDetector.analyseNext(nextValue);
    
                switch (_opStage) {
                    case OP_STAGE.DETECT_IDAM: 
                        var marker = _amDetector.get_marker();
                        if (marker && marker >= 0xFC && marker <= 0xFF) {
                            _opStage = OP_STAGE.READ_ID;
                            _rwCounter = 0;
                            _crc = new CRC16();
                            _doubleDensity && _crc.addArray([0xA1, 0xA1, 0xA1]);
                            _crc.add(nextByte);
                        }
                        break;
                    case OP_STAGE.READ_ID:
                        if (_rwCounter < 4) {
                            _crc.add(nextByte);
                        }
                        switch (_rwCounter) {
                            case 0: if (nextByte != _track) _opStage = OP_STAGE.DETECT_IDAM; break;
                            case 1: if (_fHeadCompare && nextByte != _head) _opStage = OP_STAGE.DETECT_IDAM; break;
                            case 2: if (nextByte != _sector) _opStage = OP_STAGE.DETECT_IDAM; break;
                            case 3: _dataBytesLength = (0x0080 << nextByte); break;
                            case 4: _idCrc = nextByte << 8; break;
                            case 5: _idCrc |= nextByte; break;
                        }
                        if (++_rwCounter == 6) {
                            _rwCounter = 0;
                            _crcError = (_idCrc != _crc.value);
                            _opStage = _crcError ? OP_STAGE.DETECT_IDAM : OP_STAGE.DELAY;
                        }
                        break;
                    case OP_STAGE.DELAY:
                        switch (++_rwCounter) {
                            case 2: _drq = 1; break;
                            case 10: 
                                if (_drq) {
                                    _dataLostError = 1;
                                    _writeTask.cancelled = true;
                                    _revolutionState.onIndexPulse.remove(onIndexPulse);
                                    _amDetector = null;
                                    _stream = null;
                                    onCompleted();
                                }
                                break;
                            case 11: 
                                if (!_doubleDensity) {
                                    _rwCounter = 0;
                                    _opStage = OP_STAGE.WRITE_SYNC_AND_DAM;
                                }
                                break;
                            case 22: 
                                _rwCounter = 0;
                                _opStage = OP_STAGE.WRITE_SYNC_AND_DAM;
                                break;
                        }
                        break;
                }
            }
            else {
                switch (_opStage) {
                    case OP_STAGE.WRITE_SYNC_AND_DAM:
                        var sync = _doubleDensity ? _mfmSync : _fmSync;
                        if (_rwCounter < sync.length) {
                            _stream.write(sync[_rwCounter++]);
                        }
                        else {
                            var nextByte = _recordType ? 0xF8 : 0xFB;
                            _stream.write(nextByte);
                            _crc = new CRC16();
                            _doubleDensity && _crc.addArray([0xA1, 0xA1, 0xA1]);
                            _crc.add(nextByte);
                            _rwCounter = 0;
                            _opStage = OP_STAGE.WRITE_DATA;
                        }
                        break;
                    case OP_STAGE.WRITE_DATA:
                        var nextByte;
                        if (_drq) {
                            nextByte = 0;
                            _dataLostError = 1;
                        }
                        else {
                            nextByte = _data;
                        }
                        _stream.write(nextByte);
                        _crc.add(nextByte);
                        if (++_rwCounter < _dataBytesLength) {
                            _drq = 1;
                        }
                        else {
                            _opStage = OP_STAGE.WRITE_CRC;
                            _rwCounter = 0;
                        }
                        break;
                    case OP_STAGE.WRITE_CRC:
                        switch (_rwCounter) {
                            case 0: _stream.write(_crc.value >> 8); break;
                            case 1: _stream.write(_crc.value & 0xFF); break;
                            case 2: _stream.write(0xFF); break
                        }
                        if (++_rwCounter == 3) {
                            if (_fMultuple) {
                                _sector++;
                                _indexPulsesEncountered = 0;
                                _rwCounter = 0;
                                _opStage = OP_STAGE.DETECT_IDAM;
                            }
                            else {
                                _writeTask.cancelled = true;
                                _revolutionState.onIndexPulse.remove(onIndexPulse);
                                _amDetector = null;
                                _stream = null;
                                onCompleted();
                            }
                        }
                        break;
                }
            }
        }

        function onIndexPulse() {
            _stream.seek(0);
            if (++_indexPulsesEncountered > 1) {
                _writeTask.cancelled = true;
                _notFoundError = 1;
                _amDetector = null;
                _stream = null;
                onCompleted();
            }
            else {
                _revolutionState.onIndexPulse.add(onIndexPulse);
            }
        }

        function onCompleted() {
            _intrq = 1;
            set_busy(0);
        }

        function terminate() {
            _headEngagementTask && (_headEngagementTask.cancelled = true);
            _onHeadReady.remove(checkForWriteProtection);
            _writeTask && (_writeTask.cancelled = true);
            _revolutionState.onIndexPulse.remove(onIndexPulse);
            _amDetector = null;
            _stream = null;
    }
    }

    function StepCommand(code) {
        this.execute = execute;
        this.terminate = terminate;
        this.get_status = get_status;
        
        var _cmdStepIn = (code & 0x60) == 0x40;
        var _cmdStepOut = (code & 0x60) == 0x60;
        var _fUpdate = !!(code & 0x10);
        var _fHeadLoad = !!(code & 0x08);
        var _fVerify = !!(code & 0x04);
        var _rate = code & 0x03;
        var _crcError = 0;
        var _seekError = 0;

        var _stream = null;
        var _amDetector = null;
        var _idDetected = 0;
        var _idCrc = null;
        var _rwCounter = 0;
        var _crc = null;
        var _indexPulsesEncountered = 0;
        var _stepTask = null;
        var _headEngagementTask = null;
        var _verifyTask = null;

        function get_status() {
            return (!get_ready() << 7)
                | (_floppy.get_isWriteProtected() << 6)
                | (get_headLoad() << 5)
                | (_seekError << 4)
                | (_crcError << 3)
                | (!_floppy.get_cylinder() << 2)
                | (_revolutionState.get_indexPulse() << 1)
                | get_busy();
        }

        function execute() { 
            set_busy(1);
            _drq = 0;
            if (!_intrqLocked) {
                _intrq = 0;
            }
            _crcError = 0;
            _seekError = 0;
            set_headLoad(+_fHeadLoad);
            if (_cmdStepIn || _cmdStepOut) {
                _dirc = +_cmdStepIn;
            }
            if (_fUpdate) {
                _track += (_dirc ? 1 : -1);
            }
            if (_floppy.get_cylinder() > 0 || _dirc) {
                if (_dirc) {
                    _floppy.stepIn();
                }
                else {
                    _floppy.stepOut();
                }
                _stepTask = _clock.setTimeout(onStepCompleted, STEP_DELAYS[_rate]);
            }
            else {
                _track = 0;
                onStepCompleted();
            }
        }

        function onStepCompleted() {
            if (_fVerify) {
                set_headLoad(1);
                _headEngagementTask = _clock.setTimeout(onHeadEngaged, HEAD_ENGAGE_DURATION);
            }
            else {
                onCompleted();
            }
        }

        function onHeadEngaged() {
            if (_headReady) {
                verify();
            }
            else {
                _onHeadReady.add(verify);
            }
        }

        function verify() {
            var bytesPerTrack = _doubleDensity ? BYTES_PER_TRACK_MFM : BYTES_PER_TRACK_FM;
            var startIndex = (bytesPerTrack * calcDiskAngle()) | 0;
            _stream = _floppy.openStream();
            _stream.seek(Math.min(startIndex, _stream.get_length()));
            _amDetector = new VG93AMDetector(_doubleDensity);
            _indexPulsesEncountered = 0;
            _verifyTask = _clock.setInterval(processNext, calculateReadWriteTimeout(1), 0);
            _revolutionState.onIndexPulse.add(onIndexPulse);
        }

        function processNext() {
            var nextValue = _stream.read();
            if (nextValue < 0) {
                nextValue = _doubleDensity ? 0x4E : 0xFF;
            }
            var nextByte = nextValue & 0xFF;
            _amDetector.analyseNext(nextValue);

            if (!_idDetected) {
                var marker = _amDetector.get_marker();
                if (marker && marker >= 0xFC && marker <= 0xFF) {
                    _idDetected = 1;
                    _rwCounter = 0;
                    _crc = new CRC16();
                    _doubleDensity && _crc.addArray([0xA1, 0xA1, 0xA1]);
                    _crc.add(nextByte);
                }
            }
            else {
                if (_rwCounter < 4) {
                    _crc.add(nextByte);
                }
                switch (_rwCounter) {
                    case 0: if (nextByte != _track) _idDetected = 0; break;
                    case 4: _idCrc = nextByte << 8; break;
                    case 5: _idCrc |= nextByte; break;
                }
                if (++_rwCounter == 6) {
                    _crcError = (_idCrc != _crc.value);
                    if (_crcError) {
                        _idDetected = 0;
                    }
                    else {
                        _verifyTask.cancelled = true;
                        _revolutionState.onIndexPulse.remove(onIndexPulse);
                        _amDetector = null;
                        _stream = null;
                        onCompleted();
                    }
                }
            }
        }

        function onIndexPulse() {
            _stream.seek(0);
            if (++_indexPulsesEncountered > 1) {
                _verifyTask.cancelled = true;
                _seekError = 1;
                _amDetector = null;
                _stream = null;
                onCompleted();
            }
            else {
                _revolutionState.onIndexPulse.add(onIndexPulse);
            }
        }

        function onCompleted() {
            set_busy(0);
            _intrq = 1;
        }

        function terminate() { 
            _stepTask && (_stepTask.cancelled = true);
            _headEngagementTask && (_headEngagementTask.cancelled = true);
            _onHeadReady.remove(verify);
            _verifyTask && (_verifyTask.cancelled = true);
            _revolutionState.onIndexPulse.remove(onIndexPulse);
        }
    }

    function SeekRestoreCommand(code) {
        this.execute = execute;
        this.terminate = terminate;
        this.get_status = get_status;

        var _cmdSeek = !!(code & 0x10);
        var _fHeadLoad = !!(code & 0x08);
        var _fVerify = !!(code & 0x04);
        var _rate = code & 0x03;
        var _crcError = 0;
        var _seekError = 0;

        var _stream = null;
        var _amDetector = null;
        var _idDetected = 0;
        var _idCrc = null;
        var _rwCounter = 0;
        var _crc = null;
        var _indexPulsesEncountered = 0;
        var _stepTask = null;
        var _headEngagementTask = null;
        var _verifyTask = null;

        function get_status() {
            return (!get_ready() << 7) 
                | (_floppy.get_isWriteProtected() << 6)
                | (get_headLoad() << 5)
                | (_seekError << 4)
                | (_crcError << 3)
                | (!_floppy.get_cylinder() << 2)
                | (_revolutionState.get_indexPulse() << 1)
                | get_busy();
        }

        function execute() {
            set_busy(1);
            _drq = 0;
            if (!_intrqLocked) {
                _intrq = 0;
            }
            _crcError = 0;
            _seekError = 0;
            set_headLoad(+_fHeadLoad);
            if (!_cmdSeek) {
                _track = 0xFF;
                _data = 0x00;
            }
            doStep();
        }

        function doStep() {
            _stepTask = null;
            if (_track == _data) {
                onStepCompleted();
                return;
            }
            _dirc = (_data > _track) ? 1 : 0;
            _track += (_dirc ? 1 : -1);
            if (_floppy.get_cylinder() == 0 && !_dirc) {
                _track = 0;
                onStepCompleted();
                return;
            }
            if (_dirc) {
                _floppy.stepIn();
            }
            else {
                _floppy.stepOut();
            }
            _stepTask = _clock.setTimeout(doStep, STEP_DELAYS[_rate]);
        }

        function onStepCompleted() {
            if (_fVerify) {
                set_headLoad(true);
                _headEngagementTask = _clock.setTimeout(onHeadEngaged, HEAD_ENGAGE_DURATION);
            }
            else {
                onCompleted();
            }
        }

        function onHeadEngaged() {
            _headEngagementTask = null;
            if (_headReady) {
                verify();
            }
            else {
                _onHeadReady.add(verify);
            }
        }

        function verify() {
            var bytesPerTrack = _doubleDensity ? BYTES_PER_TRACK_MFM : BYTES_PER_TRACK_FM;
            var startIndex = (bytesPerTrack * calcDiskAngle()) | 0;
            _stream = _floppy.openStream();
            _stream.seek(Math.min(startIndex, _stream.get_length()));
            _amDetector = new VG93AMDetector(_doubleDensity);
            _indexPulsesEncountered = 0;
            _verifyTask = _clock.setInterval(processNext, calculateReadWriteTimeout(1), 0);
            _revolutionState.onIndexPulse.add(onIndexPulse);
        }

        function processNext() {
            var nextValue = _stream.read();
            if (nextValue < 0) {
                nextValue = _doubleDensity ? 0x4E : 0xFF;
            }
            var nextByte = nextValue & 0xFF;
            _amDetector.analyseNext(nextValue);

            if (!_idDetected) {
                var marker = _amDetector.get_marker();
                if (marker && marker >= 0xFC && marker <= 0xFF) {
                    _idDetected = 1;
                    _rwCounter = 0;
                    _crc = new CRC16();
                    _doubleDensity && _crc.addArray([0xA1, 0xA1, 0xA1]);
                    _crc.add(nextByte);
                }
            }
            else {
                if (_rwCounter < 4) {
                    _crc.add(nextByte);
                }
                switch (_rwCounter) {
                    case 0: if (nextByte != _track) _idDetected = 0; break;
                    case 4: _idCrc = nextByte << 8; break;
                    case 5: _idCrc |= nextByte; break;
                }
                if (++_rwCounter == 6) {
                    _crcError = (_idCrc != _crc.value);
                    if (_crcError) {
                        _idDetected = 0;
                    }
                    else {
                        _verifyTask.cancelled = true;
                        _revolutionState.onIndexPulse.remove(onIndexPulse);
                        _amDetector = null;
                        _stream = null;
                        onCompleted();
                    }
                }
            }
        }

        function onIndexPulse() {
            _stream.seek(0);
            if (++_indexPulsesEncountered > 1) {
                _verifyTask.cancelled = true;
                _seekError = 1;
                _amDetector = null;
                _stream = null;
                onCompleted();
            }
            else {
                _revolutionState.onIndexPulse.add(onIndexPulse);
            }
        }

        function onCompleted() {
            set_busy(0);
            _intrq = 1;
        }

        function terminate() { 
            _stepTask && (_stepTask.cancelled = true);
            _headEngagementTask && (_headEngagementTask.cancelled = true);
            _onHeadReady.remove(verify);
            _verifyTask && (_verifyTask.cancelled = true);
            _revolutionState.onIndexPulse.remove(onIndexPulse);
        }
    }
}

function VG93AMDetector(doubleDensity) {
    var _doubleDensity = doubleDensity;
    var _state = 0;
    var _marker = null;

    this.reset = function () {
        _state = 0;
        _marker = null;
    }

    this.analyseNext = function (nextValue) {
        if (_doubleDensity) {
            switch (_state) {
                case 0:
                case 2:
                    switch (nextValue) {
                        case 0x1A1:
                        case 0x1C2:
                            _state = 1;
                            _marker = null;
                            break;

                        default:
                            _state = 0;
                            _marker = null;
                    }
                    break;

                case 1:
                    switch (nextValue) {
                        case 0xF8:
                        case 0xF9:
                        case 0xFA:
                        case 0xFB:
                        case 0xFC:
                        case 0xFD:
                        case 0xFE:
                        case 0xFF:
                            _state = 2;
                            _marker = nextValue;
                            break;
                        default:
                            _state = 0;
                            _marker = null;
                            break;
                    }
                    break;
            }
        }
        else {
            switch (nextValue) {
                case 0x1F8:
                case 0x1F9:
                case 0x1FA:
                case 0x1FB:
                case 0x1FC:
                case 0x1FE:
                    _marker = nextValue & 0xFF;
                    break;
                default:
                    _marker = null;
                    break;
            }
        }
    }

    this.get_marker = function () {
        return _marker;
    }
}

// Upstream module: hardware/clock.js
function ZX_Clock() {
    // All hardware deadlines remain on the shared emulated T-state timeline.
    // The browser's monotonic clock paces that timeline; wall-clock edits cannot jump it.
    var hostNow = typeof performance !== 'undefined' && performance.now
        ? function () { return performance.now(); } : function () { return Date.now(); };
	/*
	 * Вроде как, в Pentagon прерывание происходит каждые 71680 тактов.
	 * При частоте 3.5МГц это означает, что:
	 *   частота прерываний равна 48.828125 Гц,
	 *   период прерываний равен 20.48 мс
	 */

	// период запросов маскируемого прерывания в миллисекундах
	var _intrqPeriod = 20.48;
	// продолжлительность сигнала прерывания в тактах процессора
	var _intrqDurationTstates = 36; // Original Spectrum 128 ULA interrupt pulse.
	// количество выполняемых процессором тактов между маскируемыми прерываниями
	var _tstatesPerIntrq = 71680;
	// количество выполняемых процессором тактов за одну миллисекунду
	var _tstatesPerMs = 1;
	// коэффициент ускорение при загрузке с магнитной ленты
	var _tapeBoostFactor = 1;
	// флаг работы рабочего цикла
	var _running = false;
	// идентификатор интервала рабочего цикла
	var _intervalId;
	// точка отсчета работы тактового генератора в тактах
	var _baseTstates;
	// точка отсчета работы тактового генератора
	var _baseTimestamp;
	// время последнего вывода информации о производительности
	var _performanceTimestamp;
	// счетчик тактов с последнего вывода информации о производительности
	var _performanceTstates;
	// счетчик фреймов (прерываний) с последнего вывода инфорамции о производительности
	var _performanceFps;
	// счетчик тактов с начала работы
	var _tstates = 0;
	// максимальное ускорение (после временного спада производительности)
	var _maxBoostMs = 50.0;
	var _maxBoostTstates = _maxBoostMs * _tstatesPerMs;

	var _hwState = HWState.get_instance();
	var _bus;
	var _cpu;
	var _taskQueue = new TaskQueue(_tstatesPerMs);
	var _interruptActiveTask = null;
	var _interruptInactiveTask = null;
	var _rescheduleTaskOnNextInterrupt = false;

	var _debug = false;
	var _checkBreakConditionCallback = function (state) { return false; }
	var _stopCallback = function () { }

	function run() {
		if ( _running || !_bus || !_cpu )
			return;
		_debug = false;
		_running = true;
		var now = hostNow();
		_intervalId = setInterval(process, 4);
		_baseTstates = _tstates;
		_baseTimestamp = now;
		_performanceTimestamp = now;
		_performanceTstates = 0;
		_performanceFps = 0;
	}

	function runDebug(checkBreakConditionCallback, stopCallback) {
		if ( _running || !_bus || !_cpu)
			return;
		_debug = true;
		_running = true;
		var now = hostNow();
		_intervalId = setInterval(processDebug, 4);
		_baseTstates = _tstates;
		_baseTimestamp = now;
		_performanceTimestamp = now;
		_performanceTstates = 0;
		_performanceFps = 0;
		_checkBreakConditionCallback = checkBreakConditionCallback;
		_stopCallback = stopCallback;
	}

	function stop() {
		if ( !_running )
			return;
		_running = false;
		clearInterval(_intervalId);
		if (_debug) {
			_stopCallback();
		}
	}

    // Advance every module from one CPU T-state counter and ordered event queue.
    // Host callback cadence only controls the amount of pending work, not event phases.
    // Pause/resume explicitly starts a new host-time origin without advancing the machine.
	function process() {
		// фиксация время запуска итерации
		var now = hostNow();
		// проверка на необходимость вывода информации о производительности.
		var performanceElapsed = now - _performanceTimestamp
		if ( performanceElapsed >= 1000 ) {
			_hwState.updatePerformance({
				frequency: _performanceTstates / (performanceElapsed * 1000),
				fps: _performanceFps * 1000 / performanceElapsed
			});
			_performanceTimestamp = now;
			_performanceTstates = 0;
			_performanceFps = 0;
		}
		// время с точки отсчета
		var elapsed = now - _baseTimestamp;
		// соответствие этого времени тактам
		var elapsedTstates = _tstatesPerMs * elapsed;
		// количество тактов для выполнения в текущей итерации
		var plannedTstates = elapsedTstates - (_tstates - _baseTstates);
		if (plannedTstates > _maxBoostTstates) {
            // Bound work per callback, retaining the original real-time origin and debt.
            // Later callbacks catch up the whole machine without skipping hardware events.
            plannedTstates = _maxBoostTstates;
        }
		// сброс счетчика тактов процессора
		_cpu.set_tstates(0);
		var lastTstates = 0;
		var curTstates;
		// работа процессора
		while ((curTstates = _cpu.get_tstates()) < plannedTstates) {
			_tstates += (curTstates - lastTstates);
			lastTstates = curTstates;
			_taskQueue.process(_tstates);
			_cpu.process();
		}
		// корректировка счетчиков
		_tstates += (curTstates - lastTstates);
		lastTstates = curTstates;
		_performanceTstates += curTstates;
	}
	
	function processDebug() {
		// фиксация время запуска итерации
		var now = hostNow();
		// проверка на необходимость вывода информации о производительности.
		var performanceElapsed = now - _performanceTimestamp
		if ( performanceElapsed >= 1000 ) {
			_hwState.updatePerformance({
				frequency: _performanceTstates / (performanceElapsed * 1000),
				fps: _performanceFps * 1000 / performanceElapsed
			});
			_performanceTimestamp = now;
			_performanceTstates = 0;
			_performanceFps = 0;
		}
		// время с точки отсчета
		var elapsed = now - _baseTimestamp;
		// соответствие этого времени тактам
		var elapsedTstates = _tstatesPerMs * elapsed;
		// количество тактов для выполнения в текущей итерации
		var plannedTstates = elapsedTstates - (_tstates - _baseTstates);
		if (plannedTstates > _maxBoostTstates) {
            // Bound work per callback, retaining the original real-time origin and debt.
            // Later callbacks catch up the whole machine without skipping hardware events.
            plannedTstates = _maxBoostTstates;
        }
		// сброс счетчика тактов процессора
		_cpu.set_tstates(0);
		var lastTstates = 0;
		var curTstates;
		// работа процессора
		while ((curTstates = _cpu.get_tstates()) < plannedTstates) {
			_tstates += (curTstates - lastTstates);
			lastTstates = curTstates;
			_taskQueue.process(_tstates);
			var state = _cpu.get_state();
			if (_checkBreakConditionCallback(state)) {
				stop();
				return;
			}			
			_cpu.process();
		}
		// корректировка счетчиков
		var processedTstates = (curTstates = _cpu.get_tstates());
		_tstates += (curTstates - lastTstates);
		lastTstates = curTstates;
		_performanceTstates += processedTstates;
	}

	var rescheduleInterruptTask = function() {
		_interruptActiveTask && (_interruptActiveTask.cancelled = true);
		_interruptInactiveTask && (_interruptInactiveTask.cancelled = true);
		_interruptActiveTask = this.setInterval(onInterruptActive, _intrqPeriod, 0);
		_interruptInactiveTask = this.setInterval(onInterruptInactive, _intrqPeriod, 0, _intrqDurationTstates / _tstatesPerMs);
	}.bind(this);

	function onInterruptActive() {
		_bus.var_write('intrq', 1);
		_performanceFps++;
		if (_rescheduleTaskOnNextInterrupt) {
			rescheduleInterruptTask();
			_rescheduleTaskOnNextInterrupt = false;
		}
	}

	function onInterruptInactive() {
		_bus.var_write('intrq', 0);
	}

	function updateTstatesPerMs() {
		var tstatesPerMs = _tapeBoostFactor * _tstatesPerIntrq / _intrqPeriod;
		if (_tstatesPerMs != tstatesPerMs) {
			_tstatesPerMs = tstatesPerMs;
			_taskQueue.set_tstatesPerMs(_tstatesPerMs);
			_maxBoostTstates = _maxBoostMs * _tstatesPerMs;
			_baseTstates = _tstates;
			_baseTimestamp = hostNow();
			_rescheduleTaskOnNextInterrupt = true;
		}
	}

	/********************/
	/* public interface */
	/********************/
	this.run = run;
	this.runDebug = runDebug;
	this.stop = stop;
	this.get_running = function () { return _running; }
	this.get_tstates = function () { return _tstates; }
	this.get_ms = function () { return _tstates / _tstatesPerMs; }
	this.connect = function (bus, cpu) {
		_bus = bus;
		_cpu = cpu;

		_bus.on_opt(function (name, value) {
			_tstatesPerIntrq = value;
			updateTstatesPerMs();
		}, OPT_TSTATES_PER_INTRQ);
	
		_bus.on_opt(function (name, value) {
			_intrqPeriod = value; 
			updateTstatesPerMs();
		}, OPT_INTRQ_PERIOD);

		_bus.on_opt(function (name, value) {
			_tapeBoostFactor = value;
			updateTstatesPerMs();
		}, OPT_TAPE_BOOST_FACTOR);

		rescheduleInterruptTask();
	}
	this.setTimeout = function(func, ms) {
		return _taskQueue.enqueue(_tstates, ms, func);
	}
	this.setInterval = function (func, interval, count, firstInterval) {
		var firstInterval = (firstInterval !== undefined) ? firstInterval : interval;
		return _taskQueue.enqueue(_tstates, firstInterval, func, count, interval);
	}
}

function TaskQueue(tstatesPerMs) {
	// вместимость очереди ставим с запасом
	// (фактически одномоментно там порядка 5 заданий)
	var capacity = 100; 
	var queue = new Array(capacity);
	var begin = 0;
	var end = 0;
	var _tstatesPerMs = tstatesPerMs;

	this.set_tstatesPerMs = function (value) {
		_tstatesPerMs = value;
		var linearEnd = end < begin ? end + capacity : end;
		for (var linearIndex = begin; linearIndex < linearEnd; linearIndex++) {
			var task = queue[linearIndex % capacity];
			if (!task.valuesInTs && task.recalculateOnMsChanged) {
				task.recalculate = true;
			}
		}
	}
	this.get_tstatesPerMs = function () {
		return _tstatesPerMs;
	}

	this.enqueue = function (tsNow, timeout, func, count, repeatInterval, valuesInTs) {
		// init task
		var task = {
			tsStart: tsNow,
			tsEvent: tsNow + (valuesInTs ? timeout : (timeout * _tstatesPerMs)),
			timeout: timeout,
			next: 1,
			count: count !== undefined ? count : 1,
			repeatInterval: repeatInterval !== undefined ? repeatInterval : timeout,
			valuesInTs: valuesInTs !== undefined ? valuesInTs : false,
			invoke: func,
			recalculateOnMsChanged: !valuesInTs,
			cancelled: false,
			recalculate: false
		};
		// put in queue
		var linearEnd = end < begin ? end + capacity : end;
		var i = linearEnd;
		while ((i - 1) >= begin && queue[(i - 1) % capacity].tsEvent > task.tsEvent) {
			queue[i % capacity] = queue[(i - 1) % capacity];
			i--;
		}
		queue[i % capacity] = task;
		end = (end + 1) % capacity;
		return task;
	}

	this.reenqueue = function (task) {
		// update task
		if (task.recalculate) {
			task.tsStart = task.tsEvent;
			task.timeout = 0;
			if (task.count) {
				task.count -= (task.next - 1);
			}
			task.next = 1;
			task.recalculate = false;
		}
		task.tsEvent = task.tsStart + (
			task.valuesInTs 
			? (task.timeout + task.next * task.repeatInterval)
			: (task.timeout + task.next * task.repeatInterval) * _tstatesPerMs);
		task.next++;
		// put in queue
		var linearEnd = end < begin ? end + capacity : end;
		var i = linearEnd;
		while ((i - 1) >= begin && queue[(i - 1) % capacity].tsEvent > task.tsEvent) {
			queue[i % capacity] = queue[(i - 1) % capacity];
			i--;
		}
		queue[i % capacity] = task;
		end = (end + 1) % capacity;
		return task;
	}

	this.process = function (tsNow) {
		while (true) {
			var linearEnd = end < begin ? end + capacity : end;
			if (begin < linearEnd && queue[begin].tsEvent <= tsNow) {
				var task = queue[begin++];
				begin %= capacity;
				if (!task.cancelled) {
					task.invoke();
					if (!task.cancelled && (!task.count || task.next < task.count)) {
						this.reenqueue(task);
					}
				}
			}
			else 
				break;
		}
	}

}
// Upstream module: hardware/psg.js
function ZX_PSG() {
    var PSG_REG = {
        TONE_A_FINE: 0,
        TONE_A_COARSE: 1,
        TONE_B_FINE: 2,
        TONE_B_COARSE: 3,
        TONE_C_FINE: 4,
        TONE_C_COARSE: 5,
        NOISE: 6,
        MIXER: 7,
        VOLUME_A: 8,
        VOLUME_B: 9,
        VOLUME_C: 10,
        ENVELOPE_FINE: 11,
        ENVELOPE_COARSE: 12,
        ENVELOPE_SHAPE: 13
    };

    var _bus;
    var _clock;
    var _rom_trdos = false;
    var _set0 = {
        psg: new Ayumi(),
        regIndex: 0,
        regs: [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
    };
    var _set1 = {
        psg: new Ayumi(),
        regIndex: 0,
        regs: [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
    };
    var _activeSet = _set0;
    var _ayMasks = [0xFF, 0x0F, 0xFF, 0x0F, 0xFF, 0x0F, 0x1F, 0xFF, 0x1F, 0x1F, 0x1F, 0xFF, 0xFF, 0x0F, 0xFF, 0xFF];
    var _ymMasks = [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF];
    var _masks = _ayMasks;
    var _sampleRate = 44100;
    var _psgMode = VAL_PSG_OFF;
    var _turboSound = VAL_TS_OFF;
    var _turboSoundAutoDetected = false;
    var _channelLayout = VAL_CHANNELS_ABC;
    var _psgClock = 1773400;
    var _psgVolume = 1.0;
    var _processTask;
    var _processTaskInvalid = false;
    var _sampleBufferSize = 512;
    var _sampleBufferIndex = 0;
    var _sampleBufferLeft = new Float32Array(_sampleBufferSize);
    var _sampleBufferRight = new Float32Array(_sampleBufferSize);
    var _onDataReady = new ZX_Event();
    var _beeper = true;
    var _beeperBit = 0;
    var _beeperVolume = 0.5;
    var _lastConfig = {
        psgMode: null,
        psgClock: null,
        channelLayout: null,
    };

    function connect(bus, clock) {
        _bus = bus;
        _clock = clock;
        /*
         * запись порта FFFD - запись адреса
         * чтение порта FFFD - чтение данных
         * запись порта BFFD - запись данных
         * Дешифровка порта ведется только по линиям:
         *   A1 = 0
         *   A13, A15 = 1
         *   A14 = 0 или 1
         * 
         * В режиме NedoPC для второго чипа используются те же адреса, однако
         * при записи в порт FFFD значения FF выбирается первый чип, а при
         * записи FE - второй.
         * 
         * В режиме Power of Sound для второго чипа используются те же адреса,
         * однако при записи в порт 1F (не в режиме TR-DOS) значения 0 выбирается
         * первый чип, при записи 1 - второй.
         * 
         * В режиме QUADRO-AY для второго чипа используются следующие адреса:
         * запись порта EFFD - запись адреса
         * чтение порта EFFD - чтение данных
         * запись порта AFFD - запись данных
         * Дешифрация производится по тем же адресным линиям, но при выборе 
         * нужного чипа учитывается также линия A12.
         */
        _bus.on_io_write(io_write_reg, { mask: 0xE002, value: 0xE000 });
        _bus.on_io_write(io_write_data, { mask: 0xE002, value: 0xA000 });
        _bus.on_io_write(io_write_fe, { mask: 0x01, value: 0x00 });
        _bus.on_io_write(io_write_1f, { mask: 0xFF, value: 0x1F });
        _bus.on_io_read(io_read_data, { mask: 0xE002, value: 0xE000 });
        _bus.on_var_write(var_write_rom_trdos, 'rom_trdos');
        _bus.on_reset(reset);
        _bus.on_opt(function () { _processTaskInvalid = true; }, OPT_TSTATES_PER_INTRQ);
        _bus.on_opt(function () { _processTaskInvalid = true; }, OPT_INTRQ_PERIOD);
        configure();
        reset();
    }
    
    function configure() {
        if (_psgMode != VAL_PSG_OFF) {
            if (_psgMode !== _lastConfig.psgMode || _psgClock !== _lastConfig.psgClock) {
                _masks = _psgMode == VAL_PSG_YM_2149 ? _ymMasks : _ayMasks;
                _set0.psg.configure(_psgMode == VAL_PSG_YM_2149, _psgClock, _sampleRate);
                _set1.psg.configure(_psgMode == VAL_PSG_YM_2149, _psgClock, _sampleRate);
                _lastConfig.psgMode = _psgMode;
                _lastConfig.psgClock = _psgClock;
            }
            if (_channelLayout !== _lastConfig.channelLayout) {
                switch (_channelLayout) {
                    case VAL_CHANNELS_ABC:
                        _set0.psg.setPan(0, 0.1, 0);
                        _set0.psg.setPan(1, 0.5, 0);
                        _set0.psg.setPan(2, 0.9, 0);
                        _set1.psg.setPan(0, 0.1, 0);
                        _set1.psg.setPan(1, 0.5, 0);
                        _set1.psg.setPan(2, 0.9, 0);
                        break;
                    case VAL_CHANNELS_ACB:
                        _set0.psg.setPan(0, 0.1, 0);
                        _set0.psg.setPan(1, 0.9, 0);
                        _set0.psg.setPan(2, 0.5, 0);
                        _set1.psg.setPan(0, 0.1, 0);
                        _set1.psg.setPan(1, 0.9, 0);
                        _set1.psg.setPan(2, 0.5, 0);
                        break;
                }
                _lastConfig.channelLayout = _channelLayout;
            }
        }
        if (_beeper || _psgMode != VAL_PSG_OFF) {
            scheduleProcessTask();
        }
        else {
            cancelProcessTask();
        }
    }

    function reset() {
        for (var i = 0; i < 16; i++) {
            _set0.regIndex = i;
            _set0.regs[i] = 0;
            onPsgRegisterSet(_set0);
            _set1.regIndex = i;
            _set1.regs[i] = 0;
            onPsgRegisterSet(_set1)
        }
        _set0.regIndex = 0;
        _set1.regIndex = 0;
    }

    function scheduleProcessTask() {
        if (_processTask) {
            _processTask.cancelled = true;
        }
        _processTask = _clock.setInterval(process, 1000 / _sampleRate, 0);
        _processTaskInvalid = false;
    }

    function cancelProcessTask() {
        if (_processTask) {
            _processTask.cancelled = true;
            _processTask = null;
        }
    }

    function var_write_rom_trdos(name, value) {
		_rom_trdos = value;
	}

    function io_write_1f(address, data) {
        if (_psgMode === VAL_PSG_OFF || _rom_trdos)
            return;

        if (_turboSound === VAL_TS_AUTO) {
            _turboSound = VAL_TS_POWER_OF_SOUND;
            _turboSoundAutoDetected = true;
        }
        if (_turboSound !== VAL_TS_POWER_OF_SOUND)
            return;

        switch (data) {
            case 0: _activeSet = _set0; break;
            case 1: _activeSet = _set1; break;
        }
    }

    function io_write_reg(address, data) {
        if (_psgMode === VAL_PSG_OFF)
            return;

        if (data < 0x10) {
            var set = (_turboSound === VAL_TS_QUADRO_AY)
                ? ((address & 0x1000) ? _set0 : _set1)
                : _activeSet;
            set.regIndex = data;
        }
        else if ((data & 0xFE) === 0xFE) {
            if (_turboSound === VAL_TS_AUTO) {
                _turboSound = VAL_TS_NEDO_PC;
                _turboSoundAutoDetected = true;
            }
            if (_turboSound !== VAL_TS_NEDO_PC)
                return;

            _activeSet = (data & 1) ? _set0 : _set1;
        }
    }

    function io_write_data(address, data) {
        if (_psgMode === VAL_PSG_OFF)
            return;

        if (!(address & 0x1000) && _turboSound === VAL_TS_AUTO) {
            _turboSound = VAL_TS_QUADRO_AY;
            _turboSoundAutoDetected = true;
        }

        var set = (_turboSound === VAL_TS_QUADRO_AY)
            ? ((address & 0x1000) ? _set0 : _set1)
            : _activeSet;
        set.regs[set.regIndex] = data & _masks[set.regIndex];
        onPsgRegisterSet(set);
    }

    function io_read_data(address, data) {
        if (_psgMode === VAL_PSG_OFF)
            return;

        var set = (_turboSound === VAL_TS_QUADRO_AY)
            ? ((address & 0x1000) ? _set0 : _set1)
            : _activeSet;
        return set.regs[set.regIndex];
    }

    function io_write_fe(address, data) {
        _beeperBit = +!!(data & 0x10);
    }

    function onPsgRegisterSet(set) {
        switch (set.regIndex) {
            case PSG_REG.TONE_A_FINE:
            case PSG_REG.TONE_A_COARSE: 
                set.psg.setTone(0, (set.regs[PSG_REG.TONE_A_COARSE] << 8) | set.regs[PSG_REG.TONE_A_FINE]); 
                break;
            case PSG_REG.TONE_B_FINE:
            case PSG_REG.TONE_B_COARSE: 
                set.psg.setTone(1, (set.regs[PSG_REG.TONE_B_COARSE] << 8) | set.regs[PSG_REG.TONE_B_FINE]); 
                break;
            case PSG_REG.TONE_C_FINE:
            case PSG_REG.TONE_C_COARSE: 
                set.psg.setTone(2, (set.regs[PSG_REG.TONE_C_COARSE] << 8) | set.regs[PSG_REG.TONE_C_FINE]); 
                break;
            case PSG_REG.NOISE: 
                set.psg.setNoise(set.regs[PSG_REG.NOISE]); 
                break;
            case PSG_REG.MIXER: 
                set.psg.channels[0].tOff = (set.regs[PSG_REG.MIXER] >> 0) & 1;
                set.psg.channels[1].tOff = (set.regs[PSG_REG.MIXER] >> 1) & 1;
                set.psg.channels[2].tOff = (set.regs[PSG_REG.MIXER] >> 2) & 1;
                set.psg.channels[0].nOff = (set.regs[PSG_REG.MIXER] >> 3) & 1;
                set.psg.channels[1].nOff = (set.regs[PSG_REG.MIXER] >> 4) & 1;
                set.psg.channels[2].nOff = (set.regs[PSG_REG.MIXER] >> 5) & 1;
                break;
            case PSG_REG.VOLUME_A:
                set.psg.setVolume(0, set.regs[PSG_REG.VOLUME_A] & 0x0F);
                set.psg.channels[0].eOn = !!(set.regs[PSG_REG.VOLUME_A] & 0x10);
                break;
            case PSG_REG.VOLUME_B:
                set.psg.setVolume(1, set.regs[PSG_REG.VOLUME_B] & 0x0F);
                set.psg.channels[1].eOn = !!(set.regs[PSG_REG.VOLUME_B] & 0x10);
                break;
            case PSG_REG.VOLUME_C:
                set.psg.setVolume(2, set.regs[PSG_REG.VOLUME_C] & 0x0F);
                set.psg.channels[2].eOn = !!(set.regs[PSG_REG.VOLUME_C] & 0x10);
                break;
            case PSG_REG.ENVELOPE_FINE:
            case PSG_REG.ENVELOPE_COARSE: 
                set.psg.setEnvelope((set.regs[PSG_REG.ENVELOPE_COARSE] << 8) | set.regs[PSG_REG.ENVELOPE_FINE]); 
                break;
            case PSG_REG.ENVELOPE_SHAPE: 
                set.psg.setEnvelopeShape(set.regs[PSG_REG.ENVELOPE_SHAPE]); 
                break;
        }
    }

    function process() {
        var beeperValue = _beeper ? (_beeperBit ? _beeperVolume : 0.0) : 0.0;
        if (_turboSound === VAL_TS_OFF || _turboSound === VAL_TS_AUTO) {
            _activeSet.psg.process();
            _activeSet.psg.removeDC();
            _sampleBufferLeft[_sampleBufferIndex] = _activeSet.psg.left * _psgVolume + beeperValue;
            _sampleBufferRight[_sampleBufferIndex] = _activeSet.psg.right * _psgVolume + beeperValue;
        }
        else {
            _set0.psg.process();
            _set0.psg.removeDC();
            _set1.psg.process();
            _set1.psg.removeDC();
            _sampleBufferLeft[_sampleBufferIndex] = (_set0.psg.left + _set1.psg.left) * _psgVolume + beeperValue;
            _sampleBufferRight[_sampleBufferIndex] = (_set0.psg.right + _set1.psg.right) * _psgVolume + beeperValue;
        }

        if (++_sampleBufferIndex == _sampleBufferLeft.length) {
            _onDataReady.emit({
                left: _sampleBufferLeft,
                right: _sampleBufferRight,
                sampleCount: _sampleBufferLeft.length
            });
            _sampleBufferLeft = new Float32Array(_sampleBufferSize);
            _sampleBufferRight = new Float32Array(_sampleBufferSize);
            _sampleBufferIndex = 0;
        }

        if (_processTaskInvalid) {
            scheduleProcessTask();
        }
    }

    this.connect = connect;
    this.applySettings = function (beeper, beeperVolume, psgMode, turboSound, channelLayout, psgClock, psgPacketSize, psgVolume) {
        _beeper = beeper;
        _beeperVolume = beeperVolume;
        _psgMode = psgMode;
        if (turboSound !== VAL_TS_AUTO || !_turboSoundAutoDetected) {
            _turboSound = turboSound;
        }
        _channelLayout = channelLayout;
        _psgClock = psgClock;
        _sampleBufferSize = psgPacketSize || 512;
        _psgVolume = psgVolume;
        configure();
    }
    this.getVolume = function () {
        return {
            beeperVolume: _beeperVolume,
            psgVolume: _psgVolume
        };
    }
    this.setVolume = function (beeperVolume, psgVolume) {
        _beeperVolume = beeperVolume;
        _psgVolume = psgVolume;
    }
    this.getState = function () {
        return {
            psg0: {
                address: _set0.regIndex,
                registers: _set0.regs.slice()
            },
            psg1: {
                address: _set1.registers,
                registers: _set1.regs.slice()
            },
            activePsg: _activeSet === _set0 ? 0 : 1
        };
    }
    this.setState = function (value) {
        if (value && value.psg0) {
            for (var i = 0; i < 16; i++) {
                _set0.regIndex = i;
                _set0.regs[i] = value.psg0.registers[i];
                onPsgRegisterSet(_set0);
            }
            _set0.regIndex = value.psg0.address;
        }
        if (value && value.psg1) {
            for (var i = 0; i < 16; i++) {
                _set1.regIndex = i;
                _set1.regs[i] = value.psg1.registers[i];
                onPsgRegisterSet(_set1);
            }
            _set1.regIndex = value.psg1.address;
        }
        if (value && value.activePsg !== 'undefined') {
            _activeSet = value.activePsg === 0 ? _set0 : _set1;
        }
        else if (value && value.psg0) {
            _activeSet = _set0;
        }
    }
    this.get_onDataReady = function () {
        return _onDataReady.pub;
    }
}