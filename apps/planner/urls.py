"""URL configuration for the planner app."""

from django.urls import path

from apps.planner.views import (
    BlockCancelView,
    BlockCreateView,
    BlockDeleteView,
    BlockResizeView,
    BlockUpdateView,
    CardDetailUpdateView,
    CardDetailView,
    CellCancelView,
    ChecklistAddView,
    ChecklistDeleteView,
    ChecklistMoveView,
    ChecklistToggleView,
    ChecklistUpdateView,
    ColorCancelView,
    ColorCreateView,
    ColorDeleteView,
    ColorUpdateView,
    ExportMarkdownView,
    ExportSVGView,
    GridView,
    OccurrenceRestoreView,
    OccurrenceSkipView,
    PaletteView,
    RecurrenceUpdateView,
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
    path('blocks/<int:pk>/details/', CardDetailView.as_view(), name='card-detail'),
    path(
        'blocks/<int:pk>/details/update/',
        CardDetailUpdateView.as_view(),
        name='card-detail-update',
    ),
    path('blocks/<int:pk>/checklist/add/', ChecklistAddView.as_view(), name='checklist-add'),
    path(
        'blocks/<int:pk>/checklist/<int:item_pk>/toggle/',
        ChecklistToggleView.as_view(),
        name='checklist-toggle',
    ),
    path(
        'blocks/<int:pk>/checklist/<int:item_pk>/delete/',
        ChecklistDeleteView.as_view(),
        name='checklist-delete',
    ),
    path(
        'blocks/<int:pk>/checklist/<int:item_pk>/edit/',
        ChecklistUpdateView.as_view(),
        name='checklist-update',
    ),
    path(
        'blocks/<int:pk>/checklist/<int:item_pk>/move/',
        ChecklistMoveView.as_view(),
        name='checklist-move',
    ),
    path(
        'blocks/<int:pk>/recurrence/update/',
        RecurrenceUpdateView.as_view(),
        name='recurrence-update',
    ),
    path('blocks/<int:pk>/skip/', OccurrenceSkipView.as_view(), name='occurrence-skip'),
    path('blocks/<int:pk>/restore/', OccurrenceRestoreView.as_view(), name='occurrence-restore'),
    path('cells/cancel/', CellCancelView.as_view(), name='cell-cancel'),
    path('colors/', PaletteView.as_view(), name='palette'),
    path('colors/create/', ColorCreateView.as_view(), name='color-create'),
    path('colors/<int:pk>/edit/', ColorUpdateView.as_view(), name='color-edit'),
    path('colors/<int:pk>/cancel/', ColorCancelView.as_view(), name='color-cancel'),
    path('colors/<int:pk>/delete/', ColorDeleteView.as_view(), name='color-delete'),
    path('export/markdown/', ExportMarkdownView.as_view(), name='export-markdown'),
    path('export/svg/', ExportSVGView.as_view(), name='export-svg'),
]
