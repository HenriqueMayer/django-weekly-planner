"""Forms for the accounts app (native Django authentication, PRD FR-02)."""

from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

# Shared input styling from PRD 9.2, applied to every field's widget so
# UserCreationForm's default rendering matches the rest of the design system.
INPUT_CLASSES = (
    'w-full rounded-lg border border-slate-300 dark:border-slate-600 '
    'bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 '
    'dark:text-slate-100 focus:border-indigo-500 focus:ring-indigo-500'
)


class SignUpForm(UserCreationForm):
    """Registration form (US-1.2) styled with the shared Tailwind input pattern."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': INPUT_CLASSES})


class LoginForm(AuthenticationForm):
    """Login form (US-1.3) styled with the shared Tailwind input pattern."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': INPUT_CLASSES})
