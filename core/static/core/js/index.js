document.addEventListener('DOMContentLoaded', () => {
    console.log("Portfólio carregado.");

    // Acopla o botão de tema da versão Desktop da Home ao script global theme.js
    const themeBtnDesktop = document.getElementById('theme-toggle-desktop');
    if (themeBtnDesktop) {
        const currentTheme = document.documentElement.getAttribute('data-bs-theme');
        themeBtnDesktop.innerHTML = currentTheme === 'dark' ? '☀️' : '🌙';

        themeBtnDesktop.addEventListener('click', () => {
            const current = document.documentElement.getAttribute('data-bs-theme');
            const newTheme = current === 'dark' ? 'light' : 'dark';

            localStorage.setItem('theme', newTheme);
            document.documentElement.setAttribute('data-bs-theme', newTheme);
            window.dispatchEvent(new Event('themeChanged'));

            themeBtnDesktop.innerHTML = newTheme === 'dark' ? '☀️' : '🌙';

            // Atualiza o botão mobile para ficar em sincronia
            const themeBtnMobile = document.getElementById('theme-toggle');
            if (themeBtnMobile) themeBtnMobile.innerHTML = newTheme === 'dark' ? '☀️' : '🌙';
        });
    }
});
