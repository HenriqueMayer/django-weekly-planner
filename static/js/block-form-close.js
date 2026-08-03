/**
 * Click-away close for the inline block form (PRD 6.1.2/6.2.1).
 *
 * The create/edit form (`planner/partials/block_form.html`) only ever
 * closed via its own Save/Cancel buttons. Leaving it open while clicking
 * other cells let a user accumulate several inline forms at once -- each
 * one a separate `<td id="block-form">` swapped in by htmx -- so clicking
 * around the grid opened "more and more" of them. This file makes the
 * open form dismiss itself on any click outside it, which also means the
 * act of opening a new form (clicking another empty/block cell) closes
 * whatever was already open: no stacking.
 *
 * Event delegation lives on `document` for the same reason grid-drag.js
 * delegates: htmx swaps the form's `<td>` in and out wholesale, so a
 * listener bound to the form itself would silently go stale the moment
 * the grid re-renders. `document` is never swapped out.
 *
 * The close is performed by clicking the form's own Cancel button
 * (`[data-block-cancel]`, rendered by `partials/buttons/secondary.html`
 * via its `data_block_cancel` flag -- the same fixed-attribute pattern
 * as the `data_export_*` flags). Reusing that button rather than
 * re-implementing the cancel URL keeps the create-mode
 * (cell-cancel?day/start/end) and edit-mode (block-cancel pk) paths in
 * exactly one place each, in the template that already builds them. The
 * programmatic `.click()` dispatches a real click event, which htmx
 * handles like any other -- no application state or URL logic lives in
 * this file.
 *
 * Reentrancy: the synthetic click this file fires has the Cancel button
 * as its target, which is *inside* the form, so `form.contains()` guards
 * the handler from re-running on its own click and looping.
 */
(function () {
    'use strict';

    document.addEventListener('click', function (evt) {
        var form = document.getElementById('block-form');
        if (!form || form.contains(evt.target)) {
            return;
        }
        var cancel = form.querySelector('[data-block-cancel]');
        if (cancel) {
            cancel.click();
        }
    });
})();
