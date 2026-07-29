/**
 * Block text contrast (PRD 7.2.2).
 *
 * Users pick arbitrary hex colors for a block's background
 * (`apps/planner/models.py`'s `BlockColor.hex_code`), so the label text
 * needs a computed, readable foreground rather than a fixed color. Every
 * `<td>` with a custom background carries `data-bg-hex="#RRGGBB"`
 * (`planner/partials/block_cell.html`) -- this file computes each one's
 * relative luminance (WCAG's own formula) and toggles between `text-white`
 * and `text-slate-900` on that same element.
 *
 * Runs once immediately (this script tag loads after the grid table has
 * already been parsed, same placement convention as static/js/theme.js), and
 * again on every `htmx:afterSettle` (verified via Context7: fires once the
 * swapped-in DOM has settled), so blocks swapped in by any create/edit/
 * delete/resize response get the same treatment as the initial page load --
 * not just the first paint.
 *
 * No application state lives here -- only DOM classes are read/written,
 * recomputed fresh from each element's own `data-bg-hex` every time.
 */
(function () {
    'use strict';

    function relativeLuminanceComponent(channel) {
        var normalized = channel / 255;
        return normalized <= 0.03928
            ? normalized / 12.92
            : Math.pow((normalized + 0.055) / 1.055, 2.4);
    }

    function relativeLuminance(hex) {
        var r = parseInt(hex.slice(1, 3), 16);
        var g = parseInt(hex.slice(3, 5), 16);
        var b = parseInt(hex.slice(5, 7), 16);
        return (
            0.2126 * relativeLuminanceComponent(r) +
            0.7152 * relativeLuminanceComponent(g) +
            0.0722 * relativeLuminanceComponent(b)
        );
    }

    function applyContrast(root) {
        var scope = root && root.querySelectorAll ? root : document;
        var cells = scope.querySelectorAll('[data-bg-hex]');
        cells.forEach(function (cell) {
            var hex = cell.getAttribute('data-bg-hex');
            if (!/^#[0-9A-Fa-f]{6}$/.test(hex)) {
                return;
            }
            // 0.179 is the standard "does this background read as light or
            // dark" luminance threshold (the point past which black text
            // reads better than white per WCAG's own contrast-ratio math),
            // not a full per-pairing contrast-ratio computation -- a
            // deliberately simple, good-enough rule per PRD 7.2.2's own
            // wording ("white/black text").
            var isLight = relativeLuminance(hex) > 0.179;
            cell.classList.toggle('text-slate-900', isLight);
            cell.classList.toggle('text-white', !isLight);
        });
    }

    applyContrast(document);

    document.body.addEventListener('htmx:afterSettle', function (evt) {
        applyContrast(evt.detail.elt);
    });
})();
