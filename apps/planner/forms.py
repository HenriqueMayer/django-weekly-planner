"""Forms for the planner app (PRD FR-06, §8.2)."""

from django import forms
from django.core.exceptions import ValidationError

from apps.planner.models import PlannerSettings, minutes_since_midnight

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
