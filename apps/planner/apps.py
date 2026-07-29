from django.apps import AppConfig


class PlannerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.planner'
    label = 'planner'

    def ready(self):
        """Register signal handlers (PRD §8.2, NFR-02).

        Imported here, inside `ready()`, rather than at module level: this
        module is imported during Django's app-loading phase, before the
        app registry is fully populated, so importing models/signals at
        import time risks `AppRegistryNotReady`. Deferring the import to
        `ready()` is Django's documented pattern for this.
        """
        from apps.planner import signals  # noqa: F401
