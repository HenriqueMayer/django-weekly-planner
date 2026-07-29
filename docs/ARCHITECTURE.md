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

The project boots, has a Tailwind v4 design-system base, full native auth (signup, login,
logout), a real landing page (hero, features, decorative grid mock), and a dashboard shell
(header, toolbar). The planner domain exists: `BlockColor`, `PlannerSettings`, and `TimeBlock`
models with full validation, a signal auto-creating each new user's settings, admin registration,
and a live settings form reachable both standalone and as an inline dashboard-toolbar dropdown.
The dashboard now renders a real, server-computed weekly grid (`apps/planner/grid.py`) —
Monday-Sunday columns, time-slot rows honoring the user's interval/range/format settings, and
blocks placed with correct `rowspan`, including midnight-crossing and interval-misaligned blocks.
There is still no block CRUD/HTMX interactivity yet (Sprint 6) — the grid is read-only,
server-rendered HTML. See §13 in the PRD for the full sprint plan and checklist.

---

## Directory layout (as built)

```
django-weekly-planner/
├── manage.py
├── pyproject.toml          # uv-managed; django>=6.0.7 is the sole runtime dependency
├── uv.lock
├── .python-version         # 3.12
├── .env.example
├── .gitignore
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
│   │   └── templates/core/   # landing.html (hero/features/grid-mock — Sprint 3),
│   │                         # dashboard.html (header/toolbar/real grid — Sprint 3-5)
│   ├── accounts/             # native auth — Sprint 2
│   │   ├── forms.py           # SignUpForm, LoginForm (shared INPUT_CLASSES)
│   │   ├── views.py           # SignUpView(CreateView)
│   │   ├── urls.py            # app_name = 'accounts'; login/, signup/, logout/
│   │   └── templates/accounts/  # login.html, signup.html
│   └── planner/               # domain models/settings — Sprint 4; grid — Sprint 5; CRUD — Sprint 6+
│       ├── models.py           # BlockColor, PlannerSettings, TimeBlock (all TimestampedModel)
│       ├── grid.py             # build_week_grid() — pure-Python matrix builder (Sprint 5)
│       ├── signals.py          # post_save on User -> auto-create PlannerSettings
│       ├── apps.py             # PlannerConfig.ready() registers signals.py
│       ├── admin.py            # all three models registered
│       ├── forms.py            # PlannerSettingsForm (shared INPUT_CLASSES pattern)
│       ├── views.py            # SettingsUpdateView, GridView (both LoginRequiredMixin)
│       ├── urls.py             # app_name = 'planner'; '' (grid), settings/
│       └── templates/planner/
│           ├── settings_form.html    # standalone settings page (Sprint 4)
│           ├── grid.html             # standalone grid page (Sprint 5)
│           └── partials/
│               ├── grid_table.html    # shared <table>, included by grid.html + dashboard.html
│               ├── block_cell.html    # block-start <td> presentation
│               └── empty_cell.html    # empty, clickable <td>
├── templates/
│   ├── base.html
│   └── partials/
│       ├── navbar.html
│       ├── footer.html
│       ├── form_field.html    # shared label/widget/help/error row — Sprint 2
│       └── buttons/
│           └── primary.html   # shared primary-button partial (<a>/<button>) — Sprint 4
├── static/
│   ├── css/
│   │   ├── input.css        # Tailwind v4 source (CSS-first config)
│   │   └── app.css          # compiled output — committed, not built in CI
│   └── js/
│       ├── htmx.min.js      # vendored, not CDN-loaded
│       └── theme.js
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

Everything else in Sprints 1–5 follows the PRD as written.

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

## Known, expected gaps

- **No browser-verified visual QA.** The Playwright MCP server (required by `qa-tester`) is still
  not configured in this environment. Auth, landing/dashboard, planner settings, and now the grid
  itself were all verified via Django's test client (status codes, redirect targets, response body
  assertions, DB-state checks, and — new this sprint — actual HTML table-structure parsing) and
  every template's class strings were spot-checked against PRD §9, but nothing has been rendered in
  a real browser — no visual layout, hover/focus states, dark-mode flash, or responsive breakpoint
  check has been done. Three concrete, still-unconfirmed layout questions are now stacked up: the
  auth pages' `min-h-screen` centered card possibly not fitting one viewport (Sprint 3), the
  settings `<details>` dropdown's `absolute`-positioned panel possibly clipping at narrow widths
  (Sprint 4), and now whether a 18+ row grid table at `max-h-[75vh]` produces an awkward
  nested-scrollbar experience (page scroll + inner vertical scroll + inner horizontal scroll all at
  once) on a narrow viewport (Sprint 5). Run
  `claude mcp add playwright -- npx @playwright/mcp@latest` **before Sprint 6** — drag-to-resize
  (PRD 6.3) has no other realistic way to be verified, and this gap is now three sprints deep.
- **No tests, no Docker.** Deliberately deferred to Sprints 8 and 9 per the PRD.

---

## Agent roster

See [`.claude/agents/README.md`](../.claude/agents/README.md) for the full breakdown of which
specialist agent (`django-backend`, `django-frontend`, `htmx-interaction`, `qa-tester`,
`code-reviewer`) owns which part of the codebase and which PRD sprints/tasks each is invoked for.
