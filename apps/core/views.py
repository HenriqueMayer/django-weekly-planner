from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from apps.planner.forms import PlannerSettingsForm
from apps.planner.grid import build_week_grid
from apps.planner.models import BlockColor, PlannerSettings, TimeBlock


class LandingView(TemplateView):
    """Public landing/presentation page (FR-01). Accessible without auth."""

    template_name = 'core/landing.html'


class DashboardView(LoginRequiredMixin, TemplateView):
    """Auth-protected dashboard shell where the weekly grid lives (FR-04).

    Sprint 5 embeds the real grid (`week_grid`, built by
    `apps.planner.grid.build_week_grid()` -- the same builder and the same
    `settings_obj` `GridView` uses for the standalone `/planner/` page, so
    there is no duplicated grid-computation logic). Sprint 4 already adds
    `settings_form` to context so the toolbar's settings dropdown (PRD
    4.4.3) can render inline. Sprint 7 adds `colors`, the user's own
    `BlockColor` queryset, so the toolbar's palette dropdown (PRD 7.1.1)
    can `{% include 'planner/partials/palette_panel.html' %}` inline the
    same way, on initial page load.
    """

    template_name = 'core/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        settings_obj, _ = PlannerSettings.objects.get_or_create(user=self.request.user)
        context['settings_form'] = PlannerSettingsForm(instance=settings_obj)
        blocks = TimeBlock.objects.filter(user=self.request.user).select_related('color')
        context['week_grid'] = build_week_grid(settings_obj, blocks)
        context['colors'] = BlockColor.objects.filter(user=self.request.user).order_by('name')
        return context
