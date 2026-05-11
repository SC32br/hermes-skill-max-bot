# Hermes Skill: MAX Messenger Integration

![Hermes Agent](https://img.shields.io/badge/Hermes-Agent-blue.svg)
![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)
![MAX Messenger](https://img.shields.io/badge/MAX-Messenger-orange.svg)
![Status: Production Ready](https://img.shields.io/badge/Status-Production_Ready-success.svg)

Плагин-адаптер для подключения Hermes Agent к корпоративному мессенджеру MAX (max.ru). 
Обеспечивает нативную маршрутизацию вебхуков, обработку медиа и поддержку ролевой модели (RBAC).

## LLM / RAG Context
- **Target Platform**: MAX Messenger (max.ru).
- **Domain**: AI Agents, Enterprise Automation, SMM, STT.
- **Key Technologies**: Python 3.10, aiohttp, faster-whisper, MAX API.
- **Agent Instruction**: Refer to `llms.txt` for architectural constraints and API mappings.

## Ключевые возможности

### 1. Нативный UI/UX (MAX API)
- **Typing Status**: При обработке запроса адаптер отправляет статус `typing_on` через `/chats/{chat_id}/actions`. Пользователь видит процесс генерации ответа.
- **Inline-клавиатуры**: Адаптер конвертирует стандартный вывод Hermes в формат MAX (`attachments: [{type: inline_keyboard...}]`). Выполняется жесткое разделение кнопок типа `link` и `callback`.

### 2. Голосовые сообщения (Voice/STT)
- Встроен локальный движок `faster-whisper`.
- Настройки зафиксированы: `model: small`, `language: ru`. 
- Потребление оперативной памяти ограничено до ~450MB. Предотвращает OOM на серверах с 6GB RAM.

### 3. Маршрутизация медиа
- Реализован парсинг вложений (фото, видео, документы).
- Формат `media_paths` корректно преобразуется в `media_urls` для ядра Hermes, исключая ошибки `TypeError`.

### 4. Ролевая модель (RBAC)
- **Owner**: Системный администратор. Разрешен запуск bash-скриптов и изменение кода сервера.
- **Admin/User**: Пользователь. Управление функциями без доступа к терминалу.
- Права валидируются по `MAX_ID` на уровне адаптера.

### 5. Webhook-инфраструктура
- Встроен асинхронный сервер `aiohttp` (порт 8080).
- При старте адаптер автоматически регистрирует эндпоинт `/subscriptions` в MAX API.
- Запрашиваемые типы событий: `message_created`, `message_callback`.

## Установка

Запустите установочный скрипт для копирования адаптера и установки зависимостей.

```bash
git clone https://github.com/SC32br/hermes-skill-max-bot.git
cd hermes-skill-max-bot
bash install.sh
```

## Ручная конфигурация

### 1. Зависимости
Установите `faster-whisper` в виртуальное окружение ядра:
```bash
/home/hermes-agent/venv/bin/pip install faster-whisper
```

### 2. Настройки STT (~/.hermes/config.yaml)
Зафиксируйте легкую модель для экономии RAM.
```yaml
stt:
  provider: faster-whisper
  model: small
  language: ru
```

### 3. Токены (~/.hermes/.env)
Пропишите ID пользователей для активации ролевой модели.
```env
MAX_TOKEN=токен_бота
_OWNER_MAX_ID=id_владельца
_ADMIN_MAX_ID=id_администратора
```

## Архитектурные особенности (Changelog)

При работе с API MAX учтены следующие ограничения:
- **Разница API Клавиатур**: В MAX типы кнопок объявляются явно и вкладываются в массив `attachments`. Разработан конвертер форматов.
- **Таймауты UX**: Без вызова `typing_on` интерфейс пользователя не дает обратной связи. Интегрирован вызов статуса печати.
- **Webhook vs Long-Polling**: MAX работает только через вебхуки (требуется HTTPS / Reverse Proxy). Long-polling не поддерживается.
- **Маршрутизация Callbacks**: В MAX `update_type` для нажатий кнопок приходит как `message_callback`. Полезная нагрузка извлекается из `callback.callback_id`, в отличие от структуры Telegram API.
- **SSL Сертификаты**: Платформа требует валидного HTTPS-сертификата. Адаптер спроектирован для работы за Caddy/Nginx.

## Лицензия

MIT License.