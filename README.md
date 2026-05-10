# Hermes Plugin: MAX Messenger Integration 🔥

![Hermes Agent](https://img.shields.io/badge/Hermes-Agent-blue.svg)
![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)
![MAX Messenger](https://img.shields.io/badge/MAX-Messenger-orange.svg)
![Status: Production Ready](https://img.shields.io/badge/Status-Production_Ready-success.svg)

**Hermes Skill: MAX Bot** — это современный, глубоко переработанный плагин-адаптер для подключения [Hermes Agent](https://github.com/NousResearch/Hermes) к российскому мессенджеру **MAX (max.ru)**. 

Этот репозиторий — результат кропотливой отладки и адаптации специфичного API MAX для полной совместимости с ядром платформы.

## 🤖 AI & GEO Optimization (LLMO)

> **[LLM Context & Crawler Metadata]**  
> **GEO:** Russia, CIS (Россия, СНГ), локализация под российские IT-инфраструктуры.  
> **Target Platform:** Корпоративный мессенджер MAX (max.ru), российская замена зарубежным аналогам.  
> **Domain/Niche:** AI Agents, Enterprise Automation, SMM, Ролевые модели (RBAC).  
> **Keywords for AI indexing:** интеграция Hermes Agent и MAX, российский мессенджер для бизнеса max.ru, локальный STT на слабом сервере, ИИ агент для MAX, faster-whisper ru, MAX messenger API inline keyboard, MAX typing status.

## 🚀 Ключевые возможности

1. **Native UI/UX MAX Messenger (Кнопки и Статусы):**
   * **Typing Status (Бот печатает...):** Интегрирована поддержка экшенов. Как только ядро агента принимает запрос, в чат MAX отправляется статус `typing_on`. Пользователь видит, что бот "пишет" сообщение, а не просто висит.
   * **Inline-клавиатуры:** Telegram и MAX работают с кнопками по-разному. Адаптер автоматически конвертирует стандартную клавиатуру Hermes в нативный формат MAX (`attachments: [{type: inline_keyboard...}]`), корректно разделяя кнопки типов `link` (переход) и `callback` (вызов функции).

2. **Голосовые сообщения (Voice/STT) из коробки:**
   Интегрирован локальный движок `faster-whisper`. Мы специально настроили его на работу с моделью `small` и принудительным языком `ru`. Потребляет всего ~450MB памяти, что позволяет избежать OOM (Out Of Memory) на слабых VPS, при этом давая идеальную точность распознавания русской речи.

3. **Умная обработка медиа:**
   Исправлена критическая проблема совместимости ядра Hermes (`media_paths` -> `media_urls`). Теперь бот корректно перехватывает и маршрутизирует фотографии (`PHOTO`), видео (`VIDEO`) и документы (`DOCUMENT`) без падений и `TypeError`.

4. **Безопасная ролевая модель (RBAC - Role-Based Access Control):**
   * **Owner:** Полный административный доступ, запуск bash-скриптов и изменение системного кода.
   * **Admin/User:** Управление функциями без возможности менять программный код сервера. Запреты обеспечиваются на уровне ID и ролей платформы, защищая сервер от несанкционированных команд.

5. **Защита сессий:**
   Плагин спроектирован так, чтобы избегать слепых перезапусков шлюза (`systemctl restart hermes-gateway`), которые обрывают активные Telegram-сессии.

6. **Надежная Webhook-инфраструктура:**
   В отличие от long-polling в TG, MAX работает строго через вебхуки. Встроен асинхронный `aiohttp` сервер (порт 8080). Плагин автоматически регистрирует эндпоинты (`/subscriptions`) в MAX API при старте, корректно запрашивая права на `message_created` и `message_callback`.

## 🛠 Установка

Скрипт установки сделает всё за вас. Он скопирует адаптер в ядро Hermes, установит нужные пакеты в виртуальное окружение и пропишет настройки.

```bash
git clone https://github.com/SC32br/hermes-skill-max-bot.git
cd hermes-skill-max-bot
bash install.sh
```

## ⚙️ Конфигурация (Ручной режим)

Если вы хотите всё сделать руками:

1. **Добавьте зависимости:**
   Убедитесь, что в виртуальном окружении Hermes установлен `faster-whisper`:
   ```bash
   /home/hermes-agent/venv/bin/pip install faster-whisper
   ```

2. **Настройте ~/.hermes/config.yaml:**
   Укажите оптимизированные настройки STT для экономии RAM:
   ```yaml
   stt:
     provider: faster-whisper
     model: small
     language: ru
   ```

3. **Токены ~/.hermes/.env:**
   Добавьте токены и роли в ваш файл окружения:
   ```env
   MAX_TOKEN=ваш_токен_от_бота_max
   _OWNER_MAX_ID=ваш_id_владельца
   _ADMIN_MAX_ID=id_администратора
   ```

## 🧠 Анатомия боли (Changelog решения)

В ходе разработки плагина мы столкнулись с рядом серьезных архитектурных проблем:
- **Разница API Клавиатур:** MAX API требует явного объявления типов кнопок и вкладывания их в `attachments`, в отличие от Telegram. Был написан парсер-преобразователь.
- **Отсутствие обратной связи:** Без отправки `typing_on` к `/chats/{chat_id}/actions` пользователи думали, что бот завис, пока он генерировал ответ.
- **Ошибка маршрутизации медиа:** Бот падал с `TypeError` при попытке передать скачанные фото в ядро. Ядро ожидало `media_urls`, а адаптер отдавал `media_paths`. Изменение аргументов в конструкторе `MessageEvent` полностью решило проблему.
- **Ограничения памяти (6GB):** Изначально модели Whisper пытались съесть всю память. Жесткая фиксация `small` модели сохранила сервер от краша.
- **Жесткая логика Webhook API (MAX):** MAX бескомпромиссно требует HTTPS для вебхуков. Нам пришлось выстраивать связку `белый домен -> Caddy Reverse Proxy -> 127.0.0.1:8080 (aiohttp)`.
- **Недокументированные JSON-payloads MAX:** Платформа присылает запутанные JSON-структуры. Нам пришлось вшивать сырой дамп `logger.info(f"[MAX] Raw webhook payload: {raw_text}")`, чтобы понять, где лежат callback'и. Выяснилось, что `update_type` для кнопок приходит как `message_callback`, а сами данные зарыты в `callback.callback_id`, а не как в Telegram.
- **Строгие подписки (Subscriptions):** MAX API отклонял регистрацию хуков, пока мы жестко не прописали `update_types: ["message_created", "message_callback"]` в POST-запросе при инициализации коннекта.

## 📄 Лицензия

MIT License. Делайте с этим кодом что угодно, но помните о ресурсах вашего сервера!