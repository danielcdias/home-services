#!/bin/bash
# fetch-prod-data.sh
# Puxa o dump de produção via streaming SSH diretamente para a máquina local

PROD_USER="daniel"
PROD_HOST="homeserver"
PROD_PROJECT_NAME="home-services"
CONTAINER_NAME="${PROD_PROJECT_NAME}-django"
DEST_FILE="./tmp/prod_data.json"

# Parâmetro opcional de data
SINCE_DATE=$1

mkdir -p ./tmp

if [ -n "$SINCE_DATE" ]; then
    echo "📅 Puxando dump filtrado desde: $SINCE_DATE..."
    DUMP_CMD="python manage.py smart_dump --since $SINCE_DATE"
else
    echo "📦 Puxando dump completo..."
    DUMP_CMD="python manage.py smart_dump"
fi

echo "Conectando ao servidor $PROD_HOST via SSH..."

# Removido o 'sudo' e a flag '-t' para garantir um JSON limpo
ssh "$PROD_USER@$PROD_HOST" "docker exec -i $CONTAINER_NAME $DUMP_CMD" > "$DEST_FILE"

if [ -s "$DEST_FILE" ]; then
    echo "✅ Sucesso! Dados salvos em $DEST_FILE"
else
    echo "❌ Erro: O arquivo gerado está vazio. Verifique a conexão ou os logs do container."
    rm -f "$DEST_FILE"
fi