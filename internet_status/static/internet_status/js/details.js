document.addEventListener("DOMContentLoaded", function () {
    // Função auxiliar para ler os dados do json_script do Django
    function getDjangoData(elementId) {
        const element = document.getElementById(elementId);
        return element ? JSON.parse(element.textContent) : [];
    }

    // Lendo os dados de Velocidade
    const speedLabels = getDjangoData('speedLabels');
    const downloadData = getDjangoData('downloadData');
    const uploadData = getDjangoData('uploadData');

    // Desenhando o Gráfico de Velocidade
    const ctxSpeed = document.getElementById('speedChart');
    if (ctxSpeed) {
        new Chart(ctxSpeed, {
            type: 'line',
            data: {
                labels: speedLabels,
                datasets: [
                    {
                        label: 'Download (Mbps)',
                        data: downloadData,
                        borderColor: '#0d6efd', // Azul Bootstrap
                        backgroundColor: 'rgba(13, 110, 253, 0.1)',
                        fill: true,
                        tension: 0.3 // Deixa a linha curvada
                    },
                    {
                        label: 'Upload (Mbps)',
                        data: uploadData,
                        borderColor: '#0dcaf0', // Info Bootstrap
                        backgroundColor: 'transparent',
                        tension: 0.3
                    }
                ]
            },
            options: { responsive: true }
        });
    }

    // Lendo e Desenhando o Gráfico de Estabilidade (Ping)
    const pingLabels = getDjangoData('pingLabels');
    const pingData = getDjangoData('pingData');
    const ctxPing = document.getElementById('pingChart');

    if (ctxPing) {
        new Chart(ctxPing, {
            type: 'line',
            data: {
                labels: pingLabels,
                datasets: [{
                    label: 'Sucesso do Ping (%)',
                    data: pingData,
                    borderColor: '#198754', // Verde Bootstrap
                    backgroundColor: 'rgba(25, 135, 84, 0.2)',
                    fill: true,
                    stepped: true // Faz o gráfico em "degraus", ótimo para estabilidade
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        min: 0,
                        max: 100 // Trava o eixo Y entre 0% e 100%
                    }
                }
            }
        });
    }
});
