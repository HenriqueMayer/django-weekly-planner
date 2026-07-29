# Architecture — Time-Blocking Routine Organizer

Living document tracking how the codebase actually looks, as it's built sprint by sprint against
[`ProductRequirementDocument.md`](./ProductRequirementDocument.md). Where reality diverges from the
PRD, it's recorded here rather than silently followed or silently ignored.

---

## Current status

**Sprint 1 — Project Foundation & Design System Base: complete.**

The project boots, has a Tailwind v4 design-system base, and serves a login-gated dashboard
placeholder — but there is no auth (Sprint 2), no domain model (Sprint 4), and no grid yet
(Sprint 5). See §13 in the PRD for the full sprint plan and checklist.

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
│   ├── accounts/             # empty skeleton — Sprint 2
│   └── planner/               # empty skeleton — Sprint 4+
├── templates/
│   ├── base.html
│   └── partials/
│       ├── navbar.html
│       └── footer.html
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

Everything else in Sprint 1 follows the PRD as written.

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
wiring starts in Sprint 6 — this sprint only established the global contract.

---

## Known, expected gaps at the end of Sprint 1

- **`NoReverseMatch` on `accounts:login` / `accounts:signup` / `accounts:logout`.** `navbar.html`
  references these unconditionally, but `apps/accounts` has no URLs yet — that's Sprint 2. Any
  full-page render (`runserver` and visiting `/`) will 500 until Sprint 2 lands. URL names owned by
  `apps/core` (`core:landing`, `core:dashboard`) were verified independently via `reverse()` and do
  resolve correctly.
- **No browser-verified visual QA.** The Playwright MCP server (required by `qa-tester`) is not yet
  configured in this environment. Tailwind output was verified by inspecting the compiled
  `static/css/app.css` for the expected generated rules, not by rendering in a real browser. Run
  `claude mcp add playwright -- npx @playwright/mcp@latest` before Sprint 2's QA task (2.4) if
  browser verification is wanted.
- **No tests, no Docker.** Deliberately deferred to Sprints 8 and 9 per the PRD.

---

## Agent roster

See [`.claude/agents/README.md`](../.claude/agents/README.md) for the full breakdown of which
specialist agent (`django-backend`, `django-frontend`, `htmx-interaction`, `qa-tester`,
`code-reviewer`) owns which part of the codebase and which PRD sprints/tasks each is invoked for.
