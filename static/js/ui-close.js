(function () {
    'use strict';

    document.addEventListener('keydown', function (event) {
        if (event.key !== 'Escape') return;

        var panel = document.querySelector('[data-card-panel]');
        if (panel) {
            var close = panel.querySelector('[data-card-close]');
            if (close) close.click();
            return;
        }

        var openDetails = Array.from(document.querySelectorAll('details[open]'));
        if (openDetails.length) {
            openDetails[openDetails.length - 1].removeAttribute('open');
            event.preventDefault();
        }
    });
})();
