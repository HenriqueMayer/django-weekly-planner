from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from apps.planner.forms import PlannerSettingsForm
from apps.planner.models import PlannerSettings


class LandingView(TemplateView):
    """Public landing/presentation page (FR-01). Accessible without auth."""

    template_name = 'core/landing.html'


class DashboardView(LoginRequiredMixin, TemplateView):
    """Auth-protected dashboard shell where the weekly grid will live (FR-04).

    Sprint 5 embeds the real grid; Sprint 4 adds `settings_form` to context
    so the toolbar's settings dropdown (PRD 4.4.3) can render inline.
    """

    template_name = 'core/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        settings_obj, _ = PlannerSettings.objects.get_or_create(user=self.request.user)
        context['settings_form'] = PlannerSettingsForm(instance=settings_obj)
        return context
