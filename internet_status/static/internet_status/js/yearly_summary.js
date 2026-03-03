document.addEventListener('DOMContentLoaded', function () {
    function getDjangoData(id) {
        const el = document.getElementById(id);
        return el ? JSON.parse(el.textContent) : [];
    }

    const labels = getDjangoData('monthLabels');
    const down = getDjangoData('monthlyDown');
    const up = getDjangoData('monthlyUp');

    const CONTRACTED_DOWN = parseFloat(document.getElementById('contractedDown')?.textContent) || 0;
    const CONTRACTED_UP = parseFloat(document.getElementById('contractedUp')?.textContent) || 0;
    const lineContratadoDown = Array(labels.length).fill(CONTRACTED_DOWN);
    const lineContratadoUp = Array(labels.length).fill(CONTRACTED_UP);

    // 1. Velocidade Média
    const speedChartEl = document.getElementById('yearlySpeedChart');
    if (speedChartEl) {
        new Chart(speedChartEl, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    { label: 'Download Médio (Mbps)', data: down, backgroundColor: 'rgba(13, 110, 253, 0.8)' },
                    { label: 'Download Contratado', data: lineContratadoDown, type: 'line', borderColor: '#0d6efd', borderDash: [5, 5], pointRadius: 0, fill: false, borderWidth: 2 },
                    { label: 'Upload Médio (Mbps)', data: up, backgroundColor: 'rgba(13, 202, 240, 0.8)' },
                    { label: 'Upload Contratado', data: lineContratadoUp, type: 'line', borderColor: '#0dcaf0', borderDash: [5, 5], pointRadius: 0, fill: false, borderWidth: 2 }
                ]
            },
            options: { responsive: true, interaction: { mode: 'index', intersect: false } }
        });
    }

    // 2. Cumprimento de Velocidade
    const downAchieved = getDjangoData('monthlyDownAchievedPct');
    const downNotAchieved = getDjangoData('monthlyDownNotAchievedPct');
    const upAchieved = getDjangoData('monthlyUpAchievedPct');
    const upNotAchieved = getDjangoData('monthlyUpNotAchievedPct');

    const achievedChartEl = document.getElementById('yearlySpeedAchievedChart');
    if (achievedChartEl) {
        new Chart(achievedChartEl, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    { label: 'Download Atingido (%)', data: downAchieved, backgroundColor: '#0d6efd', stack: 'Stack 0' },
                    { label: 'Download Abaixo (%)', data: downNotAchieved, backgroundColor: '#8b0000', stack: 'Stack 0' },
                    { label: 'Upload Atingido (%)', data: upAchieved, backgroundColor: '#0dcaf0', stack: 'Stack 1' },
                    { label: 'Upload Abaixo (%)', data: upNotAchieved, backgroundColor: '#8b0000', stack: 'Stack 1' }
                ]
            },
            options: { responsive: true, scales: { x: { stacked: true }, y: { stacked: true, min: 0, max: 100 } } }
        });
    }

    // 3. Estabilidade
    const conn = getDjangoData('monthlyConnPct');
    const unst = getDjangoData('monthlyUnstPct');
    const disc = getDjangoData('monthlyDiscPct');

    const pingChartEl = document.getElementById('yearlyPingChart');
    if (pingChartEl) {
        new Chart(pingChartEl, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    { label: 'Conectado (%)', data: conn, backgroundColor: '#198754' },
                    { label: 'Instável (%)', data: unst, backgroundColor: '#ffc107' },
                    { label: 'Queda (%)', data: disc, backgroundColor: '#dc3545' }
                ]
            },
            options: { responsive: true, scales: { x: { stacked: true }, y: { stacked: true, min: 0, max: 100 } } }
        });
    }

    // Escuta mudanças no select de ano
    const autoSubmitSelects = document.querySelectorAll('.auto-submit');
    autoSubmitSelects.forEach(select => {
        select.addEventListener('change', function () {
            this.form.submit();
        });
    });
});
