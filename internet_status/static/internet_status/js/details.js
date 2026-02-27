document.addEventListener("DOMContentLoaded", function () {
    function getDjangoData(elementId) {
        const element = document.getElementById(elementId);
        return element ? JSON.parse(element.textContent) : [];
    }

    function getStringData(elementId) {
        const element = document.getElementById(elementId);
        return element ? JSON.parse(element.textContent) : 'atual';
    }

    const dailyLabels = getDjangoData('dailyLabels');

    const CONTRACTED_DOWN = parseFloat(document.getElementById('contractedDown')?.textContent) || 0;
    const CONTRACTED_UP = parseFloat(document.getElementById('contractedUp')?.textContent) || 0;

    let speedChartInstance = null;
    let speedAchievedChartInstance = null;
    let pingChartInstance = null;

    // ==========================================
    // 1. Gráfico de Velocidade Absoluta
    // ==========================================
    const ctxSpeed = document.getElementById('speedChart');
    if (ctxSpeed) {
        const dailyDown = getDjangoData('dailyDown');
        const dailyUp = getDjangoData('dailyUp');
        const lineContratadoDown = Array(dailyLabels.length).fill(CONTRACTED_DOWN);
        const lineContratadoUp = Array(dailyLabels.length).fill(CONTRACTED_UP);

        speedChartInstance = new Chart(ctxSpeed, {
            type: 'line',
            data: {
                labels: dailyLabels,
                datasets: [
                    { label: 'Download Medido', data: dailyDown, borderColor: '#0d6efd', backgroundColor: 'rgba(13, 110, 253, 0.1)', fill: true, tension: 0.3 },
                    { label: 'Download Contratado', data: lineContratadoDown, borderColor: '#0d6efd', borderDash: [5, 5], pointRadius: 0, fill: false, borderWidth: 2 },
                    { label: 'Upload Medido', data: dailyUp, borderColor: '#0dcaf0', backgroundColor: 'transparent', tension: 0.3 },
                    { label: 'Upload Contratado', data: lineContratadoUp, borderColor: '#0dcaf0', borderDash: [5, 5], pointRadius: 0, fill: false, borderWidth: 2 }
                ]
            },
            options: { responsive: true, interaction: { mode: 'index', intersect: false } }
        });
    }

    // ==========================================
    // 2. Gráfico de Cumprimento da Velocidade
    // ==========================================
    const ctxSpeedAchieved = document.getElementById('speedAchievedChart');
    if (ctxSpeedAchieved) {
        const dailyDownAchieved = getDjangoData('dailyDownAchievedPct');
        const dailyDownNotAchieved = getDjangoData('dailyDownNotAchievedPct');
        const dailyUpAchieved = getDjangoData('dailyUpAchievedPct');
        const dailyUpNotAchieved = getDjangoData('dailyUpNotAchievedPct');

        speedAchievedChartInstance = new Chart(ctxSpeedAchieved, {
            type: 'bar',
            data: {
                labels: dailyLabels,
                datasets: [
                    { label: 'Download Atingido (%)', data: dailyDownAchieved, backgroundColor: '#0d6efd', stack: 'Stack 0' },
                    { label: 'Download Abaixo (%)', data: dailyDownNotAchieved, backgroundColor: '#dc3545', stack: 'Stack 0' },
                    { label: 'Upload Atingido (%)', data: dailyUpAchieved, backgroundColor: '#0dcaf0', stack: 'Stack 1' },
                    { label: 'Upload Abaixo (%)', data: dailyUpNotAchieved, backgroundColor: '#8b0000', stack: 'Stack 1' }
                ]
            },
            options: { responsive: true, scales: { x: { stacked: true }, y: { stacked: true, min: 0, max: 100 } } }
        });
    }

    // ==========================================
    // 3. Gráfico de Estabilidade
    // ==========================================
    const ctxPing = document.getElementById('pingChart');
    if (ctxPing) {
        const dailyConnPct = getDjangoData('dailyConnPct');
        const dailyUnstPct = getDjangoData('dailyUnstPct');
        const dailyDiscPct = getDjangoData('dailyDiscPct');

        pingChartInstance = new Chart(ctxPing, {
            type: 'bar',
            data: {
                labels: dailyLabels,
                datasets: [
                    { label: 'Conectado (%)', data: dailyConnPct, backgroundColor: '#198754' },
                    { label: 'Instável (%)', data: dailyUnstPct, backgroundColor: '#ffc107' },
                    { label: 'Queda (%)', data: dailyDiscPct, backgroundColor: '#dc3545' }
                ]
            },
            options: { responsive: true, scales: { x: { stacked: true }, y: { stacked: true, min: 0, max: 100 } } }
        });
    }

    // ==========================================
    // 4. Geração do Relatório em PDF (Nativo e Perfeito)
    // ==========================================
    const btnPdf = document.getElementById('btn-gerar-pdf');

    if (btnPdf) {
        btnPdf.addEventListener('click', function () {
            // Usa o recurso de impressão nativo com a diretiva CSS @media print
            // configurada no details.html para gerar o PDF sem erros de limite de renderização.
            window.print();
        });
    }
});
