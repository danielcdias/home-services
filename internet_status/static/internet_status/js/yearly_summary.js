document.addEventListener('DOMContentLoaded', function () {
    function getDjangoData(id) {
        const el = document.getElementById(id);
        return el ? JSON.parse(el.textContent) : [];
    }

    const labels = getDjangoData('monthLabels');
    const activeCharts = [];

    // --- CONFIGURAÇÃO GLOBAL INICIAL DE CORES DO CHART.JS ---
    const updateChartColors = () => {
        const isDark = document.documentElement.getAttribute('data-bs-theme') === 'dark';

        // Uso estrito de hexadecimais para garantir alto contraste nos labels
        const textColor = isDark ? '#e9ecef' : '#212529';
        const gridColor = isDark ? '#495057' : '#dee2e6';

        Chart.defaults.color = textColor;
        Chart.defaults.borderColor = gridColor;

        if (Chart.defaults.scale) {
            Chart.defaults.scale.ticks.color = textColor;
            Chart.defaults.scale.grid.color = gridColor;
        }
    };
    updateChartColors();

    const speedChartEl = document.getElementById('yearlySpeedChart');
    if (speedChartEl) {
        const down = getDjangoData('monthlyDown');
        const up = getDjangoData('monthlyUp');
        const CONTRACTED_DOWN = parseFloat(document.getElementById('contractedDown')?.textContent) || 0;
        const CONTRACTED_UP = parseFloat(document.getElementById('contractedUp')?.textContent) || 0;
        const lineContratadoDown = Array(labels.length).fill(CONTRACTED_DOWN);
        const lineContratadoUp = Array(labels.length).fill(CONTRACTED_UP);

        const speedChart = new Chart(speedChartEl, {
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
        activeCharts.push(speedChart);
    }

    const achievedChartEl = document.getElementById('yearlySpeedAchievedChart');
    if (achievedChartEl) {
        const downAchieved = getDjangoData('monthlyDownAchievedPct');
        const downNotAchieved = getDjangoData('monthlyDownNotAchievedPct');
        const upAchieved = getDjangoData('monthlyUpAchievedPct');
        const upNotAchieved = getDjangoData('monthlyUpNotAchievedPct');

        const achievedChart = new Chart(achievedChartEl, {
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
        activeCharts.push(achievedChart);
    }

    const pingChartEl = document.getElementById('yearlyPingChart');
    if (pingChartEl) {
        const conn = getDjangoData('monthlyConnPct');
        const unst = getDjangoData('monthlyUnstPct');
        const disc = getDjangoData('monthlyDiscPct');

        const pingChart = new Chart(pingChartEl, {
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
        activeCharts.push(pingChart);
    }

    // --- REAGE À MUDANÇA DE TEMA ---
    window.addEventListener('themeChanged', () => {
        updateChartColors();
        activeCharts.forEach(chart => {
            // Força a atualização profunda nas opções de eixos (X e Y) de cada gráfico
            if (chart.options.scales) {
                Object.values(chart.options.scales).forEach(scale => {
                    if (scale.ticks) scale.ticks.color = Chart.defaults.color;
                    if (scale.grid) scale.grid.color = Chart.defaults.borderColor;
                });
            }
            chart.update();
        });
    });

    const autoSubmitSelects = document.querySelectorAll('.auto-submit');
    autoSubmitSelects.forEach(select => {
        select.addEventListener('change', function () {
            this.form.submit();
        });
    });
});
