const getPreferredTheme = () => {
    const storedTheme = localStorage.getItem('theme')
    if (storedTheme) {
        return storedTheme
    }
    // Se não tiver salvo, segue a preferência do Windows/Mac/Linux do usuário
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

const setTheme = (theme) => {
    if (theme === 'auto' && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        document.documentElement.setAttribute('data-bs-theme', 'dark')
    } else {
        document.documentElement.setAttribute('data-bs-theme', theme)
    }
    // Dispara um evento global para avisar os gráficos (Chart.js) que o tema mudou
    window.dispatchEvent(new Event('themeChanged'));
}

// 1. Aplica o tema Imediatamente para evitar o "Flash Branco" (FOUC)
setTheme(getPreferredTheme())

// 2. Lógica do Botão de Troca (Executado após o DOM carregar)
document.addEventListener('DOMContentLoaded', () => {
    const themeToggleBtn = document.getElementById('theme-toggle');

    if (themeToggleBtn) {
        // Atualiza o ícone inicial
        const currentTheme = document.documentElement.getAttribute('data-bs-theme');
        themeToggleBtn.innerHTML = currentTheme === 'dark' ? '☀️' : '🌙';

        // Evento de clique
        themeToggleBtn.addEventListener('click', () => {
            const currentTheme = document.documentElement.getAttribute('data-bs-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

            localStorage.setItem('theme', newTheme);
            setTheme(newTheme);

            // Troca o ícone do botão
            themeToggleBtn.innerHTML = newTheme === 'dark' ? '☀️' : '🌙';
        });
    }
});
