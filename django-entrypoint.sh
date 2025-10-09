#!/bin/sh
# entrypoint.sh - Versão Otimizada
set -e

echo "▶️ Executando migrações do banco de dados..."
python ./manage.py migrate --noinput

if [ -f "fixtures.json" ]; then
  echo "ℹ️ Arquivo fixtures.json encontrado. Carregando dados..."
  python ./manage.py loaddata fixtures.json
else
  echo "ℹ️ Arquivo fixtures.json não encontrado. Pulando o carregamento de dados."
fi

echo "▶️  Garantindo a existência do superusuário..."
python ./manage.py customcreatesuperuser --noinput

echo "✅ Todas as etapas de inicialização foram concluídas com sucesso."
echo "🚀 Iniciando o servidor Gunicorn..."
exec gunicorn config.wsgi:application \
        --bind 0.0.0.0:8000 \
        --log-config-json ./gunicorn_logging.json
