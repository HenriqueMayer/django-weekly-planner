/**
 * Color-picker/hex-text sync (PRD FR-13, 7.1.1/7.1.2).
 *
 * `color_form_row.html` pairs a native `<input type="color">` with a
 * plain hex `<input type="text">` sharing a `data-hex-sync="<group>"`
 * attribute value -- this file keeps the two in sync bidirectionally.
 *
 * Document-level delegation, not per-element listeners, for the exact
 * same reason `static/js/grid-drag.js` already documents: every color
 * CRUD success swaps `#palette-panel` wholesale (`hx-swap="outerHTML"`),
 * which replaces these input elements with brand-new DOM nodes -- a
 * directly-bound listener would silently stop working the moment a user
 * saves once and the panel re-renders. Delegating from `document` means
 * there is nothing to re-bind after a swap, ever.
 *
 * No application state lives here -- only DOM values are read/written,
 * looked up fresh by `data-hex-sync` on every `input` event.
 */
(function () {
    'use strict';

    var HEX_PATTERN = /^#[0-9A-Fa-f]{6}$/;

    document.addEventListener('input', function (evt) {
        var el = evt.target;
        if (!el.matches('[data-hex-sync]')) {
            return;
        }
        var group = el.dataset.hexSync;
        document.querySelectorAll('[data-hex-sync="' + group + '"]').forEach(function (partner) {
            if (partner === el) {
                return;
            }
            if (el.type === 'color') {
                // Native color inputs always yield a valid lowercase
                // #rrggbb -- the model's own HEX_COLOR_VALIDATOR
                // (apps/planner/models.py) accepts both cases, so no
                // normalization is needed here.
                partner.value = el.value;
            } else if (HEX_PATTERN.test(el.value)) {
                // Only push a *fully valid* typed hex into the native
                // color input -- a partial/in-progress string would be
                // silently clamped or rejected by the browser control
                // anyway, and syncing on every keystroke would fight the
                // user mid-edit.
                partner.value = el.value;
            }
        });
    });
})();
