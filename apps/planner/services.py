"""Transactional domain operations shared by planner presentations."""

import re

from django.contrib.auth import get_user_model
from django.db import transaction

from apps.planner.models import ActivityEvent, MentionNotification


@transaction.atomic
def record_activity(time_block, actor, event_type, payload=None):
    """Record one immutable event for an ownership-scoped card."""
    return ActivityEvent.objects.create(
        time_block=time_block,
        actor=actor,
        event_type=event_type,
        payload=payload or {},
    )


@transaction.atomic
def record_mentions(comment):
    """Create notifications for valid `@username` tokens in a comment."""
    MentionNotification.objects.filter(comment=comment).delete()
    usernames = set(re.findall(r'(?<![\w@])@([A-Za-z0-9_.+-]+)', comment.body))
    users = get_user_model().objects.filter(username__in=usernames)
    return [
        MentionNotification.objects.create(comment=comment, mentioned_user=user)
        for user in users
    ]
