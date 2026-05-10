#!/bin/bash
# Install script for Hermes Agent MAX Messenger Plugin

echo "🔥 Начинаем установку плагина MAX Messenger для Hermes Agent..."

HERMES_PLUGIN_DIR="/root/.hermes/plugins/max_messenger"
VENV_PIP="/home/hermes-agent/venv/bin/pip"

# 1. Проверяем наличие папки плагинов
if [ ! -d "$HERMES_PLUGIN_DIR" ]; then
    echo "📁 Создаем директорию плагина: $HERMES_PLUGIN_DIR"
    mkdir -p "$HERMES_PLUGIN_DIR"
fi

# 2. Копируем боевой адаптер
echo "📄 Копируем adapter.py..."
cp adapter.py "$HERMES_PLUGIN_DIR/adapter.py"
chmod 644 "$HERMES_PLUGIN_DIR/adapter.py"

# 3. Устанавливаем STT зависимости для голосовых
echo "📦 Устанавливаем faster-whisper в venv Hermes..."
if [ -f "$VENV_PIP" ]; then
    $VENV_PIP install faster-whisper
else
    echo "⚠️ ВНИМАНИЕ: $VENV_PIP не найден. Установите faster-whisper вручную в окружение Hermes."
fi

# 4. Памятка по конфигурации
echo ""
echo "✅ Установка файлов завершена!"
echo "⚠️ ВАЖНО: Не забудьте внести следующие изменения:"
echo "1. В файл /root/.hermes/.env:"
echo "   MAX_TOKEN=ваш_токен"
echo "   _OWNER_MAX_ID=ваш_id"
echo "2. В файл /root/.hermes/config.yaml:"
echo "   stt:"
echo "     model: small"
echo "     language: ru"
echo ""
echo "🚀 Готово! Перезапустите gateway для применения изменений (осторожно, это сбросит активные сессии)."