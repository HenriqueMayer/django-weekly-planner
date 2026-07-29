"""Views for the planner app (PRD FR-05, FR-06, US-2.2, US-2.1)."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import TemplateView, UpdateView

from apps.planner.forms import PlannerSettingsForm
from apps.planner.grid import build_week_grid
from apps.planner.models import PlannerSettings, TimeBlock


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
        blocks = TimeBlock.objects.filter(user=self.request.user).select_related('color')
        context['week_grid'] = build_week_grid(settings_obj, blocks)
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
