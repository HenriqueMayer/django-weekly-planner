/**
 * Drag-to-resize (PRD 6.3.1-6.3.3, R1).
 *
 * Pointer Events (not mouse events -- PRD §4 requires tablet support) on the
 * thin top/bottom handle strips `planner/partials/block_cell.html` renders
 * on every block. Everything here is a *visual preview only*: nothing is
 * persisted until pointerup, when exactly one HTMX request
 * (`htmx.ajax`, verified against the current htmx JS API docs via
 * Context7) is fired to `BlockResizeView`. The server clamps/re-validates
 * regardless of what this file computes (NFR-08) -- a rejected resize comes
 * back as the grid unchanged plus a toast, which this file does not need to
 * handle specially, since `#grid-table` is simply swapped back in as-is.
 *
 * No application state is cached across requests here (R1's "don't let this
 * turn into an SPA" warning): the only state that exists is `activeDrag`,
 * reset to `null` at the start/end of every single drag gesture, holding
 * nothing but the numbers needed to finish that one gesture. Every block's
 * pk/current start/end/resize-url is read fresh from the `<td>`'s own
 * `data-*` attributes at drag-start, and the grid's slot interval is read
 * fresh from `#grid-table`'s `data-slot-interval` every time too -- since
 * every real mutation replaces `#grid-table` (and every block `<td>`)
 * wholesale, nothing here could safely be cached from one gesture to the
 * next even if it were tempting to.
 *
 * Event delegation lives on `document` for pointerdown/move/up, rather than
 * binding listeners to individual handle elements. That is not a style
 * preference: every HTMX mutation replaces the block cells (and their
 * handles) with brand-new DOM nodes, which would silently carry no
 * listeners at all if this file ever attached them directly to a handle
 * element instead of delegating from something that is never itself
 * swapped out.
 */
(function () {
    'use strict';

    var MIN_SLOTS = 1;
    var activeDrag = null;

    function parseHHMM(value) {
        var parts = value.split(':');
        return parseInt(parts[0], 10) * 60 + parseInt(parts[1], 10);
    }

    function minutesToHHMM(totalMinutes) {
        var wrapped = ((totalMinutes % 1440) + 1440) % 1440;
        var hours = Math.floor(wrapped / 60);
        var minutes = wrapped % 60;
        return (hours < 10 ? '0' : '') + hours + ':' + (minutes < 10 ? '0' : '') + minutes;
    }

    function makePreviewOverlay(rect) {
        var overlay = document.createElement('div');
        overlay.className = 'grid-drag-preview pointer-events-none fixed z-40 rounded-md outline outline-2 outline-indigo-500 bg-indigo-500/10';
        overlay.style.left = rect.left + 'px';
        overlay.style.width = rect.width + 'px';
        overlay.style.top = rect.top + 'px';
        overlay.style.height = rect.height + 'px';
        document.body.appendChild(overlay);
        return overlay;
    }

    document.addEventListener('pointerdown', function (evt) {
        var handle = evt.target.closest('[data-resize-handle]');
        if (!handle) {
            return;
        }
        var cell = handle.closest('td[data-resize-url]');
        if (!cell) {
            return;
        }

        var gridEl = document.getElementById('grid-table');
        var slotInterval = (gridEl && parseInt(gridEl.dataset.slotInterval, 10)) || 60;
        var rect = cell.getBoundingClientRect();
        var rowSpan = cell.rowSpan || 1;

        activeDrag = {
            cell: cell,
            edge: handle.dataset.resizeHandle, // 'top' or 'bottom'
            resizeUrl: cell.dataset.resizeUrl,
            startMinutes: parseHHMM(cell.dataset.start),
            endMinutes: parseHHMM(cell.dataset.end),
            slotInterval: slotInterval,
            slotHeight: rect.height / rowSpan,
            rowSpan: rowSpan,
            rect: rect,
            pointerId: evt.pointerId,
            startClientY: evt.clientY,
            overlay: makePreviewOverlay(rect),
        };
        // 0 is a valid `end_time` (midnight, PRD's own end-of-day
        // convention) -- treat it as 24:00 for arithmetic here, matching
        // the same rule `apps.planner.models.minutes_since_midnight()`
        // applies server-side.
        if (activeDrag.endMinutes === 0) {
            activeDrag.endMinutes = 1440;
        }

        handle.setPointerCapture(evt.pointerId);
        evt.preventDefault();
    });

    document.addEventListener('pointermove', function (evt) {
        if (!activeDrag || evt.pointerId !== activeDrag.pointerId) {
            return;
        }

        var deltaSlots = Math.round((evt.clientY - activeDrag.startClientY) / activeDrag.slotHeight);
        var newSpan;
        var top;
        if (activeDrag.edge === 'bottom') {
            newSpan = Math.max(MIN_SLOTS, activeDrag.rowSpan + deltaSlots);
            top = activeDrag.rect.top;
        } else {
            newSpan = Math.max(MIN_SLOTS, activeDrag.rowSpan - deltaSlots);
            top = activeDrag.rect.top + (activeDrag.rowSpan - newSpan) * activeDrag.slotHeight;
        }

        activeDrag.overlay.style.top = top + 'px';
        activeDrag.overlay.style.height = (newSpan * activeDrag.slotHeight) + 'px';
        activeDrag.pendingSpan = newSpan;
    });

    document.addEventListener('pointerup', function (evt) {
        if (!activeDrag || evt.pointerId !== activeDrag.pointerId) {
            return;
        }

        var drag = activeDrag;
        activeDrag = null;
        drag.overlay.remove();

        var newSpan = drag.pendingSpan || drag.rowSpan;
        var slotDelta = newSpan - drag.rowSpan;
        var newStart = drag.startMinutes;
        var newEnd = drag.endMinutes;
        if (drag.edge === 'bottom') {
            newEnd = drag.endMinutes + slotDelta * drag.slotInterval;
        } else {
            newStart = drag.startMinutes + slotDelta * drag.slotInterval;
        }

        if (newSpan === drag.rowSpan) {
            return; // No net change -- nothing worth a round trip for.
        }

        // `source: drag.cell` matters, not just documentation detail: htmx
        // only walks up the DOM from a request's *source* element to collect
        // ancestor `hx-headers` (base.html's CSRF token, set on <body>).
        // Without a `source`, htmx.ajax() resolves no source element at all
        // and silently sends the request with no CSRF header, which Django
        // would reject with 403 -- verified against the htmx.js source via
        // Context7 (`getValuesForElement` returns `{}` immediately when
        // called with a null element).
        htmx.ajax('POST', drag.resizeUrl, {
            source: drag.cell,
            target: '#grid-table',
            swap: 'outerHTML',
            values: {
                start_time: minutesToHHMM(newStart),
                end_time: minutesToHHMM(newEnd),
            },
        });
    });
})();
