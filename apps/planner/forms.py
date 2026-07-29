"""Forms for the planner app (PRD FR-06, FR-07, FR-08, FR-13, §8.2, Sprint 6)."""

from django import forms
from django.core.exceptions import ValidationError

from apps.planner.models import BlockColor, PlannerSettings, TimeBlock, minutes_since_midnight

# Shared input styling from PRD 9.2, mirrored from
# `apps.accounts.forms.INPUT_CLASSES` so every widget in the project uses
# the same Tailwind input pattern.
INPUT_CLASSES = (
    'w-full rounded-lg border border-slate-300 dark:border-slate-600 '
    'bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 '
    'dark:text-slate-100 focus:border-indigo-500 focus:ring-indigo-500'
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

    class Meta:
        model = TimeBlock
        fields = ['label', 'day_of_week', 'start_time', 'end_time', 'color']
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
            'color': forms.RadioSelect,
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ('label', 'day_of_week', 'start_time', 'end_time'):
            self.fields[field_name].widget.attrs.update({'class': INPUT_CLASSES})
        # `color` intentionally keeps its bare `RadioSelect` widget --
        # swatch styling is the frontend agent's job (PRD §9.2), and
        # `repeat_days`'s checkboxes are likewise left unstyled here.
        if user is not None:
            self.instance.user = user
            self.fields['color'].queryset = BlockColor.objects.filter(user=user)
