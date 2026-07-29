"""URL configuration for the planner app."""

from django.urls import path

from apps.planner.views import GridView, SettingsUpdateView

app_name = 'planner'

urlpatterns = [
    path('', GridView.as_view(), name='grid'),
    path('settings/', SettingsUpdateView.as_view(), name='settings'),
]
