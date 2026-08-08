# Product Requirements: Routine Organizer

**Version:** 2.0
**Status:** Implemented product baseline
**Last updated:** 2026-08-08

## 1. Product Summary

Routine Organizer is a personal, date-aware weekly planner. Its primary interface is a Monday-to-Sunday time-blocking grid. Users create cards in time slots, open those cards in a detail modal, and manage their week without a single-page application framework.

The product is desktop-first because of the seven-column grid, but the planner remains usable on smaller screens through bounded horizontal and vertical scrolling.

## 2. Product Principles

- Fast capture: creating a card requires only a name; date and time come from the selected cell.
- Server authority: overlap, ownership, recurrence, and upload rules are enforced by Django.
- Progressive interaction: pages are server-rendered and HTMX enhances fragment updates.
- Lean stack: no REST framework, SPA framework, task queue, or external ORM.
- Personal ownership: planner data is private to its owner unless a card is explicitly transferred.
- Accessible basics: semantic controls, keyboard focus, readable contrast, and light/dark themes.

## 3. Users and Access

- Visitors can view the landing page, sign up, and log in.
- Signup uses Django's native username/password flow and signs the user in immediately.
- Authenticated users can access the dashboard, standalone planner, Kanban, notifications, settings, card operations, and exports.
- Planner queries and mutations must be scoped to `request.user`; inaccessible objects return 404.
- The product has no shared boards, teams, roles, email verification, social login, or MFA.

## 4. Weekly Planner

### 4.1 Grid

- The grid contains Monday through Sunday columns.
- Rows use the user's 30 or 60-minute interval.
- The visible day range and 12/24-hour labels are configurable.
- The `week=YYYY-MM-DD` query value is normalized to that date's Monday.
- Invalid or absent week values fall back to the current week.
- Previous, next, and Today controls update the planner and browser URL.
- A compact Sunday-first monthly calendar selects the week containing a clicked date.

### 4.2 Card Scheduling

- Clicking an empty slot opens a compact name form.
- New cards inherit the clicked date, start time, and one-slot duration.
- Existing cards may be edited, deleted, or resized from their top and bottom edges.
- Card duration must be positive; `00:00` as an end time means end of day.
- Cards belonging to the same user may touch but may not overlap on the same date.
- Card colors are optional and come from the owner's personal palette.
- The server may rebuild the complete grid table after a mutation because native table `rowspan` affects neighboring cells.

### 4.3 Settings and Palette

- Planner settings contain slot interval, day start, day end, and time format.
- Settings are created automatically for each new user.
- Settings save through a standard POST and redirect.
- Palette colors have a user-unique name and hexadecimal value.
- Deleting a color preserves associated cards and leaves them with a neutral fallback.

## 5. Card Details

Clicking a card opens an in-page modal. The modal supports:

- Name, description, status, and due datetime.
- Statuses: planned, in progress, partial, completed, incomplete, abandoned, and transferred.
- Reusable colored labels separate from scheduling colors.
- Checklists with completion, editing, deletion, parent items, and ordering.
- Comments, replies, author-only editing/deletion, and `@username` mentions.
- Attachments up to 10 MiB with CSV, DOC, DOCX, JPG/JPEG, Markdown, PDF, PNG, or TXT extensions.
- Transfer to another user when the schedule does not overlap the recipient's cards.
- The latest 20 activity events.
- Recurrence controls when the card belongs to a series.

Current UI boundaries:

- Schedule, time, scheduling color, and card deletion remain grid actions rather than modal actions.
- Checklist child controls and comment rendering are limited to one visible nesting level.
- Attachment validation checks extension and size, not MIME content.
- Transfer is immediate and has no recipient acceptance flow.

## 6. Recurrence

- Recurrence rules are weekly and select one or more weekdays.
- A rule stores its date range, schedule, card content, status, and color.
- Occurrences are materialized as ordinary `TimeBlock` records.
- Dates that overlap an existing card are skipped during materialization.
- An occurrence may be skipped, restored, or overridden independently.
- Updating a rule rebuilds future occurrences that are neither skipped nor overridden.
- The product does not support daily/monthly/yearly rules, recurrence counts, or a dedicated series-delete action.
- Recurrence creation exists in the backend form flow but is not exposed by the compact quick-create UI.

## 7. Collaboration

- Comments may mention any existing username using `@username`.
- A mention creates one persisted notification per comment and mentioned user.
- Editing a comment recalculates its mention notifications.
- Notifications can be marked read individually.
- A card has one owner at a time; transfer changes that owner and creates an audit record.
- Comments retain their authors, attachments retain their uploaders, and activity retains its actors after transfer.
- There is no real-time delivery, email, push, mark-all-read, or notification link that opens the referenced card.

## 8. Kanban and Export

### 8.1 Kanban

- Kanban shows the selected week's cards grouped into the seven statuses.
- Cards show their schedule and labels and open the shared detail modal.
- The board is a read-only grouping view; it has no drag-and-drop or manual ordering.

### 8.2 Export

- Markdown and SVG are generated by the server.
- PNG captures the rendered planner table in the browser.
- PDF uses the browser's print dialog.
- All exports use the selected week.
- Markdown includes scheduled cards even when they fall outside the configured visible hours; visual exports reflect the visible grid.

## 9. Themes and Responsiveness

- A global toggle switches between light and Darcula-inspired dark themes.
- The preference is stored in browser `localStorage`; otherwise the OS preference is used.
- Navigation active states must remain legible in both themes.
- User-selected card colors receive a browser-calculated readable foreground color.
- Theme preference is browser-local and is not synchronized to the account.

## 10. Quality Requirements

- Django CSRF protection applies to all state-changing requests, including HTMX requests.
- Models validate duration, recurrence, colors, and overlap before normal saves.
- Every domain model inherits timestamp fields.
- The complete automated test suite must pass before merge.
- Ruff, Django system checks, migration checks, and `git diff --check` must pass.
- New behavior should receive server-side tests; browser-only behavior should be manually smoke-tested until end-to-end tests are introduced.

## 11. Known Product Limitations

- SQLite limits write concurrency and is intended for small deployments.
- Timezone is fixed to UTC and the interface language is English.
- There are no browser end-to-end tests, JavaScript unit tests, or CI workflow.
- Quick create does not expose recurrence, repeat-day, or color controls.
- Uploaded media needs separate persistence and serving configuration in production.
- Out-of-range or unplaced cards tracked by the grid builder are not surfaced in the interface.
