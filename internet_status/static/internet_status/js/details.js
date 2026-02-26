document.addEventListener("DOMContentLoaded", function () {
    function getDjangoData(elementId) {
        const element = document.getElementById(elementId);
        return element ? JSON.parse(element.textContent) : [];
    }

    function getStringData(elementId) {
        const element = document.getElementById(elementId);
        return element ? JSON.parse(element.textContent) : 'atual';
    }

    // ==========================================
    // 1. Gráficos Recentes
    // ==========================================
    const speedLabels = getDjangoData('speedLabels');
    const downloadData = getDjangoData('downloadData');
    const uploadData = getDjangoData('uploadData');

    const ctxSpeed = document.getElementById('speedChart');
    if (ctxSpeed) {
        new Chart(ctxSpeed, {
            type: 'line',
            data: {
                labels: speedLabels,
                datasets: [
                    { label: 'Download (Mbps)', data: downloadData, borderColor: '#0d6efd', backgroundColor: 'rgba(13, 110, 253, 0.1)', fill: true, tension: 0.3 },
                    { label: 'Upload (Mbps)', data: uploadData, borderColor: '#0dcaf0', backgroundColor: 'transparent', tension: 0.3 }
                ]
            },
            options: { responsive: true }
        });
    }

    const pingLabels = getDjangoData('pingLabels');
    const pingData = getDjangoData('pingData');
    const ctxPing = document.getElementById('pingChart');
    if (ctxPing) {
        new Chart(ctxPing, {
            type: 'line',
            data: {
                labels: pingLabels,
                datasets: [{ label: 'Sucesso Ping (%)', data: pingData, borderColor: '#198754', backgroundColor: 'rgba(25, 135, 84, 0.2)', fill: true, stepped: true }]
            },
            options: { responsive: true, scales: { y: { min: 0, max: 100 } } }
        });
    }

    // ==========================================
    // 2. Gráfico Mensal Combinado
    // ==========================================
    const monthlyLabels = getDjangoData('monthlyLabels');
    const monthlyDown = getDjangoData('monthlyDown');
    const monthlyUp = getDjangoData('monthlyUp');
    const monthlyPing = getDjangoData('monthlyPing');
    const ctxMonthly = document.getElementById('monthlyChart');

    let monthlyChartInstance = null;

    if (ctxMonthly) {
        monthlyChartInstance = new Chart(ctxMonthly, {
            type: 'line',
            data: {
                labels: monthlyLabels,
                datasets: [
                    {
                        label: 'Download Médio (Mbps)',
                        data: monthlyDown,
                        borderColor: '#0d6efd',
                        backgroundColor: '#0d6efd',
                        yAxisID: 'ySpeed'
                    },
                    {
                        label: 'Upload Médio (Mbps)',
                        data: monthlyUp,
                        borderColor: '#0dcaf0',
                        backgroundColor: '#0dcaf0',
                        yAxisID: 'ySpeed'
                    },
                    {
                        label: 'Taxa de Sucesso Ping (%)',
                        data: monthlyPing,
                        type: 'bar',
                        backgroundColor: 'rgba(25, 135, 84, 0.4)',
                        borderColor: 'rgba(25, 135, 84, 1)',
                        borderWidth: 1,
                        yAxisID: 'yPing'
                    }
                ]
            },
            options: {
                responsive: true,
                interaction: { mode: 'index', intersect: false },
                scales: {
                    x: { grid: { display: false } },
                    ySpeed: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: { display: true, text: 'Velocidade (Mbps)' }
                    },
                    yPing: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        min: 0,
                        max: 100,
                        title: { display: true, text: 'Estabilidade (%)' },
                        grid: { drawOnChartArea: false }
                    }
                }
            }
        });
    }

    // ==========================================
    // 3. Geração do Relatório em PDF (Correção da Captura de Ecrã)
    // ==========================================
    const btnPdf = document.getElementById('btn-gerar-pdf');
    const filenameLabel = getStringData('filenameLabel');

    if (btnPdf) {
        btnPdf.addEventListener('click', function () {
            const btnOriginalText = btnPdf.innerHTML;
            btnPdf.innerHTML = '⏳ Ajustando Layout...';
            btnPdf.disabled = true;

            const elementoRelatorio = document.getElementById('relatorio-conteudo');
            const divTabela = elementoRelatorio.querySelector('.table-responsive');

            // 1. Guarda estado original
            const originalWidth = elementoRelatorio.style.width;
            const originalMaxWidth = elementoRelatorio.style.maxWidth;

            // 2. Força exatamente 1000px na div HTML (espaço largo e seguro)
            elementoRelatorio.style.width = '1000px';
            elementoRelatorio.style.maxWidth = '1000px';

            // 3. Remove restrições de overflow da tabela
            if (divTabela) divTabela.classList.remove('table-responsive');

            // 4. Manda o Chart.js preencher os novos 1000px
            if (monthlyChartInstance) monthlyChartInstance.resize();

            // 5. Opções de captura (Aqui está a grande jogada)
            const opt = {
                margin: 10, // Volta aos 10mm de margem bonita
                filename: 'Relatorio_Internet_' + filenameLabel + '.pdf',
                image: { type: 'jpeg', quality: 0.98 },
                html2canvas: {
                    scale: 2,
                    useCORS: true,
                    logging: false,
                    // Garante que o canvas fotografa exatamente a área de 1000px, ignorando o ecrã
                    width: 1000,
                    windowWidth: 1000
                },
                // O jsPDF vai pegar nessa imagem de 1000px e esmagá-la perfeitamente para caber num A4
                jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' }
            };

            // 6. Aumentei o timeout para 500ms para dar tempo do gráfico se redesenhar 100%
            setTimeout(function () {
                btnPdf.innerHTML = '⏳ Gerando Documento...';

                html2pdf().set(opt).from(elementoRelatorio).save().then(() => {
                    // 7. Reverte para o estado responsivo da tela
                    elementoRelatorio.style.width = originalWidth;
                    elementoRelatorio.style.maxWidth = originalMaxWidth;

                    if (divTabela) divTabela.classList.add('table-responsive');
                    if (monthlyChartInstance) monthlyChartInstance.resize();

                    btnPdf.innerHTML = btnOriginalText;
                    btnPdf.disabled = false;
                });
            }, 500);
        });
    }
});