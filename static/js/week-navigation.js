/* Keyboard shortcuts for the week navigator. */
(function () {
    function isEditable(element) {
        return element.matches('input, textarea, select, [contenteditable="true"]') ||
            element.closest('dialog, [role="dialog"], [data-calendar-popover]');
    }

    document.addEventListener('keydown', function (event) {
        if (isEditable(document.activeElement)) return;

        var navigation = document.querySelector('[data-week-navigation]');
        if (!navigation) return;

        var link;
        if (event.key === 'ArrowLeft') link = navigation.querySelector('[data-week-previous]');
        if (event.key === 'ArrowRight') link = navigation.querySelector('[data-week-next]');
        if (event.key === 'Home' && navigation.contains(document.activeElement)) {
            link = navigation.querySelector('[data-week-today]');
        }
        if (!link) return;

        event.preventDefault();
        window.location.assign(link.href);
    });
})();
