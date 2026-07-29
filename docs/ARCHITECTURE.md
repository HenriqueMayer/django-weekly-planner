# Architecture — Time-Blocking Routine Organizer

Living document tracking how the codebase actually looks, as it's built sprint by sprint against
[`ProductRequirementDocument.md`](./ProductRequirementDocument.md). Where reality diverges from the
PRD, it's recorded here rather than silently followed or silently ignored.

---

## Current status

**Sprint 1 — Project Foundation & Design System Base: complete.**
**Sprint 2 — Accounts (Native Authentication): complete.**
**Sprint 3 — Landing Page & Dashboard Shell: complete.**
**Sprint 4 — Planner Domain (Models, Signals, Admin, Settings): complete.**
**Sprint 5 — Grid Rendering (Server-Side): complete.**
**Sprint 6 — Block Interactivity (HTMX + Vanilla JS): complete.**
**Sprint 7 — Color Palette, Theming & UX Polish: complete.**
**Sprint 8 — Automated Tests: complete.**
**Sprint 9 — Docker, Documentation & Open-Source Template Release: complete (except 9.3.2, deliberately withheld).**
**Sprint 10 — Grid Export (Markdown, SVG, PNG, PDF): complete.** *(Post-launch addition, not in the PRD's original §13 plan — see below.)*

The project boots, has a Tailwind v4 design-system base, full native auth (signup, login,
logout), a real landing page (hero, features, decorative grid mock), and a dashboard shell
(header, toolbar). The planner domain exists: `BlockColor`, `PlannerSettings`, and `TimeBlock`
models with full validation, a signal auto-creating each new user's settings, admin registration,
and a live settings form reachable both standalone and as an inline dashboard-toolbar dropdown.
The dashboard renders a real, server-computed weekly grid (`apps/planner/grid.py`) —
Monday-Sunday columns, time-slot rows honoring the user's interval/range/format settings, and
blocks placed with correct `rowspan`, including midnight-crossing and interval-misaligned blocks.
The grid is no longer read-only: blocks can be created, edited, deleted, resized (by drag or by a
keyboard/click '+/-' fallback), and repeated across days, all via inline HTMX partial swaps with
zero full-page reloads. Users now also maintain a personal color palette (create/rename/recolor/
delete, HTMX-driven, from a second dashboard-toolbar dropdown) — deleting a color immediately
clears affected blocks to the neutral fallback appearance in the same response, not just
eventually. A dark/light and responsive audit pass fixed several real contrast and layout bugs
across both old and new screens, and `ruff` is now configured as a dev-only lint tool. The
project has a real, permanent automated test suite (82 tests: models, views, and the pure-Python
grid builder) that passes clean from a fresh clone with no ordering dependencies — and now also
runs identically inside a Docker container. The project can now be built and run with
`docker compose up` alone (SQLite persisted in a named volume, static files served by WhiteNoise,
no separate nginx), and has a rewritten `README.md`, a new `CONTRIBUTING.md`, and a `LICENSE`
(PolyForm Noncommercial 1.0.0 — personal use only, selling not permitted, a deliberate deviation
from the PRD's "open-source" framing, see below), making it ready to serve as a public,
source-available template — everything except actually
tagging and publishing it (9.3.2), which is withheld this session by explicit instruction. On top
of the original nine-sprint plan, users can now also export their week as Markdown, SVG, a
client-side-rendered PNG, or a printed/PDF page (`static/js/export.js` + a new "Export" toolbar
dropdown) — a post-launch feature added entirely without any new runtime dependency, per explicit
user direction. The automated suite now stands at 101 tests. See §13 in the PRD for the full
sprint plan and checklist.

---

## Directory layout (as built)

```
django-weekly-planner/
├── manage.py
├── pyproject.toml          # uv-managed; django>=6.0.7 is the sole runtime dependency;
│                           # ruff lives in [dependency-groups].dev (Sprint 7, 7.3.1);
│                           # gunicorn/whitenoise live in [dependency-groups].docker (Sprint 9)
├── uv.lock
├── .python-version         # 3.12
├── .env.example            # Sprint 9: notes docker-compose.yml also reads this file
├── .gitignore
├── Dockerfile              # Sprint 9: python:3.12-slim, uv sync, collectstatic at build time,
│                           # migrate + gunicorn at container start
├── docker-compose.yml      # Sprint 9: one `web` service, sqlite_data volume, optional env_file
├── .dockerignore           # Sprint 9
├── CONTRIBUTING.md         # Sprint 9: add-an-app / swap tokens / grid defaults / SQLite limits
├── LICENSE                 # Sprint 9: PolyForm Noncommercial 1.0.0 (personal use only, no selling)
├── assets/
│   └── preview.svg         # pre-existing concept sketch, embedded in README (Sprint 9)
├── config/                 # settings package (see "Deviations" below)
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── apps/
│   ├── core/                # landing, dashboard shell, TimestampedModel
│   │   ├── models.py         # abstract TimestampedModel
│   │   ├── views.py          # LandingView, DashboardView (both plain TemplateView)
│   │   ├── urls.py           # app_name = 'core'
│   │   ├── tests.py          # Sprint 8: 4 tests (landing anon/auth, dashboard auth-gate+context)
│   │   └── templates/core/   # landing.html (hero/features/grid-mock — Sprint 3),
│   │                         # dashboard.html (header/toolbar/real grid — Sprint 3-5)
│   ├── accounts/             # native auth — Sprint 2
│   │   ├── forms.py           # SignUpForm, LoginForm (shared INPUT_CLASSES)
│   │   ├── views.py           # SignUpView(CreateView)
│   │   ├── urls.py            # app_name = 'accounts'; login/, signup/, logout/
│   │   ├── tests.py           # Sprint 8: 5 tests (signup, login success/failure, logout)
│   │   └── templates/accounts/  # login.html, signup.html
│   └── planner/               # domain models/settings — Sprint 4; grid — Sprint 5; CRUD — Sprint 6
│       ├── models.py           # BlockColor, PlannerSettings, TimeBlock (all TimestampedModel);
│       │                       # also minutes_since_midnight()/round_half_up()/time_from_minutes()/
│       │                       # format_time_label() (Sprint 10: promoted here, public, from
│       │                       # what used to be grid.py's private _format_time_label())
│       ├── grid.py             # build_week_grid() — pure-Python matrix builder (Sprint 5)
│       ├── export.py           # Sprint 10 (new feature): render_week_markdown(),
│       │                       # build_svg_export() + SvgRect/SvgText/SvgExport dataclasses
│       ├── signals.py          # post_save on User -> auto-create PlannerSettings
│       ├── apps.py             # PlannerConfig.ready() registers signals.py
│       ├── admin.py            # all three models registered
│       ├── forms.py            # PlannerSettingsForm, TimeBlockForm (Sprint 6, incl. repeat_days),
│       │                       # BlockColorForm (Sprint 7, hand-rolled uniqueness clean())
│       ├── views.py            # SettingsUpdateView, GridView, + Sprint 6's BlockCreateView,
│       │                       # BlockUpdateView, BlockDeleteView, BlockResizeView,
│       │                       # CellCancelView, BlockCancelView, + Sprint 7's PaletteView,
│       │                       # ColorCreateView, ColorUpdateView, ColorCancelView,
│       │                       # ColorDeleteView, + Sprint 10's ExportMarkdownView,
│       │                       # ExportSVGView (all LoginRequiredMixin)
│       ├── urls.py             # app_name = 'planner'; '' (grid), settings/, blocks/*,
│       │                       # cells/cancel/, colors/* (Sprint 7), export/* (Sprint 10)
│       ├── tests/              # Sprint 8: package, not a flat tests.py (3 distinct concerns)
│       │   ├── test_models.py   # 26 tests — duration/rowspan/clean()/overlap/hex/unique/SET_NULL/signal
│       │   ├── test_views.py    # 47 tests — auth, ownership isolation, CRUD/resize, grid_oob,
│       │   │                    # settings, + Sprint 10's export view tests
│       │   ├── test_grid.py     # 8 tests — build_week_grid() matrix, SimpleTestCase, no DB
│       │   └── test_export.py   # Sprint 10: 11 tests — render_week_markdown()/build_svg_export(),
│       │                        # SimpleTestCase, no DB
│       └── templates/planner/
│           ├── settings_form.html    # standalone settings page (Sprint 4)
│           ├── grid.html             # standalone grid page (Sprint 5); loads grid-drag.js/
│           │                         # contrast.js (Sprint 6, extra_body block)
│           └── partials/
│               ├── grid_table.html    # shared <table> + #grid-toast, included by grid.html +
│               │                     # dashboard.html; grid_oob flag (Sprint 7) lets it also
│               │                     # serve as an OOB refresh for palette CRUD responses;
│               │                     # print:max-h-none print:overflow-visible print:ring-0
│               │                     # on its wrapper (Sprint 10, PDF-via-print export)
│               ├── block_cell.html    # block-start <td>: presentation, hover edit/delete
│               │                     # controls, resize handles (Sprint 6)
│               ├── empty_cell.html    # empty, clickable <td>; hx-get opens block_form.html
│               ├── block_form.html    # Sprint 6: shared inline create/edit form, overlay-card
│               │                     # layout, repeat-days checkboxes, +/- resize buttons
│               ├── palette_panel.html    # Sprint 7: #palette-panel, embedded in dashboard.html's
│               │                        # Palette dropdown + primary CRUD swap target
│               ├── color_row.html        # Sprint 7: one BlockColor's display row
│               ├── color_form_row.html   # Sprint 7: shared create/edit form, dual-moded like
│               │                        # block_form.html; hand-rolled hex_code + color picker
│               ├── color_add_trigger.html # Sprint 7: "+ Add color" button / cancel-add target
│               └── grid_export.svg        # Sprint 10 (new feature): standalone SVG export
│                                          # template, iterates SvgExport, zero layout math
├── templates/
│   ├── base.html
│   └── partials/
│       ├── navbar.html        # print:hidden (Sprint 10)
│       ├── footer.html        # print:hidden (Sprint 10)
│       ├── form_field.html    # shared label/widget/help/error row — Sprint 2
│       └── buttons/
│           ├── primary.html   # shared primary-button partial (<a>/<button>) — Sprint 4
│           └── secondary.html # shared secondary-button partial (<a>/<button>/<summary>,
│                               # +hx_get/hx_target/hx_swap, +data_export_png/data_export_print
│                               # [Sprint 10]) — Sprint 7, extracted once a 6th hand-duplicated
│                               # call site crossed Sprint 6's own pre-flagged threshold
├── static/
│   ├── css/
│   │   ├── input.css        # Tailwind v4 source (CSS-first config); .htmx-request rule (Sprint 6)
│   │   └── app.css          # compiled output — committed, not built in CI
│   └── js/
│       ├── htmx.min.js      # vendored, not CDN-loaded
│       ├── theme.js
│       ├── grid-drag.js     # Sprint 6: Pointer Events drag-to-resize, document-delegated
│       ├── contrast.js      # Sprint 6 (early PRD 7.2.2): block text-color luminance rule
│       ├── color-sync.js    # Sprint 7: pairs a native <input type=color> with a hex text
│       │                     # input via data-hex-sync, document-delegated (same rationale
│       │                     # as grid-drag.js/contrast.js)
│       └── export.js        # Sprint 10 (new feature): canvas-based PNG render of #grid-table
│                             # (getBoundingClientRect()/getComputedStyle() per cell) +
│                             # window.print() trigger, document-delegated (same rationale)
└── db.sqlite3               # gitignored
```

---

## Deviations from the PRD, and why

The PRD was written slightly ahead of the toolchain actually in play. Each deviation below was a
deliberate call made by the implementing agent, not drift — flagged here so nobody "fixes" it back
to the PRD's literal wording later.

| PRD says | Built instead | Why |
|---|---|---|
| Django 5.x | **Django 6.0.7** | Already the installed version at project start; PRD text just hadn't caught up. All APIs verified against the 6.0 docs. |
| `requirements.txt` | **`uv` + `pyproject.toml` + `uv.lock`** | Project was bootstrapped with `uv` before this sprint began; keeps a lockfile instead of an unpinned freeze. |
| `django-admin startproject config .` (settings package `config/`, shared app `apps/core/`) | Same end state, reached by **renaming** the pre-existing `core/` settings package to `config/` | The repo's initial scaffold had already used `core/` as the settings package name, which collides with the PRD's `apps/core/` shared app. Renaming the settings package (updating `ROOT_URLCONF`, `WSGI_APPLICATION`, `ASGI_APPLICATION`, `manage.py`) frees `core` for the app namespace, matching the PRD's intent without restructuring apps. |
| Tailwind v3 (`@tailwind` directives, `tailwind.config.js`, `darkMode: 'class'`) | **Tailwind v4**, CSS-first config in `static/css/input.css`: `@import 'tailwindcss'`, `@custom-variant dark (&:where(.dark, .dark *));`, `@source '../../templates'` / `@source '../../apps'` | Tailwind v4 removed the JS config file and `@tailwind` directives entirely; there is no v3 CLI to fall back to. Confirmed against current Tailwind docs. |
| `LOGIN_REDIRECT_URL = 'dashboard'`, `LOGOUT_REDIRECT_URL = 'landing'` (bare names) | **Namespaced**: `LOGIN_URL = 'accounts:login'`, `LOGIN_REDIRECT_URL = 'core:dashboard'`, `LOGOUT_REDIRECT_URL = 'core:landing'` | This project namespaces every app's URLs (`app_name = 'core'` / `'accounts'`, set in Sprint 1/2). The PRD's bare names would fail to resolve; the namespaced form is the same intent, correctly expressed for this project's URLconf. |
| PRD 2.3.1 implies `LoginView`'s default form is already styled | Added `LoginForm(AuthenticationForm)` in `apps/accounts/forms.py`, sharing the `INPUT_CLASSES` constant with `SignUpForm`, wired via `LoginView.as_view(authentication_form=LoginForm)` | `LoginView` uses Django's default `AuthenticationForm` unless told otherwise — left alone, its inputs would render unstyled while `SignUpForm`'s were styled. Not a scope addition, just the necessary plumbing for 2.3.1 to actually hold. |
| PRD 3.2.1 / §9.3 list three toolbar placeholders: Settings, Palette, theme toggle | Dashboard toolbar (`apps/core/templates/core/dashboard.html`) has only two: Settings and Palette | The theme toggle already exists globally in the navbar (`templates/partials/navbar.html`, `#theme-toggle`, included via `base.html` on every screen). FR-14 only requires it be "available on all screens," which it already is — duplicating it in the toolbar would mean a second DOM element bound to the same class string and JS wiring, itself a small NFR-05/R5 risk (two toggles that could visually desync). Reviewed and accepted by `code-reviewer`. |
| PRD 4.1.1: `BlockColor` uses `unique_together (user, name)` | **`Meta.constraints = [UniqueConstraint(fields=['user', 'name'], name='unique_block_color_name_per_user')]`** | Current Django 6.0 docs recommend `UniqueConstraint` over `unique_together` ("may eventually replace" it), confirmed via Context7. Identical DB-level uniqueness and `ValidationError` behavior via `full_clean()`; just the currently-recommended spelling. Reviewed and confirmed correct by `code-reviewer` (independently re-checked against the docs, not just trusting the claim). |
| PRD 4.4.3: settings rendered as "a dropdown panel/card in the dashboard toolbar" | A no-JS **`<details>`/`<summary>`** dropdown (PRD §9.2's own documented "Menus/dropdowns" pattern), containing the real `PlannerSettingsForm`, posting as a plain (non-HTMX) `POST` to `planner:settings` | HTMX-driven interactivity is explicitly Sprint 6 scope; wiring an HTMX fragment swap here would pull that forward. A plain POST that redirects back to `core:dashboard` on success already satisfies 4.4.3's own wording ("on save, redirect ... to re-render the grid") without adding scope. `DashboardView` gained a small `get_context_data()` building the bound form — the one Python change needed to make the dropdown work; everything else is template-only. |
| PRD 5.1.1: grid builder returns "a matrix of rows × 7 cells" | `build_week_grid()` returns typed dataclasses (`WeekGrid`/`GridRow`/`GridCell`), plus `out_of_range_blocks` and `unplaced_blocks` lists not named in the PRD | Same matrix shape and semantics, just attribute access instead of raw nested lists/dicts — friendlier for `{% for %}` template iteration (R2). The two extra lists are where PRD R3's "clamp/flag blocks... instead of deleting them" guidance concretely lives: a block can fail to render either because its stored time falls outside `[day_start, day_end)` (`out_of_range_blocks`) or because, after interval-snapping, no free row was left in its day's column (`unplaced_blocks`) — a distinct, rarer failure mode surfaced during `code-reviewer`'s pass (see below). Neither list is consumed by any template yet; the data just isn't silently lost. |
| PRD 4.1.4's `get_rowspan(interval)` (Sprint 4) used floor division | Changed this sprint to **round-half-up**, via a new shared `round_half_up()` helper in `apps/planner/models.py` | `code-reviewer` caught that `get_rowspan()` (`90 // 60 == 1`) disagreed with `grid.py`'s own independent rowspan computation for the same block (`2`, via round-half-up) — the PRD's own 5.1.3 explicitly requires "snap display to nearest slot boundary," which floor division cannot produce. Fixed by extracting one shared `round_half_up()` function (alongside `minutes_since_midnight()`, this codebase's established single home for time-math helpers) and having both `get_rowspan()` and `grid.py` use it, so they can no longer disagree. `get_rowspan()` itself was not removed — it remains documented model API and Sprint 8.1.1's planned test target, just corrected. |
| PRD 6.1.2/6.1.3 imply separate `BlockCreateFormView` (GET) and `BlockCreateView` (POST) classes | **One `BlockCreateView(CreateView)`** handling both verbs | `CreateView` already natively handles GET (unbound/initial form) and POST (validate+save) — a second, near-identical class would be pure duplication with no behavioral benefit, against NFR-01. Same reasoning applies to `BlockUpdateView` for 6.2.1/6.2.2. |
| PRD 6.1.3/6.2.2/6.3.3 say re-render "the affected day column fragment" | **Every mutating view re-renders the entire grid table** (`_render_grid_response()`, `apps/planner/views.py`) | The grid is a single native `<table>` using `rowspan` for vertical merges (Sprint 5). Any mutation can reshape which rows are `'occupied'` vs. `'empty'`/`'block-start'` for a whole day column, changing how many `<td>` elements exist across multiple `<tr>` rows — not safely expressible as a small HTMX out-of-band patch without desync risk. The PRD's own 6.1.3 wording explicitly offers "simply re-render the affected day column... for correctness" as the sanctioned simpler fallback; re-rendering the whole table (cheap — pure Python over ≤100 blocks, NFR-03) is that same idea taken to its simplest, always-correct conclusion. `code-reviewer` reviewed this design decision directly (not just the resulting code) and confirmed it sound, while flagging one accepted side effect — see the Sprint 6 section below. |
| PRD 6.2.3 implies a `DeleteView` | **A small custom `View`, POST-only** (`BlockDeleteView`) | The generic `DeleteView`'s GET-renders-a-confirmation-page default is unused scope here — the confirmation step is the client-side `hx-confirm` attribute, not a server-rendered page. |
| PRD 7.1.2 names three color CBVs (`ColorCreateView`, `ColorUpdateView`, `ColorDeleteView`) | **Two more small views added**: `PaletteView` (GET, restores the "+ Add color" trigger) and `ColorCancelView` (GET, restores a color's display row after an edit is cancelled) | Direct palette-panel analogs of Sprint 6's own `CellCancelView`/`BlockCancelView`, which the PRD's 6.1.5/6.2.1 wording likewise didn't name explicitly — same reasoning, not new scope. |
| PRD 7.1.1 doesn't mention a uniqueness-validation gap | `BlockColorForm.clean()` hand-rolls a `(user, name)` uniqueness check | `user` is excluded from `Meta.fields`, so Django's automatic `UniqueConstraint` validation never fires for it during `full_clean()` (traced through the installed Django 6.0.7 source by `code-reviewer`, not assumed) — without this, a duplicate name would 500 with an `IntegrityError` instead of a clean HTTP 200 inline error. Same class of fix as `TimeBlockForm`'s pre-existing `user`-in-`__init__` ordering fix, just a different symptom. |

Everything else in Sprints 1–7 follows the PRD as written.

---

## Design system

Single source of truth: PRD §9. `base.html` is the only template with a full `<html>` skeleton;
every screen extends it. Color tokens, button/input/card class strings, and the grid table pattern
are copied verbatim from §9.2 — no ad hoc classes. See `static/css/input.css`'s header comment for
the token table mirrored in CSS form (PRD risk R5's mitigation).

Dark mode: class-based (`dark` on `<html>`), toggled by `static/js/theme.js` and applied
pre-paint by a synchronous inline script in `base.html`'s `<head>` to avoid a flash of the wrong
theme. Preference persists in `localStorage`, defaulting to `prefers-color-scheme` when unset.

**Primary-button partial** (`templates/partials/buttons/primary.html`, Sprint 4): the PRD §9.2
primary-button class string had reached 8 call sites across the navbar, landing page, both auth
templates, and the new settings form/dropdown — past the point NFR-05/R5 flag as drift. Extracted
into one partial that renders either an `<a href>` or a `<button type="submit">` depending on
whether an `href` context variable is supplied; the long class string now exists exactly once.
Same rationale as `form_field.html` in Sprint 2. Secondary/danger button strings are not yet
extracted (still below the 3+ repetition threshold) — see Sprint 4 section below.

**Secondary-button partial** (`templates/partials/buttons/secondary.html`, Sprint 7): the PRD §9.2
secondary-button class string reached 6 call sites across 5 templates (landing's "Log in" link,
the navbar's Logout button, both dashboard toolbar `<summary>` triggers, and the block/color
inline forms' Cancel buttons) — Sprint 6's own ARCHITECTURE.md notes had already pre-flagged the
extraction as due "once a fifth call site would otherwise appear," and `code-reviewer` caught that
this sprint's own new code (the Palette `<summary>`, the new color-form Cancel button) is exactly
what crossed it. Mirrors `primary.html`'s dual-mode `<a href>`/`<button>` shape, extended with a
third `as_summary` mode (for the toolbar `<details>` triggers, which are neither a link nor a
button) and optional named `hx_get`/`hx_target`/`hx_swap` context variables for the two HTMX
Cancel buttons — plain, auto-escaped Django template variables, not a raw attribute-string
escape hatch, so there is no `|safe`/`{% autoescape off %}` anywhere in the partial and no
injection surface even though two call sites now feed it dynamic (but always server-resolved,
never user-controlled) URLs.

**Colorless-block fallback (Sprint 5)**: a `TimeBlock` with no `color` (nullable, `SET_NULL` on
delete per FR-13) has no hex value to source an inline `style` from. PRD §9.1's token table has no
entry for this case, so `block_cell.html` falls back to a plain Tailwind fill: `bg-slate-500`
(light) / `dark:bg-slate-600` (dark) — not the `slate-400` a literal reading of the existing slate
family might suggest, chosen instead because it's the lightest slate step that still holds ≥ 4.5:1
contrast against the fixed `text-white` block label in light mode (`slate-400` measures ~2.56:1,
well under WCAG AA; `slate-500` measures ~4.76:1). `code-reviewer` verified this contrast math
independently and flagged it as a good one-off but a good candidate for promotion to a named §9.1
token once Sprint 6/7 need the same "neutral block" concept again (color picker's "no color"
option, palette panel) — not done yet, single call site today.

**Hover-control icon buttons (Sprint 6)**: `block_cell.html`'s edit/delete icon buttons use a
translucent `bg-black/20`/`hover:bg-black/40` scrim rather than PRD §9.2's documented Danger token
(`bg-rose-600`/`hover:bg-rose-700`) for delete. `code-reviewer` judged this a deliberate, acceptable
exception rather than drift: these buttons sit on top of an *arbitrary user-chosen hex background*
(or the colorless fallback above), and a fixed `rose-600` fill could itself clash with or fail
contrast against some user colors, whereas a translucent black scrim reliably darkens any
background it sits on. Not promoted to a token; single call site.

**Color-swatch keyboard focus (Sprint 6)**: the hand-rolled color-swatch radios in
`block_form.html` (`class="peer sr-only"`, needed because Django's `RadioSelect` subwidgets don't
expose each choice's `hex_code`) initially had a visible ring only for `peer-checked`, not
`peer-focus` — `code-reviewer` caught this as a genuine NFR-06 violation (a keyboard user tabbing
through swatches had no visual indication of focus). Fixed with
`peer-focus-visible:ring-2 peer-focus-visible:ring-indigo-500 peer-focus-visible:ring-offset-1` on
both swatch `<span>`s, mirroring the existing `peer-checked:ring-offset-1` sibling pattern already
in the same file (which is also the only other `ring-offset` usage anywhere in the project — no
new convention was invented). Each radio `<input>` also gained `aria-label` (the color's name, or
`'No color'`) rather than relying solely on the ancestor `<label>`'s `title` attribute.

**Two contrast fixes from the Sprint 7 dark/light audit**: `templates/partials/footer.html`'s
`text-slate-500` had no dark variant (~3.74:1 against `dark:bg-slate-900`, under WCAG AA) — fixed
with `dark:text-slate-400`, PRD §9.1's own secondary-text token, reused verbatim. `block_form.html`'s
"no color" swatch `×` glyph (already flagged as a known deferred item in the Sprint 6 section below)
went from unconditional `text-slate-400` to `text-slate-600 dark:text-slate-400`. Both are
one-line, no-new-token fixes to pre-existing drift, not Sprint 7 feature code.

**Second icon-button convention (Sprint 7)**: `color_row.html`'s Edit/Delete icon buttons reuse
`block_cell.html`'s pencil/trash SVG markup and sizing verbatim, but deliberately do *not* reuse
its translucent `bg-black/20` scrim — that treatment exists specifically because a block cell's
background is an arbitrary user-chosen hex color, where a translucent-black overlay is the only
reliably-visible choice against literally any background. A color row's background is the fixed
light/dark card token this panel already uses, where that same scrim computes to roughly 1.5:1
contrast — well under WCAG AA. A neutral/danger icon-button treatment (`text-slate-500
hover:bg-slate-100` / `hover:bg-rose-50`) is used there instead. This is now a second,
distinct icon-button convention in the codebase (scrim-on-arbitrary-background vs.
neutral-on-fixed-background); a third call site should reuse whichever of the two actually
matches its own background, not invent a third variant.

---

## HTMX and CSRF

`static/js/htmx.min.js` is vendored (release v2.0.9), never CDN-loaded. Every element under
`<body>` inherits `hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'`, set once in `base.html`, so
no individual future endpoint can forget the CSRF header. No HTMX-driven forms exist yet — that
wiring starts in Sprint 6 — this sprint only established the global contract. Sprint 2's auth forms
are standard (non-HTMX) POSTs and carry their own `{% csrf_token %}` tags instead.

---

## Native authentication (Sprint 2)

- **Routes** (`apps/accounts/urls.py`, `app_name = 'accounts'`, included under `'accounts/'`):
  `login/` → Django's built-in `LoginView` with `template_name='accounts/login.html'` and
  `authentication_form=LoginForm`; `signup/` → `SignUpView`; `logout/` → Django's built-in
  `LogoutView` (POST-only as of Django 6.0 — the navbar's logout control is a `<form method="post">`,
  not a link).
- **Forms** (`apps/accounts/forms.py`): `SignUpForm(UserCreationForm)` and
  `LoginForm(AuthenticationForm)` both apply a shared `INPUT_CLASSES` constant (the PRD §9.2 input
  string) to every field's widget in `__init__`, so neither form needs template-side class overrides.
- **`SignUpView(CreateView)`** (`apps/accounts/views.py`): on `form_valid`, saves the user then calls
  `django.contrib.auth.login()` with an explicit `backend='django.contrib.auth.backends.ModelBackend'`
  (the project's sole configured backend), redirecting to `core:dashboard`.
- **Templates**: `accounts/login.html` and `accounts/signup.html` both extend `base.html`, use the
  §9.3 centered-card auth layout (`min-h-screen grid place-items-center`), and render their fields
  through a new shared partial, `templates/partials/form_field.html` (label → widget → help text →
  field errors) — introduced because both forms loop over 2–3 fields each, which would otherwise
  repeat the same label/error markup 5 times across two templates (the exact pattern NFR-05 flags).
  It renders no ancestor-dependent markup, so it's safe to reuse for future HTMX-fragment forms too.
- **Verification**: all four PRD 2.4.1 smoke-test checks (signup→auto-login→dashboard,
  logout→landing, wrong-password error, anonymous `/dashboard/` redirect) pass via Django's test
  client. No real-browser verification yet — see the Playwright gap below.

---

## Landing page & dashboard shell (Sprint 3)

- **`core/landing.html`**: hero section (gradient headline reusing the navbar brand's exact
  gradient-text pattern, one-paragraph pitch, primary/secondary CTAs), a three-card features
  section (free-form blocks, drag-to-merge, color-coding — the shared §9.2 card pattern), and a
  decorative visual grid mock. The hero's CTAs are auth-aware: `{% if request.user.is_authenticated %}`
  swaps Sign up/Log in for a single "Go to dashboard" link, using `request.user` from Django's
  built-in auth context processor — no view changes needed, `LandingView` stays a plain
  `TemplateView`.
- **Grid mock is intentionally static**: a hand-written `<table>` with hardcoded `rowspan` values
  and flat Tailwind background utilities (`bg-indigo-500`, etc., not inline hex) standing in for
  real block colors, since no `BlockColor`/`TimeBlock` model exists yet (Sprint 4/5). No
  `{% for %}`, no computed spans — nothing here anticipates the Sprint 5 grid-builder service, per
  NFR-01 and risk R2. Marked `aria-hidden="true"` on the `<table>` root since it's purely
  illustrative and the adjacent heading/paragraph already carry the real content.
- **`core/dashboard.html`**: page header ("My Week") plus a toolbar with two disabled placeholder
  buttons (Settings, Palette — `disabled`, `cursor-not-allowed`, no `href`/URL, since those views
  don't exist until Sprint 4/7 and a real link would 404), and an empty-state card explaining the
  grid will populate once the planner domain lands. See the deviations table above for why the
  toolbar has two placeholders, not three.
- **Bug found and fixed while building this sprint**: `templates/base.html` and
  `templates/partials/navbar.html` each had a `{# ... #}` Django template comment spanning
  multiple lines. Per Django's docs, `{# #}` does **not** support newlines — when it spans one,
  the tokenizer fails to treat it as a comment and the literal text leaks straight into the
  rendered HTML. This had been present since Sprint 1/2 and affected every screen in the app, not
  just the two built this sprint. Fixed by converting both to `{% comment %}...{% endcomment %}`
  blocks (Django's documented mechanism for multi-line comments), confirmed via Context7 against
  the Django 6.0 docs. Re-swept every template afterward (`code-reviewer`, independently) — no
  other multi-line `{# #}` instances remain anywhere in `templates/` or `apps/*/templates/`.
- **Verification**: `qa-tester`'s 3.3.1 consistency pass diffed every class string across all six
  screens (landing anon/auth, dashboard anon/auth, login, signup) against PRD §9.2 verbatim — no
  drift found. A Django test-client sweep of the same six screens confirmed correct status codes,
  the signup→auto-login→dashboard redirect chain, and no template-syntax leaks (`{%`, `{{`, `{#`)
  in any rendered response. `code-reviewer` independently re-checked the same class strings and
  found no blocking issues. Real-browser visual/responsive/dark-mode verification remains
  deferred — see the Playwright gap below.

---

## Planner domain (Sprint 4)

- **Models** (`apps/planner/models.py`), all inheriting `TimestampedModel`:
  - `BlockColor`: `user` FK (CASCADE), `name`/`hex_code` with a `RegexValidator` for
    `#RRGGBB`, uniqueness per `(user, name)` via `UniqueConstraint` (see deviations table).
  - `PlannerSettings`: `user` OneToOne (CASCADE), `slot_interval` (30/60, default 60), `day_start`
    (default 06:00), `day_end` (default 00:00), `time_format` ('24h'/'12h', default '24h'). Created
    automatically for every new user by a `post_save` signal (below) — never created ad hoc by a
    view.
  - `TimeBlock`: `user` FK (CASCADE), `label`, `day_of_week` (`DAY_CHOICES` 0–6), `start_time`,
    `end_time`, `color` FK to `BlockColor` (nullable, `SET_NULL`).
  - **Midnight-crossing rule, centralized**: a module-level `minutes_since_midnight(value,
    treat_midnight_as_end_of_day=False)` helper in `models.py` is the single implementation of PRD
    R3's "treat `00:00` end as 24:00" rule. `TimeBlock.get_duration_minutes()`/`_overlaps()` and
    `PlannerSettingsForm.clean()` (`apps/planner/forms.py`) both call it rather than each
    reimplementing the exception — confirmed by `code-reviewer` as the correct anti-duplication
    shape R3 asks for.
  - **Known edge case, not a bug**: because the midnight exception only inspects `end_time`, a
    block with `start_time == end_time == 00:00` validates as a full 1440-minute (24h) block
    rather than a zero-duration error. This falls directly out of R3's rule rather than being
    explicitly designed for, but is a defensible reading (a block that "starts and ends at
    midnight" spans the whole day) — flagged by `qa-tester`, left as-is rather than special-cased,
    since block-creation UI (Sprint 6) will make this combination unlikely to occur by accident.
  - `TimeBlock.clean()` rejects `start >= end` (midnight exception aside) and same-user/same-day
    overlaps (touching blocks are legal); `save()` calls `full_clean()` so nothing reaches the
    database via `.save()` unvalidated — note this does not cover bulk `QuerySet.update()` calls,
    which bypass `save()`/`clean()` entirely (a standard Django limitation; no `.update()` calls
    exist anywhere in the codebase yet).
- **Signal** (`apps/planner/signals.py`, registered from `apps/planner/apps.py`'s `ready()` via a
  deferred import — Django's documented pattern, confirmed via Context7): `post_save` on
  `settings.AUTH_USER_MODEL` creates the new user's `PlannerSettings` row when `created=True`.
  Verified to fire exactly once per user, not on subsequent saves.
- **Admin** (`apps/planner/admin.py`): `TimeBlock` (list: label/user/day/start/end/color; filters:
  day/user), `BlockColor`, `PlannerSettings` all registered, per FR-15.
- **Settings UI**: `PlannerSettingsForm` (`apps/planner/forms.py`) mirrors the
  `INPUT_CLASSES`-in-`__init__` styling pattern already used by `apps/accounts/forms.py`, and
  validates `day_start < day_end` via the same midnight-aware helper as the model.
  `SettingsUpdateView(LoginRequiredMixin, UpdateView)` (`apps/planner/views.py`) takes no pk from
  the URL — `get_object()` is always `PlannerSettings.objects.get_or_create(user=self.request.user)`
  — so there is no path to view or edit another user's settings (NFR-07). Reachable two ways:
  standalone at `/planner/settings/` (`planner/settings_form.html`) and inline from the dashboard
  toolbar via a no-JS `<details>`/`<summary>` dropdown (see deviations table for why it's plain
  POST, not HTMX). `DashboardView` (`apps/core/views.py`) gained a small `get_context_data()` to
  build the bound form for that dropdown — the only Python change outside `apps/planner/`.
- **Verification**: `qa-tester` ran 40+ checks covering hex validation, uniqueness, duration/rowspan
  math (normal, midnight-crossing, both intervals), overlap/touching-block validation, self-exclusion
  on update, `SET_NULL` on color deletion, signal idempotency, admin registration, auth-gating and
  per-user isolation on the settings view/form (two independent user sessions confirmed mutually
  unaffected), and dashboard dropdown pre-fill — all passed. `code-reviewer` independently
  re-verified the `UniqueConstraint` deviation and the signal registration pattern against current
  Django 6.0 docs, confirmed data isolation was airtight, and flagged the primary-button
  duplication (now fixed, see design system section above) as the one blocking finding.
  `manage.py check` and `makemigrations --check --dry-run` both clean throughout.

---

## Grid rendering (Sprint 5)

- **`apps/planner/grid.py`**: `build_week_grid(planner_settings, blocks)` is the sole entry point,
  and the only place the grid's row/column/rowspan matrix is computed (PRD R2 — "compute the grid
  matrix server-side... templates only iterate, no logic-heavy DTL"). Pure Python: no database
  query, no Django import beyond the `TimeBlock`/`minutes_since_midnight`/`round_half_up` it reuses
  from `apps/planner/models.py`. Returns a `WeekGrid` dataclass: `day_headers` (7 names),
  `rows` (each a time-slot `label` plus 7 `GridCell`s), and two "don't lose this" lists,
  `out_of_range_blocks` and `unplaced_blocks` (see deviations table above for what each means).
  Every `GridCell` is tagged `'empty'`, `'block-start'` (carries the `TimeBlock` and a `rowspan`),
  or `'occupied'` (a row a block above already covers via `rowspan` — templates render nothing at
  all for these, not an empty `<td>`, or every column to its right desyncs for the rest of that
  row).
- **Midnight-crossing and interval-misaligned blocks**: both reuse Sprint 4's centralized
  `minutes_since_midnight()` helper (no reimplementation of the midnight rule) and a new shared
  `round_half_up()` helper (also now in `models.py`) for snapping a block's display position to the
  nearest slot boundary without ever mutating its stored `start_time`/`end_time` — the PRD's own
  5.1.3 wording ("snap display to nearest slot boundary; keep stored times authoritative").
- **Two bugs found by `code-reviewer` and fixed before sign-off, not shipped as first-written**:
  1. Two legally non-overlapping blocks (e.g. two short blocks that touch exactly) could snap onto
     the same visual row at a coarse interval; the first-written code silently dropped the second
     one into an inert list, meaning it never rendered anywhere. Fixed: on a row collision,
     `build_week_grid()` now searches forward for the next free row in that day's column,
     re-anchors the block there (shrinking its rowspan only as needed), and flags it `clamped`.
     Only a genuinely packed day (no free row left at all) falls back to the `unplaced_blocks` list.
  2. A day range that isn't an exact multiple of `slot_interval` (nothing prevents a user from
     setting e.g. `day_end = 23:45` at a 60-minute interval) silently truncated the trailing
     partial slot via floor division, and blocks cut off by that truncation incorrectly reported
     `clamped=False`. Fixed: slot count now rounds up (`math.ceil`) so the full configured range is
     always representable, and the `clamped` flag now also accounts for this second clamping
     mechanism, not just the day-range boundary one.
  Both were caught because `code-reviewer` executed the code against constructed scenarios rather
  than reading it, per this project's established review practice — see the qa-tester/code-reviewer
  verification note below.
- **`TimeBlock.get_rowspan(interval)` corrected** (Sprint 4 method, zero callers in the codebase):
  changed from floor division to the same `round_half_up()` `grid.py` uses, so a 90-minute block at
  a 60-minute interval now returns `2` from both, not `1` from one and `2` from the other. See
  deviations table.
- **Views**: `GridView(LoginRequiredMixin, TemplateView)` at `/planner/` (`planner:grid`), and
  `DashboardView` (`apps/core/views.py`) both call the identical `build_week_grid()` with a
  `request.user`-scoped `PlannerSettings`/`TimeBlock` queryset (`.select_related('color')`, NFR-03)
  — no pk taken from any URL (NFR-07), and no duplicated grid-computation logic between the
  standalone page and the embedded dashboard view, mirroring Sprint 4's settings dual-access
  pattern.
- **Templates**: the actual `<table>` markup exists in exactly one place,
  `planner/partials/grid_table.html` (`table-fixed w-full border-collapse`, sticky day-header row
  and sticky time column, per PRD §9.2's "Grid" bullet verbatim), included by both
  `planner/grid.html` (standalone) and `core/dashboard.html` (embedded, replacing Sprint 3's
  placeholder empty-state card — an all-empty grid's inert, hoverable cells already communicate
  "nothing here yet" on their own). `planner/partials/block_cell.html` and `empty_cell.html` render
  the two "real" cell kinds; `empty_cell.html` already carries `data-day`/`data-start`/`data-end`
  attributes so Sprint 6 can wire `hx-get` straight off this markup without touching the template
  again. No HTMX, no JS anywhere in this sprint's templates — pure server-rendered HTML, per scope.
  The table is wrapped in its own bounded, scrollable container (`overflow-x-auto overflow-y-auto
  max-h-[75vh]`) so its sticky header/column stick to that container's edges rather than
  competing with the navbar's own `sticky top-0` once the page scrolls.
- **Verification**: `qa-tester` independently recomputed grid math (aligned blocks, midnight
  crossing, both interval settings, interval-misaligned snapping, day-range narrowing/clamping) via
  direct calls to `build_week_grid()`, parsed real rendered HTML to confirm every table row's
  column count is always consistent with active `rowspan`s, verified per-user isolation with a
  second test user, confirmed the Sprint 4 settings dropdown still works end-to-end (posted a real
  interval change and confirmed the re-rendered grid reflected it), and confirmed auth gating on
  both `/planner/` and `/dashboard/`. `code-reviewer` then found and this session fixed the two
  bugs described above, plus corrected `get_rowspan()`; all fixes were independently re-verified
  (not just trusted) by re-reading the corrected `grid.py`/`models.py` and re-running the exact
  regression scenarios, plus confirming the previously-seeded `alice` data rendered unchanged.
  `manage.py check` and `makemigrations --check --dry-run` stayed clean throughout (no model field
  changes this sprint).

---

## Block interactivity (Sprint 6)

- **Swap strategy**: every block-mutating view — `BlockCreateView`, `BlockUpdateView`,
  `BlockDeleteView`, `BlockResizeView`, and the repeat-across-days path folded into create — shares
  one helper, `_render_grid_response()` (`apps/planner/views.py`), which re-runs `build_week_grid()`
  and re-renders the *entire* `planner/partials/grid_table.html` fragment on every success (and on
  a rejected resize). See the deviations table above for why whole-table replacement was chosen
  over a per-cell/per-column patch. The **one exception**: opening or cancelling an inline form
  (GET) never touches the matrix at all, so `BlockCreateView`/`BlockUpdateView`'s GET handling and
  the two small cancel views (`CellCancelView`, `BlockCancelView`) stay scoped to a single `<td>`
  swap.
- **The success/failure retarget problem**: the same `<form>` (in the shared
  `planner/partials/block_form.html`) declares `hx-target="#grid-table" hx-swap="outerHTML"` for
  its success path, but an invalid submission must swap back into the form's own small
  `<td id="block-form">`, not dump a bare form fragment into the full grid target. Since one
  element can't declare two different targets for the same trigger, `BlockCreateView.form_invalid()`
  /`BlockUpdateView.form_invalid()` set `HX-Retarget: #block-form` + `HX-Reswap: outerHTML` response
  headers, which override the swap target/style for that one response only (confirmed against the
  htmx docs via Context7). `#block-form` is a **fixed** id, not derived from pk/day/time, precisely
  because a data-derived selector could desync if the user edits the day/time fields before an
  invalid submit. Known, accepted edge case (see below).
- **Toast/notice channel**: a single persistent `<div id="grid-toast" hx-swap-oob="true">` lives at
  the top of `grid_table.html` (a sibling before the `#grid-table` wrapper, both top-level in the
  partial's own output — confirmed via Context7 that OOB matching is by id against the current DOM
  regardless of nesting depth, but top-level placement is the unambiguous case). Every mutating
  view always passes `toast_message`/`toast_level` context vars, even as empty strings, so the div
  re-renders (and clears) on every single mutation — a stale error from one action can never linger
  after an unrelated, clean action. Used for resize/extend/shrink rejections (`toast_level='error'`)
  and repeat-across-days skip notices (`toast_level='info'`).
- **Ownership and validation**: `TimeBlockForm` (`apps/planner/forms.py`) requires a `user` kwarg,
  set on `self.instance` inside `__init__` rather than in any view's `form_valid()` — a real,
  non-obvious ordering constraint: `ModelForm._post_clean()` calls `instance.full_clean()` during
  `is_valid()`, which runs *before* `form_valid()`, so `TimeBlock.clean()`'s overlap check (which
  filters by `self.user`) would silently validate against `user=None` if set any later. Every
  pk-scoped view (`BlockUpdateView`, `BlockDeleteView`, `BlockResizeView`, `BlockCancelView`) filters
  by `request.user` *before* the pk lookup, so a cross-user pk is a 404, never a 403 or a silent
  leak — independently re-verified by both `qa-tester` and `code-reviewer`.
- **Drag-to-resize** (`static/js/grid-drag.js`): Pointer Events (not mouse events, for tablet
  support per PRD §4), delegated from `document` rather than bound to individual handle elements,
  since every HTMX mutation replaces block cells — and their handles — with brand-new DOM nodes
  that would silently carry no listeners if bound directly. Purely a visual preview until
  `pointerup`, when exactly one `htmx.ajax()` call fires to `BlockResizeView`; the server
  clamps/re-validates regardless of what the client computed (NFR-08).
- **Keyboard/click resize fallback** (PRD 6.3.4): folded into `BlockUpdateView` itself as a
  POST `action=extend`/`action=shrink` branch (`_handle_resize_action()`), rather than a separate
  view, since it's a fallback on the same edit action, not a distinct feature.
- **Repeat-across-days** (PRD 6.4.1/6.4.2): `TimeBlockForm.repeat_days` (a non-model
  `CheckboxSelectMultiple`) is only rendered in create mode (`block_form.html`) — repeating an
  *edit* of an existing instance isn't a meaningful action. `BlockCreateView.form_valid()` saves the
  primary block, then attempts a per-day copy for each selected day (skipping the primary's own
  day), catching `ValidationError` per copy so one overlapping day doesn't abort the rest; skipped
  days are named in the toast.
- **Three bugs found and fixed before sign-off, not shipped as first-written**:
  1. `static/js/grid-drag.js`'s `htmx.ajax()` call for the drag-release POST initially omitted
     `source` from its context object. Confirmed via Context7 (reading the actual htmx source) that
     without a `source` element, htmx never walks up the DOM to collect ancestor `hx-headers` — so
     `base.html`'s global CSRF-token header would never have been attached, and the request would
     have failed with a 403 in a real browser. Fixed by passing `source: drag.cell` (the dragged
     block's own `<td>`, a DOM descendant of `<body hx-headers=...>`). Caught by this session's own
     review before `qa-tester`/`code-reviewer` ran, then independently confirmed correct by both.
  2. `code-reviewer` found `BlockUpdateView._handle_resize_action()` (the '+/-' keyboard fallback)
     clamped only to the absolute `[00:00, 24:00)` calendar day, never to the user's configured
     `PlannerSettings.day_start`/`day_end` — unlike its sibling `BlockResizeView` (the drag
     endpoint), which correctly clamped to the visible day range. Reproduced directly: with
     `day_end=20:00`, extending a `19:00-20:00` block via the `+` button silently saved
     `19:00-21:00` with no rejection and no toast — a stored/displayed-state mismatch invisible
     until `day_end` was later widened. Fixed by extracting a shared `_day_range_minutes()` helper
     (`apps/planner/views.py`) used by both resize code paths, so they can no longer silently
     diverge; the keyboard fallback now rejects (error toast, block unchanged) rather than
     partially clamping, since a fixed single-slot nudge has no sensible "partial clamp" to fall
     back to the way a free-position drag does.
  3. `code-reviewer` also found `views.py`'s `_time_from_minutes()` and `grid.py`'s
     `_minutes_to_time()` were byte-for-byte identical private functions in two different modules —
     directly contradicting `models.py`'s own `minutes_since_midnight()` docstring, which claims to
     be "the single, centralized implementation... so the rule is never re-implemented elsewhere"
     for the same minutes-of-day math (just the reverse direction). Fixed by moving one public
     `time_from_minutes()` into `apps/planner/models.py` alongside `minutes_since_midnight()` and
     `round_half_up()`; both call sites now import it, and both private duplicates were deleted
     outright (not left as thin wrappers).
- **Reviewed and deliberately deferred, not shipped as fixes this sprint**:
  - Any grid-wide mutation (e.g. resizing block A) silently discards any *other* still-open,
    unsubmitted create/edit form elsewhere in the grid (e.g. one opened on block B), since the
    whole `#grid-table` gets replaced. `code-reviewer` confirmed this is real but judged it an
    acceptable consequence of the documented whole-table-swap design — no data is lost (nothing in
    the discarded form was ever submitted), and building a client-side "unsaved form" guard would
    itself grow `grid-drag.js`'s state footprint against R1's explicit warning. A future
    nice-to-have, not a defect.
  - The `#block-form` fixed-id retarget mechanism assumes at most one inline form is open at a
    time. Nothing currently prevents a user from opening a second form while a first sits
    unsubmitted (confirmed reachable by `qa-tester`); if that happens, an invalid submission from
    either form retargets to the first `#block-form` match in document order. Documented directly
    in `block_form.html`'s own comment as a known, accepted rare edge case.
  - Minor design-token/cleanup items raised by `code-reviewer` — the Danger-token deviation on the
    hover-control delete button (see design system section above, judged intentional, not
    drift), dead `focus:ring-2` CSS on `.block-label` (that div isn't natively focusable, so the
    rule can never match — harmless, just unused), the "no color" swatch's `×` glyph using
    `text-slate-400` unconditionally instead of a light/dark pairing, and the exact §9.2
    Secondary-button class string now being hand-rolled across four templates (a
    `partials/buttons/secondary.html` extraction, mirroring the existing `primary.html`, is the
    recommended follow-up once a fifth call site would otherwise appear).
- **`static/js/contrast.js` implemented a sprint early** (PRD 7.2.2 is nominally Sprint 7 scope):
  `htmx-interaction` built the JS luminance-based text-contrast rule this sprint as a natural
  extension of the color-swatch/block-cell work, retiring the Sprint 5 `text-white`-fixed
  placeholder. `code-reviewer` reviewed this explicitly and did not consider it NFR-01 scope creep
  — small, single-purpose, no new dependency, replaces documented placeholder rather than adding
  net-new complexity. Marked `[x]` in the PRD ahead of its nominal sprint, with this note, so it
  isn't miscounted or redone in Sprint 7.
- **Verification**: this session ran a full create/edit/delete/resize/extend-shrink/cancel/
  repeat-across-days/ownership-isolation smoke test via Django's test client before handing off to
  `qa-tester`, which then ran a deeper adversarial pass (row-collision and out-of-range scenarios
  produced through the real HTTP endpoints rather than ORM seeding, toast-staleness-clearing
  across sequential mutations, `repeat_days` edge cases including a same-day self-skip, and a
  from-scratch CSRF-enforcement re-test of the drag-resize path). `code-reviewer` then ran an
  independent pass — reading the module docstrings' own design rationale before judging it, not
  just the resulting code — and found the three bugs above, all fixed and independently
  re-verified afterward (both the originally-reported scenario and, for the resize-clamp fix, a
  regression check that `BlockResizeView`'s already-correct behavior was unchanged). `manage.py
  check` and `makemigrations --check --dry-run` stayed clean throughout (no model field changes
  this sprint).

---

## Color palette (Sprint 7)

- **`BlockColorForm`** (`apps/planner/forms.py`): a `ModelForm` over `name`/`hex_code`, styled via
  the same `INPUT_CLASSES`-in-`__init__` pattern every other form in this project uses. Requires a
  `user` kwarg, set on `self.instance` in `__init__` — the same ordering fix `TimeBlockForm`
  already established (Sprint 6), needed here for the identical reason: `ModelForm._post_clean()`
  runs `instance.full_clean()` during `is_valid()`, before any view's `form_valid()`. A second,
  less obvious gap surfaced this sprint: setting `self.instance.user` alone is *not* sufficient for
  the model's `UniqueConstraint(fields=['user', 'name'])` to actually be enforced, because `user`
  isn't one of this form's `Meta.fields` — Django's `_get_validation_exclusions()` adds any
  form-excluded field to the `exclude` list passed into both `full_clean()` and
  `validate_constraints()`, and `UniqueConstraint.validate()` skips the whole check the moment any
  of its fields is in that `exclude` set. `code-reviewer` traced this through the installed Django
  6.0.7 source directly (not just the docs) to confirm the reasoning, not just the symptom. Fixed
  with a hand-rolled `clean()` uniqueness check (same shape `TimeBlock.clean()`'s own user-scoped
  overlap check already uses, for the same class of reason — a check spanning a field excluded
  from the form). Without this, a duplicate color name wouldn't fail validation at all; it would
  pass `is_valid()` and then raise an unhandled `IntegrityError` from the database at `.save()`
  time, a 500 instead of a clean inline error.
- **Views** (`apps/planner/views.py`, bottom): `ColorCreateView`/`ColorUpdateView` mirror
  `BlockCreateView`/`BlockUpdateView` exactly — `get_form_kwargs()` injects `user`,
  `get_queryset()` (update only) scopes by `request.user` before the pk lookup (404, not 403,
  NFR-07), `form_invalid()` sets `HX-Retarget`/`HX-Reswap` to redirect a validation-error response
  back into the form's own small slot rather than the whole panel. `ColorDeleteView` mirrors
  `BlockDeleteView` (POST-only, no confirmation page — that's the client-side `hx-confirm`).
  `PaletteView` and `ColorCancelView` are the palette-panel analogs of Sprint 6's
  `CellCancelView`/`BlockCancelView` — GET-only fragment endpoints restoring, respectively, the
  "+ Add color" trigger and one color's display row.
- **The palette-panel swap + grid-refresh problem**: a color rename/recolor/delete changes how
  *other* parts of the page render (any block using that color), not just the palette panel
  itself — unlike Sprint 6's block mutations, which only ever need to affect `#grid-table`. Rather
  than inventing a second toast-like channel, `_render_palette_response()` reuses the exact
  mechanism `#grid-toast` already established: render `palette_panel.html` (the primary content,
  matched by whichever element's `hx-target="#palette-panel"` triggered the request) immediately
  followed by a second render of `grid_table.html`, concatenated into one `HttpResponse` — but this
  time `grid_table.html` is *not* the primary target, so it needs the `hx-swap-oob="true"`
  attribute to be picked up as an out-of-band swap instead. Rather than a second, OOB-only wrapper
  template (which would reintroduce the nested-vs-top-level OOB-matching ambiguity `#grid-toast`'s
  own docstring already goes out of its way to avoid), `grid_table.html` gained one new context
  flag, `grid_oob`: `{% if grid_oob %}hx-swap-oob="true"{% endif %}` on its existing `#grid-table`
  wrapper. Every Sprint 6 block-mutating view never passes this flag, so it stays absent/falsy
  there and that whole code path is byte-for-byte unchanged — `qa-tester` and `code-reviewer` both
  independently confirmed this empirically (inspecting the actual `#grid-table` tag in a normal
  block-mutation response), not just by reading the `{% if %}` and assuming.
- **Hand-rolled hex field + native color picker** (`color_form_row.html`): same reasoning as
  Sprint 6's hand-rolled color-swatch `RadioSelect` — a native `<input type="color">` isn't a
  Django form field at all, and pairing it with the real `hex_code` text input needs a shared
  `data-hex-sync="<id>"` attribute that generic field rendering (`form_field.html`) has no hook to
  inject. `static/js/color-sync.js` pairs any two same-valued `data-hex-sync` elements
  bidirectionally, document-delegated (not per-element listeners) for the same reason
  `grid-drag.js` already documents: every save swaps `#palette-panel` wholesale, which would
  silently orphan a directly-bound listener the moment a user saved once. The native color input
  always yields a valid lowercase hex, matching the model's case-insensitive
  `HEX_COLOR_VALIDATOR`; typed hex text only pushes into the color input once it's a *complete*
  valid match, so an in-progress keystroke never fights the native control.
- **Responsive/dark-mode fixes bundled into this sprint's audit** (PRD 7.2.1/7.2.3, executed by
  `django-frontend`): the grid table's `table-fixed w-full` inside `overflow-x-auto` could never
  actually overflow, so narrow viewports silently squeezed columns instead of scrolling — fixed
  with `min-w-[760px]`. The two dashboard toolbar `<details>` dropdowns (Settings, Palette) each
  declared their own `relative` context, so Settings' panel would anchor to Settings' own right
  edge and overflow off-screen now that Palette sits to its right — fixed by hoisting `relative` to
  their shared row wrapper, plus a shared `name="dashboard-toolbar"` attribute opting both
  `<details>` into the HTML living standard's native exclusive-accordion behavior (no JS). Neither
  fix is browser-confirmed — see the Playwright gap below, now materially relevant to two more
  concrete, previously-nonexistent UI elements.
- **Real bug found via a real browser screenshot, post-Sprint-9, and fixed**: the user opened the
  Settings dropdown and reported (screenshot) the grid's sticky day-header row ("Sat"/"Sun")
  visibly painting on top of the "Grid settings" panel instead of behind it. Root cause: both the
  Settings/Palette dropdown panels (`apps/core/templates/core/dashboard.html`) and the grid's
  sticky header `<th>` cells (`apps/planner/templates/planner/partials/grid_table.html`) used the
  identical `z-20`; neither the `<details>` nor the shared toolbar row wrapper establishes its own
  stacking context (`relative` alone, no `z-index`), so the two `z-20` layers competed directly in
  the same stacking context and — being later in the DOM — the grid table won every tie. Fixed by
  bumping both dropdown panels to `z-30`, matching this codebase's existing higher layer already
  used by `block_form.html`'s identical floating-popover pattern (the project's de facto z-index
  scale, confirmed by grepping every `z-\d+` usage in the codebase: `10` grid sticky column <
  `20` grid sticky header < `30` floating panels/popovers < `40` navbar). This is the first item
  in the Playwright gap's running list below to go from "hand-reasoned, unconfirmed" to "confirmed
  broken, then fixed" via an actual rendered screenshot rather than continued speculation.
- **`ruff` added as a dev-only lint tool** (PRD 7.3.1): `uv add --dev ruff`, keeping it out of the
  runtime `dependencies` list entirely (the KPI's "≤5 entries" budget is about runtime deps, and
  stays untouched). `[tool.ruff]`/`[tool.ruff.lint]` config in `pyproject.toml` (E/F/W/I,
  migrations excluded from line-length since they're generated, not hand-written). `ruff check`
  found and fixed 6 genuinely dead `F401` imports, all in Django's own `startapp` boilerplate stub
  files (`admin.py`/`models.py`/`tests.py` across `accounts`/`core`/`planner`) — real dead code per
  PRD 7.3.2, zero risk to remove. Deliberately did **not** run `ruff format` across the repo: its
  own preview diff would have reverted the Sprint 6 PEP 701 single-quote-nesting fix
  (`f'Skipped {', '.join(...)}...'`) back to mixed quotes, and would have reflowed large amounts of
  this codebase's deliberate, hand-crafted multi-line docstrings — a bulk restyle was never this
  task's intent, and NFR-01 argues against a large, low-value diff. `ruff check .` is the enforced
  command; `[tool.ruff.format] quote-style = 'single'` stays configured for future new code.
- **Verification**: `qa-tester` ran a dedicated adversarial pass (uniqueness enforcement including
  no-op-rename and rename-to-collide edge cases, hex validation against malformed input, ownership
  isolation across all 5 new endpoints including method-confusion 404/405 checks, the SET_NULL +
  immediate-OOB-grid-refresh requirement end to end, `HX-Retarget` precision for both create- and
  edit-mode invalid submissions, cancel-flow data freshness against a simulated concurrent update,
  toast-channel isolation from an unrelated prior block-resize rejection, the `grid_oob`-defaults-
  falsy regression check on every Sprint 6 view, and `repeat_days` correctly propagating a real
  palette color for the first time) plus PRD 7.3.3's full manual regression checklist — zero
  defects found. `code-reviewer` then independently traced the two "verify, don't trust" claims
  above through Django's own source and live requests, confirmed the `grid_oob` mechanism and the
  palette OOB-response's raw string concatenation were both safe and proportionate (not a param
  pile, not fragile HTML), confirmed the `name="dashboard-toolbar"` exclusive-accordion trick is
  real, standards-track HTML behavior, executed PRD 7.3.2's dead-code/English sweep explicitly, and
  found one blocking issue (the Secondary-button partial threshold, see the design-system section
  above) — fixed immediately and independently re-verified (byte-for-byte behavior parity via test
  client against all 6 migrated call sites, including the two HTMX Cancel buttons' resolved URLs).
  `manage.py check`/`makemigrations --check --dry-run` stayed clean throughout (no model changes
  this sprint).

---

## Automated tests (Sprint 8)

- **Structure**: `apps/planner/tests/` is a package (`test_models.py`, `test_views.py`,
  `test_grid.py`), not a flat `tests.py` — the old stub file was deleted in favor of it. Judged
  proportionate, not NFR-01 over-engineering: it's a straight file split with zero new
  abstractions, mapping 1:1 onto PRD §13's own 8.1/8.2/8.3 subdivision (model validation via
  `TestCase`, HTTP view contracts via `TestCase`, pure-function grid math via `SimpleTestCase`),
  each landing at a reasonable 170-570 lines rather than one ~1050-line file mixing three
  genuinely distinct concerns. `apps/core/tests.py` and `apps/accounts/tests.py` stay flat
  (4 and 5 tests respectively) — correctly, since neither app's test surface is large enough to
  need splitting.
- **82 tests total, all passing**: 26 model tests (PRD 8.1), 39 view tests (PRD 8.2), 8 grid
  builder tests (PRD 8.3), plus core's 4 and accounts' 5. `uv run python manage.py test`,
  `ruff check apps/`, `manage.py check`, and `makemigrations --check --dry-run` are all clean.
- **Model tests** (`test_models.py`) cover `TimeBlock.get_duration_minutes()`/`get_rowspan()`
  (including the round-half-up 90-minute case and the documented `00:00`-to-`00:00` full-day
  edge case from the Sprint 4 section above — asserted as valid, not an error), `clean()`'s
  start/end rule, same-user/same-day overlap rejection with touching-blocks-allowed and
  self-exclusion-on-update, `BlockColor`'s hex validator and `(user, name)` `UniqueConstraint`,
  `SET_NULL` on color deletion, and the `PlannerSettings` auto-creation signal (defaults, and
  no duplicate row on a second `save()`).
- **View tests** (`test_views.py`) cover: auth protection swept across all 14 planner/dashboard
  routes via one parametrized `subTest`; ownership isolation on every pk-taking block/color
  endpoint (9 tests, each asserting both the 404 *and* that the underlying row is untouched, not
  just the status code — matching this codebase's own "404, never 403" convention documented in
  the Sprint 6 section above); the full block/color CRUD + resize success/failure contract,
  including the `HX-Retarget`/`HX-Reswap` fixed-id behavior, the keyboard `+/-` resize fallback,
  and day-range clamping; the `repeat_days` feature; and settings updates actually changing the
  next grid fetch's row count/label format, not just redirecting. One regression pair is worth
  calling out specifically: `test_block_mutation_response_grid_table_is_not_out_of_band` and
  `test_create_success_response_carries_palette_and_oob_grid_fragment` together lock in the
  Sprint 7 `grid_oob` flag's documented default-falsy behavior via a regex
  (`_grid_table_tag()`) that `code-reviewer` independently confirmed matches only the
  `#grid-table` div's own opening tag, not the neighboring `#grid-toast` div (which
  unconditionally carries its own `hx-swap-oob`) — verified live against a real response, not
  just trusted from the helper's own comment.
- **Grid builder tests** (`test_grid.py`) construct unsaved `PlannerSettings`/`TimeBlock`
  instances directly and use `SimpleTestCase` (no database), since `build_week_grid()` is pure
  Python (PRD R2). Cover an empty grid, a single block's rowspan at both 30- and 60-minute
  intervals, two sequential blocks, the row-collision re-anchoring behavior documented in the
  Grid Rendering section above (verified by hand-tracing the exact 09:00-09:20/09:20-09:40
  scenario against the real collision branch in `grid.py`), an out-of-range block, and 12h vs.
  24h time labels.
- **Test hygiene, verified empirically, not just by inspection**: the full suite was run under
  normal order, `--shuffle`, `--reverse`, and `--parallel 4` — identical pass/fail result every
  time, confirming PRD 8.4.1's "runs clean from a fresh clone" requirement isn't accidentally
  order- or state-dependent. A "Running tests" section was added to `README.md` for the
  documentation half of the same PRD item.
- **One real, small bug this sprint's own review pass caught and fixed**: `apps/accounts/tests.py`
  had one double-quoted string wrapping a Unicode curly apostrophe (matching Django's own
  `SetPasswordForm` message text verbatim) with no escaping need to justify the double quotes — a
  genuine NFR-02 single-quote violation, not a false positive. `code-reviewer` caught it during
  its Sprint 8 pass; fixed directly, re-verified via a full test/ruff re-run.
- **Verification**: `qa-tester` wrote the entire suite (single foreground dispatch, since writing
  tests *is* this sprint's deliverable rather than a separate verification step), self-verified
  via its own `manage.py test`/`ruff check` run before reporting done. This session then
  independently re-read every test file in full and re-ran the same checks directly.
  `code-reviewer` then ran its own independent pass — tracing the trickier assertions (round-half-up,
  midnight edge cases, row-collision re-anchoring, the `grid_oob` regex claim) against the actual
  model/view/grid source rather than trusting the tests' own docstrings, and additionally
  re-running the suite under `--shuffle`/`--reverse`/`--parallel` itself rather than accepting the
  "no ordering dependency" claim on faith — and found the two items above (the quote-style bug and
  the missing README section), both fixed and re-verified.

---

## Docker & release readiness (Sprint 9)

- **`Dockerfile`**: `python:3.12-slim`. `uv` itself is installed by copying its prebuilt binary
  from `ghcr.io/astral-sh/uv` (the current Context7-confirmed approach), pinned to the version
  used to develop this project. Dependencies install in two layers for cache efficiency:
  `uv sync --locked --no-dev --group docker --no-install-project` (deps only, before `COPY . .`)
  then a second `uv sync ... ` after the app code is copied in. `--no-dev` excludes the `dev` group
  (`ruff`) and `--group docker` adds a **new** `[dependency-groups]` entry
  (`gunicorn`, `whitenoise`) — the same "tooling that isn't needed by the shipped app itself"
  pattern Sprint 7 established for `ruff`, so the main `dependencies` list in `pyproject.toml`
  stays at exactly one entry (`django`) even after this sprint. `collectstatic --noinput
  --ignore=input.css` runs at **build time** (static files are baked into the image); the
  `--ignore` flag is load-bearing, not defensive over-caution — `code-reviewer` reproduced the
  exact `whitenoise.storage.MissingFileError` it prevents by running `collectstatic` without it
  (the raw, uncompiled Tailwind v4 source file contains a bare `@import 'tailwindcss'` that
  WhiteNoise's manifest post-processor otherwise tries and fails to resolve as a relative file
  path). `migrate --noinput` runs at container **start**, not build time, via a one-line inline
  `CMD` (`sh -c 'python manage.py migrate --noinput && gunicorn ...'`) — it depends on the
  runtime-mounted volume, which may not exist on a first run; a separate `entrypoint.sh` file for
  one `&&` would be unnecessary ceremony (NFR-01).
- **Static files, no separate web server**: WhiteNoise serves the collected static files directly
  from the same gunicorn process — no nginx/reverse proxy container (NFR-01). Wiring is
  **conditional**, not unconditional: `config/settings.py` only inserts
  `whitenoise.middleware.WhiteNoiseMiddleware` into `MIDDLEWARE` (right after `SecurityMiddleware`,
  Context7-confirmed placement) and sets the `STORAGES['staticfiles']['BACKEND']` to
  `whitenoise.storage.CompressedManifestStaticFilesStorage` when a `DJANGO_USE_WHITENOISE` env var
  is set — which only the Dockerfile sets. Since `whitenoise` lives only in the `docker`
  dependency-group, a plain local `uv sync` never installs it at all; an unconditional `MIDDLEWARE`
  entry would break local `manage.py check`/`runserver` the moment Django tried to import an
  uninstalled module. `code-reviewer` independently confirmed (via Context7) that `uv sync` only
  pulls in the `dev` group by default, so this conditional split is necessary, not paranoia.
- **SQLite persistence**: the significant deviation this sprint. PRD 9.1.2 says "volume for SQLite
  file," which reads naturally as mounting a named volume directly onto `db.sqlite3`. That was
  tried first and **fails outright** on this environment's Docker daemon with
  `"<path> is not directory"` on first container creation — reproduced independently by the
  implementing agent, this session, and `code-reviewer` (three times, including with a trivial
  one-file test image), so it's a genuine Docker/overlay2 limitation with named volumes mounted
  onto a single file, not a Dockerfile mistake. Fixed by mounting the volume onto a **directory**
  instead (`sqlite_data:/app/data`) and adding a `SQLITE_DB_PATH` environment variable that
  `config/settings.py`'s `DATABASES['default']['NAME']` reads, falling back to the original
  `BASE_DIR / 'db.sqlite3'` when unset — local development is completely unaffected; only the
  Dockerfile sets `SQLITE_DB_PATH=/app/data/db.sqlite3`. Persistence (a user survives
  `docker compose down` → `up`, without `-v`) was verified end-to-end, independently, three
  separate times (implementing agent, this session, `code-reviewer`).
- **`docker-compose.yml`**: one `web` service (`build: .`), host port **8010** (8000 was already
  occupied locally by a dev `runserver` — verified free before choosing it; change it in this file
  if 8000 is free on your machine), `env_file: - path: .env / required: false` (the Compose
  long-form syntax that lets `docker compose up` still work on a fresh clone with no `.env` yet,
  falling back to `settings.py`'s dev-safe defaults — confirmed current, non-deprecated syntax via
  Context7), and the `sqlite_data` named volume described above. No other services — no nginx, no
  Celery, no Redis; NFR-01 applies to the deployment topology just as much as the application code.
- **Verification chain** (PRD 9.1.3 and 9.3.1): `django-backend` built the whole stack and verified
  it itself (build → up → migrate confirmation → static-file curl checks with correct
  `Content-Type` → SQLite persistence test → down). This session then independently repeated the
  exact same cycle from scratch and got identical results. `qa-tester` then ran the **full 82-test
  suite inside the running container** (`docker compose exec web python manage.py test` — 82/82
  pass, matching the local result exactly) plus a full manual HTTP-level regression checklist
  against the live container: signup → auto-login → dashboard (with the `PlannerSettings` signal
  firing), login/logout, a complete block CRUD cycle (create → edit → resize → delete) and a
  complete color CRUD cycle via real HTTP requests (not ORM shortcuts), overlap rejection with
  DB-state confirmation that no phantom row was created, touching-blocks-still-allowed, `SET_NULL`
  on color deletion, the `grid_oob` out-of-band contract, and static-file serving scrutinized
  specifically (real response headers: `Content-Type`, `Cache-Control`, `ETag`). `code-reviewer`
  then ran an independent third full build/up/test/down cycle of its own, cross-checked
  `CONTRIBUTING.md`'s claims against the actual `apps/planner/models.py`/`apps/planner/apps.py`
  code, and found zero blocking issues.
- **One real gap found and fixed**: `qa-tester` noticed the README's Docker quickstart didn't warn
  that the no-`.env` default (`DEBUG=True`, empty `ALLOWED_HOSTS`) is dev-only — verified concretely
  (a bad URL served Django's verbose debug 404/traceback page, `SECRET_KEY` correctly redacted by
  Django's own exception filter but the rest of the traceback fully exposed). A warning was added
  to the README. `code-reviewer`'s independent pass then caught that the warning's own wording
  ("...before building") was itself wrong — `DEBUG`/`ALLOWED_HOSTS` are read from the environment
  at container **start**, not baked in at `docker compose build` time, confirmed by writing a new
  `.env` against an already-built image and observing the behavior change on `up` alone with no
  rebuild — and that the same paragraph didn't mention replacing the public repo's insecure
  fallback `SECRET_KEY`. Both fixed directly in the same paragraph.
- **Deliberately deferred, not fixed this sprint**: `code-reviewer` suggested the container run as
  a non-root user (currently `root`, no `USER` directive) as a hardening step appropriate for a
  public reference template. Not a PRD requirement, and not attempted this sprint — the named
  volume's default root ownership would need matching UID/GID handling to avoid a SQLite
  write-permission regression, which is real additional scope beyond a one-line fix. Worth
  revisiting alongside a future `v1.0.0` hardening pass, not before.
- **`README.md`/`CONTRIBUTING.md`/`LICENSE`**: README gained a features list, tech-stack table,
  condensed project-structure tree, the Docker quickstart above, and a design-tokens summary table
  (all cross-linking to the PRD/this document for full detail rather than duplicating it wholesale
  — the existing Tailwind-pipeline and "Running tests" sections were left as-is). `CONTRIBUTING.md`
  is new: how to add a Django app, how to change the *design-system* tokens (Tailwind classes in
  the already-extracted shared partials) versus the unrelated *per-user* `BlockColor` runtime
  palette feature, how to change `PlannerSettings`' per-field defaults for new users, and how to
  swap SQLite for another engine (no code depends on SQLite specifically; every query goes through
  the ORM). The pre-existing `assets/preview.svg` (a hand-drawn concept sketch, not app output) is
  now embedded in the README, explicitly labeled as a concept sketch rather than a live screenshot,
  since no browser-screenshot tooling exists in this environment (same root cause as the
  Playwright gap below).
- **`LICENSE` changed from MIT to the PolyForm Noncommercial License 1.0.0**, per explicit user
  instruction after this sprint's initial sign-off: personal/noncommercial use is permitted,
  selling the software or any commercial use is not. Full, unmodified license text (fetched
  verbatim from the license's own canonical source, `github.com/polyformproject/polyform-licenses`
  at the `1.0.0` tag, rather than reproduced from memory) plus a copyright/`Required Notice:` line
  per the license's own "Notices" section. **Deviation from PRD §1/§5/9.2.3's framing**: the PRD
  repeatedly describes the end goal as an "open-source template" (US-5.2's acceptance criteria,
  9.2.3's task wording), but PolyForm Noncommercial is a *source-available*, not an OSI-approved
  open-source license — it explicitly forbids commercial use, which the Open Source Definition
  does not allow a license to do. This is a deliberate, user-directed choice overriding the PRD's
  literal "open-source" wording, not an oversight; anyone reusing this project's docs/marketing
  copy going forward should say "source-available, personal use" rather than "open-source."
- **9.3.2 (tag `v1.0.0`, publish) intentionally not done**: requires `git tag`/`git push`, and this
  entire session operates under a hard standing "never commit or push" instruction. This is the
  one remaining PRD checklist item, withheld pending explicit user authorization — not an
  oversight.

---

## Grid export (Sprint 10)

Added entirely after Sprint 9 by explicit user request ("Add a option to export (PDF, PNG, SVG,
markdown)") — not part of the PRD's original nine-sprint plan (see FR-16, §13 Sprint 10). Before
implementing anything, the user was asked to choose between a zero-new-dependency approach (client
rendering + the browser's native print-to-PDF) and a heavier server-rendered-file approach (adding
PDF/image-generation libraries); they chose the zero-new-dependency path, and it was honored
throughout — `pyproject.toml`/`uv.lock` are completely untouched by this feature.

- **Markdown and SVG are server-rendered, pure Python** (`apps/planner/export.py`), mirroring
  `grid.py`'s own PRD-R2 discipline ("compute everything server-side, templates only iterate, no
  logic-heavy DTL"): `render_week_markdown(blocks, time_format)` groups an already-user-filtered
  `TimeBlock` iterable by day (via `TimeBlock.DAY_CHOICES`, so every day gets a heading even with
  zero blocks) and formats each as a `- <start>–<end> <label>` bullet; `build_svg_export(week_grid)`
  turns the *exact same* `WeekGrid` matrix the on-screen `<table>` renders from into flat,
  pixel-positioned `SvgRect`/`SvgText` dataclasses, so the exported SVG's block placement always
  matches what's on screen (same collision re-anchoring, same out-of-range clamping) — reusing
  `build_week_grid()` here rather than re-deriving positions from raw blocks was a deliberate
  design choice, not a shortcut. `format_time_label()` (used by both the Markdown export and
  `grid.py`'s on-screen row labels) was promoted from a private `grid.py` function to a public one
  in `models.py`, alongside the module's other centralized time helpers — the same move already
  made once before for `time_from_minutes()` (Sprint 6).
- **`ExportMarkdownView`/`ExportSVGView`** (`apps/planner/views.py`): both `LoginRequiredMixin`,
  GET-only, no pk in either URL (there's nothing to scope by pk — an export is always "my whole
  week"), following the exact same `PlannerSettings.objects.get_or_create(user=...)` +
  `TimeBlock.objects.filter(user=...)` pattern every other view in this file uses (NFR-07). Markdown
  returns `text/markdown; charset=utf-8`; SVG renders a new template,
  `apps/planner/templates/planner/partials/grid_export.svg` — a standalone file (no
  `{% extends %}`, since it *is* the entire downloaded response body, not one piece of a page).
  Both set `Content-Disposition: attachment` so the browser downloads them directly.
- **A real bug found by `qa-tester`'s adversarial pass, fixed, and covered by a regression test on
  both call sites**: a `TimeBlock.label` containing an embedded newline (not reachable via a normal
  browser `<input type="text">` keystroke, but not rejected by the model — plain
  `CharField(max_length=200)` — or the form either) let a crafted label inject a fabricated
  `## Heading`/`- bullet` line into the exported Markdown document, landing under the wrong day's
  section, since the raw label was interpolated straight into an f-string with no newline handling.
  Fixed with `safe_label = ' '.join(block.label.split())` before formatting each bullet (collapses
  any embedded whitespace, including newlines, to single spaces) — and, for consistency, the same
  normalization was applied to `build_svg_export()`'s block-label text too (`code-reviewer` flagged
  this second call site; SVG's own default whitespace handling meant it wasn't a live bug there, but
  a single invariant enforced the same way at both call sites is worth the one extra line).
- **SVG autoescaping is deliberately left on** — no `|safe`, no `{% autoescape off %}` anywhere in
  `grid_export.svg` — since a block label is untrusted user text flowing directly into XML markup.
  Verified well-formed (not just eyeballed) by rendering the real template with an adversarial
  `&`/`<`/`>`/quote-carrying label and parsing the response with Python's
  `xml.etree.ElementTree.fromstring()`, both independently by the implementing agent, this session,
  and `code-reviewer`.
- **PNG export is entirely client-side, zero new dependencies**: `static/js/export.js` reads the
  live `#grid-table table` DOM (`getBoundingClientRect()`/`getComputedStyle()` per `<th>`/`<td>` —
  background, border, and either the `.block-label` child's text or the cell's own text), draws it
  onto an off-screen `<canvas>` sized by `devicePixelRatio` for crispness on high-DPI screens, and
  downloads it via `canvas.toDataURL('image/png')`. No server endpoint exists for this format at
  all — there is nothing to link to, since a PNG is a snapshot of whatever the grid looks like
  *right now* in this browser. Reads whatever the browser already resolved for colors (a block's
  real hex, the colorless fallback, header/time-label tints) with no knowledge of this app's color
  logic baked into the script itself. Iterating only `th`/`td` elements (never their descendants)
  structurally excludes the hover-control edit/delete buttons and resize-handle strips from ever
  being drawn — verified by reading `block_cell.html`'s actual current markup, not assumed.
- **PDF export is the browser's own native print-to-PDF, zero new dependencies**: print-only
  Tailwind `print:` variant classes (a core v4 variant, no config needed) — `print:hidden` on
  `templates/partials/navbar.html`, `templates/partials/footer.html`, and the dashboard toolbar row;
  `print:max-h-none print:overflow-visible print:ring-0` on `#grid-table`'s wrapper in
  `grid_table.html`, removing the on-screen scroll-clamp so the *entire* grid prints, not just
  whatever's currently scrolled into view — plus a "Print / Save as PDF" button that calls
  `window.print()`. Nothing else: no PDF-generation library, no separate print-preview page.
- **Dashboard UI**: a third toolbar `<details name="dashboard-toolbar">` ("Export"), joining the
  existing Settings/Palette exclusive-accordion group for free. Markdown/SVG are plain `<a href>`
  downloads (routing them through HTMX would swap the response into the page instead of downloading
  it — actively wrong, not merely unnecessary); PNG/Print are buttons carrying
  `data-export-png`/`data-export-print` for `export.js` to delegate off of `document`, the same
  correctness requirement `grid-drag.js`'s own module comment already documents (a future HTMX
  mutation could in principle replace DOM around a directly-bound listener; delegating from
  `document` means there's nothing to ever re-bind).
- **Two real NFR-05 duplication regressions caught by `code-reviewer` in the first draft, both
  fixed**:
  1. The toolbar panel's long wrapper class string (full-bleed on mobile, fixed `w-80` at `sm:` and
     up, same card treatment) was hand-copied a third time for the new Export panel, crossing the
     "3+ identical repeats" threshold this codebase's own button partials were extracted at. Fixed
     with a single `{% with panel_class=... %}` value spanning all three `<details>` panels in
     `dashboard.html` — not a new shared partial file: unlike `primary.html`/`secondary.html`
     (genuinely reused across many templates — navbar, landing, both auth pages), this exact panel
     wrapper is only ever used inside this one file, wrapping three genuinely different bodies (a
     form, an HTMX-driven palette list, a plain action list) that DTL's `{% include %}` has no way
     to parametrize as passed-in markup anyway (unlike Jinja2). A full new partial would have been
     disproportionate (NFR-01); a single template-scoped variable was the fix that actually matched
     the problem's shape.
  2. The PNG/Print `<button>`s hand-copied `secondary.html`'s plain-button class string verbatim
     instead of routing through the partial — recreating exactly the duplication that partial
     exists to prevent. Fixed by adding two narrowly-named, auto-escaped boolean flags,
     `data_export_png`/`data_export_print`, to `secondary.html`'s plain-button branch (each renders
     its own fixed, literal attribute name, never an interpolated one) — mirroring the exact shape
     of that same branch's pre-existing `hx_get`/`hx_target`/`hx_swap` flags, not a new, generic
     `data-*` passthrough (which would have reopened the raw attribute-string escape hatch this
     partial's whole design already avoids).
- **Export fidelity intentionally differs between formats, and the UI now says so**: Markdown lists
  every block the user owns regardless of their configured day range, while SVG/PNG/Print only show
  what's visible in the current `[day_start, day_end)` window — exactly like the on-screen grid
  itself (`out_of_range_blocks`/`unplaced_blocks`, see the Sprint 5 section above). `code-reviewer`
  flagged this as a real, unmentioned surprise risk; the Export panel's own description text now
  says so directly rather than leaving it undiscovered.
- **Verification**: `qa-tester` ran an adversarial HTTP-level pass beyond the implementing agents'
  own unit/view tests — full and empty weeks, mixed colored/colorless blocks, Markdown- and
  XML-special characters in labels, both `time_format`s including a midnight-crossing block,
  two-user ownership isolation (confirmed by reading the actual query code too, not just trusting
  the HTTP test result), anonymous-auth redirects, and POST-method rejection on both new endpoints
  — finding the newline-injection bug above and nothing else. `code-reviewer` then independently
  re-verified the fix by tracing it line-by-line, re-confirmed NFR-07 isolation and NFR-01 (zero new
  dependencies) by reading the code directly, and found the two duplication issues above. Both
  passes' findings were fixed and re-verified before sign-off. The automated suite grew from 82 to
  101 tests (`test_export.py`, new; `test_views.py`'s export-view tests; both new routes added to
  the existing `AuthProtectionTests` parametrized sweep); `ruff check .`, `manage.py check`, and
  `makemigrations --check --dry-run` stayed clean throughout.

---

## Known, expected gaps

- **No browser-verified visual QA.** The Playwright MCP server (required by `qa-tester`) is still
  not configured in this environment. Auth, landing/dashboard, planner settings, the read-only
  grid, every block-interactivity flow, every palette CRUD flow, and now the containerized
  deployment have all been verified via Django's test client or direct HTTP requests (status
  codes, redirect targets, response headers including `HX-Retarget`/`HX-Reswap`, response body
  assertions, DB-state checks, and HTML structure parsing) and every template's class strings were
  spot-checked/hand-verified for contrast against PRD §9, but nothing has been rendered in a real
  browser — no visual layout, hover/focus states, dark-mode flash, or responsive breakpoint check
  has been done. The pointer-drag gesture in `static/js/grid-drag.js` (Sprint 6) and
  `static/js/color-sync.js`'s bidirectional color-picker/hex-field pairing (Sprint 7) have still
  never been exercised in a real DOM, only reasoned through by reading their source. Sprint 10 adds
  two more of the same shape: **`static/js/export.js`'s PNG canvas render has never been visually
  confirmed** (does the drawn image actually look like the on-screen grid, not just "the code reads
  the right DOM properties" — reasoned through, not seen), and **the print-only CSS's actual
  printed/PDF output has never been seen either** (does `window.print()` really produce a clean,
  full, chrome-free page once the browser's own print engine gets involved, not just "the right
  Tailwind classes are compiled"). Run `claude mcp add playwright -- npx @playwright/mcp@latest` at
  the next opportunity — this gap is now eight additions deep across ten sprints and has not been
  shrinking, only accumulating. Neither Sprint 9's Docker work nor Sprint 10's export feature closes
  this gap: both prove the app runs/behaves identically at the HTTP/data layer (same test suite,
  same request/response contract), which is orthogonal to whether anything actually looks or
  behaves correctly once painted and scripted in a real browser.
- **No CI pipeline.** `manage.py test` and `ruff check` are both clean and documented as the
  commands to run, and now also verified to pass identically inside the Docker image, but nothing
  runs them automatically on push/PR yet — no `.github/workflows/` or equivalent exists. Now that
  Sprint 9's Docker image exists, a CI job has a natural, ready-made thing to build and test
  inside — this is the most natural remaining next step, but it is not a PRD requirement for any
  sprint through 9 and was not attempted.
- **Container runs as root.** No `USER` directive in the `Dockerfile`. Not a PRD requirement and
  not a regression (nothing in this project ever ran differently), but flagged by `code-reviewer`
  as worth revisiting for a public reference template — see the Sprint 9 section above for why it
  wasn't attempted this sprint (named-volume ownership complications).

---

## Agent roster

See [`.claude/agents/README.md`](../.claude/agents/README.md) for the full breakdown of which
specialist agent (`django-backend`, `django-frontend`, `htmx-interaction`, `qa-tester`,
`code-reviewer`) owns which part of the codebase and which PRD sprints/tasks each is invoked for.
