"""Views for the planner app (PRD FR-06, US-2.2)."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import UpdateView

from apps.planner.forms import PlannerSettingsForm
from apps.planner.models import PlannerSettings


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
