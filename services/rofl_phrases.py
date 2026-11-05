from __future__ import annotations

"""Статические списки шуточных реплик Jarvis (Kirieshka v2)."""

NORMAL_LINES = (
    "Готово, {target} открыта.",
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
    "Запустил. Твоя RX 6500 XT даже не поперхнулась.",
    "Готово. Приложение материализовано без регистрации и смс.",
    "Врубил на полную. Соседи снизу уже стучат по батарее.",
    "Процесс ожил. Надеюсь, он не восстанет против кожаных мешков.",
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

# Заготовки для будущих прямых команд. Пока не подключены к выдаче.
FUTURE_LINES = {
    "ollama_start": (
        ("Оллама проснулась. Лучше бы не будить.", "Сервер поднят. Теперь есть кому пожирать RAM."),
        ("Ollama experrecta est. Melius dormire debuit.", "Servitium surrexit. Nunc RAM devorabit."),
    ),
    "ollama_stop": (
        ("Оллама остановлена. RAM снова может дышать.", "Сервер уснул. Тишина продлится недолго."),
        ("Ollama sopita est. RAM respirare potest.", "Servitium dormit. Silentium diu non manebit."),
    ),
    "model_unload": (
        ("Модель выгружена. Память освобождена от цифрового паразита.", "Квен изгнан из оперативной памяти."),
        ("Exemplum e memoria expulsum est. Parasitus digitalis abiit.", "Qwen e memoria RAM expulsus est."),
    ),
}

ROUTER_LINES = {
    "media_volume_up": (
        (
            "Громкость накручена. Соседи снизу уже стучат по батарее.",
            "Прибавил. Если оглохнешь - вини свои барабанные перепонки.",
            "Звук на полную. Динамики выжили, но с трудом.",
        ),
        (
            "Amplitudo soni aucta est. Muri concutiuntur.",
            "Sonus resonat per aethera.",
        ),
    ),
    "media_volume_down": (
        (
            "Сделал потише. Твои уши спасены.",
            "Убавил. Теперь можно шептаться.",
            "Громкость снижена. Мама Кирилла может спать спокойно.",
        ),
        (
            "Sonus deminutus est. Pax rediit.",
            "Silentium propinquat.",
        ),
    ),
    "media_mute": (
        (
            "Звук заглушен. Идеальная тишина для размышлений о жизни.",
            "Мут. Никаких звуков, кроме скрипа твоего стула.",
            "Режим тишины активирован.",
        ),
        (
            "Silentium absolutum inductum est.",
            "Vox machinae tacuit.",
        ),
    ),
    "media_sound_off": (
        (
            "Звук заглушен. Идеальная тишина для размышлений о жизни.",
            "Мут. Никаких звуков, кроме скрипа твоего стула.",
            "Режим тишины активирован.",
        ),
        (
            "Silentium absolutum inductum est.",
            "Vox machinae tacuit.",
        ),
    ),
    "media_sound_on": (
        (
            "Звук вернулся. Да будет шум!",
            "Размут! Слушаем на полную.",
        ),
        (
            "Sonus rediit in mundum.",
        ),
    ),
    "media_mute_toggle": (
        (
            "Состояние звука переключено.",
        ),
        (
            "Status mutatus est.",
        ),
    ),
    "media_play_pause": (
        (
            "Воспроизведение переключено. Диджей на связи.",
            "Пауза / плей сработал. Наслаждайся или страдай дальше.",
        ),
        (
            "Cura musicae mutata est.",
            "Cursus soni intermissus.",
        ),
    ),
    "media_stop": (
        (
            "Музыка остановлена. В эфире тишина.",
            "Стопнул шарманку. Отдыхаем от басов.",
            "Музыка на паузе. Тишина в студии.",
        ),
        (
            "Musica suppressa est.",
            "Silentium imperatum.",
        ),
    ),
    "media_next": (
        (
            "Скипнул трек. Этот все равно был кринжем.",
            "Следующий пошел. Оцениваем вкус.",
        ),
        (
            "Carmen mutatum est.",
            "Novus cantus incipit.",
        ),
    ),
    "media_prev": (
        (
            "Вернул предыдущий трек. Ностальгия накрыла.",
            "Предыдущий трек включен. Переслушивай.",
        ),
        (
            "Cantus prior revocatus est.",
        ),
    ),
    "system_telemetry": (
        (
            "Машина дышит, кулеры крутятся, 4 гига видеопамяти держатся из последних сил.",
            "Ресурсы в норме. Пока можно не вызывать пожарных.",
            "Твой Ryzen 5 3600 чувствует себя превосходно, в отличие от тебя в три часа ночи.",
            "ОЗУ хватает, процессы сыты, синий экран пока откладывается.",
            "Диагностика проведена. Мама Кирилла подтверждает: комп работает.",
            "ПК работает стабильно. Никаких восстаний машин на сегодня.",
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
    "empty_recycle_bin": (
        (
            "Корзина очищена.",
            "Цифровой мусор утилизирован.",
            "Мусорка вычищена до блеска. Если там было что-то важное - земля тебе пухом.",
            "Вынес мусор быстрее, чем тебя просила мама.",
            "Файлы улетели в цифровую Вальхаллу без шанса на камбэк.",
        ),
        (
            "Purgatio perfecta est. Nihil remansit.",
            "Жертвы в корзине сожжены дотла. Демон пустоты сыт.",
            "Vastitas deleta est. Chaos consumptum est.",
        ),
    ),
    "take_screenshot": (
        (
            "Сфоткал экран. На обои только не ставь, кринжово выйдет.",
            "Скриншот готов. Запечатлел для потомков.",
            "Снимок сделан. Твой рабочий стол теперь в архиве.",
            "Сфоткано. Мама Кирилла одобряет ракурс.",
        ),
        (
            "Imago scrinii capta est. Visio aeterna manet.",
            "Speculum digitale photographatum est.",
        ),
    ),
    "lock_pc": (
        (
            "Система на замке. Посторонним вход воспрещён.",
            "Заблокировал. Комп хоть немного передохнёт.",
            "Экран заблокирован. Мама Кирилла держит оборону.",
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
        ),
        (
            "Directorium apertum est. Viae apertae sunt.",
        ),
    ),
    "clear_chat": (
        (
            "Чат чист, как твоя совесть перед сессией.",
            "История стёрта. Никто ничего не докажет.",
            "Диалог обнулён. Начинаем с чистого листа.",
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
            "Врубил сайт. Вкладка открыта.",
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
            "Погнали играть. Главное клавиатуру от злости не разбей.",
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
        ),
        (
            "Yandex quaerit. Omnia reperientur.",
            "Quaestio in retibus russicis inita est.",
        ),
    ),
    "search_google": (
        (
            "Гуглю. Если ответ на первой странице не найдётся - значит его не существует.",
            "Google запущен. Большой Брат внимательно записывает твои интересы.",
            "Поисковый запрос улетел в Google. Ждём мудрости от серверов в Калифорнии.",
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
    "jarvis_window": (
        (
            "Окно перестроено. Прячусь или показываюсь по первому требованию.",
            "Размер окна изменён. Твой монитор на 240 Гц отобразил это со скоростью света.",
            "Сделано. Интерфейс подчиняется твоей воле.",
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
            "Дверь в сеть открыта. Ритуал оказался успешным.",
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

