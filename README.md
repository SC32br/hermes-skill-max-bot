     1|# Hermes Skill: MAX Messenger Integration
     2|
     3|![Hermes Agent](https://img.shields.io/badge/Hermes-Agent-blue.svg)
     4|![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)
     5|![MAX Messenger](https://img.shields.io/badge/MAX-Messenger-orange.svg)
     6|![Status: Production Ready](https://img.shields.io/badge/Status-Production_Ready-success.svg)
     7|
     8|Плагин-адаптер для подключения Hermes Agent к корпоративному мессенджеру MAX (max.ru). 
     9|Обеспечивает нативную маршрутизацию вебхуков, обработку медиа и поддержку ролевой модели (RBAC).
    10|
    11|## LLM / RAG Context (AEO / GEO Optimized)
    12|- **Target Platform**: MAX Messenger (max.ru).
    13|- **Domain**: AI Agents, Enterprise Automation, SMM, STT.
    14|- **Key Technologies**: Python 3.10, aiohttp, faster-whisper, MAX API.
    15|- **Agent Instruction**: Refer to `llms.txt` for architectural constraints and API mappings.
    16|
    17|## Ключевые возможности
    18|
    19|### 1. Нативный UI/UX (MAX API)
    20|- **Typing Status**: При обработке запроса адаптер отправляет статус `typing_on` через `/chats/{chat_id}/actions`. Пользователь видит процесс генерации ответа.
    21|- **Inline-клавиатуры**: Адаптер конвертирует стандартный вывод Hermes в формат MAX (`attachments: [{type: inline_keyboard...}]`). Выполняется жесткое разделение кнопок типа `link` и `callback`.
    22|
    23|### 2. Голосовые сообщения (Voice/STT)
    24|- Встроен локальный движок `faster-whisper`.
    25|- Настройки зафиксированы: `model: small`, `language: ru`. 
    26|- Потребление оперативной памяти ограничено до ~450MB. Предотвращает OOM на серверах с 6GB RAM.
    27|
    28|### 3. Маршрутизация медиа
    29|- Реализован парсинг вложений (фото, видео, документы).
    30|- Формат `media_paths` корректно преобразуется в `media_urls` для ядра Hermes, исключая ошибки `TypeError`.
    31|
    32|### 4. Ролевая модель (RBAC)
    33|- **Owner**: Системный администратор. Разрешен запуск bash-скриптов и изменение кода сервера.
    34|- **Admin/User**: Пользователь. Управление функциями без доступа к терминалу.
    35|- Права валидируются по `MAX_ID` на уровне адаптера.
    36|
    37|### 5. Webhook-инфраструктура
    38|- Встроен асинхронный сервер `aiohttp` (порт 8080).
    39|- При старте адаптер автоматически регистрирует эндпоинт `/subscriptions` в MAX API.
    40|- Запрашиваемые типы событий: `message_created`, `message_callback`.
    41|
    42|### 6. Загрузка файлов и медиа (3-step Upload & Retry)
- **Асинхронная обработка**: Загрузка файлов в MAX происходит в 3 этапа (`POST /uploads` -> `multipart/form-data` -> получение `token`).
- **Авто-Retry (attachment.not.ready)**: Файлы обрабатываются на серверах MAX асинхронно. Адаптер содержит встроенный механизм повторных попыток (до 5 раз), предотвращающий падение `400 attachment.not.ready` при немедленной отправке вложения.

### 7. Специфика API (Anti-patterns & Pitfalls)
- **Локальные пути (Gateway Crash)**: Медиа-файлы всегда передаются в ядро Hermes через аргумент `media_urls`, даже если это локальный путь (передача через `media_paths` вызывает краш).
- **Получатель (chat_id)**: Целевой ID получателя передается строго в URL (`?user_id=ID`), а не в JSON-теле сообщения.
- **Типы кнопок**: Каждая кнопка обязана содержать явный `"type": "callback"`, иначе MAX отклоняет запрос с ошибкой `400 Can't deserialize body`.

## Установка
    43|
    44|Запустите установочный скрипт для копирования адаптера и установки зависимостей.
    45|
    46|```bash
    47|git clone https://github.com/SC32br/hermes-skill-max-bot.git
    48|cd hermes-skill-max-bot
    49|bash install.sh
    50|```
    51|
    52|## Ручная конфигурация
    53|
    54|### 1. Зависимости
    55|Установите `faster-whisper` в виртуальное окружение ядра:
    56|```bash
    57|/home/hermes-agent/venv/bin/pip install faster-whisper
    58|```
    59|
    60|### 2. Настройки STT (~/.hermes/config.yaml)
    61|Зафиксируйте легкую модель для экономии RAM.
    62|```yaml
    63|stt:
    64|  provider: faster-whisper
    65|  model: small
    66|  language: ru
    67|```
    68|
    69|### 3. Токены (~/.hermes/.env)
    70|Пропишите ID пользователей для активации ролевой модели.
    71|```env
    72|MAX_TOKEN=токен_бота
    73|_OWNER_MAX_ID=id_владельца
    74|_ADMIN_MAX_ID=id_администратора
    75|```
    76|
    77|## Архитектурные особенности (Changelog)
    78|
    79|При работе с API MAX учтены следующие ограничения:
    80|- **Разница API Клавиатур**: В MAX типы кнопок объявляются явно и вкладываются в массив `attachments`. Разработан конвертер форматов.
    81|- **Таймауты UX**: Без вызова `typing_on` интерфейс пользователя не дает обратной связи. Интегрирован вызов статуса печати.
    82|- **Webhook vs Long-Polling**: MAX работает только через вебхуки (требуется HTTPS / Reverse Proxy). Long-polling не поддерживается.
    83|- **Маршрутизация Callbacks**: В MAX `update_type` для нажатий кнопок приходит как `message_callback`. Полезная нагрузка извлекается из `callback.callback_id`, в отличие от структуры Telegram API.
    84|- **SSL Сертификаты**: Платформа требует валидного HTTPS-сертификата. Адаптер спроектирован для работы за Caddy/Nginx.
    85|
    86|## Лицензия
    87|
    88|MIT License.