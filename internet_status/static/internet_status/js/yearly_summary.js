document.addEventListener('DOMContentLoaded', function () {
    function getDjangoData(id) {
        const el = document.getElementById(id);
        return el ? JSON.parse(el.textContent) : [];
    }

    const rawLabels = getDjangoData('monthLabels');
    const rawDown = getDjangoData('monthlyDown');
    const rawUp = getDjangoData('monthlyUp');

    // Filtro para não exibir meses futuros (corta o array onde os dados param)
    let lastIdx = rawDown.length - 1;
    while (lastIdx >= 0 && rawDown[lastIdx] === 0 && rawUp[lastIdx] === 0) {
        lastIdx--;
    }
    if (lastIdx < 0) lastIdx = rawLabels.length - 1;

    const labels = rawLabels.slice(0, lastIdx + 1);
    const down = rawDown.slice(0, lastIdx + 1);
    const up = rawUp.slice(0, lastIdx + 1);

    const activeCharts = [];

    // --- CONFIGURAÇÃO GLOBAL INICIAL DE CORES DO CHART.JS ---
    const updateChartColors = () => {
        const isDark = document.documentElement.getAttribute('data-bs-theme') === 'dark';

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
        const contractedDown = parseFloat(document.getElementById('contractedDown')?.textContent) || 0;
        const contractedUp = parseFloat(document.getElementById('contractedUp')?.textContent) || 0;
        const minDown = parseFloat(document.getElementById('minDown')?.textContent) || 0;
        const minUp = parseFloat(document.getElementById('minUp')?.textContent) || 0;

        const speedChart = new Chart(speedChartEl, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Download Médio (Mbps)',
                        data: down,
                        borderColor: '#0d6efd',
                        backgroundColor: 'rgba(13, 110, 253, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.3
                    },
                    {
                        label: 'Upload Médio (Mbps)',
                        data: up,
                        borderColor: '#0dcaf0',
                        backgroundColor: 'rgba(13, 202, 240, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.3
                    },
                    {
                        label: 'Contratado (Download)',
                        data: Array(labels.length).fill(contractedDown),
                        borderColor: 'rgba(25, 135, 84, 0.5)',
                        borderWidth: 1.5,
                        borderDash: [5, 5],
                        pointRadius: 0,
                        pointHoverRadius: 0,
                        fill: false,
                        tension: 0
                    },
                    {
                        label: 'Contratado (Upload)',
                        data: Array(labels.length).fill(contractedUp),
                        borderColor: 'rgba(23, 162, 184, 0.5)',
                        borderWidth: 1.5,
                        borderDash: [5, 5],
                        pointRadius: 0,
                        pointHoverRadius: 0,
                        fill: false,
                        tension: 0
                    },
                    {
                        label: 'Limite Aceitável (Download)',
                        data: Array(labels.length).fill(minDown),
                        borderColor: 'rgba(220, 53, 69, 0.7)',
                        borderWidth: 1.5,
                        borderDash: [5, 5],
                        pointRadius: 0,
                        pointHoverRadius: 0,
                        fill: false,
                        tension: 0
                    },
                    {
                        label: 'Limite Aceitável (Upload)',
                        data: Array(labels.length).fill(minUp),
                        borderColor: 'rgba(253, 126, 20, 0.7)',
                        borderWidth: 1.5,
                        borderDash: [5, 5],
                        pointRadius: 0,
                        pointHoverRadius: 0,
                        fill: false,
                        tension: 0
                    }
                ]
            },
            options: { responsive: true, interaction: { mode: 'index', intersect: false } }
        });
        activeCharts.push(speedChart);
    }

    const speedAchievedChartEl = document.getElementById('yearlySpeedAchievedChart');
    if (speedAchievedChartEl) {
        const d_achieved = getDjangoData('monthlyDownAchievedPct').slice(0, lastIdx + 1);
        const d_not_achieved = getDjangoData('monthlyDownNotAchievedPct').slice(0, lastIdx + 1);
        const u_achieved = getDjangoData('monthlyUpAchievedPct').slice(0, lastIdx + 1);
        const u_not_achieved = getDjangoData('monthlyUpNotAchievedPct').slice(0, lastIdx + 1);

        const speedAchievedChart = new Chart(speedAchievedChartEl, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    { label: 'Download ≥ Contratado (%)', data: d_achieved, backgroundColor: '#198754', stack: 'Stack 0' },
                    { label: 'Download < Contratado (%)', data: d_not_achieved, backgroundColor: '#dc3545', stack: 'Stack 0' },
                    { label: 'Upload ≥ Contratado (%)', data: u_achieved, backgroundColor: '#0dcaf0', stack: 'Stack 1' },
                    { label: 'Upload < Contratado (%)', data: u_not_achieved, backgroundColor: '#ffc107', stack: 'Stack 1' }
                ]
            },
            options: { responsive: true, scales: { x: { stacked: true }, y: { stacked: true, min: 0, max: 100 } } }
        });
        activeCharts.push(speedAchievedChart);
    }

    const pingChartEl = document.getElementById('yearlyPingChart');
    if (pingChartEl) {
        const conn = getDjangoData('monthlyConnPct').slice(0, lastIdx + 1);
        const unst = getDjangoData('monthlyUnstPct').slice(0, lastIdx + 1);
        const disc = getDjangoData('monthlyDiscPct').slice(0, lastIdx + 1);

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
    autoSubmitSelects.forEach(select => select.addEventListener('change', function () { this.form.submit(); }));
});
