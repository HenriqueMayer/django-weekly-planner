/**
 * Grid export: PNG canvas render + print trigger (Sprint 10, new feature --
 * not FR-numbered, added on top of the already-complete Sprint 1-9 plan).
 *
 * Markdown/SVG export need no JS at all: both are plain `<a href>` links to
 * server endpoints (`planner:export-markdown`/`planner:export-svg`) that
 * already set their own `Content-Disposition: attachment` header, so the
 * browser's native download handling does all the work (see
 * apps/core/templates/core/dashboard.html's own Export-dropdown comment).
 * This file only exists for the two exports that genuinely have no
 * server-rendered resource to link to: a PNG is a canvas render of
 * whatever `#grid-table` looks like *right now* in this browser, and
 * "print" is not a resource at all, just the browser's own
 * `window.print()` API.
 *
 * Document-delegated click listener, not a listener bound directly to the
 * two trigger buttons -- the exact same correctness requirement
 * static/js/grid-drag.js's own module comment already documents: both
 * triggers live inside a toolbar `<details>` panel that (like every other
 * templated fragment on this page) could in principle be re-rendered by a
 * future change, and delegating from `document` means there is nothing to
 * ever re-bind.
 *
 * No application state lives here. `exportPng()` reads the live DOM fresh
 * on every click and returns as soon as the download is triggered; nothing
 * is cached between calls, and there is no server round trip at all for
 * either action -- both are pure client-side reads of what the browser has
 * already rendered and computed (NFR-08 does not apply here the way it
 * does to grid-drag.js's resize preview, since nothing here is ever
 * persisted).
 */
(function () {
    'use strict';

    function isDarkMode() {
        return document.documentElement.classList.contains('dark');
    }

    function surfaceColor() {
        // PRD §9.1's "Surface" token (mirrored in static/css/input.css's
        // own header comment: `white / slate-50` light, `slate-900 /
        // slate-800` dark) and templates/base.html's own `<body>` classes
        // (`bg-white dark:bg-slate-900`) -- hardcoded here as hex rather
        // than read via getComputedStyle(document.body), since the canvas
        // background must be filled before any cell is drawn on top of it
        // and a concrete color string is simplest. input.css documents no
        // custom `@theme` color overrides, so these two hex values are
        // exactly Tailwind's own default `white`/`slate-900` palette
        // entries, not a guess.
        return isDarkMode() ? '#0f172a' : '#ffffff';
    }

    function fallbackBorderColor() {
        // This project's own "Grid lines" token (static/css/input.css's
        // header comment: `slate-200` light / `slate-700` dark), used only
        // if a cell's own computed border color is unusable (transparent /
        // empty) -- a minor visual fallback, not a correctness concern.
        return isDarkMode() ? '#334155' : '#e2e8f0';
    }

    function isUsableColor(value) {
        return Boolean(value) && value !== 'transparent' && value.indexOf('rgba(0, 0, 0, 0)') === -1;
    }

    function drawCell(ctx, cell, tableRect) {
        var cellRect = cell.getBoundingClientRect();
        // Positioned relative to the table's own rect, not the viewport --
        // the canvas only represents the table itself, so this is the only
        // coordinate space that makes sense here, regardless of the
        // grid's on-screen scroll position (both rects are read at the
        // same instant, so the subtraction cancels any shared scroll
        // offset out).
        var x = cellRect.left - tableRect.left;
        var y = cellRect.top - tableRect.top;
        var width = cellRect.width;
        var height = cellRect.height;

        var computed = window.getComputedStyle(cell);

        // Reads whatever background the browser already resolved --
        // a block's own inline hex color, the neutral colorless-block
        // fallback, or a header/time-label surface tint -- with no
        // knowledge of this app's color logic needed here at all.
        ctx.fillStyle = computed.backgroundColor;
        ctx.fillRect(x, y, width, height);

        var borderColor = computed.borderColor;
        ctx.strokeStyle = isUsableColor(borderColor) ? borderColor : fallbackBorderColor();
        ctx.lineWidth = 1;
        // Inset by half a pixel so a 1px stroke doesn't get antialiased
        // across two pixels and read as blurry.
        ctx.strokeRect(x + 0.5, y + 0.5, Math.max(width - 1, 0), Math.max(height - 1, 0));

        // A block cell's real label lives in `.block-label`
        // (planner/partials/block_cell.html); everything else (day
        // headers, time labels, empty cells) has no such child, so its own
        // `textContent` is the label. Iterating only `th`/`td` themselves
        // (never their descendants) already skips the hover-control
        // edit/delete buttons and the resize-handle strips entirely --
        // they are sibling `<div>`s of `.block-label` inside the `<td>`,
        // never picked up as a "cell" of their own, and they contribute no
        // stray text either (confirmed by reading block_cell.html: their
        // only text-shaped content is an `aria-label` attribute, not a
        // text node, and the resize handles are empty `aria-hidden` divs).
        var labelEl = cell.querySelector('.block-label');
        var textSource = labelEl || cell;
        var text = (textSource.textContent || '').trim();
        if (!text) {
            return;
        }

        var textComputed = window.getComputedStyle(textSource);
        ctx.fillStyle = textComputed.color;
        ctx.font = textComputed.fontWeight + ' ' + textComputed.fontSize + ' ' + textComputed.fontFamily;
        ctx.textBaseline = 'top';
        // `maxWidth` (the optional 4th argument) lets the canvas shrink
        // the text to fit rather than let it visually spill into the next
        // cell -- a documented Canvas 2D API behavior, not a guess.
        ctx.fillText(text, x + 4, y + 4, Math.max(width - 8, 1));
    }

    function triggerDownload(canvas) {
        var link = document.createElement('a');
        link.download = 'weekly-planner.png';
        link.href = canvas.toDataURL('image/png');
        // Appended to the DOM before `.click()` and removed right after --
        // some browsers only reliably dispatch a synthetic click on an
        // element that is actually attached to the document.
        document.body.appendChild(link);
        link.click();
        link.remove();
    }

    function exportPng() {
        var table = document.querySelector('#grid-table table');
        if (!table) {
            // Defensive only -- the dashboard always has a grid, but this
            // script should never throw on a page that doesn't.
            return;
        }

        var tableRect = table.getBoundingClientRect();
        var dpr = window.devicePixelRatio || 1;

        var canvas = document.createElement('canvas');
        // Backing-store size is scaled by devicePixelRatio for a crisp
        // export on high-DPI screens; every subsequent drawing call below
        // stays in plain CSS-pixel coordinates because of the ctx.scale()
        // call further down.
        canvas.width = Math.round(tableRect.width * dpr);
        canvas.height = Math.round(tableRect.height * dpr);

        var ctx = canvas.getContext('2d');
        ctx.scale(dpr, dpr);

        ctx.fillStyle = surfaceColor();
        ctx.fillRect(0, 0, tableRect.width, tableRect.height);

        table.querySelectorAll('th, td').forEach(function (cell) {
            drawCell(ctx, cell, tableRect);
        });

        triggerDownload(canvas);
    }

    document.addEventListener('click', function (evt) {
        if (evt.target.closest('[data-export-png]')) {
            exportPng();
            return;
        }
        if (evt.target.closest('[data-export-print]')) {
            // The print-only CSS (`print:hidden` on chrome,
            // `print:max-h-none print:overflow-visible` on the grid
            // wrapper) is already in place elsewhere -- this is the
            // entire job of the print trigger.
            window.print();
        }
    });
})();
