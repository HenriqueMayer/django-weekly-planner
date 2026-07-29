# Architecture — Time-Blocking Routine Organizer

Living document tracking how the codebase actually looks, as it's built sprint by sprint against
[`ProductRequirementDocument.md`](./ProductRequirementDocument.md). Where reality diverges from the
PRD, it's recorded here rather than silently followed or silently ignored.

---

## Current status

**Sprint 1 — Project Foundation & Design System Base: complete.**
**Sprint 2 — Accounts (Native Authentication): complete.**

The project boots, has a Tailwind v4 design-system base, and now has full native auth: signup,
login, logout, all styled and wired to the navbar. There is still no domain model (Sprint 4) and
no grid yet (Sprint 5). See §13 in the PRD for the full sprint plan and checklist.

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
│   │   ├── views.py          # LandingView, DashboardView
│   │   ├── urls.py           # app_name = 'core'
│   │   └── templates/core/   # landing.html, dashboard.html
│   ├── accounts/             # native auth — Sprint 2
│   │   ├── forms.py           # SignUpForm, LoginForm (shared INPUT_CLASSES)
│   │   ├── views.py           # SignUpView(CreateView)
│   │   ├── urls.py            # app_name = 'accounts'; login/, signup/, logout/
│   │   └── templates/accounts/  # login.html, signup.html
│   └── planner/               # empty skeleton — Sprint 4+
├── templates/
│   ├── base.html
│   └── partials/
│       ├── navbar.html
│       ├── footer.html
│       └── form_field.html    # shared label/widget/help/error row — Sprint 2
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

Everything else in Sprints 1–2 follows the PRD as written.

---

## Design system

Single source of truth: PRD §9. `base.html` is the only template with a full `<html>` skeleton;
every screen extends it. Color tokens, button/input/card class strings, and the grid table pattern
are copied verbatim from §9.2 — no ad hoc classes. See `static/css/input.css`'s header comment for
the token table mirrored in CSS form (PRD risk R5's mitigation).

Dark mode: class-based (`dark` on `<html>`), toggled by `static/js/theme.js` and applied
pre-paint by a synchronous inline script in `base.html`'s `<head>` to avoid a flash of the wrong
theme. Preference persists in `localStorage`, defaulting to `prefers-color-scheme` when unset.

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

## Known, expected gaps

- **No browser-verified visual QA.** The Playwright MCP server (required by `qa-tester`) is still
  not configured in this environment. Auth flows were verified via Django's test client (status
  codes, redirect targets, response body assertions) and template source was spot-checked against
  PRD §9, but nothing has been rendered in a real browser — no visual layout, hover/focus states,
  dark-mode flash, or responsive check has been done. Run
  `claude mcp add playwright -- npx @playwright/mcp@latest` if browser verification is wanted before
  Sprint 3.
- **No tests, no Docker.** Deliberately deferred to Sprints 8 and 9 per the PRD.

---

## Agent roster

See [`.claude/agents/README.md`](../.claude/agents/README.md) for the full breakdown of which
specialist agent (`django-backend`, `django-frontend`, `htmx-interaction`, `qa-tester`,
`code-reviewer`) owns which part of the codebase and which PRD sprints/tasks each is invoked for.
