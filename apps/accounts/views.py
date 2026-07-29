"""Views for the accounts app (native Django authentication, PRD FR-02/FR-03)."""

from django.contrib.auth import login
from django.urls import reverse_lazy
from django.views.generic import CreateView

from apps.accounts.forms import SignUpForm


class SignUpView(CreateView):
    """Registration view (US-1.2): creates the account and logs the user in.

    `LoginView`/`LogoutView` are Django's built-in CBVs, wired directly in
    `apps.accounts.urls` with no need for a custom subclass here.
    """

    form_class = SignUpForm
    template_name = 'accounts/signup.html'
    success_url = reverse_lazy('core:dashboard')

    def form_valid(self, form):
        """Save the new user, then authenticate the session (FR-02)."""
        response = super().form_valid(form)
        # Explicit backend: only one is configured (ModelBackend), but login()
        # raises if that ever changes and the backend is left implicit.
        login(self.request, self.object, backend='django.contrib.auth.backends.ModelBackend')
        return response
