#!/bin/bash
# load-local-dev.sh
# Carrega o dump no ambiente de desenvolvimento local (fora do Docker)

DUMP_FILE="./tmp/prod_data.json"

if [ ! -f "$DUMP_FILE" ]; then
    echo "❌ Erro: Arquivo de dump não encontrado em $DUMP_FILE"
    echo "Rode o script ./fetch-prod-data.sh primeiro."
    exit 1
fi

echo "🧹 Limpando o banco de dados local (Flush)..."
python manage.py flush --no-input

echo "🏗️ Aplicando migrações pendentes (se houver)..."
python manage.py migrate

echo "📥 Inserindo dados do dump..."
python manage.py loaddata "$DUMP_FILE"

echo "✅ Carga concluída com sucesso no ambiente local!"
