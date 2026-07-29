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

The project boots, has a Tailwind v4 design-system base, full native auth (signup, login,
logout), a real landing page (hero, features, decorative grid mock), and a dashboard shell
(header, toolbar, empty state). The planner domain now exists: `BlockColor`, `PlannerSettings`,
and `TimeBlock` models with full validation, a signal auto-creating each new user's settings, admin
registration, and a live settings form reachable both standalone and as an inline dashboard-toolbar
dropdown. There is still no functional grid yet (Sprint 5) and no block CRUD/HTMX interactivity
(Sprint 6). See §13 in the PRD for the full sprint plan and checklist.

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
│   │                         # dashboard.html (header/toolbar/empty-state — Sprint 3)
│   ├── accounts/             # native auth — Sprint 2
│   │   ├── forms.py           # SignUpForm, LoginForm (shared INPUT_CLASSES)
│   │   ├── views.py           # SignUpView(CreateView)
│   │   ├── urls.py            # app_name = 'accounts'; login/, signup/, logout/
│   │   └── templates/accounts/  # login.html, signup.html
│   └── planner/               # domain models, settings UI — Sprint 4; grid/CRUD — Sprint 5+
│       ├── models.py           # BlockColor, PlannerSettings, TimeBlock (all TimestampedModel)
│       ├── signals.py          # post_save on User -> auto-create PlannerSettings
│       ├── apps.py             # PlannerConfig.ready() registers signals.py
│       ├── admin.py            # all three models registered
│       ├── forms.py            # PlannerSettingsForm (shared INPUT_CLASSES pattern)
│       ├── views.py            # SettingsUpdateView(LoginRequiredMixin, UpdateView)
│       ├── urls.py             # app_name = 'planner'; settings/
│       └── templates/planner/  # settings_form.html (standalone page)
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

Everything else in Sprints 1–4 follows the PRD as written.

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

## Known, expected gaps

- **No browser-verified visual QA.** The Playwright MCP server (required by `qa-tester`) is still
  not configured in this environment. Auth, landing/dashboard, and now the planner settings flows
  were all verified via Django's test client (status codes, redirect targets, response body
  assertions, DB-state checks) and every template's class strings were spot-checked against PRD §9,
  but nothing has been rendered in a real browser — no visual layout, hover/focus states,
  dark-mode flash, or responsive breakpoint check has been done. Two concrete, still-unconfirmed
  layout questions are now stacked up: the auth pages' `min-h-screen` centered card possibly not
  fitting one viewport (flagged in Sprint 3), and whether the new settings `<details>` dropdown's
  `absolute`-positioned panel (`apps/core/templates/core/dashboard.html`) actually stays within the
  viewport and doesn't get clipped/overlapped at narrow widths in a real browser, despite the
  `w-[calc(100vw-2rem)] sm:w-80` sizing intended to prevent that. Run
  `claude mcp add playwright -- npx @playwright/mcp@latest` before Sprint 5 — grid rendering and
  drag-to-resize will be much harder to verify blind, and this gap is now two sprints deep.
- **No tests, no Docker.** Deliberately deferred to Sprints 8 and 9 per the PRD.

---

## Agent roster

See [`.claude/agents/README.md`](../.claude/agents/README.md) for the full breakdown of which
specialist agent (`django-backend`, `django-frontend`, `htmx-interaction`, `qa-tester`,
`code-reviewer`) owns which part of the codebase and which PRD sprints/tasks each is invoked for.
