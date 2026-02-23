document.addEventListener("DOMContentLoaded", function () {
    function getDjangoData(elementId) {
        const element = document.getElementById(elementId);
        return element ? JSON.parse(element.textContent) : [];
    }

    function getStringData(elementId) {
        const element = document.getElementById(elementId);
        return element ? JSON.parse(element.textContent) : 'atual';
    }

    // 1. Gráficos Recentes
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
            options: { responsive: true } // Mantém a responsividade natural da col-12
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

    // 2. Gráfico Mensal Combinado
    const monthlyLabels = getDjangoData('monthlyLabels');
    const monthlyDown = getDjangoData('monthlyDown');
    const monthlyUp = getDjangoData('monthlyUp');
    const monthlyPing = getDjangoData('monthlyPing');
    const ctxMonthly = document.getElementById('monthlyChart');

    if (ctxMonthly) {
        new Chart(ctxMonthly, {
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

    // 3. Geração do Relatório em PDF com nome dinâmico
    const btnPdf = document.getElementById('btn-gerar-pdf');
    const filenameLabel = getStringData('filenameLabel');

    if (btnPdf) {
        btnPdf.addEventListener('click', function () {
            const btnOriginalText = btnPdf.innerHTML;
            btnPdf.innerHTML = '⏳ Gerando Documento...';
            btnPdf.disabled = true;

            const elementoRelatorio = document.getElementById('relatorio-conteudo');

            const opt = {
                margin: 10,
                filename: 'Relatorio_Internet_' + filenameLabel + '.pdf', // Aplica o nome dinâmico (ex: 2026_02)
                image: { type: 'jpeg', quality: 0.98 },
                html2canvas: { scale: 2, useCORS: true },
                jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' }
            };

            html2pdf().set(opt).from(elementoRelatorio).save().then(() => {
                btnPdf.innerHTML = btnOriginalText;
                btnPdf.disabled = false;
            });
        });
    }
});
