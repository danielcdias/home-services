document.addEventListener("DOMContentLoaded", function () {
    // 1. Embeleza os Inputs de Texto e Senha
    const inputs = document.querySelectorAll('form input[type="text"], form input[type="password"], form input[type="number"], form select');
    inputs.forEach(input => {
        input.className = 'form-control bg-body text-body';
    });

    // 2. Coleta TODOS os elementos de ação (botões e links)
    const actions = document.querySelectorAll('form button, form input[type="submit"], main.container a');

    actions.forEach(el => {
        // Pega o texto visível no botão ou link, em minúsculas
        const text = (el.textContent || el.value || '').toLowerCase().trim();

        // Ignora campos escondidos estruturais
        if (el.type === 'hidden' || el.style.display === 'none' || el.hasAttribute('hidden')) return;

        // Se o botão estiver nativamente desabilitado (ex: botão voltar na 1ª tela), esconde ele de vez
        if (el.disabled) {
            el.style.display = 'none';
            return;
        }

        // ==========================================
        // FORMATAÇÃO BASEADA NO TEXTO DO BOTÃO
        // ==========================================
        if (text.includes('cancelar')) {
            // w-100 (largura total) e mt-3 (cria o espaço entre este botão e o de cima)
            el.className = 'btn btn-outline-danger w-100 fw-bold py-2 mt-3';
            el.setAttribute('formnovalidate', 'formnovalidate'); // Permite clicar sem validar senha
        }
        else if (text.includes('voltar')) {
            el.className = 'btn btn-secondary w-100 fw-bold py-2 text-white mt-3';
            el.setAttribute('formnovalidate', 'formnovalidate'); // Permite voltar sem validar o token
        }
        else if (text.includes('avançar') || text.includes('entrar') || text.includes('confirmar') || text.includes('próximo')) {
            el.className = 'btn btn-primary w-100 fw-bold py-2 mt-3';
        }
        else if (el.tagName.toLowerCase() === 'a') {
            // Outros links secundários
            el.className = 'btn btn-outline-secondary w-100 py-2 mt-3 text-decoration-none';
        }

        // Garante que o CSS não vai espremer o elemento
        el.style.display = 'block';
    });
});
