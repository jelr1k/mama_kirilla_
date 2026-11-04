from __future__ import annotations

from pathlib import Path, PurePath

import logging
import re
import time

from core.alias_manager import AliasManager, DEFAULT_ACTION_ALIASES
from core.website_manager import WebsiteManager
from tools import applications
from tools.executor import ToolExecutor
from tools.paths import get_workspace_index
from core.target_resolver import TargetResolver
from tools.registry import TOOLS
from services.stark_protocols import StarkProtocols

logger = logging.getLogger("jarvis.router")


class CommandRouter:
    """Определяет однозначные команды, которым не нужен LLM."""

    _GENERIC_APPLICATION_TARGETS = {"приложение", "приложения", "программу", "программа"}
    _CONTEXTUAL_SEARCH_ALIASES = {"где находится", "где лежит", "расположение", "местоположение", "покажи"}
    _FILE_SEARCH_CONTEXT_RE = re.compile(
        r"(?:\bфайл(?:а|ы|ом|ов)?\b|\bпапк\w*\b|\bкаталог\w*\b|\bдиректор\w*\b|\bдокумент\w*\b|[\\/]"
        r"|\b[\wА-Яа-яЁё-]+\.[A-Za-z0-9]{1,8}\b)",
        flags=re.IGNORECASE,
    )

    ROUTER_COMMANDS = {
        "create_file": {
            "name": "Создать файл",
            "category": "files",
            "description": "Создание нового пустого файла или файла с начальным текстом в рабочей директории.",
            "pattern": r"(?:создай|создать)\s+(?:новый\s+)?файл\s+(.+?)(?:\s+с\s+(?:содержимым|текстом))?\s*",
            "display": ["создай файл <имя>", "создать файл <имя>"],
        },
        "create_folder": {
            "name": "Создать папку",
            "category": "files",
            "description": "Создание новой папки или вложенного каталога в рабочей директории.",
            "pattern": r"(?:создай|создать)\s+(?:новую\s+)?папку\s+(.+?)\s*",
            "display": ["создай папку <имя>", "создать папку <имя>"],
        },
        "write_file": {
            "name": "Записать / перезаписать файл",
            "category": "files",
            "description": "Запись или полная перезапись текстового содержимого в указанный файл.",
            "patterns": [
                r"(?:запиши|записать|перезапиши|перезаписать)\s+(?:в\s+)?(?:файл\s+)?(.+?)\s+(?:на|содержимым|текстом|со\s+текстом)\s+(.+)",
                r"(?:запиши|перезапиши)\s+(?:в\s+)?(?:файл\s+)?(.+?)\s*:\s*(.+)"
            ],
            "display": ["запиши в файл <имя> на <текст>", "запиши в файл <имя>: <текст>", "перезапиши файл <имя> на <текст>", "перезапиши файл <имя>: <текст>"],
        },
        "rename_file": {
            "name": "Переименовать файл",
            "category": "files",
            "description": "Переименование существующего файла в рабочей папке.",
            "pattern": r"(?:переименуй|переименовать)\s+(?:файл\s+)?(.+?)\s+(?:в|на)\s+(.+)",
            "display": ["переименуй файл <имя> в <новое имя>", "переименовать файл <имя> в <новое имя>"],
        },
        "copy_file": {
            "name": "Скопировать файл",
            "category": "files",
            "description": "Создание копии файла в указанной директории.",
            "pattern": r"(?:скопируй|скопировать)\s+(?:файл\s+)?(.+?)\s+(?:в|в папку|на)\s+(.+)",
            "display": ["скопируй файл <имя> в <папку>", "скопировать файл <имя> в <папку>"],
        },
        "move_file": {
            "name": "Переместить файл",
            "category": "files",
            "description": "Перемещение файла в другой каталог на диске.",
            "pattern": r"(?:перемести|переместить)\s+(?:файл\s+)?(.+?)\s+(?:в|в папку|на)\s+(.+)",
            "display": ["перемести файл <имя> в <папку>", "переместить файл <имя> в <папку>"],
        },
        "file_info": {
            "name": "Информация о файле",
            "category": "files",
            "description": "Получение сведений о файле (размер, дата изменения, полный путь).",
            "pattern": r"(?:информация|сведения|свойства)\s+(?:о\s+)?(?:файле\s+)?(.+)",
            "display": ["информация о файле <имя>", "сведения о файле <имя>", "свойства файла <имя>"],
        },
        "open_system_folder": {
            "name": "Открыть системную папку",
            "category": "files",
            "description": "Быстрое открытие системных директорий (Загрузки, Документы, Рабочий стол, Проводник).",
            "patterns": [
                r"^(?:открой|открыть)\s+(?:папку\s+)?(загрузки|рабочий\s+стол|документы|видео|музыку|картинки|изображения|проводник|корзину|скриншоты)$",
            ],
            "display": ["открой загрузки", "открой рабочий стол", "открой документы", "открой проводник", "открой скриншоты"],
        },
        "find_application": {
            "name": "Найти приложение",
            "category": "apps",
            "description": "Поиск установленного софта на ПК через встроенный индексатор.",
            "pattern": r"(?:найди|найти)\s+(?:приложение|приложения|программу|программа)\s+(.+)",
            "display": ["найди приложение <имя>", "найти приложение <имя>"],
        },
        "open_url": {
            "name": "Открыть URL",
            "category": "apps",
            "description": "Открытие веб-ссылки или сайта в браузере по умолчанию.",
            "pattern": r"(?:открой|открыть)\s+(https?://\S+)",
            "display": ["открой <http://...>", "открыть <https://...>"],
        },
        "search_google": {
            "name": "Поиск в Google",
            "category": "apps",
            "description": "Поиск информации в интернете через поисковую систему Google.",
            "patterns": [
                r"(?:загугли|найди\s+в\s+гугле|поищи\s+в\s+гугле)\s+(.+)",
                r"(?:найди|поищи)\s+в\s+интернете\s+(.+)",
            ],
            "display": ["загугли <запрос>", "найди в интернете <запрос>"],
        },
        "search_youtube": {
            "name": "Поиск на YouTube",
            "category": "apps",
            "description": "Поиск видеороликов и каналов на YouTube.",
            "patterns": [
                r"найди\s+(?:на|в)\s+ютубе\s+(.+)",
                r"поищи\s+(?:на|в)\s+ютубе\s+(.+)",
            ],
            "display": ["найди на ютубе <запрос>"],
        },
        "search_yandex": {
            "name": "Поиск в Яндексе",
            "category": "apps",
            "description": "Поиск информации в интернете через поисковик Яндекс.",
            "patterns": [
                r"(?:найди|поищи)\s+в\s+яндексе\s+(.+)",
            ],
            "display": ["найди в яндексе <запрос>"],
        },
        "media_volume_up": {
            "name": "Сделать громче",
            "category": "media",
            "description": "Увеличение системной громкости Windows (на 10% или указанное число).",
            "patterns": [r"(?:сделай|сделать)?\s*(?:по)?громче(?:\s+(?:на\s+)?(\d+))?", r"прибавь\s+(?:звук|громкость)(?:\s+(?:на\s+)?(\d+))?"],
            "display": ["сделай громче", "громче", "прибавь громкость", "прибавь звук"],
        },
        "media_volume_down": {
            "name": "Сделать тише",
            "category": "media",
            "description": "Уменьшение системной громкости Windows (на 10% или указанное число).",
            "patterns": [r"(?:сделай|сделать)?\s*(?:по)?тише(?:\s+(?:на\s+)?(\d+))?", r"убавь\s+(?:звук|громкость)(?:\s+(?:на\s+)?(\d+))?"],
            "display": ["сделай тише", "тише", "убавь громкость", "убавь звук"],
        },
        "media_sound_off": {
            "name": "Выключить звук",
            "category": "media",
            "description": "Полное мгновенное отключение звука в системе (Mute).",
            "patterns": [r"(?:выключи|заглуши|выруби|замуть)\s+(?:звук|громкость)", r"^без\s+звука$", r"^мут$"],
            "display": ["выключи звук", "заглуши звук", "без звука", "мут"],
        },
        "media_sound_on": {
            "name": "Включить звук",
            "category": "media",
            "description": "Включение системного звука и возврат прежней громкости (Unmute).",
            "patterns": [r"(?:включи|разглуши|вруби|верни|размуть)\s+(?:звук|громкость)", r"^размут$"],
            "display": ["включи звук", "разглуши звук", "верни звук", "размут"],
        },
        "media_mute_toggle": {
            "name": "Переключить звук",
            "category": "media",
            "description": "Переключение состояния звука (вкл/выкл).",
            "patterns": [r"переключи\s+(?:звук|громкость)"],
            "display": ["переключи звук"],
        },
        "media_play_pause": {
            "name": "Пауза / Плей музыки",
            "category": "media",
            "description": "Возобновление или постановка на паузу мультимедиа (Яндекс Музыка, браузер, плеер).",
            "patterns": [
                r"^(?:пауза|плей|возобнови|play|pause)$",
                r"^(?:пауза|плей|возобнови(?:ть)?|продолжи(?:ть)?)\s+(?:музыку|трек|видео|яндекс(?:\s+музыку)?)$",
                r"^(?:включи|вруби|запусти)\s+(?:музыку|трек|песню|яндекс(?:\s+музыку)?)$",
            ],
            "display": ["пауза", "плей", "музыка пауза", "включи музыку", "возобнови музыку"],
        },
        "media_stop": {
            "name": "Остановить музыку (Стоп)",
            "category": "media",
            "description": "Полная остановка воспроизведения музыки и аудио.",
            "patterns": [
                r"^(?:стоп|stop)$",
                r"^(?:стоп|останови(?:ть)?|выключи(?:ть)?|выруби(?:ть)?|заглуши(?:ть)?)\s+(?:музыку|трек|песню|яндекс(?:\s+музыку)?)$",
                r"^(?:музык[ау]|трек|яндекс(?:\s+музык[ау])?)\s+(?:стоп|на\s+паузу|пауза)$",
                r"^(?:поставь\s+на\s+паузу|на\s+паузу|сделай\s+паузу)(?:\s+(?:музыку|трек))?$",
            ],
            "display": ["стоп", "музыка стоп", "стоп музыка", "останови музыку", "на паузу", "яндекс стоп"],
        },
        "media_next": {
            "name": "Следующий трек (Вперед)",
            "category": "media",
            "description": "Переход к следующему музыкальному треку в активном приложении.",
            "patterns": [
                r"^(?:впер[её]д|дальше|след|next|скип|скипни)$",
                r"^(?:следующ(?:ий|ая|ую)|включи\s+следующ(?:ий|ую)|пропусти(?:ть)?|скип(?:ни|нуть)?)\s*(?:трек|песню|музыку)?$",
                r"^(?:трек|музык[ау]|песн[юя]|яндекс(?:\s+музык[ау])?)\s+(?:впер[её]д|дальше|след)$",
                r"^переключи\s+(?:впер[её]д|на\s+следующ(?:ий|ую))(?:\s+(?:трек|песню|музыку))?$",
            ],
            "display": ["вперед", "следующий трек", "трек вперед", "музыка вперед", "яндекс вперед", "скипни трек"],
        },
        "media_prev": {
            "name": "Предыдущий трек (Назад)",
            "category": "media",
            "description": "Возврат к предыдущему воспроизводимому треку.",
            "patterns": [
                r"^(?:назад|пред|prev|back)$",
                r"^(?:предыдущ(?:ий|ая|ую)|включи\s+предыдущ(?:ий|ую)|верни(?:ть)?)\s*(?:трек|песню|музыку)?$",
                r"^(?:трек|музык[ау]|песн[юя]|яндекс(?:\s+музык[ау])?)\s+назад$",
                r"^переключи\s+(?:назад|на\s+предыдущ(?:ий|ую))(?:\s+(?:трек|песню|музыку))?$",
            ],
            "display": ["назад", "предыдущий трек", "трек назад", "музыка назад", "яндекс назад", "верни трек"],
        },
        "protocol_morning": {
            "name": "Протокол «Доброе утро»",
            "category": "protocols",
            "description": "Утренний сценарий: приветствие, сводка времени/даты, запуск рабочих сервисов.",
            "patterns": [
                r"^(?:джарвис\s+)?(?:протокол\s+)?доброе\s+утро$",
            ],
            "display": ["доброе утро", "протокол доброе утро"],
        },
        "protocol_lockdown": {
            "name": "Протокол «Защита» (Блокировка)",
            "category": "protocols",
            "description": "Сценарий блокировки: мгновенный Win+L, выключение звука и сворачивание окон.",
            "patterns": [
                r"^(?:джарвис\s+)?(?:протокол\s+)?(?:защита|блокировка)$",
                r"^(?:джарвис\s+)?терминал\s+защита$",
            ],
            "display": ["защита", "протокол защита", "протокол блокировка"],
        },
        "protocol_cinema": {
            "name": "Протокол «Кино»",
            "category": "protocols",
            "description": "Сценарий кино: подготовка атмосферы для фильмов, комфортная громкость.",
            "patterns": [
                r"^(?:джарвис\s+)?(?:протокол|режим)\s+кино$",
                r"^(?:джарвис\s+)?время\s+кино$",
                r"^(?:джарвис\s+)?кино$",
            ],
            "display": ["кино", "протокол кино", "режим кино"],
        },
        "protocol_game": {
            "name": "Протокол «Игра»",
            "category": "protocols",
            "description": "Игровой сценарий: подготовка компьютера к играм, запуск Steam и клиентов.",
            "patterns": [
                r"^(?:джарвис\s+)?(?:протокол|режим)\s+игра$",
                r"^(?:джарвис\s+)?время\s+играть$",
                r"^(?:джарвис\s+)?игра$",
            ],
            "display": ["игра", "протокол игра", "режим игра"],
        },
        "protocol_clean_desk": {
            "name": "Протокол «Чистый стол» (Очистка)",
            "category": "protocols",
            "description": "Сценарий очистки: сворачивание окон на рабочий стол и очистка корзины.",
            "patterns": [
                r"^(?:джарвис\s+)?(?:протокол\s+)?чистый\s+стол$",
                r"^(?:джарвис\s+)?(?:протокол\s+)?очистк[аи]$",
            ],
            "display": ["чистый стол", "протокол чистый стол", "очистка"],
        },
        "protocol_work": {
            "name": "Протокол «Работа»",
            "category": "protocols",
            "description": "Рабочий сценарий: запуск рабочих программ, браузера и необходимых вкладок.",
            "patterns": [
                r"^(?:джарвис\s+)?(?:протокол|режим)\s+работа$",
                r"^(?:джарвис\s+)?к\s+работе$",
                r"^(?:джарвис\s+)?работа$",
            ],
            "display": ["работа", "протокол работа", "к работе"],
        },
        "protocol_default": {
            "name": "Протокол «Дефолт» (Обычный режим)",
            "category": "protocols",
            "description": "Сброс активных протоколов и возврат стандартного профиля работы ПК.",
            "patterns": [
                r"^(?:джарвис\s+)?дефолт$",
                r"^(?:джарвис\s+)?(?:верни|сделай)\s+как\s+обычно$",
                r"^(?:джарвис\s+)?(?:обычный|стандартный|дефолтный)\s+режим$",
                r"^(?:джарвис\s+)?сброс\s+режима$",
            ],
            "display": ["дефолт", "верни как обычно", "обычный режим"],
        },
        "zapret_start": {
            "name": "Запрет Discord/YouTube (service.bat)",
            "category": "network",
            "description": "Запуск службы обхода замедления для Discord и YouTube через service.bat.",
            "patterns": [
                r"^(?:включи|включить|запусти|запустить|открой|открыть|подними|поднять|активируй|активировать|старт)\s+(?:запрет|zapret|service\.bat|сервис\.bat|сервисный\s+бат)$",
                r"^(?:запрет|zapret|service\.bat|сервис\.bat)$",
                r"^(?:открой|запусти|включи)\s+(?:окно\s+)?(?:сервис\.бат|service\.bat)$",
            ],
            "display": ["запрет", "включи запрет", "открой service.bat", "zapret"],
        },
        "vpn_connect": {
            "name": "VPN-клиент (Happ / FlClashX)",
            "category": "network",
            "description": "Запуск и автоматическое подключение выбранного VPN-клиента (Happ или FlClashX).",
            "patterns": [
                r"^(?:включи|включить|запусти|запустить|открой|открыть|подними|поднять|активируй|активировать|старт)\s+(?:впн|vpn)(?:\s+(happ|хапп|хэпп|хепп|flclashx|flclash|флклэш|флклаш))?$",
                r"^(?:впн|vpn)(?:\s+(happ|хапп|хэпп|хепп|flclashx|flclash|флклэш|флклаш))?$",
            ],
            "display": ["впн", "включи впн", "впн happ", "впн flclashx"],
        },
        "vpn_status": {
            "name": "Статус VPN и Запрета",
            "category": "network",
            "description": "Проверка статуса подключения активного VPN-туннеля и службы Zapret.",
            "patterns": [
                r"^(?:статус|состояние|проверь|покажи)\s+(?:впн|vpn|запрет|zapret)$",
                r"^(?:впн|vpn|запрет|zapret)\s+(?:статус|состояние)$",
            ],
            "display": ["статус впн", "состояние vpn", "статус запрет", "проверь zapret"],
        },
        "apply_mouse_settings": {
            "name": "Настройки мыши (ZET Gaming Fury)",
            "category": "devices",
            "description": "Автоматическая активация профиля и чувствительности сенсора мыши ZET Gaming Fury.",
            "patterns": [
                r"^(?:мышь|мыш|мышка)$",
                r"^(?:примени(?:ть)?|нажми\s+применить|активируй)\s+(?:в\s+)?(?:прог(?:е|у|рамм[еу])\s+)?(?:мышь|мыш|мышк[уе]|zet(?:\s+gaming)?|fury)$",
                r"^(?:мышь|мыш|мышка)\s+(?:примени(?:ть)?|нажми\s+применить)$",
                r"^(?:настройки|софт|программа)\s+мыши?$",
            ],
            "display": ["мышь", "мыш", "мышка", "примени мышь"],
        },
        "system_telemetry": {
            "name": "Телеметрия и нагрузка ПК",
            "category": "system",
            "description": "Голосовой отчет и вывод параметров загрузки CPU, RAM, накопителей и температуры.",
            "display": [
                "телеметрия", "телеметрия пк", "нагрузка пк", "нагрузка процессора",
                "состояние пк", "состояние системы", "статус пк", "статус системы",
                "ресурсы пк", "системные ресурсы", "сколько памяти", "сколько оперативы",
                "че по нагрузке", "покажи нагрузку", "параметры пк", "инфо о системе"
            ]
        },
        "empty_recycle_bin": {
            "name": "Очистить корзину",
            "category": "system",
            "description": "Окончательное удаление всех временных файлов из Корзины Windows.",
            "patterns": [
                r"(?:очисти|почисти|очистить|вынеси)\s+(?:корзину|мусор|мусорку)",
                r"^(?:очисти|очистить)\s+корзину$",
                r"^вынеси\s+мусор$",
            ],
            "display": ["очисти корзину", "почисти корзину", "вынеси мусор"],
        },
        "take_screenshot": {
            "name": "Сделать скриншот",
            "category": "system",
            "description": "Создание снимка экрана с сохранением в папку скриншотов и отправкой в чат.",
            "patterns": [
                r"^(?:сделай|сделать)?\s*(?:скриншот|скрин|снимок\s+экрана)$",
                r"^скриншот$",
                r"^скрин$",
                r"^снимок\s+экрана$",
            ],
            "display": ["сделай скриншот", "скрин", "снимок экрана"],
        },
        "lock_pc": {
            "name": "Заблокировать ПК",
            "category": "system",
            "description": "Мгновенная блокировка сеанса пользователя Windows (эквивалент Win+L).",
            "patterns": [
                r"^(?:заблокируй|заблочь)\s+(?:пк|комп|компьютер|экран|систему)$",
                r"^заблокируй\s+экран$",
                r"^блок\s+пк$",
            ],
            "display": ["заблокируй пк", "заблокируй экран", "заблочь комп"],
        },
        "date_time": {
            "name": "Текущее время и дата",
            "category": "system",
            "description": "Озвучивание точного времени, сегодняшнего числа и дня недели.",
            "patterns": [
                r"^(?:сколько\s+времени|который\s+час|какое\s+сегодня\s+число|какая\s+дата|какой\s+сегодня\s+день(?: недели)?)$",
                r"^время$",
                r"^дата$",
            ],
            "display": ["сколько времени", "который час", "какая дата", "какой сегодня день"],
        },
        "jarvis_minimize": {
            "name": "Свернуть окно",
            "category": "system",
            "description": "Сворачивание графического интерфейса ассистента в системный трей.",
            "display": ["свернись", "сверни окно", "свернись в трей"],
        },
        "jarvis_maximize": {
            "name": "Развернуть окно",
            "category": "system",
            "description": "Разворачивание окна интерфейса на весь рабочий стол.",
            "display": ["развернись", "разверни окно", "на весь экран", "сделай окно на весь экран"],
        },
        "jarvis_restore": {
            "name": "Восстановить размер окна",
            "category": "system",
            "description": "Возврат окна ассистента к стандартным пропорциям.",
            "display": ["восстанови окно", "верни обычный размер", "сделай окно обычным", "верни окно"],
        },
        "jarvis_shutdown": {
            "name": "Закрыть ассистента",
            "category": "system",
            "description": "Полное выключение ядра Кириэшки, UI и фоновых служб.",
            "display": ["закрой себя", "выключись", "закройся", "заверши работу"],
        },
        "ollama_status": {
            "name": "Статус Ollama",
            "category": "ai",
            "description": "Проверка работоспособности локального ИИ-сервера Ollama.",
            "display": ["статус ollama", "состояние ollama"],
        },
        "ollama_start": {
            "name": "Запустить Ollama",
            "category": "ai",
            "description": "Запуск фонового процесса сервиса Ollama на компьютере.",
            "display": ["запусти ollama", "запустить ollama", "запусти сервер ollama", "запустить сервер ollama"],
        },
        "ollama_stop": {
            "name": "Остановить Ollama",
            "category": "ai",
            "description": "Завершение процесса Ollama для освобождения системных ресурсов.",
            "display": ["останови ollama", "остановить ollama", "останови сервер ollama", "остановить сервер ollama"],
        },
        "model_unload": {
            "name": "Выгрузить модель",
            "category": "ai",
            "description": "Принудительное освобождение VRAM / RAM от загруженной модели нейросети.",
            "display": ["выгрузи модель", "выгрузить модель", "выгрузи текущую модель", "освободи модель", "освободи память от модели"],
        },
        "clear_chat": {
            "name": "Очистить чат",
            "category": "ai",
            "description": "Очистка истории переписки и сброс контекста диалога с ассистентом.",
            "patterns": [
                r"^(?:очисти|очистить|сотри)\s+(?:чат|историю|сообщения)$",
                r"^очисти\s+чат$",
                r"^сбрось\s+чат$",
            ],
            "display": ["очисти чат", "очисти историю", "сотри сообщения"],
        },
    }
    @classmethod
    def _definition_display(cls, command_id: str) -> list[str]:
        return list(cls.ROUTER_COMMANDS.get(command_id, {}).get("display", []))

    @classmethod
    def _match_definition(cls, command_id: str, text: str):
        definition = cls.ROUTER_COMMANDS[command_id]
        patterns = definition.get("patterns")
        if patterns is None:
            pattern = definition.get("pattern")
            patterns = [pattern] if pattern else []
        for pattern in patterns:
            match = re.fullmatch(pattern, text, flags=re.IGNORECASE)
            if match:
                return match
        return None

    def __init__(self, config, ollama_manager, alias_manager: AliasManager | None = None, website_manager: WebsiteManager | None = None, event_bus=None, protocols_manager=None, steam_manager=None, app_indexer=None):
        self.config = config
        self.ollama_manager = ollama_manager
        self.alias_manager = alias_manager or AliasManager()
        self.website_manager = website_manager or WebsiteManager(event_bus=event_bus)
        self.events = event_bus
        self.protocols_manager = protocols_manager
        if steam_manager is None:
            try:
                from core.steam_manager import SteamManager
                steam_manager = SteamManager.get_instance()
            except Exception:
                steam_manager = None
        self.steam_manager = steam_manager
        if app_indexer is None:
            try:
                from core.app_indexer import AppIndexer
                app_indexer = AppIndexer.get_instance(event_bus=event_bus)
            except Exception:
                app_indexer = None
        self.app_indexer = app_indexer
        self.target_resolver = TargetResolver(self.alias_manager, get_workspace_index)
        self.ui_actions = {}
        logger.debug("router_created")

    def set_ui_actions(self, actions: dict[str, callable] | None) -> None:
        """Registers abstract application-window actions, without knowing the UI framework."""
        self.ui_actions = dict(actions or {})

    def _executor(self) -> ToolExecutor:
        return ToolExecutor(self.config, set(TOOLS), self.alias_manager, event_bus=self.events)

    @classmethod
    def _is_contextual_file_search(cls, alias: str, target: str) -> bool:
        if alias not in cls._CONTEXTUAL_SEARCH_ALIASES:
            return True
        return bool(cls._FILE_SEARCH_CONTEXT_RE.search(target))

    @classmethod
    def _contains_action_alias(cls, text: str, action: str, alias: str) -> bool:
        pattern = rf"(?<!\w){re.escape(alias)}(?!\w)"
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            return False
        if action != "search" or alias not in cls._CONTEXTUAL_SEARCH_ALIASES:
            return True
        target = text[match.end():].lstrip(" ,:;—-\t")
        return cls._is_contextual_file_search(alias, target)

    def _has_multiple_actions(self, text: str) -> bool:
        normalized = " ".join(text.strip().split())
        if not normalized:
            return False
        matches = []
        for action, defaults in DEFAULT_ACTION_ALIASES.items():
            for alias in defaults:
                if self._contains_action_alias(normalized, action, alias):
                    matches.append(action)
                    break
        for action, entry in self.alias_manager.data.get("actions", {}).items():
            for alias in entry.get("aliases", []):
                if self._contains_action_alias(normalized, action, alias):
                    matches.append(action)
                    break
        unique_actions = set(matches)
        if len(unique_actions) > 1:
            logger.info("compound_command detected actions=%s text=%r", sorted(unique_actions), text)
            return True
        return False

    ASYNC_SYSTEM_COMMANDS = (
        "empty_recycle_bin",
        "take_screenshot",
        "system_telemetry",
        "open_system_folder",
        "search_google",
        "search_youtube",
        "search_yandex",
        "zapret_start",
        "vpn_connect",
        "vpn_status",
    )

    def is_async_system_command(self, text: str) -> bool:
        """Определяет команды, которые выполняют системные/дисковые/сетевые операции и должны запускаться в фоне."""
        normalized = self._normalize_command_text(text)
        lower = normalized.casefold()

        if lower in {item.casefold() for item in self._definition_display("system_telemetry")}:
            return True

        for cmd_id in self.ASYNC_SYSTEM_COMMANDS:
            if self._match_definition(cmd_id, normalized):
                return True

        action = self._resolve_action(normalized)
        if action and action[0] == "launch":
            if getattr(self, "website_manager", None) and self.website_manager.resolve_url(action[1]):
                return True
            if getattr(self, "steam_manager", None) and self.steam_manager.resolve_game(action[1]):
                return True
            if getattr(self, "app_indexer", None) and self.app_indexer.resolve_app(action[1]):
                return True

        return False

    def _resolve_action(self, text: str):
        action = self.alias_manager.resolve_action(text)
        if not action:
            return None
        action_name, target = action
        if action_name == "search":
            for alias in self._CONTEXTUAL_SEARCH_ALIASES:
                if re.match(rf"^{re.escape(alias)}(?:,)?\s+", text, flags=re.IGNORECASE):
                    if not self._is_contextual_file_search(alias, target):
                        logger.info("contextual_search_rejected target=%r text=%r", target, text)
                        return None
                    break
        return action

    @staticmethod
    def _reply(result: dict, include_path: bool = True) -> str:
        if result.get("pending_confirmation"):
            tool_name = result.get("confirmation_tool", "действие")
            labels = {
                "delete_file": "удаление файла",
                "write_file": "перезапись файла",
                "rename_file": "переименование файла",
                "copy_file": "копирование файла",
                "move_file": "перемещение файла",
                "close_application": "закрытие приложения",
            }
            return f"[Подтверждение] Подтвердить {labels.get(tool_name, tool_name)}? Ответь «да» или «нет»."
        if not result.get("success"):
            matches = result.get("matches") or []
            if result.get("ambiguous") and matches:
                return result.get("error") or "Неоднозначный запрос."
            return f"Не выполнено: {result.get('error', 'неизвестная ошибка')}"
        if result.get("content") is not None:
            content_str = str(result["content"])
            if result.get("system_telemetry") or result.get("media_control") or "Скриншот" in content_str:
                return content_str
            if include_path:
                path = result.get("path")
                if path:
                    file_name = PurePath(str(path).replace("\\", "/")).name
                    prefix = f"Содержимое {file_name}:\n"
                else:
                    prefix = "Содержимое файла:\n"
            else:
                prefix = "Содержимое файла:\n"
            return prefix + content_str
        if result.get("matches") is not None:
            matches = result.get("matches") or []
            if not matches:
                return "Ничего не найдено."
            return "Найдено:\n" + "\n".join(matches[:20])
        if result.get("running") is not None:
            return "Приложение запущено." if result["running"] else "Приложение не запущено."
        if result.get("path"):
            file_name = PurePath(str(result["path"]).replace("\\", "/")).name
            return f"Готово: {file_name}" if file_name else f"Готово: {result['path']}"
        return "Готово."

    @classmethod
    def _close_reply(cls, target: str, result: dict) -> str:
        if result.get("pending_confirmation"):
            return cls._reply(result)
        if not result.get("success"):
            matches = result.get("matches") or []
            if result.get("ambiguous") and matches:
                return result.get("error") or "Неоднозначный запрос."
            return f"Не удалось закрыть {target}: {result.get('error', 'неизвестная ошибка')}"
        if result.get("already_closed") or result.get("running") is False:
            return f"{target} уже закрыт."
        return f"{target} закрыт."

    def _resolve_target(self, query, categories, alias_confirmation_callback=None, *, use_workspace_index=False):
        """Разрешает цель даже если она является частью естественной фразы."""
        return self.target_resolver.resolve(
            query,
            categories,
            alias_confirmation_callback=alias_confirmation_callback,
            use_workspace_index=use_workspace_index,
        )

    def execute_confirmed(self, tool_name: str, arguments: dict) -> str:
        """Исполняет ранее подтверждённое действие без повторной маршрутизации."""
        result = self._executor().execute(
            tool_name,
            dict(arguments),
            confirmation_callback=lambda *_args: True,
        )
        if tool_name == "close_application":
            target = str(arguments.get("name") or arguments.get("target") or "приложение")
            return self._close_reply(target, result)
        return self._reply(result)

    def _direct_tool(self, tool_name: str, arguments: dict, confirmation_callback=None) -> str:
        result = self._executor().execute(
            tool_name,
            arguments,
            confirmation_callback=confirmation_callback,
        )
        return self._reply(result)

    def _route_extended_tools(self, text: str, confirmation_callback=None, alias_confirmation_callback=None) -> str | None:
        """Прямые маршруты для всех инструментов, которые иначе доступны LLM."""
        lower = " ".join(text.lower().split())
        executor = self._executor()

        # Фирменные и пользовательские протоколы JARVIS
        if self.protocols_manager is not None:
            matched_proto = self.protocols_manager.find_protocol_by_phrase(text)
            if matched_proto is not None:
                ollama_url = getattr(self.config, "ollama_url", None)
                model = self.config.get("model") if hasattr(self.config, "get") else None
                return StarkProtocols.execute_protocol(matched_proto, ollama_url=ollama_url, model=model)
        for proto_cmd, proto_id in (
            ("protocol_morning", "morning"),
            ("protocol_lockdown", "lockdown"),
            ("protocol_cinema", "cinema"),
            ("protocol_game", "game"),
            ("protocol_clean_desk", "clean_desk"),
            ("protocol_work", "work"),
            ("protocol_default", "default"),
        ):
            if self._match_definition(proto_cmd, text):
                return StarkProtocols.execute_protocol(proto_id)

        # Настройки мыши (ZET Gaming Fury)
        if self._match_definition("apply_mouse_settings", text):
            return self._reply(executor.execute("apply_mouse_settings", {}))

        # VPN-клиенты и Запрет Discord/YouTube.
        if self._match_definition("zapret_start", text) or self._match_definition("vpn_connect", text) or self._match_definition("vpn_status", text):
            from core.vpn_manager import get_vpn_manager

            manager = get_vpn_manager()
            if self._match_definition("zapret_start", text):
                return manager.launch_zapret().get("message") or "Запускаю Запрет."
            if self._match_definition("vpn_status", text):
                status = manager.status()
                lines = [status.get("zapret", {}).get("message", "")]
                for client_status in (status.get("clients") or {}).values():
                    lines.append(client_status.get("message", ""))
                return "\n".join(line for line in lines if line)
            match = self._match_definition("vpn_connect", text)
            client = match.group(1) if match and match.groups() else None
            return manager.connect(client).get("message") or "Запускаю VPN."

        # Очистить чат
        if self._match_definition("clear_chat", text):
            if self.ui_actions and "clear_chat" in self.ui_actions:
                try:
                    self.ui_actions["clear_chat"]()
                except Exception as exc:
                    logger.warning("clear_chat action failed: %s", exc)
                return "История чата очищена."
            return "Чат очищен."

        # Скриншот
        if self._match_definition("take_screenshot", text):
            return self._reply(executor.execute("take_screenshot", {}))

        # Блокировка экрана
        if self._match_definition("lock_pc", text):
            return self._reply(executor.execute("lock_pc", {}))

        # Текущее время и дата
        if self._match_definition("date_time", text):
            return self._reply(executor.execute("get_current_time_date", {}))

        # Системные папки
        match = self._match_definition("open_system_folder", text)
        if match:
            folder = match.group(1).strip()
            return self._reply(executor.execute("open_system_folder", {"folder_name": folder}))

        # Очистка корзины
        match = self._match_definition("empty_recycle_bin", text)
        if match:
            return self._reply(executor.execute("empty_recycle_bin", {}))

        # Поиск в веб
        for search_cmd, engine in (
            ("search_google", "google"),
            ("search_youtube", "youtube"),
            ("search_yandex", "yandex"),
        ):
            match = self._match_definition(search_cmd, text)
            if match:
                query = match.group(1).strip()
                import urllib.parse
                import webbrowser
                if engine == "youtube":
                    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
                    webbrowser.open(url)
                    return f"Ищу «{query}» на YouTube."
                elif engine == "yandex":
                    url = f"https://ya.ru/search/?text={urllib.parse.quote(query)}"
                    webbrowser.open(url)
                    return f"Ищу «{query}» в Яндексе."
                else:
                    url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
                    webbrowser.open(url)
                    return f"Ищу «{query}» в Google."


        # Создание файла/папки.
        match = self._match_definition("create_file", text)
        if match and executor._is_enabled("create_file"):
            path = match.group(1).strip().strip("\"'")
            return self._direct_tool("create_file", {"path": path, "content": ""}, confirmation_callback)

        match = re.fullmatch(r"(?:создай|создать)\s+(?:новую\s+)?папку\s+(.+?)\s*", text, re.IGNORECASE)
        if match and executor._is_enabled("create_folder"):
            path = match.group(1).strip().strip("\"'")
            return self._direct_tool("create_folder", {"path": path}, confirmation_callback)

        # Запись файла. Форматы: «запиши в файл X: текст» / «перезапиши файл X на текст».
        match = self._match_definition("write_file", text)
        if match and executor._is_enabled("write_file"):
            path, content = match.groups()
            return self._direct_tool("write_file", {"path": path.strip().strip("\"'"), "content": content.strip()}, confirmation_callback)

        # Переименование/копирование/перемещение.
        match = self._match_definition("rename_file", text)
        if match and executor._is_enabled("rename_file"):
            path, new_name = match.groups()
            return self._direct_tool("rename_file", {"path": path.strip().strip("\"'"), "new_name": new_name.strip().strip("\"'")}, confirmation_callback)

        match = self._match_definition("copy_file", text)
        if match and executor._is_enabled("copy_file"):
            path, destination = match.groups()
            return self._direct_tool("copy_file", {"path": path.strip().strip("\"'"), "destination": destination.strip().strip("\"'")}, confirmation_callback)

        match = self._match_definition("move_file", text)
        if match and executor._is_enabled("move_file"):
            path, destination = match.groups()
            return self._direct_tool("move_file", {"path": path.strip().strip("\"'"), "destination": destination.strip().strip("\"'")}, confirmation_callback)

        # Информация о файле.
        match = self._match_definition("file_info", text)
        if match and executor._is_enabled("file_info"):
            path = match.group(1).strip().strip("\"'")
            return self._direct_tool("file_info", {"path": path}, confirmation_callback)

        # Поиск приложения.
        match = self._match_definition("find_application", text)
        if match and executor._is_enabled("find_application"):
            name = match.group(1).strip()
            return self._direct_tool("find_application", {"name": name}, confirmation_callback)

        # Открытие URL.
        match = self._match_definition("open_url", text)
        if match and executor._is_enabled("open_url"):
            return self._direct_tool("open_url", {"url": match.group(1)}, confirmation_callback)

        for media_cmd, media_act in (
            ("media_volume_up", "volume_up"),
            ("media_volume_down", "volume_down"),
            ("media_sound_off", "sound_off"),
            ("media_sound_on", "sound_on"),
            ("media_mute_toggle", "toggle_mute"),
            ("media_stop", "stop"),
            ("media_play_pause", "play_pause"),
            ("media_next", "next_track"),
            ("media_prev", "prev_track"),
        ):
            match = self._match_definition(media_cmd, text)
            if match and executor._is_enabled("control_media"):
                steps = 5
                if match.groups() and match.group(1):
                    try:
                        steps = max(1, min(25, int(match.group(1)) // 2))
                    except ValueError:
                        pass
                return self._reply(executor.execute("control_media", {"action": media_act, "steps": steps}))

        # Управление окнами обычных приложений. Алиасы приложения разрешаются
        # тем же TargetResolver, что и для запуска/закрытия.
        action = self._resolve_action(lower)
        if action and action[0] == "minimize" and executor._is_enabled("minimize_application"):
            target = action[1]
            if target.strip().casefold() in self._GENERIC_APPLICATION_TARGETS:
                return "Какое приложение свернуть?"
            resolved, error = self._resolve_target(target, ("applications",), alias_confirmation_callback)
            if error:
                return f"Не выполнено: {error}"
            result = executor.execute("minimize_application", {"name": resolved}, confirmation_callback=confirmation_callback)
            if result.get("success"):
                return f"{target} свернут."
            return f"Не удалось свернуть {target}: {result.get('error', 'неизвестная ошибка')}"

        # Специальные команды Jarvis/окна. Backend знает только абстрактные
        # действия. Конкретный UI предоставляет их через ui_actions.
        ui_actions = self.ui_actions
        assistant_name = str(self.config.get("assistant_name", "Kirieshcka")).strip().casefold()
        shutdown_commands = {"закрой себя", "закрой приложение", "закрой джарвис", "закрой jarvis", "выключись", "закройся", "заверши работу"}
        if assistant_name:
            shutdown_commands.add(f"закрой {assistant_name}")

        if lower in shutdown_commands:
            action = ui_actions.get("shutdown")
            if action:
                action()
            return "Полностью закрываю приложение."

        if lower in {item.casefold() for item in self._definition_display("jarvis_minimize")}:
            action = ui_actions.get("minimize")
            if action:
                action()
            return "Сворачиваю окно."

        if lower in {item.casefold() for item in self._definition_display("jarvis_maximize")}:
            action = ui_actions.get("maximize")
            if action:
                action()
            return "Разворачиваю окно."

        if lower in {item.casefold() for item in self._definition_display("jarvis_restore")}:
            action = ui_actions.get("restore")
            if action:
                action()
            return "Восстанавливаю обычный размер окна."

        # Ollama и модель. Русские варианты намеренно широкие: Vosk часто
        # искажает «Ollama» и название Qwen.
        model = str(self.config.get("model", "")).strip()
        model_aliases = {
            "модель", "модел", "квен", "квэн", "квен 3", "квэн 3", "квен3", "квэн3",
            "qwen", "qwen 3", "qwen3", "qwen3 1.7b", "qwen 1.7b",
            "ллм", "ллмку", "ллам", "llm",
        }
        model_action = re.fullmatch(
            r"(?:выгрузи|выгрузить|освободи|освободить|закрой|закрыть|останови|остановить|выключи|выключить)"
            r"\s+(?:текущую\s+)?(.+)",
            lower,
        )
        if model_action:
            target = model_action.group(1).strip()
            if target in model_aliases or any(alias in target for alias in model_aliases if alias not in {"модель"}):
                result = self.ollama_manager.unload_model(model)
                return f"Модель {model} выгружена." if result.get("success") else f"Не удалось выгрузить модель: {result.get('error', 'неизвестная ошибка')}"

        ollama_aliases = {
            "оллама", "олламу", "олламы", "оллам", "оллама", "ollama",
            "сервер оллама", "сервер ollama", "сервер ламы", "сервер лам",
        }
        server_action = re.fullmatch(
            r"(?:закрой|закрыть|останови|остановить|выключи|выключить|заверши|завершить)"
            r"\s+(.+)",
            lower,
        )
        if server_action and server_action.group(1).strip() in ollama_aliases:
            result = self.ollama_manager.stop_server()
            return "Ollama Server остановлен." if result.get("success") else f"Не удалось остановить Ollama: {result.get('error', 'неизвестная ошибка')}"

        if lower in {item.casefold() for item in self._definition_display("model_unload")}:
            result = self.ollama_manager.unload_model(model)
            return f"Модель {model} выгружена." if result.get("success") else f"Не удалось выгрузить модель: {result.get('error', 'неизвестная ошибка')}"

        return None

    def command_catalog(self) -> list[dict[str, object]]:
        """Справочник из единого набора определений Router.

        Действия берутся непосредственно из AliasManager, а расширенные команды
        из ROUTER_COMMANDS с полными метаданными (категория, описание, примеры).
        """
        action_meta = {
            "launch": {
                "name": "Открыть приложение",
                "category": "apps",
                "description": "Запуск установленной программы, игры или ярлыка по имени или голосовому алиасу.",
                "example": "открой стим",
            },
            "close": {
                "name": "Закрыть приложение",
                "category": "apps",
                "description": "Принудительное или мягкое завершение запущенного приложения или игры.",
                "example": "закрой дискорд",
            },
            "search": {
                "name": "Найти файл или папку",
                "category": "files",
                "description": "Поиск файлов или каталогов на диске по маске или части названия.",
                "example": "найди файл отчет",
            },
            "read": {
                "name": "Прочитать файл",
                "category": "files",
                "description": "Чтение текстового содержимого файла и озвучивание или показ ответа.",
                "example": "прочитай файл заметки.txt",
            },
            "delete": {
                "name": "Удалить файл",
                "category": "files",
                "description": "Безопасное удаление указанного файла из разрешённой рабочей папки.",
                "example": "удали файл лог.txt",
            },
            "status": {
                "name": "Проверить статус приложения",
                "category": "apps",
                "description": "Проверка, запущен ли процесс на компьютере в данный момент.",
                "example": "статус телеграм",
            },
            "minimize": {
                "name": "Свернуть приложение",
                "category": "apps",
                "description": "Сворачивание окна активного или указанного приложения.",
                "example": "сверни браузер",
            },
        }
        catalog = []
        for action, aliases in DEFAULT_ACTION_ALIASES.items():
            meta = action_meta.get(action)
            if not meta:
                continue
            commands = list(aliases)
            custom = self.alias_manager.data.get("actions", {}).get(action, {})
            for alias in custom.get("aliases", []):
                if alias not in commands:
                    commands.append(alias)
            catalog.append({
                "id": f"action_{action}",
                "name": meta["name"],
                "category": meta["category"],
                "description": meta["description"],
                "example": meta["example"],
                "commands": commands,
            })
        for cmd_id, definition in self.ROUTER_COMMANDS.items():
            if definition.get("display"):
                catalog.append({
                    "id": cmd_id,
                    "name": definition["name"],
                    "category": definition.get("category", "system"),
                    "description": definition.get("description", ""),
                    "example": definition.get("example", (definition.get("display") or [""])[0]),
                    "commands": list(definition["display"]),
                })
        return catalog

    def tools_for_message(self, text: str) -> set[str]:
        """Определяет набор LLM-инструментов для текущего сообщения."""
        lower = self._normalize_command_text(text).casefold()
        action = self._resolve_action(lower)
        executor = self._executor()
        enabled = {name for name in TOOLS if executor._is_enabled(name)}

        action_tools = {
            "launch": {"launch_application", "get_process_status"},
            "close": {"close_application", "get_process_status"},
            "minimize": {"minimize_application", "get_process_status"},
            "status": {"get_process_status"},
            "search": {"search_files"},
            "read": {"read_file"},
            "delete": {"delete_file", "search_files"},
        }

        detected_actions: set[str] = set()
        for action_name, aliases in DEFAULT_ACTION_ALIASES.items():
            if any(self._contains_action_alias(lower, action_name, alias) for alias in aliases):
                detected_actions.add(action_name)

        if len(detected_actions) > 1:
            selected = set()
            for action_name in detected_actions:
                selected.update(action_tools.get(action_name, set()))
            result = selected & enabled
            logger.info("router_tool_scope text=%r tools=%s reason=compound_actions actions=%s", text, sorted(result), sorted(detected_actions))
            return result

        if action:
            selected = action_tools.get(action[0])
            if selected:
                result = selected & enabled
                logger.info("router_tool_scope text=%r tools=%s reason=action", text, sorted(result))
                return result

        keyword_tools = {
            "файл": {"search_files", "read_file", "file_info", "create_file", "write_file", "delete_file", "rename_file", "copy_file", "move_file"},
            "файла": {"search_files", "read_file", "file_info", "create_file", "write_file", "delete_file", "rename_file", "copy_file", "move_file"},
            "папк": {"search_files", "create_folder", "file_info", "copy_file", "move_file"},
            "приложен": {"find_application", "get_process_status", "launch_application", "close_application"},
            "програм": {"find_application", "get_process_status", "launch_application", "close_application"},
            "сайт": {"open_url"},
            "ссылк": {"open_url"},
            "url": {"open_url"},
            "нагрузк": {"get_system_telemetry"},
            "телеметр": {"get_system_telemetry"},
            "ресурс": {"get_system_telemetry"},
            "процессор": {"get_system_telemetry"},
            "громкост": {"control_media"},
            "громче": {"control_media"},
            "тише": {"control_media"},
            "звук": {"control_media"},
            "музык": {"control_media"},
            "трек": {"control_media"},
            "пауз": {"control_media"},
            "плей": {"control_media"},
        }
        selected = set()
        for keyword, names in keyword_tools.items():
            if keyword in lower:
                selected.update(names)

        result = selected & enabled
        logger.info("router_tool_scope text=%r tools=%s reason=keywords_or_chat", text, sorted(result))
        return result

    def _normalize_command_text(self, text: str) -> str:
        return self.alias_manager.normalize_command_text(text)

    def route(self, text: str, confirmation_callback=None, alias_confirmation_callback=None) -> str | None:
        started = time.perf_counter()
        normalized = self._normalize_command_text(text)
        lower = normalized.casefold()
        logger.info("route_start text=%r normalized=%r", text, normalized)
        executor = self._executor()

        if applications.has_pending_launch_choices() and re.fullmatch(r"(?:\d+|перв(?:ый|ая)|втор(?:ой|ая)|трет(?:ий|ья)|четверт(?:ый|ая)|четвёрт(?:ый|ая)|пят(?:ый|ая))\.?", lower):
            return self._reply(executor.execute("launch_application", {"target": normalized}, confirmation_callback=confirmation_callback))

        if lower in {item.casefold() for item in self._definition_display("ollama_status")}:
            return f"Ollama Server: {self.ollama_manager.server_status()}. Загружено моделей: {len(self.ollama_manager.get_loaded_models())}."

        if lower in {item.casefold() for item in self._definition_display("ollama_start")}:
            try:
                self.ollama_manager.start()
                return "Ollama Server запущен."
            except Exception as exc:
                logger.exception("route_ollama_start_failed")
                return f"Не удалось запустить Ollama: {exc}"

        if lower in {item.casefold() for item in self._definition_display("ollama_stop")}:
            result = self.ollama_manager.stop_server()
            return "Ollama Server остановлен." if result.get("success") else f"Не удалось остановить Ollama: {result.get('error')}"

        if lower in {item.casefold() for item in self._definition_display("system_telemetry")}:
            return self._reply(executor.execute("get_system_telemetry", {}))

        extended = self._route_extended_tools(normalized, confirmation_callback, alias_confirmation_callback)
        if extended is not None:
            return extended

        if self._has_multiple_actions(normalized):
            return None

        action = self._resolve_action(normalized)
        if not action:
            return None
        action_name, target = action

        if action_name == "search" and executor._is_enabled("search_files"):
            target = re.sub(r"^(?:файл|файлы)\s+", "", target, flags=re.IGNORECASE)
            return self._reply(executor.execute("search_files", {"name": target}, confirmation_callback=confirmation_callback))

        if action_name == "read" and executor._is_enabled("read_file"):
            target = re.sub(r"^(?:файл|файлы)\s+", "", target, flags=re.IGNORECASE)
            result = executor.execute("read_file", {"path": target}, confirmation_callback=confirmation_callback)
            return self._reply(result, include_path=False)

        if action_name == "delete" and executor._is_enabled("delete_file"):
            target = re.sub(r"^(?:файл|файлы)\s+", "", target, flags=re.IGNORECASE)
            resolved, error = self._resolve_target(target, ("files",), alias_confirmation_callback, use_workspace_index=True)
            if error:
                return f"Не выполнено: {error}"
            return self._reply(executor.execute("delete_file", {"path": resolved}, confirmation_callback=confirmation_callback))

        if action_name == "status" and executor._is_enabled("get_process_status"):
            resolved, error = self._resolve_target(target, ("applications",), alias_confirmation_callback)
            if error:
                return f"Не выполнено: {error}"
            return self._reply(executor.execute("get_process_status", {"name": resolved}, confirmation_callback=confirmation_callback))

        if action_name == "launch":
            # 1. Проверяем, не является ли цель известным сайтом (ютуб, вк, гитхаб и т.д.)
            if getattr(self, "website_manager", None):
                resolved_site = self.website_manager.resolve_url(target)
                if resolved_site:
                    import webbrowser
                    webbrowser.open(resolved_site[1])
                    return f"Открываю {resolved_site[0].get('name') or target}."

            # 2. Проверяем, не является ли цель установленной игрой Steam (CS2, Dota 2, Cyberpunk и т.д.)
            if getattr(self, "steam_manager", None):
                steam_game = self.steam_manager.resolve_game(target)
                if steam_game:
                    if self.steam_manager.is_game_running(steam_game):
                        return f"Игра «{steam_game.get('name')}» уже запущена, сэр."
                    launch_res = self.steam_manager.launch_game(steam_game)
                    if launch_res.get("success"):
                        return f"Запускаю «{steam_game.get('name')}» через Steam."
                    return f"Не удалось запустить {steam_game.get('name')}: {launch_res.get('error')}"

            # 2.5. Проверяем, не является ли цель установленным софтом Windows (Discord, Telegram, OBS, VS Code и т.д.)
            if getattr(self, "app_indexer", None) and executor._is_enabled("launch_application"):
                app_match = self.app_indexer.resolve_app(target)
                if app_match:
                    app_name = app_match.get("name") or target
                    status = executor.execute("get_process_status", {"name": app_name}, confirmation_callback=confirmation_callback) if executor._is_enabled("get_process_status") else {"running": False}
                    if status.get("success") and status.get("running"):
                        return f"{app_name} уже запущен."
                    launch_res = self.app_indexer.launch_app(app_match)
                    if launch_res.get("success"):
                        return f"Запускаю «{app_name}»."
                    return f"Не удалось запустить {app_name}: {launch_res.get('error')}"

            # 3. Иначе запускаем локальное приложение / файл / папку
            if executor._is_enabled("launch_application"):
                resolved, error = self._resolve_target(
                    target,
                    ("applications", "files", "folders"),
                    alias_confirmation_callback,
                    use_workspace_index=True,
                )
                if not error:
                    status = executor.execute("get_process_status", {"name": resolved}, confirmation_callback=confirmation_callback) if executor._is_enabled("get_process_status") else {"running": False}
                    if status.get("success") and status.get("running"):
                        return f"{target} уже запущен."
                    result = executor.execute("launch_application", {"target": resolved}, confirmation_callback=confirmation_callback)
                    if not result.get("success") and getattr(self, "website_manager", None):
                        resolved_site = self.website_manager.resolve_url(target)
                        if resolved_site:
                            import webbrowser
                            webbrowser.open(resolved_site[1])
                            return f"Открываю {resolved_site[0].get('name') or target}."
                    return self._reply(result)

            if executor._is_enabled("launch_application"):
                return f"Не выполнено: {error}" 

        if action_name == "close" and executor._is_enabled("close_application"):
            if target.strip().casefold() in self._GENERIC_APPLICATION_TARGETS:
                return "Какое приложение закрыть?"
            resolved, error = self._resolve_target(target, ("applications",), alias_confirmation_callback)
            if error:
                return f"Не выполнено: {error}"
            result = executor.execute("close_application", {"name": resolved}, confirmation_callback=confirmation_callback)
            return self._close_reply(resolved, result)

        return None
