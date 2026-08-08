from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import render
from django.views.generic import TemplateView

from apps.planner.dates import (
    navigation_context,
    normalize_week_start,
    parse_week_start,
    week_end,
)
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
        week_start = parse_week_start(self.request.GET.get('week'))
        legacy_blocks = (
            Q(scheduled_date__isnull=True)
            if week_start == normalize_week_start()
            else Q(pk__in=[])
        )
        blocks = TimeBlock.objects.filter(user=self.request.user).filter(
            Q(scheduled_date__gte=week_start, scheduled_date__lte=week_end(week_start))
            | legacy_blocks,
        ).select_related('color')
        context['week_grid'] = build_week_grid(settings_obj, blocks, week_start)
        context['colors'] = BlockColor.objects.filter(user=self.request.user).order_by('name')
        context.update(navigation_context(week_start, self.request.GET.get('month')))
        context['navigation_htmx'] = True
        return context

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get('HX-Request') == 'true':
            if self.request.headers.get('HX-Target') == 'calendar-picker':
                return render(self.request, 'planner/partials/calendar_picker.html', context)
            return render(self.request, 'planner/partials/planner_surface.html', context)
        return super().render_to_response(context, **response_kwargs)
