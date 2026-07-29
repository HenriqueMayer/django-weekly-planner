"""Signal handlers for the planner app.

Per NFR-02, all signal receivers live in this module and are registered
exclusively from `PlannerConfig.ready()` (apps/planner/apps.py) -- nowhere
else in the codebase.
"""

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.planner.models import PlannerSettings


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_planner_settings(sender, instance, created, **kwargs):
    """Create default `PlannerSettings` for every newly created user (PRD §8.2)."""
    if created:
        PlannerSettings.objects.get_or_create(user=instance)
