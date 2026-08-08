# Architecture

This document describes the current system. Product behavior belongs in [`ProductRequirementDocument.md`](ProductRequirementDocument.md); development and deployment procedures live in [`DEVELOPMENT.md`](DEVELOPMENT.md) and [`OPERATIONS.md`](OPERATIONS.md).

## 1. System Shape

Routine Organizer is a server-rendered Django application with three local apps:

- `apps.core`: public landing page, authenticated dashboard, and `TimestampedModel`.
- `apps.accounts`: signup form and native Django authentication views.
- `apps.planner`: scheduling models, forms, views, grid/date/recurrence/export services, templates, and tests.

The frontend uses Django templates, compiled Tailwind CSS, vendored HTMX, and small vanilla-JavaScript modules. There is no JSON API or SPA state layer.

## 2. Request and Rendering Model

- Full requests render pages extending `templates/base.html`.
- HTMX GET requests render targeted fragments such as the planner surface, calendar picker, forms, and card panel.
- HTMX mutation responses generally rebuild `#grid-table`; native table `rowspan` means a card mutation can alter neighboring cells.
- Card-detail mutations return the modal plus an out-of-band grid refresh when the visible card changes.
- `base.html` supplies the CSRF token through inherited `hx-headers`.
- JavaScript uses event delegation so behavior survives HTMX swaps.

Important fragments:

- `planner/partials/planner_surface.html`: week navigation and grid.
- `planner/partials/grid_table.html`: shared planner table.
- `planner/partials/calendar_picker.html`: month-local HTMX date picker.
- `planner/partials/quick_block_form.html`: compact card creation.
- `planner/partials/card_detail_panel.html`: modal and collaboration features.

## 3. Domain Model

All planner models inherit `TimestampedModel`.

| Model | Responsibility |
|---|---|
| `PlannerSettings` | Per-user interval, visible hours, and time format |
| `TimeBlock` | One scheduled card occurrence owned by one user |
| `BlockColor` | User-owned scheduling color palette |
| `CardLabel` | User-owned reusable card label |
| `RecurrenceSeries` | Weekly recurrence rule |
| `RecurrenceException` | Date omitted from a recurrence series |
| `ActivityEvent` | Card activity audit entry |
| `ChecklistItem` | Ordered, optionally parented checklist item |
| `CardComment` | Authored, optionally parented card comment |
| `MentionNotification` | Read/unread notification for a comment mention |
| `CardAttachment` | Uploaded file metadata and storage reference |
| `CardTransfer` | Card ownership-transfer audit record |

`TimeBlock.scheduled_date` is the current scheduling identity. `day_of_week` is synchronized from it and remains available for legacy date-less rows. Normal planner forms populate `scheduled_date`.

## 4. Core Services

### Grid

`apps/planner/grid.py` converts settings and cards into typed `WeekGrid`, `GridRow`, and `GridCell` structures. Templates only iterate this matrix; duration snapping, placement, collision fallback, and `rowspan` calculation stay in Python.

### Dates

`apps/planner/dates.py` normalizes selected dates to Monday, builds labels and navigation values, and creates the Sunday-first monthly picker matrix. Week navigation replaces the planner surface; month browsing replaces only the calendar fragment.

### Recurrence

`apps/planner/recurrence.py` materializes weekly rules into `TimeBlock` occurrences. Rule changes preserve skipped and overridden occurrences while rebuilding eligible future rows. Exceptions represent intentionally omitted dates.

### Export

`apps/planner/export.py` creates Markdown and SVG output. Browser JavaScript handles PNG capture and print/PDF because those formats reflect the rendered table.

## 5. Ownership and Integrity

- Authenticated planner views filter objects by `request.user`.
- Cross-user object access returns 404 rather than exposing object existence.
- `TimeBlock.save()` runs model validation and rejects non-positive duration and same-owner overlap.
- `00:00` is treated as end of day only when used as an end time.
- Direct `QuerySet.update()` bypasses model validation and must be used only with explicit safeguards.
- Color and label names are unique per owner.
- Card transfers run overlap validation for the recipient and create `CardTransfer` records.

Related records such as comments, attachments, activity, and checklist items remain attached to the card after transfer. Their original authors/uploaders/actors remain unchanged. A recurrence series and user-owned color or label definitions are not automatically re-owned by transfer.

## 6. Frontend Modules

| Module | Responsibility |
|---|---|
| `theme.js` | Initial theme choice and persisted toggle |
| `contrast.js` | Readable card text for arbitrary hex colors |
| `grid-drag.js` | Pointer-based card resizing |
| `block-form-close.js` | Quick-form cancellation and Escape handling |
| `week-navigation.js` | Keyboard week navigation |
| `card-panel.js` | Modal focus, backdrop, scroll lock, and Escape handling |
| `checklist-drag.js` | HTML5 checklist ordering |
| `color-sync.js` | Native picker and hex field synchronization |
| `export.js` | PNG and print actions |
| `ui-close.js` | Global close behavior for open details elements |

Tailwind v4 uses CSS-first configuration in `static/css/input.css`. The compiled `static/css/app.css` is committed because Docker and CI do not build it.

## 7. Main Routes

- `/`: landing page.
- `/dashboard/`: primary planner and toolbar.
- `/accounts/`: signup, login, and logout.
- `/planner/`: standalone weekly grid.
- `/planner/kanban/`: selected-week status board.
- `/planner/notifications/`: mention notifications.
- `/planner/blocks/...`: card CRUD, details, recurrence, checklist, comment, label, attachment, and transfer actions.
- `/planner/colors/...`: palette CRUD.
- `/planner/export/...`: Markdown and SVG downloads.
- `/admin/`: Django admin.

## 8. Persistence and Files

- Local development stores SQLite at `db.sqlite3`.
- Docker sets `SQLITE_DB_PATH=/app/data/db.sqlite3`; Compose persists `/app/data`.
- Attachments use Django's filesystem storage under `MEDIA_ROOT` (`/app/media` in Docker).
- WhiteNoise serves collected static assets, not uploaded media.
- Deleting an attachment explicitly removes its file; deleting a card cascades metadata but does not guarantee physical file cleanup.

## 9. Architectural Decisions

- Django native auth instead of an external account package.
- SQLite instead of a network database for simple, small deployments.
- Server-rendered HTML and HTMX instead of REST plus SPA.
- Native table layout for accurate weekly `rowspan` rendering.
- Whole-table mutation swaps for correctness over fragile cell patching.
- Materialized recurrence occurrences for ordinary card behavior.
- Tailwind standalone CLI instead of Node-based frontend tooling.
- Browser-native PNG/print capabilities to avoid runtime dependencies.

## 10. Current Gaps

- No CI, browser end-to-end tests, JavaScript unit tests, or performance benchmarks.
- No production media storage/serving configuration.
- No health check, monitoring, backups, reverse proxy, or HTTPS configuration.
- No real-time notifications or collaborative board permissions.
- Deeper checklist/comment trees are supported by relationships but not fully rendered or controlled by the UI.
