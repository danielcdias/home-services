# Captura de argumentos para permitir --upgrade-all
$flagUpgrade = ($args -contains "--upgrade-all")

# Função para gerar o arquivo requirements.txt
function Export-Requirements {
    try {
        pip freeze | Out-File -Encoding UTF8 requirements.txt -ErrorAction Stop
        Write-Host "✅ Arquivo 'requirements.txt' atualizado com sucesso." -ForegroundColor Green
    }
    catch {
        Write-Host "❌ Erro ao salvar o arquivo: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# --- Lógica Principal ---

if ($flagUpgrade) {
    Write-Host "🚀 Iniciando manutenção global (--upgrade-all)..." -ForegroundColor Cyan
    $erroOcorrido = $false

    # 1. Coletar todos os pacotes desatualizados (incluindo o pip)
    Write-Host "🔍 Verificando pacotes desatualizados..." -ForegroundColor Yellow
    
    # Capturamos a lista uma única vez para otimizar
    $outdatedRaw = pip list --outdated --format=columns | Select-String -Pattern "^[a-zA-Z0-9\-_]+\s+\d+"
    
    if (-not $outdatedRaw) {
        Write-Host "✨ Todos os pacotes (incluindo o pip) já estão na última versão." -ForegroundColor Green
        Export-Requirements
    } else {
        # Extrair apenas os nomes dos pacotes
        $outdatedNames = $outdatedRaw | ForEach-Object { ($_ -split '\s+')[0] }
        $outdatedList = @($outdatedNames)

        # 2. Atualizar o PIP apenas se ele estiver na lista
        if ($outdatedList -contains "pip") {
            Write-Host "📦 Atualização encontrada para o 'pip'. Atualizando..." -ForegroundColor Yellow
            python.exe -m pip install --upgrade pip
            if ($LASTEXITCODE -ne 0) { 
                Write-Host "❌ Falha crítica ao atualizar o pip." -ForegroundColor Red
                $erroOcorrido = $true 
            }
        } else {
            Write-Host "ℹ️ O pip já está atualizado." -ForegroundColor Gray
        }

        # 3. Atualizar os demais pacotes (exceto o pip que já foi tratado ou ignorado)
        if (-not $erroOcorrido) {
            $pacotesParaAtualizar = $outdatedList | Where-Object { $_ -ne "pip" }

            if ($pacotesParaAtualizar) {
                Write-Host "📦 Atualizando $($pacotesParaAtualizar.Count) pacote(s)..." -ForegroundColor Yellow
                foreach ($pkg in $pacotesParaAtualizar) {
                    Write-Host "-> Atualizando $pkg..." -ForegroundColor Gray
                    pip install --upgrade $pkg
                    if ($LASTEXITCODE -ne 0) { 
                        Write-Host "⚠️ Falha ao atualizar o pacote: $pkg" -ForegroundColor Red
                        $erroOcorrido = $true 
                    }
                }
            }
        }

        # 4. Finalização condicional
        if (-not $erroOcorrido) {
            Write-Host "✨ Todos os processos de upgrade concluídos com sucesso!" -ForegroundColor Cyan
            Export-Requirements
        } else {
            Write-Host "🚫 Erro detectado durante o upgrade. O 'requirements.txt' NÃO foi alterado." -ForegroundColor Red
        }
    }

} else {
    Write-Host "📝 Modo padrão: Apenas atualizando 'requirements.txt'..." -ForegroundColor Blue
    Export-Requirements
}
