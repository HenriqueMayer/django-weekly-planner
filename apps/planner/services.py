"""Transactional domain operations shared by planner presentations."""

from django.db import transaction

from apps.planner.models import ActivityEvent


@transaction.atomic
def record_activity(time_block, actor, event_type, payload=None):
    """Record one immutable event for an ownership-scoped card."""
    return ActivityEvent.objects.create(
        time_block=time_block,
        actor=actor,
        event_type=event_type,
        payload=payload or {},
    )
