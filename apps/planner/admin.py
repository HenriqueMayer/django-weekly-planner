"""Django admin registrations for the planner app (PRD FR-15).

Kept minimal per the sprint scope -- this is a maintenance surface, not a
user-facing feature.
"""

from django.contrib import admin

from apps.planner.models import BlockColor, PlannerSettings, TimeBlock


@admin.register(TimeBlock)
class TimeBlockAdmin(admin.ModelAdmin):
    list_display = ('label', 'user', 'day_of_week', 'start_time', 'end_time', 'color')
    list_filter = ('day_of_week', 'user')


admin.site.register(BlockColor)
admin.site.register(PlannerSettings)
