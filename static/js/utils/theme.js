export class ThemeManager {
  constructor() {
    this.themeBtn = document.getElementById('themeToggleBtn');
    this.currentTheme = localStorage.getItem('folio_theme') || 'light';
    this.init();
  }

  init() {
    this.applyTheme(this.currentTheme);
    if (this.themeBtn) {
      this.themeBtn.addEventListener('click', () => {
        const nextTheme = this.currentTheme === 'light' ? 'dark' : 'light';
        this.applyTheme(nextTheme);
      });
    }
  }

  applyTheme(theme) {
    this.currentTheme = theme;
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('folio_theme', theme);
    if (this.themeBtn) {
      this.themeBtn.textContent = theme === 'light' ? '🌙' : '☀️';
    }
  }
}
