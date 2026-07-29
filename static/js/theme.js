/**
 * Theme toggle (PRD 1.4.4 / FR-14).
 *
 * The `dark` class on <html> is already applied before first paint by the
 * small synchronous inline script in templates/base.html's <head> (that is
 * what prevents a flash of the wrong theme). This file only has to:
 *   1. wire up the #theme-toggle button to flip that class, and
 *   2. persist the user's explicit choice to localStorage.
 *
 * No application state lives here — only a DOM class and a localStorage
 * value are read/written.
 */
(function () {
    var STORAGE_KEY = 'theme';
    var root = document.documentElement;
    var toggle = document.getElementById('theme-toggle');

    if (!toggle) {
        return;
    }

    toggle.addEventListener('click', function () {
        var isDark = root.classList.toggle('dark');
        localStorage.setItem(STORAGE_KEY, isDark ? 'dark' : 'light');
    });
})();
