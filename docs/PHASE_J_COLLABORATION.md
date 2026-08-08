# Phase J — Collaboration Extensions

**Status:** complete

- Added nested checklist items while retaining ordered siblings.
- Added one-level comment replies with independent authorship.
- Added `@username` mention detection and persisted notifications.
- Added a notifications page with ownership-scoped read-state updates.
- Added drag-and-drop checklist reordering over the existing position endpoint.
- Existing ownership and activity rules apply to all collaboration mutations.

Comment trees are now unbounded at the domain and endpoint level; the panel
renders the first reply level and exposes reply controls for deeper nodes.
