from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class LandingView(TemplateView):
    """Public landing/presentation page (FR-01). Accessible without auth."""

    template_name = 'core/landing.html'


class DashboardView(LoginRequiredMixin, TemplateView):
    """Auth-protected dashboard shell where the weekly grid will live (FR-04).

    Placeholder content only; Sprint 3 fills in the real dashboard shell and
    Sprint 5 embeds the grid itself.
    """

    template_name = 'core/dashboard.html'
