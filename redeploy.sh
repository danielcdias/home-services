#!/bin/bash

# Interrompe a execução se qualquer comando falhar
set -e

# Função de ajuda
show_help() {
  echo "Uso: ./redeploy.sh [OPÇÕES]"
  echo ""
  echo "Opções:"
  echo "  -h                  Mostra esta mensagem de ajuda."
  echo "  -b                  Executa o build com --no-cache antes de subir."
  echo "  -f nome_arquivo.yml Especifica um arquivo docker-compose customizado."
  echo ""
  echo "Exemplos:"
  echo "  ./redeploy.sh"
  echo "  ./redeploy.sh -b"
  echo "  ./redeploy.sh -f prod.yaml -b"
  exit 0
}

# Configurações iniciais
DOCKER_FILE=""
BUILD_REQUIRED=false

# Processamento de parâmetros
while getopts "bhf:" opt; do
  case $opt in
    h)
      show_help
      ;;
    b)
      BUILD_REQUIRED=true
      ;;
    f)
      DOCKER_FILE="-f $OPTARG"
      ;;
    \?)
      echo "❌ Parâmetro inválido. Use -h para ajuda." >&2
      exit 1
      ;;
  esac
done

# Função para exibir mensagem de erro customizada
trap 'echo "🛑 Erro: O comando acima falhou. O redeploy foi interrompido!"' ERR

echo "🚀 Iniciando o redeploy..."

# 1. Down (Stop)
echo "⏹️  Derrubando os containers (down)..."
sudo docker compose $DOCKER_FILE down

# 2. Build (se a flag -b for passada)
if [ "$BUILD_REQUIRED" = true ]; then
  echo "🛠️  Executando build (--no-cache)..."
  sudo docker compose $DOCKER_FILE build --no-cache
fi

# 3. Up (Play)
echo "▶️  Subindo os containers (up -d)..."
sudo docker compose $DOCKER_FILE up -d

echo "✅ Redeploy concluído com sucesso! 🎉"

