"""URL configuration for the planner app."""

from django.urls import path

from apps.planner.views import SettingsUpdateView

app_name = 'planner'

urlpatterns = [
    path('settings/', SettingsUpdateView.as_view(), name='settings'),
]
