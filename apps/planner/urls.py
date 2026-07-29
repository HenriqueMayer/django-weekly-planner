"""URL configuration for the planner app."""

from django.urls import path

from apps.planner.views import (
    BlockCancelView,
    BlockCreateView,
    BlockDeleteView,
    BlockResizeView,
    BlockUpdateView,
    CellCancelView,
    GridView,
    SettingsUpdateView,
)

app_name = 'planner'

urlpatterns = [
    path('', GridView.as_view(), name='grid'),
    path('settings/', SettingsUpdateView.as_view(), name='settings'),
    path('blocks/create/', BlockCreateView.as_view(), name='block-create'),
    path('blocks/<int:pk>/edit/', BlockUpdateView.as_view(), name='block-edit'),
    path('blocks/<int:pk>/delete/', BlockDeleteView.as_view(), name='block-delete'),
    path('blocks/<int:pk>/resize/', BlockResizeView.as_view(), name='block-resize'),
    path('blocks/<int:pk>/cancel/', BlockCancelView.as_view(), name='block-cancel'),
    path('cells/cancel/', CellCancelView.as_view(), name='cell-cancel'),
]
