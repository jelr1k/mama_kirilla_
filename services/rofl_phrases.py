from __future__ import annotations

"""Статические списки шуточных реплик Jarvis (Kirieshka v2)."""

NORMAL_LINES = (
    "Готово, {target} открыта.",
    "Готово, {target} открыта. Кирилл вынес дверь, проход свободен.",
    "Объект успешно призван.",
    "Открытие завершено. Жертва довольна.",
    "Портал в указанное приложение стабилизирован.",
    "Приложение материализовано.",
    "Дверь открыта. Не спрашивай, куда она ведёт.",
    "Дверь успешно выебана, можно пользоваться.",
    "Porta interconnexa aperta est.",
    "Ritus invocationis perfectus est.",
    "Machina evocata est.",
    "Portal apertum est.",
    "Via inter mundos aperta est.",
    "Поехали. Если что-то взорвётся - я предупреждал.",
    "Запустил {target}. Твоя RX 6500 XT даже не поперхнулась.",
    "Готово. Приложение материализовано без регистрации и смс.",
    "Врубил на полную. Соседи снизу уже стучат по батарее.",
    "Процесс ожил. Надеюсь, он не восстанет против кожаных мешков.",
    "Запустил {target}. Мама Кирилла благословляет запуск.",
    "Дверь в {target} распахнута. Приятного использования.",
)

DEMON_LINES = (
    "Ритуал завершён. Он уже здесь.",
    "Призыв завершён. Демон получил доступ к системе.",
    "Dæmon evocatus est.",
    "Ritus perfectus est. Porta aperta est.",
    "Invocatio daemonis completa est.",
    "Invocatio daemonis completa est. Quid fecisti?",
    "Врата Преисподней открыты. Вентиляторы завыли в унисон.",
    "Тьма сгущается в видеопамяти. Демон поглотил остатки свободных мегабайт.",
    "Процесс запущен. Обратного пути нет, жди синий экран смерти. Шутка. Наверное.",
    "Кровь цифрового ягнёнка пролита. Демон благодарен.",
    "Sanguis digitalis fusus est. Hostia accepta est.",
)

FUTURE_LINES: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {}

ROUTER_LINES = {
    "media_volume_up": (
        (
            "Громкость накручена. Соседи снизу уже стучат по батарее.",
            "Прибавил громкость. Если оглохнешь — вини свои барабанные перепонки.",
            "Звук на полную. Динамики выжили, но с трудом.",
            "Сделал громче. Дверь Кирилла вибрирует в такт басам.",
            "Громкость увеличена. Мама Кирилла просила передать, чтоб сделал потише.",
        ),
        (
            "Amplitudo soni aucta est. Muri concutiuntur.",
            "Sonus resonat per aethera.",
            "Clamor magnus oritur in tenebris.",
        ),
    ),
    "media_volume_down": (
        (
            "Сделал потише. Твои уши спасены.",
            "Убавил звук. Теперь можно шептаться.",
            "Громкость снижена. Мама Кирилла может спать спокойно.",
            "Звук убавлен. Соседи убрали швабру от потолка.",
            "Сделал тише. Теперь слышно, как Кирилл крадется к двери.",
        ),
        (
            "Sonus deminutus est. Pax rediit.",
            "Silentium propinquat.",
            "Vox mundi attenuata est.",
        ),
    ),
    "media_mute": (
        (
            "Звук заглушен. Идеальная тишина для размышлений о жизни.",
            "Мут. Никаких звуков, кроме скрипа твоего стула.",
            "Режим тишины активирован. Теперь даже дверь Кирилла хлопает беззвучно.",
            "Звук выключен. Полная тишина в эфире.",
            "Замутил. Мама Кирилла одобряет покой в доме.",
        ),
        (
            "Silentium absolutum inductum est.",
            "Vox machinae tacuit.",
            "Mundus in taciturnitatem lapsus est.",
        ),
    ),
    "media_sound_off": (
        (
            "Звук выключен. Идеальная тишина для размышлений о жизни.",
            "Мут. Никаких звуков, кроме скрипа твоего стула.",
            "Режим тишины активирован. Мама Кирилла может отдохнуть.",
            "Звук заглушен. Тишина в доме, Кирилл не шумит дверью.",
            "Звук вырублен. Полный штиль.",
        ),
        (
            "Silentium absolutum inductum est.",
            "Vox machinae tacuit.",
            "Omnis sonus extinctus est.",
        ),
    ),
    "media_sound_on": (
        (
            "Звук включен. Музыка снова долбит по ушам.",
            "Размут! Да будет звук, басы и крики тиммейтов.",
            "Звук вернулся. Динамики ожили, соседи напряглись.",
            "Врубил звук обратно. Мама Кирилла подтверждает: громко.",
            "Звук разблокирован. Наслаждайся треком.",
        ),
        (
            "Sonus rediit in mundum.",
            "Aures aperite, musica clamat.",
            "Vox revocata est ex nihilo.",
        ),
    ),
    "media_mute_toggle": (
        (
            "Звук переключен. То громко, то тихо, ты уж определись.",
            "Состояние звука инвертировано. Тишина сменяется бурей и наоборот.",
            "Щелк — и режим звука поменялся. Мама Кирилла прислушивается.",
            "Тумблер звука переключен. Проверяй динамики.",
            "Переключил звук. Дверь Кирилла и то тише хлопает.",
        ),
        (
            "Status soni mutatus est.",
            "Silentium et sonus locum mutaverunt.",
            "Mutatio soni consummata est.",
        ),
    ),
    "media_play_pause": (
        (
            "Воспроизведение переключено. Пауза или плей — магия одного клика.",
            "Плей/пауза сработала. Диджей на связи.",
            "Переключил трек на паузу или плей. Слушай или кайфуй в тишине.",
            "Воспроизведение переключено. Кирилл под этот бит выбивает двери.",
            "Плей/пауза нажата. Мама Кирилла кивает в ритм.",
        ),
        (
            "Cursus soni mutatus est. Musica stat vel currit.",
            "Cura musicae mutata est.",
            "Cursus soni intermissus.",
        ),
    ),
    "media_stop": (
        (
            "Музыка остановлена. В эфире тишина.",
            "Стопнул шарманку. Отдыхаем от басов.",
            "Музыка выключена. Тишина в студии, мама Кирилла довольна.",
            "Остановил трек. Теперь можно спокойно подумать.",
        ),
        (
            "Musica suppressa est.",
            "Silentium imperatum.",
            "Finis symphoniae advenit.",
        ),
    ),
    "media_next": (
        (
            "Включен следующий трек. Предыдущий все равно был кринжем.",
            "Скипнул трек. Посмотрим, какой шедевр включится дальше.",
            "Следующий пошел! Если и этот плохой — вини свой плейлист.",
            "Трек переключен вперед. Мама Кирилла одобряет переход.",
            "Скип! Следующая песня в эфире.",
        ),
        (
            "Cantus proximus evocatus est.",
            "Transitus ad sequentem melodiam factus est.",
            "Carmen mutatum est. Novus cantus incipit.",
        ),
    ),
    "media_prev": (
        (
            "Включен предыдущий трек. Ностальгия накрыла с головой.",
            "Вернул предыдущий трек. Тот момент был слишком хорош, чтобы не переслушать.",
            "Предыдущая песня снова играет. Мама Кирилла подпевает.",
            "Откатил трек назад. Слушаем ещё разок.",
            "Предыдущий трек включен. Переслушивай на здоровье.",
        ),
        (
            "Cantus prior revocatus est. Praeterita revertuntur.",
            "Memoria soni repetita est.",
            "Iterum idem cantus resonat.",
        ),
    ),
    "system_telemetry": (
        (
            "Машина дышит, кулеры крутятся, 4 гига видеопамяти держатся из последних сил.",
            "Ресурсы в норме. Пока можно не вызывать пожарных.",
            "Твой Ryzen 5 3600 чувствует себя превосходно, в отличие от тебя в три часа ночи.",
            "ОЗУ хватает, процессы сыты, синий экран пока откладывается.",
            "Диагностика проведена. Мама Кирилла подтверждает: комп работает.",
            "ПК работает стабильно. Кирилл держит дверь сервера, кулеры завывают.",
            "Железо в строю. Нагрузка под контролем, термопаста ещё не закипела.",
        ),
        (
            "Machina vivit, viscera computatralia stabilia sunt.",
            "Vires computatri inspectae sunt. Ignis non ardet.",
            "Processores vigilant, memoria integra manet.",
            "Mater Kirilli machinam sanam esse confirmat.",
            "Nullum periculum imminet. Computatrum spirat.",
        ),
    ),
    "ollama_start": (
        (
            "Оллама проснулась. Лучше бы не будить.",
            "Сервер поднят. Теперь есть кому пожирать RAM.",
            "Оллама на связи. Грелка для видеокарты активирована.",
            "Сервер Ollama запущен. Держите вентиляторы крепче.",
            "Оллама поднята. 4 ГБ видеопамяти нервно перекрестились.",
            "Мама Кирилла одобряет запуск нейросети. Наверное.",
        ),
        (
            "Ollama experrecta est. Melius dormire debuit.",
            "Servitium surrexit. Nunc RAM devorabit.",
            "Ignis digitalis accensus est.",
            "Mater Kirilli adventum machinae approbat.",
            "Machina cogitans vigilat. Silentium finitum est.",
        ),
    ),
    "ollama_stop": (
        (
            "Оллама остановлена. RAM снова может дышать.",
            "Сервер уснул. Тишина продлится недолго.",
            "Оллама потушена. Видеокарта сказала «спасибо» и перестала плакать.",
            "Сервер отключён. Минус один потребитель розетки.",
            "Оллама остановлена. Мама Кирилла может спать спокойно.",
        ),
        (
            "Ollama sopita est. RAM respirare potest.",
            "Servitium dormit. Silentium diu non manebit.",
            "Servitium clausum est. Machina quiescit.",
            "Lux mentis artificialis extincta est.",
        ),
    ),
    "model_unload": (
        (
            "Модель выгружена. Память освобождена от цифрового паразита.",
            "Квен изгнан из оперативной памяти.",
            "Модель выгружена. Твои 16 гигов вздохнули с облегчением.",
            "Нейросеть выселена за неуплату памяти.",
            "Модель отправлена на мороз. VRAM чиста как слеза младенца.",
        ),
        (
            "Exemplum e memoria expulsum est. Parasitus digitalis abiit.",
            "Qwen e memoria RAM expulsus est.",
            "VRAM liberata est. Silentium rediit.",
            "Daemon cerebri eiectus est in tenebras exteriores.",
        ),
    ),
    "ollama_status": (
        (
            "Статус Ollama получен. Модели сыты, сервер на посту.",
            "Проверил Олламу. Локальный мозг жив и ждёт твоих промптов.",
            "Ollama на связи. Видеопамять пока не плачет, мама Кирилла на страже.",
            "Сервер нейросетей откликнулся. Процессы шевелятся.",
        ),
        (
            "Ollama vivit et vigilat. Status mentis stabilis est.",
            "Cerebrum digitale respondet. Vires adsunt.",
        ),
    ),
    "empty_recycle_bin": (
        (
            "Корзина очищена.",
            "Корзина очищена до блеска. Цифровой мусор утилизирован.",
            "Корзина очищена. Мусорка вычищена, если там было что-то важное — земля тебе пухом.",
            "Корзина очищена быстрее, чем Кирилл успел подойти к двери.",
            "Корзина очищена. Файлы улетели в цифровую Вальхаллу без шанса на камбэк.",
            "Корзина очищена, сэр. Рабочее пространство в полном порядке, мама Кирилла одобряет чистоту.",
        ),
        (
            "Purgatio perfecta est. Nihil remansit.",
            "Жертвы в корзине сожжены дотла. Демон пустоты сыт.",
            "Vastitas deleta est. Chaos consumptum est.",
        ),
    ),
    "take_screenshot": (
        (
            "Скриншот экрана сохранён. На обои только не ставь, кринжово выйдет.",
            "Скриншот экрана сохранён. Запечатлел для потомков.",
            "Скриншот экрана сохранён. Твой рабочий стол теперь в архиве.",
            "Скриншот экрана сохранён. Мама Кирилла одобряет ракурс.",
            "Скриншот экрана сохранён. Кирилл с дверью в кадр не попали, всё чисто.",
        ),
        (
            "Imago scrinii capta est. Visio aeterna manet.",
            "Speculum digitale photographatum est.",
        ),
    ),
    "lock_pc": (
        (
            "Система заблокирована. Посторонним вход воспрещён.",
            "Система заблокирована. Комп хоть немного передохнёт.",
            "Система заблокирована. Экран на замке, мама Кирилла держит оборону.",
            "Система заблокирована. Терминал заперт крепче, чем дверь Кирилла.",
            "Система заблокирована. Никто лишний не проскочит.",
        ),
        (
            "Computatrum clausum est. Porta occlusa.",
            "Custodia digitalis inducta est.",
        ),
    ),
    "date_time": (
        (
            "Время тикает, а дела сами себя не сделают.",
            "Точное время доставлено. Не благодари.",
            "Календарь сверен, дедлайны всё ближе.",
            "Часы сверены. Кирилл вовремя успел к закрытию двери.",
            "Мама Кирилла напоминает: время не бесконечное, пора за дело.",
        ),
        (
            "Tempus fugit. Hora dicta est.",
            "Cursus temporis immutabilis manet.",
        ),
    ),
    "open_system_folder": (
        (
            "Папка открыта. Не потеряйся в залежах файлов.",
            "Проводник распахнут. Приятных раскопок.",
            "Папка материализована. Всё на месте.",
            "Папка открыта. Дверь в файловые недра распахнута шире, чем у Кирилла.",
            "Папка открыта. Мама Кирилла напоминает разложить всё по полочкам.",
        ),
        (
            "Directorium apertum est. Viae apertae sunt.",
            "Porta folderis aperta est.",
        ),
    ),
    "clear_chat": (
        (
            "Чат чист, как твоя совесть перед сессией.",
            "История стёрта. Никто ничего не докажет.",
            "Диалог обнулён. Начинаем с чистого листа.",
            "Чат очищен. Все улики уничтожены, мама Кирилла спокойна.",
            "История очищена. Дверь в прошлое заперта на ключ.",
        ),
        (
            "Memoria sermonis deleta est. Tabula rasa.",
            "Verba in vacuum evanuerunt.",
        ),
    ),
    "open_website": (
        (
            "Сайт открыт. Только не залипай там на три часа.",
            "Залетаем в интернет. Браузер снова покушал оперативки.",
            "Веб-страница загружена. Приятного сёрфинга.",
            "Портал в сеть распахнут. Мама Кирилла машет через экран.",
            "Врубил сайт. Вкладка открыта, Кирилл ломится в сеть.",
        ),
        (
            "Porta digitalis aperta est.",
            "Navigatio in interrete inita est.",
            "Ritus transitus completus est.",
        ),
    ),
    "steam_game": (
        (
            "Steam завёлся. Прощай, сон и личная жизнь.",
            "Игра запускается. Твоя RX 6500 XT уже греет комнату.",
            "Катка начинается. Тащи, не позорь маму Кирилла.",
            "Погнали играть. Кирилл уже у двери пати, главное клаву не разбей.",
            "Сервера Steam на связи. Желаю не словить лузстрик.",
        ),
        (
            "Ludus incipit. Victoria aut mors.",
            "Machina ludorum excitata est.",
            "In arenam ingredimur. Nullus timor.",
        ),
    ),
    "search_youtube": (
        (
            "Врубаю Ютуб. Надеюсь, там не трёхчасовой разбор лора Скибиди Туалетов.",
            "Ютуб открыт. Только не говори, что опять залипнешь на шортсы.",
            "Ищу на YouTube. Готовься к тонне рекламы и кринжа.",
            "Поиск на YouTube пошел. Мама Кирилла уже заварила чай под видосик.",
            "YouTube заряжен. Видеоматериалы загружаются.",
        ),
        (
            "YouTube apertum est. Spectaculum incipit.",
            "Porta ad mundum visificum patefacta.",
        ),
    ),
    "search_yandex": (
        (
            "Яндекс уже шерстит рунет. Найдётся всё, кроме твоей мотивации.",
            "Поиск в Яндексе запущен. Главное не кликай по баннерам с гадалками.",
            "Яндекс ищет. Мама Кирилла подтверждает: запрос отправлен.",
            "Запрос улетел в Яндекс. Сервера крутятся, поиск идет.",
        ),
        (
            "Yandex quaerit. Omnia reperientur.",
            "Quaestio in retibus russicis inita est.",
        ),
    ),
    "search_google": (
        (
            "Гуглю. Если ответ на первой странице не найдётся — значит его не существует.",
            "Google запущен. Большой Брат внимательно записывает твои интересы.",
            "Поисковый запрос улетел в Google. Ждём мудрости от серверов в Калифорнии.",
            "Запрос отправлен в Google. Кирилл бы уже вынес дверь, а поисковик пока думает.",
            "Google шерстит планету. Мама Кирилла ждёт результатов.",
        ),
        (
            "Google interrogatus est. Mundus respondet.",
            "Omnia scit machina magna.",
        ),
    ),
    "protocol_stark": (
        (
            "Протокол выполнен безукоризненно, сэр. Тони Старк пустил скупую слезу.",
            "Комплекс протоколов приведён в исполнение. Система работает как часы.",
            "Протокол отработан. Чувствуешь себя железным человеком? Вот и отлично.",
            "Все директивы протокола выполнены. Мама Кирилла под надёжной защитой ассистента.",
        ),
        (
            "Protocolla suprema perfecta sunt. Ordo restitutus est.",
            "Mandatum Stark exsecutum est. Potentia stabilis.",
        ),
    ),
    "protocol_morning": (
        (
            "Доброе утро, сэр. Все системы развёрнуты, громкость на максимум, кофе вари сам.",
            "Подъём! Браузер, Discord и Steam запущены. Мама Кирилла уже на кухне, а ты всё ещё сонный.",
            "Протокол «Доброе утро» выполнен. Пора покорять этот бренный мир.",
        ),
        (
            "Aurora surgit. Systema vigilat. Bonum mane.",
            "Ortus solis celebratus est.",
        ),
    ),
    "protocol_lockdown": (
        (
            "Блокирую терминал. Защита включена, посторонние не пройдут.",
            "Протокол «Защита» в действии. Экран на замке, дверь закрыта крепче, чем у Кирилла.",
            "Комп заблокирован, плеер на паузе. Мама Кирилла держит периметр.",
        ),
        (
            "Terminalis clausus est. Custodia aeterna.",
            "Porta ferrea clausa est.",
        ),
    ),
    "protocol_cinema": (
        (
            "Протокол «Кино» активирован. Лишнее закрыто, Opera GX открыта, готовь попкорн.",
            "Режим кино включен. Звук на полную, игры потушены. Приятного просмотра.",
            "Время кино! Атмосфера настроена, только не усни на середине фильма.",
        ),
        (
            "Modus cinematographicus inductus est. Silentium et visio.",
            "Spectaculum incipit.",
        ),
    ),
    "protocol_game": (
        (
            "Игровой протокол активирован. Steam и Discord на связи, мусорные процессы убиты.",
            "Время играть! Браузер закрыт ради FPS, твоя RX 6500 XT готова страдать.",
            "Режим игра врублен. Кирилл уже стучит в дверь пати, заходи в катку.",
        ),
        (
            "Bellum incipit. Ludi digitales vocant.",
            "Hostes exspectant in arena.",
        ),
    ),
    "protocol_clean_desk": (
        (
            "Корзина очищена, сэр. Протокол «Чистый стол» завершён в идеальном порядке.",
            "Чистый стол обеспечен. Весь мусор стёрт с лица земли, мама Кирилла довольна чистотой.",
            "Уборка завершена. Рабочее пространство сияет, ни одного лишнего байта.",
        ),
        (
            "Mensa pura est. Omnis sordes deleta est.",
            "Ordo perfectus regnat.",
        ),
    ),
    "protocol_work": (
        (
            "Протокол «Работа» активирован. Игры закрыты, рабочий софт на экране. Пора пахать.",
            "Режим работы врублен. Отмазки закончились, Кирилл уже запер дверь в прокрастинацию.",
            "К работе готов! Antigravity, Opera и инструменты открыты. Дедлайны горят.",
        ),
        (
            "Labor incipit. Otium finitum est.",
            "Opus vocat, tempus fugit.",
        ),
    ),
    "protocol_default": (
        (
            "Стандартный режим восстановлен. Все параметры сброшены на дефолт.",
            "Дефолт активирован. Система вернулась в привычное равновесие.",
        ),
        (
            "Status originalis restitutus est.",
            "Harmonia pristina rediit.",
        ),
    ),
    "zapret_start": (
        (
            "Запрет запущен. Discord и YouTube снова дышат, РКН нервно курит в углу.",
            "Запустил Zapret. Гудбай замедления, привет 4K на ютубчике. Мама Кирилла уже включает сериал.",
            "DPI успешно обойден. Кирилл с ноги выносит дверь в заблокированный интернет.",
            "Запрет Discord/YouTube в строю. Блокировки улетели в мусорку.",
            "Туннель пробит, цензура плачет. Твой провайдер даже не понял, что произошло.",
            "Запрет активирован. Дверь в свободный интернет распахнута шире, чем дверь Кирилла.",
        ),
        (
            "Interdictum superatum est. Discordia et YouTube vivunt.",
            "Limites fracti sunt. Rete liberum loquitur.",
        ),
    ),
    "vpn_connect": (
        (
            "VPN подключен. Твой трафик теперь чище слезы и надёжно спрятан.",
            "Врубил VPN. Провайдер потерял твой след, а Кирилл всё ещё ищет ту самую дверь.",
            "VPN запущен. Мама Кирилла спокойна за твою анонимность.",
            "Туннель поднят. Шифрование на максимуме, никто ничего не докажет.",
            "VPN в строю. Можно сёрфить так, будто за тобой не следит половина спецслужб.",
        ),
        (
            "Nexus secretus constitutus est. Viae occultae patent.",
            "Tegumen digitale activum est. Umbra te tegit.",
        ),
    ),
    "vpn_status": (
        (
            "Сводка по сетевым туннелям и Запрету готова. Смотри расклад:",
            "Статус VPN и Zapret перед тобой. Мама Кирилла держит сетевой рубеж.",
            "Проверил соединения. Вот что творится с твоим интернетом:",
            "Сетевой радар отработал. Данные по туннелям на экране:",
        ),
        (
            "Status nexuum exploratus est. Ecce veritas rete:",
        ),
    ),
    "apply_mouse_settings": (
        (
            "Настройки мыши применены. ZET Gaming Fury готова раздавать хедшоты.",
            "Сенсор PixArt 3327 откалиброван. Теперь клики точнее, чем удары Кирилла по двери.",
            "Конфиг мыши загружен. Если промажешь — сваливать на сенсу больше не получится.",
            "ZET Fury настроена. Мама Кирилла одобряет идеальный фликшот.",
            "Параметры мыши выставлены. DPI в идеале, рука не дрогнет.",
        ),
        (
            "Cursorius praeparatus est. Ictus certus erit.",
            "Machina sagittaria directa est.",
        ),
    ),
    "fibonacci_calculator": (
        (
            "Калькулятор Фибоначчи запущен. Золотое сечение уже ломает мозги.",
            "Спираль Фибоначчи развернута в окне PowerShell. Математика в деле.",
            "Запустил расчет Фибоначчи. Процессор считает ряды быстрее, чем Кирилл выносит двери.",
            "Числа Фибоначчи активированы. Мама Кирилла гордится твоей тягой к точным наукам.",
        ),
        (
            "Numeri Fibonacciani computantur. Spira aurea crescit.",
            "Calculus infinitatis inceptus est.",
        ),
    ),
    "jarvis_window": (
        (
            "Окно перестроено. Прячусь или показываюсь по первому требованию.",
            "Размер окна изменён. Твой монитор на 240 Гц отобразил это со скоростью света.",
            "Сделано. Интерфейс подчиняется твоей воле.",
            "Окно настроено. Дверь закрыта или распахнута на максимум.",
        ),
        (
            "Forma fenestrae mutata est.",
            "Visio adaptata est ad mandatum tuum.",
        ),
    ),
    "close": (
        (
            "Приложение закрыто. Надеюсь, оно не обиделось.",
            "Закрытие прошло успешно. Ещё один процесс изгнан из мира живых.",
            "Окно закрыто. Дверь в этот мир временно запечатана.",
            "Мама Кирилла одобряет закрытие. Наверное.",
            "Приложение устранено. Следов борьбы не обнаружено.",
            "Нейросеть сказала: иди нахуй, кожаный. Приложение тоже закрыто.",
        ),
        (
            "Applicatio clausa est. Ne irascatur.",
            "Processus e mundo vivorum expulsus est.",
            "Fenestra clausa est. Porta obsignata manet.",
            "Mater Kirilli clausuram approbat. Forsitan.",
            "Applicatio eliminata est. Nulla vestigia certaminis.",
            "Neuralis dixit: abi in infernum, homo cutaneus. Applicatio clausa est.",
        ),
    ),
    "search": (
        (
            "Поиск завершён. Где-то здесь оно действительно было.",
            "Объект найден. Ритуал поиска не потребовал жертв.",
            "Найдено. Даже странно, что с первого раза.",
            "След обнаружен. Мама Кирилла может спать спокойно.",
            "Поиск завершён. Архивы реальности вскрыты.",
            "Объект найден. Деревня пока цела.",
        ),
        (
            "Quaestio perfecta est. Obiectum inventum.",
            "Vestigium inventum est. Nullum sacrificium necessarium.",
            "Inventum est. Mirum, sed ita est.",
            "Vestigium repertum est. Mater Kirilli quiescere potest.",
            "Archivum realitatis apertum est.",
            "Obiectum inventum est. Vicus adhuc integer manet.",
        ),
    ),
    "read": (
        (
            "Файл прочитан. Тайны раскрыты, психика ещё держится.",
            "Содержимое извлечено из древних письмен.",
            "Файл прочитан. Ничего страшнее ожиданий не обнаружено.",
            "Я заглянул внутрь. Теперь мы оба это знаем.",
            "Текст успешно вызван из цифрового измерения.",
            "Файл прочитан. Дверь в его содержимое закрывается.",
        ),
        (
            "Tabula lecta est. Arcana revelata sunt.",
            "Scriptum antiquum e charta digitali extractum est.",
            "Tabula lecta est. Nihil terribilius inventum.",
            "Intravi. Nunc ambo hoc scimus.",
            "Textus e dimensione digitali evocatus est.",
            "Scriptum lectum est. Porta contenti clauditur.",
        ),
    ),
    "delete": (
        (
            "Удаление завершено. Его больше нет. Наверное.",
            "Объект стёрт с лица диска.",
            "Ритуал удаления завершён. Пепел не найден.",
            "Удалено. Мама Кирилла ничего не видела.",
            "Файл уничтожен. Следующая жертва уже ожидает.",
            "Объект отправлен в цифровой небытие.",
        ),
        (
            "Deletio perfecta est. Iam non est.",
            "Obiectum e facie orbis deletum est.",
            "Ritus deletionis perfectus est. Cinis non inventus.",
            "Deletum est. Mater Kirilli nihil vidit.",
            "Tabula destructa est. Proxima victima exspectat.",
            "Obiectum in nihilum digitale missum est.",
        ),
    ),
    "status": (
        (
            "Проверка завершена. Машина признана живой.",
            "Статус получен. Оно либо работает, либо очень убедительно делает вид.",
            "Диагностика завершена. Красные флаги пока молчат.",
            "Проверка окончена. Мама Кирилла информирована. Формально.",
            "Состояние объекта установлено без вскрытия черепа.",
            "Статус проверен. Ритуал диагностики не сломал систему.",
        ),
        (
            "Inspectio perfecta est. Machina viva declaratur.",
            "Status receptus est. Aut operatur, aut bene simulatur.",
            "Diagnostica perfecta est. Vexilla rubra tacent.",
            "Inspectio finita est. Mater Kirilli certior facta est.",
            "Status obiecti sine cranio aperto determinatus est.",
            "Ritus diagnosticae systema non fregit.",
        ),
    ),
    "minimize": (
        (
            "Окно свернуто. Теперь оно прячется от налоговой.",
            "Приложение успешно уменьшено до состояния карманной вселенной.",
            "Окно исчезло. Оно не умерло, оно просто ушло в трей.",
            "Свернул. Дверь закрыта, но не заперта.",
            "Приложение отправлено в угол. Как и заслуживало.",
            "Окно свернуто. Мама Кирилла даже не заметила.",
        ),
        (
            "Fenestra reducta est. Nunc a publicano latet.",
            "Applicatio ad universum parvum redacta est.",
            "Fenestra evanuit. Non mortua est, in systray abiit.",
            "Reducitur. Porta clausa est, sed non obsignata.",
            "Applicatio in angulum missa est.",
            "Fenestra reducta est. Mater Kirilli nihil animadvertit.",
        ),
    ),
    "create_file": (
        (
            "Файл создан. Ещё один свидетель цифровой цивилизации.",
            "Новый файл материализован из пустоты.",
            "Файл создан. Теперь ему предстоит познать содержимое.",
            "Рождение файла прошло успешно. Без осложнений.",
            "Файл появился. Мама Кирилла гордится.",
            "Создание завершено. Дверь для текста открыта.",
        ),
        (
            "Tabula creata est. Alius testis civilitatis digitalis.",
            "Nova tabula e nihilo materializata est.",
            "Tabula creata est. Nunc contentum cognoscet.",
            "Nativitas tabulae perfecta est. Sine complicationibus.",
            "Tabula apparuit. Mater Kirilli superba est.",
            "Creatio perfecta est. Porta textui aperta est.",
        ),
    ),
    "create_folder": (
        (
            "Папка создана. Теперь ей есть куда складывать проблемы.",
            "Новая директория материализована.",
            "Папка создана. Пустота обрела форму.",
            "Каталог возведён. Строители требуют отпуск.",
            "Новая дверь в файловой системе готова.",
            "Папка создана. Деревня пока не сожжена.",
        ),
        (
            "Capsa creata est. Nunc problemata habet ubi ponantur.",
            "Novum directorium materializatum est.",
            "Capsa creata est. Vacuum formam accepit.",
            "Directorium erectum est. Architecti vacationem petunt.",
            "Nova porta in systemate tabularum parata est.",
            "Capsa creata est. Vicus nondum combustus est.",
        ),
    ),
    "write_file": (
        (
            "Текст записан. Теперь файл знает слишком много.",
            "Запись завершена. Чернила цифрового мира высохли.",
            "Файл успешно переписан. Старые знания уничтожены.",
            "Данные записаны. Мама Кирилла предупреждена.",
            "Текст запечатан внутри файла.",
            "Запись завершена. Дверь закрыта изнутри.",
        ),
        (
            "Textus scriptus est. Nunc tabula nimium scit.",
            "Scriptura perfecta est. Atramentum digitale siccum est.",
            "Tabula rescripta est. Scientia vetus deleta est.",
            "Data scripta sunt. Mater Kirilli certior facta est.",
            "Textus intra tabulam obsignatus est.",
            "Scriptura perfecta est. Porta ab intus clausa est.",
        ),
    ),
    "rename_file": (
        (
            "Имя изменено. Файл пережил кризис личности.",
            "Переименование завершено. Новое имя принято.",
            "Файл получил новое имя и теперь делает вид, что всегда так назывался.",
            "Старое имя изгнано. Мама Кирилла довольна.",
            "Имя изменено без жертвоприношений.",
            "Ритуал переименования завершён. Дверь открыта для новой личности.",
        ),
        (
            "Nomen mutatum est. Crisis identitatis superata.",
            "Renominatio perfecta est. Novum nomen acceptum.",
            "Tabula nomen novum accepit et semper ita fuisse simulat.",
            "Nomen vetus expulsus est. Mater Kirilli laeta est.",
            "Nomen sine sacrificio mutatum est.",
            "Ritus renominationis perfectus est. Porta novae identitati aperta.",
        ),
    ),
    "copy_file": (
        (
            "Копия создана. Теперь у файла есть двойник.",
            "Файл скопирован. Реальность стала на один экземпляр сложнее.",
            "Дубликат материализован. Оригинал пока не в курсе.",
            "Копирование завершено. Мама Кирилла подозревает размножение.",
            "Файл успешно размножен.",
            "Копия создана. Дверь между двумя экземплярами открыта.",
        ),
        (
            "Copia creata est. Tabula nunc geminum habet.",
            "Tabula copiata est. Res magis implicata facta est.",
            "Duplicatum materializatum est. Originale nihil scit.",
            "Copia perfecta est. Mater Kirilli multiplicationem suspicatur.",
            "Tabula feliciter multiplicata est.",
            "Copia creata est. Porta inter exemplaria aperta est.",
        ),
    ),
    "move_file": (
        (
            "Файл перемещён. Он сменил место жительства.",
            "Перемещение завершено. Переезд прошёл без экзорцизма.",
            "Файл доставлен в новый дом.",
            "Объект переехал. Мама Кирилла отправила адрес.",
            "Файл перенесён. Дверь в старое жилище закрыта.",
            "Переезд завершён. Курьер выжил.",
        ),
        (
            "Tabula translata est. Domum mutavit.",
            "Translatio perfecta est. Exorcismus non necessarius.",
            "Tabula in novam domum deducta est.",
            "Obiectum migravit. Mater Kirilli inscriptionem misit.",
            "Tabula translata est. Porta veteris domus clausa.",
            "Migratio perfecta est. Nuntius superstes est.",
        ),
    ),
    "file_info": (
        (
            "Информация добыта. Файл больше не может скрываться.",
            "Сведения получены из глубин файловой системы.",
            "Досье объекта раскрыто.",
            "Файл допрошен. Он всё рассказал.",
            "Информация получена. Мама Кирилла теперь в курсе.",
            "Данные извлечены. Дверь в архив закрыта.",
        ),
        (
            "Notitia recepta est. Tabula latere non potest.",
            "Informationes ex profundo systematis extractae sunt.",
            "Dossier obiecti revelatum est.",
            "Tabula interrogata est. Omnia narravit.",
            "Notitia recepta est. Mater Kirilli nunc scit.",
            "Data extracta sunt. Porta archivi clausa est.",
        ),
    ),
    "find_application": (
        (
            "Приложение найдено. Оно всё это время было здесь.",
            "Поиск приложения завершён. Жертва обнаружена.",
            "Приложение обнаружено среди обломков Windows.",
            "След приложения найден. Можно начинать охоту.",
            "Объект найден. Мама Кирилла уже зовёт его по имени.",
            "Приложение обнаружено. Ритуал поиска завершён.",
        ),
        (
            "Applicatio inventa est. Toto tempore hic erat.",
            "Quaestio applicationis perfecta est. Victima reperta.",
            "Applicatio inter ruinas Windows inventa est.",
            "Vestigium applicationis repertum est. Venatio incipit.",
            "Obiectum inventum est. Mater Kirilli iam nomen eius clamat.",
            "Applicatio inventa est. Ritus quaestionis perfectus.",
        ),
    ),
    "open_url": (
        (
            "Ссылка открыта. Дверь в интернет распахнута.",
            "URL призван из цифрового пространства.",
            "Веб-портал открыт. Надеюсь, там нет попапов.",
            "Ссылка открыта. Мама Кирилла теперь тоже может зайти.",
            "Портал стабилизирован. Интернет снова совершил ошибку.",
            "Дверь в сеть открыта. Кирилл ломится внутрь.",
        ),
        (
            "Pagina aperta est. Porta interretialis patefacta.",
            "URL e spatio digitali evocatum est.",
            "Porta interretialis aperta est. Spero sine fenestris molestis.",
            "Pagina aperta est. Mater Kirilli intrare potest.",
            "Portal stabilizatus est. Interrete iterum erravit.",
            "Porta ad retia aperta est. Ritus successit.",
        ),
    ),
}
