"""Views for the planner app (PRD FR-05..FR-13, US-2.1/2.2, US-3.1..3.6).

Sprint 6 swap-strategy note (applies to every block-mutating view below --
create, update, delete, resize, and the repeat-across-days path folded
into create): on success (and on a rejected resize), the response is
always a *fresh* `build_week_grid()` call re-rendered through
`planner/partials/grid_table.html` in full, never a per-cell or
per-column fragment. This is a deliberate design decision, not a
shortcut: the grid uses a native HTML `<table>` with `rowspan` for
vertical block merging (Sprint 5, PRD §9.2's "Grid" pattern), and any
mutation can shift which rows are `'occupied'` vs. `'empty'`/
`'block-start'` for an entire day column -- which changes how many
`<td>` elements exist across multiple `<tr>` rows. That structural change
cannot be safely expressed as a single-element HTMX out-of-band swap
without desync risk. PRD 6.1.3 itself offers "re-render the affected day
column" as the sanctioned simpler fallback for correctness; re-rendering
the whole table (cheap -- pure Python over <=100 blocks, well under
NFR-03's 200ms budget) is that same idea taken to its simplest,
always-correct conclusion. The one exception is opening/cancelling an
inline form (GET): those never change the matrix at all, so they stay
scoped to a single `<td>` swap (`BlockCreateView`/`BlockUpdateView`'s GET
handling, `CellCancelView`, `BlockCancelView`).

Toast/notice channel: every mutating view's response passes two extra
context variables into `grid_table.html` -- `toast_message` (str, empty
when there's nothing to report) and `toast_level` (`'error'` or `'info'`,
empty when unused). These are always passed, even as empty strings, so a
stale toast from an earlier unrelated action never lingers in the UI.
The actual toast markup and its `hx-swap-oob` wiring is a later
`htmx-interaction` pass's job; this module only guarantees the two
variables are always present in context.
"""

from datetime import timedelta

from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, TemplateView, UpdateView

from apps.planner.dates import (
    navigation_context,
    normalize_week_start,
    parse_week_start,
    week_end,
)
from apps.planner.export import build_svg_export, render_week_markdown
from apps.planner.forms import (
    BlockColorForm,
    CardDetailForm,
    ChecklistItemForm,
    PlannerSettingsForm,
    RecurrenceForm,
    TimeBlockForm,
)
from apps.planner.grid import GridCell, build_week_grid
from apps.planner.models import (
    BlockColor,
    ChecklistItem,
    PlannerSettings,
    TimeBlock,
    minutes_since_midnight,
    time_from_minutes,
)
from apps.planner.recurrence import (
    create_weekly_series,
    restore_occurrence,
    update_weekly_series,
)
from apps.planner.services import record_activity


def _format_validation_error(exc):
    """Flatten a `ValidationError` into one human-readable string for the
    toast channel (see module docstring)."""
    return ' '.join(exc.messages)


def _day_range_minutes(settings_obj):
    """Return `(range_start, range_end)`, the user's configured visible day
    range in minutes-since-midnight, via the shared `minutes_since_midnight()`
    helper (midnight-crossing `day_end` treated as 24:00).

    The single place both resize code paths -- `BlockResizeView` (drag-
    release) and `BlockUpdateView._handle_resize_action()` (the +/-
    keyboard/click fallback, PRD 6.3.4) -- derive the grid's day boundaries
    from, so the two can never again silently diverge on how they clamp
    (that divergence was exactly the bug this helper was extracted to
    close).
    """
    range_start = minutes_since_midnight(settings_obj.day_start)
    range_end = minutes_since_midnight(settings_obj.day_end, treat_midnight_as_end_of_day=True)
    return range_start, range_end


def selected_week(request):
    return parse_week_start(request.POST.get('week') or request.GET.get('week'))


def _week_blocks(user, week_start):
    legacy_blocks = (
        Q(scheduled_date__isnull=True)
        if week_start == normalize_week_start()
        else Q(pk__in=[])
    )
    return TimeBlock.objects.filter(
        user=user,
    ).filter(
        Q(scheduled_date__gte=week_start, scheduled_date__lte=week_end(week_start))
        | legacy_blocks,
    ).filter(skipped=False).select_related('color')


def _navigation_context(request, week_start):
    month_value = request.GET.get('month') or request.POST.get('month')
    return navigation_context(week_start, month_value)


def _render_grid_response(request, toast_message='', toast_level=''):
    """Re-render the entire grid table fragment for `request.user`.

    Shared by every block-mutating view's success/failure response (see
    the swap-strategy note in the module docstring). Always issues
    exactly one blocks query (`select_related('color')`, per NFR-03) and
    never trusts anything but `request.user` to scope it (NFR-07).
    """
    settings_obj, _ = PlannerSettings.objects.get_or_create(user=request.user)
    week_start = selected_week(request)
    blocks = _week_blocks(request.user, week_start)
    week_grid = build_week_grid(settings_obj, blocks, week_start)
    context = {
        'week_grid': week_grid,
        **_navigation_context(request, week_start),
        'toast_message': toast_message,
        'toast_level': toast_level,
    }
    return render(request, 'planner/partials/grid_table.html', context)


def _card_detail_context(request, block, form=None, checklist_form=None):
    week_start = selected_week(request)
    return {
        'block': block,
        'detail_form': form or CardDetailForm(instance=block),
        'checklist_form': checklist_form or ChecklistItemForm(),
        'checklist_items': block.checklist_items.all(),
        'activities': block.activity_events.select_related('actor')[:20],
        'recurrence_form': (
            RecurrenceForm(instance=block.recurrence_series, user=request.user)
            if block.recurrence_series_id else None
        ),
        'selected_week_start': week_start,
        'selected_week_value': week_start.isoformat(),
    }


def _render_card_detail_response(request, block, form=None, checklist_form=None):
    """Return the detail panel plus an OOB refresh of the shared grid."""
    detail_html = render_to_string(
        'planner/partials/card_detail_panel.html',
        _card_detail_context(request, block, form, checklist_form),
        request=request,
    )
    settings_obj, _ = PlannerSettings.objects.get_or_create(user=request.user)
    week_start = selected_week(request)
    grid_html = render_to_string(
        'planner/partials/grid_table.html',
        {
            'week_grid': build_week_grid(
                settings_obj,
                _week_blocks(request.user, week_start),
                week_start,
            ),
            'grid_oob': True,
            'toast_message': '',
            'toast_level': '',
            **_navigation_context(request, week_start),
        },
        request=request,
    )
    return HttpResponse(detail_html + grid_html)


class CardDetailView(LoginRequiredMixin, View):
    """Open one ownership-scoped card in the in-page detail panel."""

    def get(self, request, *args, **kwargs):
        block = get_object_or_404(TimeBlock, pk=kwargs['pk'], user=request.user)
        return render(
            request,
            'planner/partials/card_detail_panel.html',
            _card_detail_context(request, block),
        )


class ChecklistAddView(LoginRequiredMixin, View):
    """Add one checklist item to an ownership-scoped card."""

    def post(self, request, *args, **kwargs):
        block = get_object_or_404(TimeBlock, pk=kwargs['pk'], user=request.user)
        form = ChecklistItemForm(request.POST)
        if not form.is_valid():
            return _render_card_detail_response(request, block, checklist_form=form)
        item = form.save(commit=False)
        item.time_block = block
        item.position = block.checklist_items.count()
        item.save()
        record_activity(block, request.user, 'checklist_item_added', {'text': item.text})
        return _render_card_detail_response(request, block)


class ChecklistToggleView(LoginRequiredMixin, View):
    """Toggle completion on one ownership-scoped checklist item."""

    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        item = get_object_or_404(
            ChecklistItem.objects.select_related('time_block'),
            pk=kwargs['item_pk'],
            time_block__pk=kwargs['pk'],
            time_block__user=request.user,
        )
        item.is_completed = not item.is_completed
        item.save(update_fields=['is_completed'])
        record_activity(
            item.time_block,
            request.user,
            'checklist_item_toggled',
            {'item_id': item.pk, 'completed': item.is_completed},
        )
        return _render_card_detail_response(request, item.time_block)


class ChecklistDeleteView(LoginRequiredMixin, View):
    """Delete one ownership-scoped checklist item."""

    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        item = get_object_or_404(
            ChecklistItem.objects.select_related('time_block'),
            pk=kwargs['item_pk'],
            time_block__pk=kwargs['pk'],
            time_block__user=request.user,
        )
        block = item.time_block
        text = item.text
        item.delete()
        record_activity(block, request.user, 'checklist_item_deleted', {'text': text})
        return _render_card_detail_response(request, block)


class ChecklistUpdateView(LoginRequiredMixin, View):
    """Edit one ownership-scoped checklist item."""

    def post(self, request, *args, **kwargs):
        item = get_object_or_404(
            ChecklistItem.objects.select_related('time_block'),
            pk=kwargs['item_pk'],
            time_block__pk=kwargs['pk'],
            time_block__user=request.user,
        )
        form = ChecklistItemForm(request.POST, instance=item)
        if not form.is_valid():
            return _render_card_detail_response(request, item.time_block)
        form.save()
        record_activity(
            item.time_block,
            request.user,
            'checklist_item_updated',
            {'item_id': item.pk},
        )
        return _render_card_detail_response(request, item.time_block)


class ChecklistMoveView(LoginRequiredMixin, View):
    """Move one checklist item one position up or down."""

    http_method_names = ['post']

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        item = get_object_or_404(
            ChecklistItem.objects.select_related('time_block'),
            pk=kwargs['item_pk'],
            time_block__pk=kwargs['pk'],
            time_block__user=request.user,
        )
        direction = request.POST.get('direction')
        items = list(item.time_block.checklist_items.order_by('position', 'created_at', 'pk'))
        index = items.index(item)
        target_index = index - 1 if direction == 'up' else index + 1
        if direction not in ('up', 'down') or not 0 <= target_index < len(items):
            return _render_card_detail_response(request, item.time_block)
        other = items[target_index]
        item.position, other.position = other.position, item.position
        item.save(update_fields=['position'])
        other.save(update_fields=['position'])
        record_activity(
            item.time_block,
            request.user,
            'checklist_item_moved',
            {'item_id': item.pk, 'direction': direction},
        )
        return _render_card_detail_response(request, item.time_block)


class CardDetailUpdateView(LoginRequiredMixin, UpdateView):
    """Update card properties and record a single activity transaction."""

    model = TimeBlock
    form_class = CardDetailForm
    template_name = 'planner/partials/card_detail_panel.html'

    def get_queryset(self):
        return TimeBlock.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_card_detail_context(self.request, self.object, context.get('form')))
        return context

    def form_invalid(self, form):
        response = super().form_invalid(form)
        response['HX-Retarget'] = '#card-panel'
        response['HX-Reswap'] = 'outerHTML'
        return response

    @transaction.atomic
    def form_valid(self, form):
        previous = TimeBlock.objects.get(pk=self.object.pk)
        before = {
            'label': previous.label,
            'description': previous.description,
            'status': previous.status,
            'due_at': previous.due_at.isoformat() if previous.due_at else None,
        }
        self.object = form.save()
        changed = {
            field: (
                getattr(self.object, field).isoformat()
                if field == 'due_at' and getattr(self.object, field)
                else getattr(self.object, field)
            )
            for field in before
            if before[field] != (
                getattr(self.object, field).isoformat()
                if field == 'due_at' and getattr(self.object, field)
                else getattr(self.object, field)
            )
        }
        if changed:
            if self.object.recurrence_series_id:
                self.object.overridden = True
                self.object.save(update_fields=['overridden'])
            record_activity(
                self.object,
                self.request.user,
                'card_updated',
                {'changes': changed},
            )
        return _render_card_detail_response(self.request, self.object)


class RecurrenceUpdateView(LoginRequiredMixin, UpdateView):
    """Update the future rule for an ownership-scoped recurring card."""

    model = TimeBlock
    form_class = RecurrenceForm

    def get_queryset(self):
        return TimeBlock.objects.filter(user=self.request.user).select_related('recurrence_series')

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        block = self.get_object()
        series = block.recurrence_series
        if series is None:
            return HttpResponseBadRequest('This card is not recurring.')
        form = self.form_class(request.POST, instance=series, user=request.user)
        if not form.is_valid():
            return _render_card_detail_response(request, block, form=form)
        form.save()
        update_weekly_series(series)
        replacement = series.occurrences.order_by('scheduled_date', 'pk').first()
        target = replacement or block
        record_activity(target, request.user, 'recurrence_updated', {'series_id': series.pk})
        return _render_card_detail_response(request, target)


class OccurrenceSkipView(LoginRequiredMixin, View):
    """Exclude one recurring occurrence while preserving its row and history."""

    http_method_names = ['post']

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        block = get_object_or_404(
            TimeBlock.objects.select_related('recurrence_series'),
            pk=kwargs['pk'],
            user=request.user,
        )
        if block.recurrence_series_id is None or block.scheduled_date is None:
            return HttpResponseBadRequest('This card is not a recurring occurrence.')
        block.recurrence_series.exceptions.get_or_create(occurrence_date=block.scheduled_date)
        block.skipped = True
        block.save(update_fields=['skipped'])
        record_activity(
            block,
            request.user,
            'occurrence_skipped',
            {'date': block.scheduled_date.isoformat()},
        )
        return _render_card_detail_response(request, block)


class OccurrenceRestoreView(LoginRequiredMixin, View):
    """Restore one occurrence's rule values and remove its exception."""

    http_method_names = ['post']

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        block = get_object_or_404(
            TimeBlock.objects.select_related('recurrence_series'),
            pk=kwargs['pk'],
            user=request.user,
        )
        if block.recurrence_series_id is None:
            return HttpResponseBadRequest('This card is not a recurring occurrence.')
        restore_occurrence(block)
        record_activity(block, request.user, 'occurrence_restored', {})
        return _render_card_detail_response(request, block)


def _render_palette_response(request):
    """Palette CRUD success response (PRD 7.1.1-7.1.3): re-renders the
    whole palette panel (primary content) plus an out-of-band refresh of
    the grid table, since a color rename/recolor/delete can change how
    existing blocks render (inline hex background) or, per FR-13, must
    visibly clear to the colorless fallback the moment a color is
    deleted -- not just eventually, on a later full page load. Cheap and
    always correct, the same justification `_render_grid_response()`'s
    own module docstring already gives for whole-fragment over
    partial-patch swaps.
    """
    colors = BlockColor.objects.filter(user=request.user).order_by('name')
    palette_html = render_to_string(
        'planner/partials/palette_panel.html', {'colors': colors}, request=request,
    )
    settings_obj, _ = PlannerSettings.objects.get_or_create(user=request.user)
    week_start = selected_week(request)
    blocks = _week_blocks(request.user, week_start)
    week_grid = build_week_grid(settings_obj, blocks, week_start)
    grid_html = render_to_string(
        'planner/partials/grid_table.html',
        {
            'week_grid': week_grid,
            'toast_message': '',
            'toast_level': '',
            'grid_oob': True,
            **_navigation_context(request, week_start),
        },
        request=request,
    )
    return HttpResponse(palette_html + grid_html)


class GridView(LoginRequiredMixin, TemplateView):
    """Standalone weekly grid page (PRD 5.2.1), reachable at `/planner/`.

    Builds the same `WeekGrid` context, from the same `build_week_grid()`
    builder, that `apps.core.views.DashboardView` embeds -- there is
    exactly one place the matrix is computed (PRD R2, R6); this view and
    the dashboard just both call it. No pk is taken from the URL: the
    settings and blocks are always scoped to `request.user` (NFR-07).
    """

    template_name = 'planner/grid.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        settings_obj, _ = PlannerSettings.objects.get_or_create(user=self.request.user)
        week_start = selected_week(self.request)
        blocks = _week_blocks(self.request.user, week_start)
        context['week_grid'] = build_week_grid(settings_obj, blocks, week_start)
        context.update(_navigation_context(self.request, week_start))
        return context


class SettingsUpdateView(LoginRequiredMixin, UpdateView):
    """Lets the logged-in user edit their own planner settings (PRD 4.4.2).

    There is no pk in the URL by design: settings are always "my settings",
    scoped to `request.user` rather than trusted from the request (NFR-07).
    `get_or_create` is a defensive fallback in case a user row exists
    without a `PlannerSettings` row (e.g. created before this signal was
    registered) -- the normal path is the `post_save` signal in
    `apps/planner/signals.py` creating it at signup time.
    """

    model = PlannerSettings
    form_class = PlannerSettingsForm
    template_name = 'planner/settings_form.html'
    success_url = reverse_lazy('core:dashboard')

    def get_object(self, queryset=None):
        settings_obj, _ = PlannerSettings.objects.get_or_create(user=self.request.user)
        return settings_obj


class BlockCreateView(LoginRequiredMixin, CreateView):
    """Creates a new `TimeBlock` from an inline cell form (PRD FR-07,
    6.1.1-6.1.5, US-3.1).

    One CBV handles both GET (render the inline create form, pre-filled
    from the clicked empty cell's `day`/`start`/`end` query params, which
    `planner/partials/empty_cell.html` already emits as `data-*`
    attributes) and POST (validate + save) -- `CreateView` already covers
    both verbs natively, so there is no separate 'form view' class.
    """

    model = TimeBlock
    form_class = TimeBlockForm
    template_name = 'planner/partials/block_form.html'

    def get_initial(self):
        initial = super().get_initial()
        params = self.request.GET
        if 'day' in params:
            initial['day_of_week'] = params['day']
        if 'start' in params:
            initial['start_time'] = params['start']
        if 'end' in params:
            initial['end_time'] = params['end']
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['week_start'] = selected_week(self.request)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # An empty cell always spans exactly one row (PRD 5.2.4); the
        # wrapping <td> for the inline create form matches that.
        context['rowspan'] = 1
        week_start = selected_week(self.request)
        context['selected_week_start'] = week_start
        context['selected_week_value'] = week_start.isoformat()
        return context

    def form_invalid(self, form):
        """htmx-interaction, Sprint 6: the `<form>` in `block_form.html`
        declares `hx-target="#grid-table" hx-swap="outerHTML"` for its
        SUCCESS path (`form_valid()` below, via `_render_grid_response()`).
        On a validation failure, `FormMixin`'s default behavior --
        preserved here via `super().form_invalid(form)` -- re-renders this
        same `template_name` (the form fragment, with errors now bound),
        status 200. That fragment must swap back into the form's own small
        `<td id="block-form">`, never into `#grid-table` -- one element
        can't declare two different targets for the same trigger. `HX-
        Retarget`/`HX-Reswap` override the target/swap for this one
        response only (verified against the htmx 2.x docs via Context7:
        `HX-Retarget` takes a CSS selector, `HX-Reswap` a swap-style
        string). `#block-form` is a fixed id, not parameterized by day/
        start/pk -- see `block_form.html`'s docstring for why a
        data-derived selector would be unsafe here (the user can edit the
        day/time fields before an invalid submit, which would desync a
        selector computed from that same submitted data from whatever id
        the currently-live DOM element actually carries).
        """
        response = super().form_invalid(form)
        response['HX-Retarget'] = '#block-form'
        response['HX-Reswap'] = 'outerHTML'
        return response

    def form_valid(self, form):
        """Save the primary block, then materialize `repeat_days` copies
        (PRD 6.4.1/6.4.2). A copy that would overlap an existing block is
        skipped, not aborted -- reported through the toast channel, since
        the primary block has already saved successfully by that point.
        """
        if form.cleaned_data.get('recurrence_weekly'):
            series = create_weekly_series(
                user=self.request.user,
                label=form.cleaned_data['label'],
                start_time=form.cleaned_data['start_time'],
                end_time=form.cleaned_data['end_time'],
                starts_on=form.instance.scheduled_date,
                weekdays=[int(day) for day in form.cleaned_data['recurrence_weekdays']],
                ends_on=form.cleaned_data['recurrence_until'],
                color=form.cleaned_data.get('color'),
            )
            occurrences = list(series.occurrences.order_by('scheduled_date'))
            if occurrences:
                self.object = occurrences[0]
                record_activity(
                    self.object,
                    self.request.user,
                    'recurrence_created',
                    {'series_id': series.pk, 'occurrence_count': len(occurrences)},
                )
            return _render_grid_response(self.request)

        self.object = form.save()
        record_activity(
            self.object,
            self.request.user,
            'card_created',
            {'label': self.object.label},
        )

        day_labels_by_value = dict(TimeBlock.DAY_CHOICES)
        skipped_day_labels = []
        for raw_day in form.cleaned_data.get('repeat_days') or []:
            day = int(raw_day)
            if day == self.object.day_of_week:
                continue  # Already covered by the primary block itself.
            copy = TimeBlock(
                user=self.request.user,
                label=self.object.label,
                scheduled_date=self.object.scheduled_date + timedelta(
                    days=day - self.object.day_of_week,
                ),
                day_of_week=day,
                start_time=self.object.start_time,
                end_time=self.object.end_time,
                color=self.object.color,
            )
            try:
                copy.save()
            except ValidationError:
                skipped_day_labels.append(day_labels_by_value[day])

        toast_message = ''
        toast_level = ''
        if skipped_day_labels:
            toast_message = f'Skipped {', '.join(skipped_day_labels)} (overlap).'
            toast_level = 'info'

        return _render_grid_response(self.request, toast_message, toast_level)

    # `form_invalid` is intentionally not overridden: `FormMixin`'s
    # default -- `render_to_response(self.get_context_data(form=form))`
    # -- already re-renders `template_name` (the form fragment, with
    # errors bound onto it) with a normal 200 status, which is exactly
    # PRD 6.1.4's requirement ("return the form fragment with inline
    # errors, status 200 for HTMX swap").


class BlockUpdateView(LoginRequiredMixin, UpdateView):
    """Edits an existing `TimeBlock` inline (PRD FR-08, 6.2.1/6.2.2,
    US-3.2).

    Also doubles as PRD 6.3.4's keyboard/click '+/-' fallback: when the
    POST carries an `action` of `'extend'` or `'shrink'` instead of the
    normal form fields, `_handle_resize_action()` shifts `end_time` by one
    of the user's own `slot_interval` slots and runs it through the same
    validate/save path -- this is a fallback branch on the same edit
    action, not a separate view.
    """

    model = TimeBlock
    form_class = TimeBlockForm
    template_name = 'planner/partials/block_form.html'

    def get_queryset(self):
        # Ownership scoping (NFR-07, PRD 6.2.4): filter by owner *before*
        # the pk lookup, so a cross-user pk yields 404, never 403.
        return TimeBlock.objects.filter(user=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['week_start'] = selected_week(self.request)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        settings_obj, _ = PlannerSettings.objects.get_or_create(user=self.request.user)
        context['rowspan'] = self.object.get_rowspan(settings_obj.slot_interval)
        week_start = selected_week(self.request)
        context['selected_week_start'] = week_start
        context['selected_week_value'] = week_start.isoformat()
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        if action in ('extend', 'shrink'):
            self.object = self.get_object()
            return self._handle_resize_action(action)
        return super().post(request, *args, **kwargs)

    def _handle_resize_action(self, action):
        """PRD 6.3.4: shift `end_time` by one slot, forward for 'extend',
        backward for 'shrink'.

        Unlike `BlockResizeView`'s free-position drag-release resize, this
        is a fixed single-step nudge, so there is no sensible "partial"
        clamp to fall back to -- if the requested one-slot shift would
        land outside the user's configured `[day_start, day_end)` range
        (via the shared `_day_range_minutes()` helper, same source of
        truth `BlockResizeView` uses), the whole action is rejected with
        an error toast and the block is left untouched, rather than
        silently saving a no-op or, worse, silently drifting outside the
        visible grid range. A shrink that collapses the block to zero/
        negative duration is still caught independently by `TimeBlock.
        clean()` via `full_clean()` in `save()`; both rejection paths
        report through the same error-toast channel.
        """
        settings_obj, _ = PlannerSettings.objects.get_or_create(user=self.request.user)
        interval = settings_obj.slot_interval
        delta = interval if action == 'extend' else -interval

        range_start, range_end = _day_range_minutes(settings_obj)

        current_end_minutes = minutes_since_midnight(
            self.object.end_time, treat_midnight_as_end_of_day=True,
        )
        new_end_minutes = current_end_minutes + delta

        if new_end_minutes < range_start or new_end_minutes > range_end:
            return _render_grid_response(
                self.request,
                toast_message=(
                    'Resize rejected: block would extend beyond the '
                    'configured day range.'
                ),
                toast_level='error',
            )

        self.object.end_time = time_from_minutes(new_end_minutes)
        if self.object.recurrence_series_id:
            self.object.overridden = True

        try:
            self.object.save()
        except ValidationError as exc:
            return _render_grid_response(
                self.request,
                toast_message=_format_validation_error(exc),
                toast_level='error',
            )
        return _render_grid_response(self.request)

    def form_valid(self, form):
        changed_fields = list(form.changed_data)
        self.object = form.save()
        if self.object.recurrence_series_id:
            self.object.overridden = True
            self.object.save(update_fields=['overridden'])
        if changed_fields:
            record_activity(
                self.object,
                self.request.user,
                'card_schedule_updated',
                {'fields': changed_fields},
            )
        return _render_grid_response(self.request)

    def form_invalid(self, form):
        """See `BlockCreateView.form_invalid()`'s docstring -- identical
        htmx-interaction reasoning, just for the edit form."""
        response = super().form_invalid(form)
        response['HX-Retarget'] = '#block-form'
        response['HX-Reswap'] = 'outerHTML'
        return response


class BlockDeleteView(LoginRequiredMixin, View):
    """Deletes a `TimeBlock` (PRD FR-11, 6.2.3, US-3.5).

    POST-only: the generic `DeleteView`'s GET-renders-a-confirmation-page
    default is not used here, since the confirmation step is a
    client-side `hx-confirm` rather than a server-rendered page.
    """

    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        block = get_object_or_404(TimeBlock, pk=kwargs['pk'], user=request.user)
        block.delete()
        return _render_grid_response(request)


class BlockResizeView(LoginRequiredMixin, View):
    """Drag-release resize endpoint (PRD FR-09, 6.3.1-6.3.3, US-3.3).

    POST-only. Accepts `start_time`/`end_time` for one block, already
    slot-snapped client-side for display convenience (NFR-08), but
    re-validated and clamped server-side into the user's
    `[day_start, day_end)` range before saving -- the client's snap is
    never trusted on its own.
    """

    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        block = get_object_or_404(TimeBlock, pk=kwargs['pk'], user=request.user)
        settings_obj, _ = PlannerSettings.objects.get_or_create(user=request.user)

        time_field = forms.TimeField()
        try:
            new_start = time_field.clean(request.POST.get('start_time'))
            new_end = time_field.clean(request.POST.get('end_time'))
        except ValidationError:
            return _render_grid_response(
                request,
                toast_message='Resize rejected: invalid start/end time.',
                toast_level='error',
            )

        range_start, range_end = _day_range_minutes(settings_obj)

        start_minutes = minutes_since_midnight(new_start)
        end_minutes = minutes_since_midnight(new_end, treat_midnight_as_end_of_day=True)

        clamped_start = max(range_start, min(start_minutes, range_end))
        clamped_end = max(range_start, min(end_minutes, range_end))

        if clamped_end <= clamped_start:
            return _render_grid_response(
                request,
                toast_message=(
                    'Resize rejected: block would have zero or negative '
                    'duration within the grid range.'
                ),
                toast_level='error',
            )

        block.start_time = time_from_minutes(clamped_start)
        block.end_time = time_from_minutes(clamped_end)
        if block.recurrence_series_id:
            block.overridden = True
        try:
            block.save()
        except ValidationError as exc:
            return _render_grid_response(
                request,
                toast_message=_format_validation_error(exc),
                toast_level='error',
            )

        return _render_grid_response(request)


class CellCancelView(LoginRequiredMixin, View):
    """Restores one empty grid cell (PRD 6.1.5's create-cancel target).

    Given `day`/`start`/`end` query params (the same values the create
    form was opened with), re-renders `planner/partials/empty_cell.html`
    for that slot -- a single-cell swap that never touches the grid
    matrix.
    """

    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        time_field = forms.TimeField()
        try:
            day = int(request.GET['day'])
            start = time_field.clean(request.GET.get('start'))
            end = time_field.clean(request.GET.get('end'))
        except (KeyError, TypeError, ValueError, ValidationError):
            return HttpResponseBadRequest('Invalid day/start/end parameters.')

        cell = GridCell(kind='empty', day=day, slot_start=start, slot_end=end)
        return render(
            request,
            'planner/partials/empty_cell.html',
            {'cell': cell, 'selected_week_start': selected_week(request)},
        )


class BlockCancelView(LoginRequiredMixin, View):
    """Restores one block cell (the symmetric edit-cancel target, PRD
    6.1.5/6.2.1).

    Given an ownership-scoped block pk, re-renders
    `planner/partials/block_cell.html` in place of the inline edit form --
    also a single-cell swap.
    """

    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        block = get_object_or_404(TimeBlock, pk=kwargs['pk'], user=request.user)
        settings_obj, _ = PlannerSettings.objects.get_or_create(user=request.user)
        cell = GridCell(
            kind='block-start',
            day=block.day_of_week,
            slot_start=block.start_time,
            slot_end=block.end_time,
            block=block,
            rowspan=block.get_rowspan(settings_obj.slot_interval),
        )
        return render(request, 'planner/partials/block_cell.html', {'cell': cell})


class PaletteView(LoginRequiredMixin, TemplateView):
    """Restores the "+ Add color" trigger button (PRD 7.1.1's create-cancel
    target), the palette-panel analog of `CellCancelView`/`BlockCancelView`.

    GET-only; `TemplateView` already covers that with no context needed
    beyond what it provides for free.
    """

    template_name = 'planner/partials/color_add_trigger.html'


class ColorCreateView(LoginRequiredMixin, CreateView):
    """Creates a new `BlockColor` palette entry (PRD FR-13, 7.1.1, US-4.1).

    Mirrors `BlockCreateView` exactly, but palette entries have no
    per-day analog, so there is no repeat-across-days step here.
    """

    model = BlockColor
    form_class = BlockColorForm
    template_name = 'planner/partials/color_form_row.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_invalid(self, form):
        """See `BlockCreateView.form_invalid()`'s docstring for the full
        htmx-interaction reasoning. `#color-form-row` is a fixed id, not
        derived from any submitted data, for the identical reason
        `#block-form` is fixed there: a data-derived selector could desync
        if the user edits the form's fields before an invalid submit.
        """
        response = super().form_invalid(form)
        response['HX-Retarget'] = '#color-form-row'
        response['HX-Reswap'] = 'outerHTML'
        return response

    def form_valid(self, form):
        self.object = form.save()
        return _render_palette_response(self.request)


class ColorUpdateView(LoginRequiredMixin, UpdateView):
    """Edits an existing `BlockColor` inline (PRD FR-13, 7.1.2, US-4.1).

    Mirrors `BlockUpdateView` exactly.
    """

    model = BlockColor
    form_class = BlockColorForm
    template_name = 'planner/partials/color_form_row.html'

    def get_queryset(self):
        # Ownership scoping (NFR-07): filter by owner *before* the pk
        # lookup, so a cross-user pk yields 404, never 403.
        return BlockColor.objects.filter(user=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_invalid(self, form):
        """See `BlockCreateView.form_invalid()`'s docstring for the full
        htmx-interaction reasoning. Here the edit form replaces this
        color's own row element, so the retarget is that row's own id
        (`#color-row-{pk}`, the same id `color_row.html` and
        `color_form_row.html` both render onto their row wrapper), not a
        single fixed id shared across all colors.
        """
        response = super().form_invalid(form)
        response['HX-Retarget'] = f'#color-row-{self.object.pk}'
        response['HX-Reswap'] = 'outerHTML'
        return response

    def form_valid(self, form):
        self.object = form.save()
        return _render_palette_response(self.request)


class ColorCancelView(LoginRequiredMixin, View):
    """Restores one color's display row after an edit is cancelled (PRD
    7.1.2), the palette analog of `BlockCancelView`.
    """

    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        color = get_object_or_404(BlockColor, pk=kwargs['pk'], user=request.user)
        return render(request, 'planner/partials/color_row.html', {'color': color})


class ColorDeleteView(LoginRequiredMixin, View):
    """Deletes a `BlockColor` palette entry (PRD FR-13, 7.1.3).

    POST-only, mirrors `BlockDeleteView` exactly. Any `TimeBlock` still
    referencing this color has its `color` set to `NULL` at the DB level
    automatically (`on_delete=models.SET_NULL`, already correct on the
    model) -- this view does nothing extra for that itself, but the
    grid's out-of-band re-render in `_render_palette_response()` is what
    makes the colorless fallback show up immediately, not just on the
    next full page load.
    """

    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        color = get_object_or_404(BlockColor, pk=kwargs['pk'], user=request.user)
        color.delete()
        return _render_palette_response(request)


class ExportMarkdownView(LoginRequiredMixin, View):
    """Exports the logged-in user's week as a Markdown document (Sprint
    10, a new, user-requested feature added on top of the original PRD
    sprint plan -- not FR-numbered).

    GET-only, plain `View` (no template involved on this path at all --
    `render_week_markdown()` returns a plain string): mirrors
    `GridView`'s `settings_obj`/`blocks` pattern exactly. No pk is taken
    from the URL: everything is scoped to `request.user` (NFR-07).
    """

    def get(self, request, *args, **kwargs):
        settings_obj, _ = PlannerSettings.objects.get_or_create(user=request.user)
        # No `select_related('color')` here (unlike every other view in
        # this file) -- render_week_markdown() never reads `block.color`,
        # so that join would be pure overhead for this one view.
        blocks = _week_blocks(request.user, selected_week(request))
        week_start = selected_week(request)
        content = render_week_markdown(blocks, settings_obj.time_format, week_start)
        response = HttpResponse(content, content_type='text/markdown; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="weekly-planner.md"'
        return response


class ExportSVGView(LoginRequiredMixin, View):
    """Exports the logged-in user's week as an SVG image (Sprint 10, a
    new, user-requested feature added on top of the original PRD sprint
    plan -- not FR-numbered).

    Builds the same `WeekGrid`, from the same `build_week_grid()` call,
    that `GridView` does, so the exported SVG's block placement
    (collision re-anchoring, out-of-range clamping) always matches the
    on-screen grid -- then hands it to `build_svg_export()` for the
    pixel-positioned drawing primitives. No pk is taken from the URL:
    everything is scoped to `request.user` (NFR-07).

    Renders `planner/partials/grid_export.svg` (owned by
    `django-frontend`) with one context variable, `svg_export` -- an
    `apps.planner.export.SvgExport` instance (`.width`, `.height`,
    `.rects` -- each an `SvgRect` with `.x`/`.y`/`.width`/`.height`/
    `.fill`/`.stroke` -- and `.texts` -- each an `SvgText` with `.x`/
    `.y`/`.content`/`.fill`/`.font_size`/`.font_weight`). The template
    only needs to iterate `rects`/`texts`; no arithmetic belongs there
    (PRD R2's "templates only iterate", applied to this export exactly
    as it already applies to `grid_table.html`).
    """

    def get(self, request, *args, **kwargs):
        settings_obj, _ = PlannerSettings.objects.get_or_create(user=request.user)
        week_start = selected_week(request)
        blocks = _week_blocks(request.user, week_start)
        week_grid = build_week_grid(settings_obj, blocks, week_start)
        svg_export = build_svg_export(week_grid)
        response = render(
            request,
            'planner/partials/grid_export.svg',
            {'svg_export': svg_export},
            content_type='image/svg+xml',
        )
        response['Content-Disposition'] = 'attachment; filename="weekly-planner.svg"'
        return response
