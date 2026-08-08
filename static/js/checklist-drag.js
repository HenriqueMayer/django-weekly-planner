/* Submit an accessible server-side reorder after an HTML5 checklist drop. */
(function () {
    var dragged = null;
    document.addEventListener('dragstart', function (event) {
        var item = event.target.closest('[data-checklist-item]');
        if (!item) return;
        dragged = item;
        event.dataTransfer.effectAllowed = 'move';
        event.dataTransfer.setData('text/plain', item.dataset.checklistItem);
    });
    document.addEventListener('dragover', function (event) {
        if (event.target.closest('[data-checklist-item]')) event.preventDefault();
    });
    document.addEventListener('drop', function (event) {
        var target = event.target.closest('[data-checklist-item]');
        if (!dragged || !target || dragged === target || !window.htmx) return;
        event.preventDefault();
        htmx.ajax('POST', dragged.dataset.checklistMoveUrl, {
            target: '#card-panel',
            swap: 'outerHTML',
            values: {target_pk: target.dataset.checklistItem},
        });
        dragged = null;
    });
})();
