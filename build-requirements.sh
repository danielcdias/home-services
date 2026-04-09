#!/bin/bash

# Definição de cores ANSI
CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
GRAY='\033[0;90m'
BLUE='\033[0;34m'
NC='\033[0m' # Sem Cor (No Color)

# Captura de argumentos
FLAG_UPGRADE=false
for arg in "$@"; do
    if [[ "$arg" == "--upgrade-all" || "$arg" == "-u" ]]; then
        FLAG_UPGRADE=true
        break
    fi
done

# Função para gerar o arquivo requirements.txt
export_requirements() {
    if pip freeze > requirements.txt 2> pip_error.log; then
        echo -e "${GREEN}✅ Arquivo 'requirements.txt' atualizado com sucesso.${NC}"
    else
        echo -e "${RED}❌ Erro ao salvar o arquivo: $(cat pip_error.log)${NC}"
    fi
    rm -f pip_error.log
}

# --- Lógica Principal ---

if [ "$FLAG_UPGRADE" = true ]; then
    echo -e "${CYAN}🚀 Iniciando manutenção global...${NC}"
    ERRO_OCORRIDO=false

    echo -e "${YELLOW}🔍 Verificando pacotes desatualizados...${NC}"
    
    OUTDATED_RAW=$(pip list --outdated --format=columns 2>/dev/null | tail -n +3 | awk '{print $1}')
    
    if [ -z "$OUTDATED_RAW" ]; then
        echo -e "${GREEN}✨ Todos os pacotes (incluindo o pip) já estão na última versão.${NC}"
        export_requirements
    else
        OUTDATED_LIST=($OUTDATED_RAW)

        HAS_PIP=false
        PACOTES_ARRAY=()
        for pkg in "${OUTDATED_LIST[@]}"; do
            if [[ "$pkg" == "pip" ]]; then
                HAS_PIP=true
            else
                PACOTES_ARRAY+=("$pkg")
            fi
        done

        # 1. Pip isolado
        if [ "$HAS_PIP" = true ]; then
            echo -e "${YELLOW}📦 Atualizando o 'pip'...${NC}"
            if python -m pip install --upgrade pip >/dev/null 2>&1; then
                :
            else
                echo -e "${RED}❌ Falha crítica ao atualizar o pip.${NC}"
                ERRO_OCORRIDO=true
            fi
        else
            echo -e "${GRAY}ℹ️ O pip já está atualizado.${NC}"
        fi

        # 2. Atualização em Lote
        if [ "$ERRO_OCORRIDO" = false ] && [ ${#PACOTES_ARRAY[@]} -gt 0 ]; then
            echo -e "${YELLOW}📦 Atualizando ${#PACOTES_ARRAY[@]} pacote(s) em lote...${NC}"
            
            if pip install --upgrade --upgrade-strategy eager "${PACOTES_ARRAY[@]}"; then
                
                echo -e "${YELLOW}🛡️ Auditando integridade das dependências...${NC}"
                CHECK_OUTPUT=$(pip check 2>&1)
                
                if [ $? -eq 0 ]; then
                    echo -e "${GREEN}✅ Árvore de dependências validada sem conflitos.${NC}"
                else
                    echo -e "${RED}⚠️ CONFLITO DETECTADO!${NC}"
                    echo -e "${GRAY}$CHECK_OUTPUT${NC}"
                    
                    # ==========================================
                    # OPÇÃO 2: TENTATIVA DE AUTO-HEAL
                    # ==========================================
                    echo -e "${YELLOW}🔧 Tentando Auto-Correção (Extraindo e forçando requerimentos)...${NC}"
                    
                    # Extrai a string exata do requerimento (ex: pydantic-core==2.41.5)
                    # O awk procura "has requirement", pega a coluna 5 e tira a vírgula do final
                    FIX_PACKAGES=$(echo "$CHECK_OUTPUT" | awk '/has requirement/ {gsub(/,/, "", $5); print $5}')
                    
                    AUTO_HEAL_SUCCESS=false
                    if [ -n "$FIX_PACKAGES" ]; then
                        FIX_ARRAY=($FIX_PACKAGES)
                        echo -e "${GRAY}-> Instalando estritamente: ${FIX_ARRAY[*]}${NC}"
                        
                        if pip install "${FIX_ARRAY[@]}" >/dev/null 2>&1; then
                            if pip check >/dev/null 2>&1; then
                                echo -e "${GREEN}✅ Auto-correção bem-sucedida! Ambiente estabilizado.${NC}"
                                AUTO_HEAL_SUCCESS=true
                            fi
                        fi
                    fi
                    
                    # ==========================================
                    # OPÇÃO 1: ROLLBACK ESTRITO (Se a autocura falhar)
                    # ==========================================
                    if [ "$AUTO_HEAL_SUCCESS" = false ]; then
                        echo -e "${RED}❌ A auto-correção falhou ou foi insuficiente.${NC}"
                        echo -e "${RED}🚨 Iniciando ROLLBACK ESTRITO para o estado anterior do requirements.txt...${NC}"
                        
                        if [ -f "requirements.txt" ]; then
                            echo -e "${GRAY}-> Restaurando versões exatas...${NC}"
                            pip install -r requirements.txt >/dev/null 2>&1
                            
                            echo -e "${GRAY}-> Varrimento e remoção de pacotes intrusos (Órfãos)...${NC}"
                            # Extrai apenas os nomes dos pacotes atuais e do requirements
                            pip freeze | awk -F '==| @ ' '{print tolower($1)}' | sort > /tmp/cur_names.txt
                            cat requirements.txt | awk -F '==| @ ' '{print tolower($1)}' | sort > /tmp/req_names.txt
                            
                            # Compara as listas ignorando ferramentas nativas (pip, setuptools, wheel)
                            ORPHANS=$(comm -23 /tmp/cur_names.txt /tmp/req_names.txt | grep -vE "^(pip|setuptools|wheel|distribute)$")
                            
                            if [ -n "$ORPHANS" ]; then
                                for orphan in $ORPHANS; do
                                    echo -e "${GRAY}   Limpando $orphan...${NC}"
                                    pip uninstall -y "$orphan" >/dev/null 2>&1
                                done
                            fi
                            rm -f /tmp/cur_names.txt /tmp/req_names.txt
                            
                            echo -e "${GREEN}♻️ Rollback concluído. Ambiente revertido para os pacotes e versões originais.${NC}"
                            ERRO_OCORRIDO=true # Bloqueia a geração de um novo requirements.txt
                        else
                            echo -e "${RED}❌ requirements.txt não encontrado! Rollback impossível.${NC}"
                            ERRO_OCORRIDO=true
                        fi
                    fi
                fi
                
            else
                echo -e "${RED}⚠️ Falha na execução da instalação em lote.${NC}"
                ERRO_OCORRIDO=true
            fi
        fi

        # 3. Finalização
        if [ "$ERRO_OCORRIDO" = false ]; then
            echo -e "${CYAN}✨ Processos de upgrade concluídos em segurança!${NC}"
            export_requirements
        else
            echo -e "${RED}🚫 Update abortado ou revertido. O 'requirements.txt' FOI PRESERVADO para manter a integridade.${NC}"
        fi
    fi

else
    echo -e "${BLUE}📝 Modo padrão: Apenas atualizando 'requirements.txt'...${NC}"
    export_requirements
fi
