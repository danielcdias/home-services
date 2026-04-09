#!/bin/bash
# load-docker-dev.sh
# Carrega o dump no ambiente Docker de Dev de forma inteligente

COMPOSE_FILE="compose.dev.yaml"
SERVICE_NAME="django"
DUMP_FILE="./tmp/prod_data.json"
COMPOSE_WAS_DOWN=false

if [ ! -f "$DUMP_FILE" ]; then
    echo "❌ Erro: Arquivo de dump não encontrado em $DUMP_FILE"
    exit 1
fi

# Verifica se o container do Django está rodando
if ! docker compose -f "$COMPOSE_FILE" ps --services --filter "status=running" | grep -q "^$SERVICE_NAME$"; then
    echo "🛌 Ambiente Docker está dormindo. Subindo o compose em background..."
    COMPOSE_WAS_DOWN=true
    docker compose -f "$COMPOSE_FILE" up -d
    
    echo "⏳ Aguardando o container ficar saudável (isso pode levar alguns segundos)..."
    # Fica testando o healthcheck até ele reportar 'healthy'
    until [ "$(docker inspect -f '{{.State.Health.Status}}' "$(docker compose -f $COMPOSE_FILE ps -q $SERVICE_NAME)")" == "healthy" ]; do
        sleep 2
        echo -n "."
    done
    echo -e "\n✅ Container pronto!"
else
    echo "🏃 Ambiente Docker já está em execução."
fi

echo "🧹 Executando Flush no banco de dados do container..."
docker compose -f "$COMPOSE_FILE" exec "$SERVICE_NAME" python manage.py flush --no-input

echo "📥 Transferindo e carregando os dados no container..."
# Lemos o arquivo local e injetamos via stdin (entrada padrão) direto no loaddata do container
# Isso evita a necessidade de dar um 'docker cp' de um arquivo temporário
cat "$DUMP_FILE" | docker compose -f "$COMPOSE_FILE" exec -T "$SERVICE_NAME" sh -c 'cat > /tmp/temp_dump.json && python manage.py loaddata /tmp/temp_dump.json && rm /tmp/temp_dump.json'

echo "✅ Carga concluída com sucesso no ambiente Docker!"

# Se o script subiu o compose, ele deve derrubá-lo no final
if [ "$COMPOSE_WAS_DOWN" = true ]; then
    echo "🛑 Derrubando o ambiente Docker conforme estado original..."
    docker compose -f "$COMPOSE_FILE" down
    echo "✅ Ambiente finalizado."
fi
