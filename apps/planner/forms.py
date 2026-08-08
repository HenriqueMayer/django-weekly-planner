"""Forms for the planner app (PRD FR-06, FR-07, FR-08, FR-13, §8.2, Sprint 6)."""

from datetime import timedelta

from django import forms
from django.core.exceptions import ValidationError

from apps.planner.dates import normalize_week_start
from apps.planner.models import (
    BlockColor,
    PlannerSettings,
    TimeBlock,
    minutes_since_midnight,
)

# Shared input styling from PRD 9.2, mirrored from
# `apps.accounts.forms.INPUT_CLASSES` so every widget in the project uses
# the same Tailwind input pattern.
INPUT_CLASSES = (
    'w-full rounded-lg border border-slate-300 dark:border-slate-600 '
    'bg-white dark:bg-[#313335] px-3 py-2 text-sm text-slate-900 '
    'dark:text-neutral-100 focus:border-indigo-500 focus:ring-indigo-500'
)


class PlannerSettingsForm(forms.ModelForm):
    """Per-user grid display preferences (US-2.2, PRD 4.4.1/4.4.4)."""

    class Meta:
        model = PlannerSettings
        fields = ['slot_interval', 'day_start', 'day_end', 'time_format']
        widgets = {
            'day_start': forms.TimeInput(attrs={'type': 'time'}),
            'day_end': forms.TimeInput(attrs={'type': 'time'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': INPUT_CLASSES})

    def clean(self):
        """Validate `day_start < day_end`, with the same midnight-as-24:00
        exception as `TimeBlock` (server-side validation is authoritative,
        NFR-08). Reuses the shared `minutes_since_midnight()` helper so the
        rule is defined in exactly one place.
        """
        cleaned_data = super().clean()
        day_start = cleaned_data.get('day_start')
        day_end = cleaned_data.get('day_end')
        if day_start is not None and day_end is not None:
            start_minutes = minutes_since_midnight(day_start)
            end_minutes = minutes_since_midnight(day_end, treat_midnight_as_end_of_day=True)
            if end_minutes <= start_minutes:
                raise ValidationError('Day start must be before day end.')
        return cleaned_data


class TimeBlockForm(forms.ModelForm):
    """Create/edit form for a single `TimeBlock` (PRD 6.1.1/6.2.1, US-3.1/3.2).

    Requires a `user` kwarg. This is not optional convenience: `TimeBlock.
    clean()`'s overlap check (`_same_day_queryset()`) filters by `self.
    user`, and `ModelForm._post_clean()` calls `instance.full_clean()`
    during `is_valid()` -- which runs *before* any view's `form_valid()`.
    Setting `form.instance.user = request.user` inside `form_valid()`
    would be too late: validation would already have run against
    `user=None`, silently skipping the overlap check. The fix is to set
    `self.instance.user` right here in `__init__`, for both the create
    (fresh, unsaved instance) and update (already the right user, so this
    assignment is idempotent) cases.
    """

    repeat_days = forms.MultipleChoiceField(
        choices=TimeBlock.DAY_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Repeat on days',
        help_text=(
            'Create identical copies of this block on the selected days '
            '(PRD 6.4.1). Days where a copy would overlap an existing '
            'block are skipped and reported after saving.'
        ),
    )
    recurrence_weekly = forms.BooleanField(
        required=False,
        label='Repeat weekly',
        help_text='Create dated occurrences until the selected end date.',
    )
    recurrence_weekdays = forms.MultipleChoiceField(
        choices=TimeBlock.DAY_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Weekly days',
    )
    recurrence_until = forms.DateField(
        required=False,
        widget=forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
        label='Repeat until',
    )

    class Meta:
        model = TimeBlock
        fields = ['label', 'day_of_week', 'start_time', 'end_time', 'color']
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
            'color': forms.RadioSelect,
        }

    def __init__(self, *args, user=None, week_start=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.week_start = normalize_week_start(week_start)
        for field_name in ('label', 'day_of_week', 'start_time', 'end_time'):
            self.fields[field_name].widget.attrs.update({'class': INPUT_CLASSES})
        # `color` intentionally keeps its bare `RadioSelect` widget --
        # swatch styling is the frontend agent's job (PRD §9.2), and
        # `repeat_days`'s checkboxes are likewise left unstyled here.
        if user is not None:
            self.instance.user = user
            self.fields['color'].queryset = BlockColor.objects.filter(user=user)

    def clean(self):
        cleaned_data = super().clean()
        day = cleaned_data.get('day_of_week')
        if day is not None:
            self.instance.scheduled_date = self.week_start + timedelta(days=int(day))
        if cleaned_data.get('recurrence_weekly'):
            if not cleaned_data.get('recurrence_weekdays'):
                self.add_error('recurrence_weekdays', 'Choose at least one weekly day.')
            until = cleaned_data.get('recurrence_until')
            if until and until < self.week_start:
                self.add_error(
                    'recurrence_until',
                    'Repeat-until date must be on or after this week.',
                )
            if not until:
                self.add_error('recurrence_until', 'Choose an end date for weekly repetition.')
        return cleaned_data


class CardDetailForm(forms.ModelForm):
    """Edit card properties that do not change its grid geometry."""

    due_at = forms.DateTimeField(
        required=False,
        input_formats=['%Y-%m-%dT%H:%M'],
        widget=forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local'}),
    )

    class Meta:
        model = TimeBlock
        fields = ['label', 'description', 'status', 'due_at']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': INPUT_CLASSES})


class BlockColorForm(forms.ModelForm):
    """Create/edit form for a single `BlockColor` palette entry (PRD FR-13,
    Epic E4/US-4.1, 7.1.1-7.1.3).

    Requires a `user` kwarg, set on `self.instance` right here in
    `__init__` -- the same ordering fix already documented on
    `TimeBlockForm` above: `ModelForm._post_clean()` calls `instance.
    full_clean()` during `is_valid()`, which runs *before* any view's
    `form_valid()`, so `self.instance.user` must already be set by then.

    That alone is *not* sufficient for uniqueness, though (verified
    empirically, not assumed): because `user` is not one of this form's
    `Meta.fields`, `ModelForm._get_validation_exclusions()` adds `'user'`
    to the `exclude` list passed into `instance.full_clean()`, and
    Django's own docs are explicit that "any unique_together constraint
    involving an excluded field will also be ignored during validation"
    -- the same rule applies to a `Meta.constraints` `UniqueConstraint`.
    Left alone, `BlockColorForm.is_valid()` would return `True` for a
    genuine duplicate `(user, name)` pair, and `form.save()` would then
    raise an unhandled `IntegrityError` from the database's own UNIQUE
    constraint, instead of returning the form fragment with a clean
    validation error and HTTP 200 (breaking the same contract PRD 6.1.4
    already establishes for block validation). `clean()` below closes
    that gap with an explicit, hand-rolled duplicate check -- the same
    shape `TimeBlock.clean()` already uses for its own user-scoped
    overlap check, since that same model also can't rely on automatic
    per-field/`Meta` validation for a check that spans a field excluded
    from its form.
    """

    class Meta:
        model = BlockColor
        fields = ['name', 'hex_code']

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': INPUT_CLASSES})
        if user is not None:
            self.instance.user = user

    def clean(self):
        """Hand-rolled `(user, name)` uniqueness check -- see the class
        docstring for why Django's automatic `UniqueConstraint` check
        can't be relied on here. Excludes `self.instance.pk` so editing a
        color's own unchanged name is not mistaken for a collision with
        itself.
        """
        cleaned_data = super().clean()
        name = cleaned_data.get('name')
        if name and self.instance.user_id:
            duplicate_qs = BlockColor.objects.filter(user=self.instance.user, name=name)
            if self.instance.pk:
                duplicate_qs = duplicate_qs.exclude(pk=self.instance.pk)
            if duplicate_qs.exists():
                raise ValidationError('You already have a color with this name.')
        return cleaned_data
