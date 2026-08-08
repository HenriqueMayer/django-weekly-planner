/* Keep card-panel focus predictable across HTMX swaps. */
(function () {
    var opener = null;

    document.body.addEventListener('htmx:beforeRequest', function (event) {
        if (event.detail.target && event.detail.target.id === 'card-panel') {
            opener = document.activeElement;
        }
    });

    document.body.addEventListener('htmx:afterSwap', function (event) {
        if (!event.detail.target || event.detail.target.id !== 'card-panel') return;
        var close = event.detail.target.querySelector('[data-card-close]');
        if (close) close.focus();
    });

    document.addEventListener('click', function (event) {
        var close = event.target.closest('[data-card-close]');
        if (!close) return;
        var panel = close.closest('[data-card-panel]');
        if (panel) panel.remove();
        if (opener && document.contains(opener)) opener.focus();
        opener = null;
    });

    document.addEventListener('keydown', function (event) {
        if (event.key !== 'Escape') return;
        var panel = document.querySelector('[data-card-panel]');
        if (!panel) return;
        var close = panel.querySelector('[data-card-close]');
        if (close) close.click();
    });
})();
