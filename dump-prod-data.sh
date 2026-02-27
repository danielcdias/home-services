#!/bin/bash
# Script para dump dos dados de produção

original_dir=$(pwd)
ORIGINAL_HOME="$HOME"

# 1. Solicita a senha de forma segura (não exibe no terminal)
read -s -p "Digite a senha para daniel.dias@gmail.com: " SMB_PASS
echo "" # Apenas para quebrar a linha após você dar Enter

# 2. Garante que o arquivo antigo seja apagado sem erros (adicionei o -f)
sudo rm -f "$ORIGINAL_HOME/tmp/prod_data.json"

echo "Gerando dump do banco de dados..."
# 3. Removi o '-t' do '-it'. O '-t' exige um terminal real e pode quebrar redirects (>) dentro de scripts
sudo docker exec -i django python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission --indent 4 > "$ORIGINAL_HOME/tmp/prod_data.json"

cd "$ORIGINAL_HOME/tmp" || exit

echo "Copiando arquivo para a máquina dev..."
# 4. Passa a senha pela variável usando a sintaxe Usuario%Senha do smbclient
smbclient //10.1.1.197/temp -U "daniel.dias@gmail.com%${SMB_PASS}" -c "put prod_data.json"

cd "$original_dir"
echo "Processo concluído com sucesso!"
