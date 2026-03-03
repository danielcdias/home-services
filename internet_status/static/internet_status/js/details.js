document.addEventListener('DOMContentLoaded', function () {

    // ==========================================
    // 1. LÓGICA DOS GRÁFICOS (CHART.JS)
    // ==========================================
    function getDjangoData(id) {
        const el = document.getElementById(id);
        return el ? JSON.parse(el.textContent) : [];
    }

    const labels = getDjangoData('dailyLabels');

    // Gráfico 1: Desempenho Médio Diário
    const speedChartEl = document.getElementById('speedChart');
    if (speedChartEl) {
        const down = getDjangoData('dailyDown');
        const up = getDjangoData('dailyUp');
        const contractedDown = parseFloat(document.getElementById('contractedDown')?.textContent) || 0;
        const contractedUp = parseFloat(document.getElementById('contractedUp')?.textContent) || 0;

        const lineContratadoDown = Array(labels.length).fill(contractedDown);
        const lineContratadoUp = Array(labels.length).fill(contractedUp);

        new Chart(speedChartEl, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    { label: 'Download (Mbps)', data: down, borderColor: '#0d6efd', backgroundColor: 'rgba(13, 110, 253, 0.1)', fill: true, tension: 0.3 },
                    { label: 'Upload (Mbps)', data: up, borderColor: '#0dcaf0', backgroundColor: 'rgba(13, 202, 240, 0.1)', fill: true, tension: 0.3 },
                    { label: 'Download Contratado', data: lineContratadoDown, type: 'line', borderColor: '#0d6efd', borderDash: [5, 5], pointRadius: 0, fill: false, borderWidth: 2 },
                    { label: 'Upload Contratado', data: lineContratadoUp, type: 'line', borderColor: '#0dcaf0', borderDash: [5, 5], pointRadius: 0, fill: false, borderWidth: 2 }
                ]
            },
            options: { responsive: true, interaction: { mode: 'index', intersect: false } }
        });
    }

    // Gráfico 2: Cumprimento da Velocidade
    const speedAchievedChartEl = document.getElementById('speedAchievedChart');
    if (speedAchievedChartEl) {
        const downAchieved = getDjangoData('dailyDownAchievedPct');
        const downNotAchieved = getDjangoData('dailyDownNotAchievedPct');
        const upAchieved = getDjangoData('dailyUpAchievedPct');
        const upNotAchieved = getDjangoData('dailyUpNotAchievedPct');

        new Chart(speedAchievedChartEl, {
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

    // Gráfico 3: Estabilidade Diária (Ping)
    const pingChartEl = document.getElementById('pingChart');
    if (pingChartEl) {
        const conn = getDjangoData('dailyConnPct');
        const unst = getDjangoData('dailyUnstPct');
        const disc = getDjangoData('dailyDiscPct');

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

    // ==========================================
    // 2. LÓGICA DO AUTO-SUBMIT (SELECT DE MÊS)
    // ==========================================
    const autoSubmitSelects = document.querySelectorAll('.auto-submit');
    autoSubmitSelects.forEach(select => {
        select.addEventListener('change', function () {
            this.form.submit();
        });
    });

    // ==========================================
    // 3. LÓGICA DO TOOLTIP GLOBAL E DINÂMICO
    // ==========================================
    const tooltipBox = document.createElement('div');
    tooltipBox.className = 'dcd-global-tooltip';
    document.body.appendChild(tooltipBox);

    const rows = document.querySelectorAll('.dcd-tooltip-row');

    rows.forEach(row => {
        row.addEventListener('mouseenter', function () {
            const contentElement = this.querySelector('.tooltip-content-html');
            if (!contentElement) return;

            // Injeta o conteúdo oculto da linha no balão global
            tooltipBox.innerHTML = contentElement.innerHTML;
            tooltipBox.classList.add('visible');

            // Calcula a posição geométrica da linha (<tr>)
            const rect = this.getBoundingClientRect();

            // Centraliza horizontalmente e coloca um pouco acima da linha
            let top = rect.top + window.scrollY - tooltipBox.offsetHeight - 10;
            const left = rect.left + window.scrollX + (rect.width / 2) - (tooltipBox.offsetWidth / 2);

            // Prevenção de corte na borda superior da janela
            if (top < window.scrollY) {
                top = rect.bottom + window.scrollY + 10;
                tooltipBox.classList.add('tooltip-bottom');
            } else {
                tooltipBox.classList.remove('tooltip-bottom');
            }

            tooltipBox.style.top = `${top}px`;
            tooltipBox.style.left = `${left}px`;
        });

        row.addEventListener('mouseleave', function () {
            tooltipBox.classList.remove('visible');
            setTimeout(() => {
                if (!tooltipBox.classList.contains('visible')) {
                    tooltipBox.innerHTML = '';
                }
            }, 150);
        });
    });
});
