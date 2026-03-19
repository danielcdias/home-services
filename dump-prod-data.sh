#!/bin/bash
# Script para dump dos dados de produção com filtro inteligente

original_dir=$(pwd)
ORIGINAL_HOME="$HOME"

# Carregamento do .env 
ENV_FILE="$original_dir/.env"
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
fi

CONTAINER_NAME="${PROJECT_NAME:-home-services}-django"

# Parâmetro de data (formato YYYY-MM-DD)
SINCE_DATE=$1

if [ -n "$SINCE_DATE" ]; then
    echo "📅 Filtrando logs brutos desde: $SINCE_DATE"
    DUMP_CMD="python manage.py smart_dump --since $SINCE_DATE"
else
    echo "📦 Gerando dump completo (logs brutos + summaries)."
    DUMP_CMD="python manage.py smart_dump"
fi

# 1. Solicita a senha 
read -s -p "Digite a senha para daniel.dias@gmail.com: " SMB_PASS
echo ""

# 2. Limpeza do arquivo temporário local 
sudo rm -f "$ORIGINAL_HOME/tmp/prod_data.json"

echo "Executando dump no container $CONTAINER_NAME..."
# 3. Execução do comando customizado 
sudo docker exec -i "$CONTAINER_NAME" $DUMP_CMD > "$ORIGINAL_HOME/tmp/prod_data.json"

cd "$ORIGINAL_HOME/tmp" || exit

echo "Enviando para a máquina dev..."
smbclient //10.1.1.197/temp -U "daniel.dias@gmail.com%${SMB_PASS}" -c "put prod_data.json"

cd "$original_dir"
echo "Sucesso!"
