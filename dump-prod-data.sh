#!/bin/bash
# Script para dump dos dados de produção

original_dir=$(pwd)
ORIGINAL_HOME="$HOME"

# ==========================================
# Carregamento Dinâmico do .env
# ==========================================
ENV_FILE="$original_dir/.env"

if [ -f "$ENV_FILE" ]; then
    # 'set -a' faz com que todas as variáveis lidas no source sejam exportadas
    set -a
    source "$ENV_FILE"
    set +a
else
    echo "⚠️  Aviso: Arquivo .env não encontrado em $ENV_FILE. Tentando usar o nome padrão."
fi

# Define o nome do container dinamicamente. 
# NOTA: Troque PROJECT_NAME por COMPOSE_PROJECT_NAME ou PROJECT_PREFIX caso tenha usado esses nomes no .env.
# O ':-home-services' é um fallback de segurança caso a variável não exista.
CONTAINER_NAME="${PROJECT_NAME:-home-services}-django"

echo "🔍 Target Container: $CONTAINER_NAME"

# ==========================================

# 1. Solicita a senha de forma segura (não exibe no terminal)
read -s -p "Digite a senha para daniel.dias@gmail.com: " SMB_PASS
echo "" # Apenas para quebrar a linha após você dar Enter

# 2. Garante que o arquivo antigo seja apagado sem erros (adicionei o -f)
sudo rm -f "$ORIGINAL_HOME/tmp/prod_data.json"

echo "Gerando dump do banco de dados..."
# 3. Usa a variável do nome do container ($CONTAINER_NAME) ao invés do nome engessado
sudo docker exec -i "$CONTAINER_NAME" python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission --indent 4 > "$ORIGINAL_HOME/tmp/prod_data.json"

cd "$ORIGINAL_HOME/tmp" || exit

echo "Copiando arquivo para a máquina dev..."
# 4. Passa a senha pela variável usando a sintaxe Usuario%Senha do smbclient
smbclient //10.1.1.197/temp -U "daniel.dias@gmail.com%${SMB_PASS}" -c "put prod_data.json"

cd "$original_dir"
echo "Processo concluído com sucesso!"
