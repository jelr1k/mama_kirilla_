# Модули расширения (modules/)

Пакет `modules/` содержит подключаемые сервисы и расширения функционала JARVIS, не входящие в минимальное ядро.

## 1. Удалённое управление через Telegram (`modules/telegram/`, `modules/telegram_bot.py`)

Асинхронный сервис управления компьютером через Telegram-бота (`httpx` + `asyncio`):
- `telegram/service.py`: Жизненный цикл бота, сессионная изоляция (`session_id`), очистка очереди устаревших команд (`drop_pending_updates=True`), обработка ошибок.
- `telegram/client.py`: Клиент Telegram Bot API с поддержкой реверс-прокси Cloudflare Worker (`api_base_url`) для обхода блокировок IP-подсетей Telegram в РФ без VPN.
- `telegram/handlers.py`: Обработчики команд (`/status`, `/screen`, `/vpn`, `/ping`, `/lock`, `/sleep`, `/shutdown`, `/help`) и роутинг входящего текста в `CommandRouter` ассистента.
- `telegram/keyboards.py`: Инлайн-клавиатуры быстрого управления ПК.
- Безопасность: доступ строго ограничен белым списком `allowed_chat_ids`.

`modules/telegram_bot.py` предоставляет обратную совместимость для существующих импортов.

## 2. Мониторинг доступности сервисов и DPI (`modules/network_checker.py`)

Асинхронная диагностика состояния сетевых шлюзов:
- Проверка доступности Discord Gateway, YouTube, Steam Store, Telegram API и GitHub.
- Разделение статусов: норма (`ok`), задержка (`slow`), блокировка/таймаут (`blocked`).
- Встроенный TTL-кэш результатов (15 сек) для мгновенной отдачи во фронтенд через `/api/network/services`.
