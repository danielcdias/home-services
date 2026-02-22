document.addEventListener("DOMContentLoaded", function() {
    console.log("Sistema Home Services inicializado com sucesso.");

    // Configuração do Auto-Refresh do Dashboard
    const timerElement = document.getElementById('refresh-timer');
    
    if (timerElement) {
        let timeLeft = 60; // Recarrega a página a cada 60 segundos
        
        setInterval(function() {
            timeLeft -= 1;
            timerElement.textContent = timeLeft;
            
            if (timeLeft <= 0) {
                // Atualiza a página mantendo o cache ignorado
                window.location.reload();
            }
        }, 1000); // 1000 milissegundos = 1 segundo
    }
});
