from django.db import models


class TimestampedModel(models.Model):
    """Abstract base model providing creation and update timestamps.

    Every domain model in this project (e.g. `TimeBlock`, `BlockColor`,
    `PlannerSettings`) inherits from this class so that record creation
    and modification times are tracked consistently (NFR-08).
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
