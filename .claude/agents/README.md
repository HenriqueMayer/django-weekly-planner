# Agents — Time-Blocking Routine Organizer

Specialist AI agents for building the project described in [`docs/ProductRequirementDocument.md`](../../docs/ProductRequirementDocument.md).

Each `.md` file in this folder is a Claude Code subagent: a scoped role with its own system prompt, tool set, and slice of the codebase. Claude Code auto-discovers them — no registration needed. This `README.md` is documentation only; it has no agent frontmatter, so the loader ignores it.

The roster is deliberately small: only roles that produce or verify code.

---

## The roster

| Agent | Owns | Documentation source |
|---|---|---|
| [`django-backend`](django-backend.md) | `*.py` — models, CBVs, forms, signals, admin, URLs, grid builder | Context7 → Django |
| [`django-frontend`](django-frontend.md) | `templates/`, `static/css/` — DTL, Tailwind, design system | Context7 → Tailwind + Django |
| [`htmx-interaction`](htmx-interaction.md) | `hx-*` attributes, `static/js/` — swaps, drag-resize, theme | Context7 → htmx |
| [`qa-tester`](qa-tester.md) | Browser verification, `apps/**/tests/` | Playwright MCP |
| [`code-reviewer`](code-reviewer.md) | Standards, security, scope discipline — reports only | Context7 (verification) |

---

### `django-backend`

Every line of server-side Python: the domain model (`TimeBlock`, `BlockColor`, `PlannerSettings`), Class-Based Views, forms and validators, signals, admin registration, URL routing, settings, and the pure-Python grid builder in `apps/planner/grid.py`.

**Use it for** — Sprints 1.5, 2, 4, 5.1; the server half of Sprints 6 and 7. Anything involving migrations, overlap validation, the midnight-end rule, per-user query scoping, or the HTML-fragment endpoints HTMX calls.

**Don't use it for** — templates, Tailwind classes, HTMX attributes, browser testing.

---

### `django-frontend`

Markup and styling: `base.html`, navbar and footer, auth and landing screens, the weekly grid `<table>`, all reusable partials, the Tailwind design system, and the standalone-CLI build pipeline.

**Use it for** — Sprints 1.3, 1.4, 2.3, 3, 5.2, 7.2. Anything about visual consistency, dark mode, responsive layout, or a new shared partial.

**Don't use it for** — Python, HTMX behavior, or JavaScript.

Carries the full PRD §9 token and component tables inline, so it styles from the spec rather than from taste.

---

### `htmx-interaction`

What makes the grid feel live: `hx-*` attributes and swap strategies, inline create/edit/delete flows, out-of-band updates, `HX-Trigger` events, global CSRF wiring, loading indicators, and the three small Vanilla JS modules (`grid-drag.js`, `theme.js`, contrast helper).

**Use it for** — Sprints 1.4.4, 1.4.5, 6, 7.1.4. Drag-to-resize, "repeat on days", theme persistence, and anything that must happen without a page reload.

**Don't use it for** — Python or base styling.

Enforces risk R1: the client stays thin, the server owns all state. It ships the click/keyboard resize path *before* the drag enhancement, so the accessible fallback is never an afterthought.

---

### `qa-tester`

Drives a real browser through the **Playwright MCP server** to verify the app against the PRD — auth and grid flows, drag-to-resize (`browser_drag` is the only way to test FR-09), overlap rejection, zero-page-reload confirmation via network traces, design compliance against §9, responsive audits at three breakpoints, and keyboard accessibility. Also writes the Django test suite in Sprint 8.

**Use it for** — after any feature lands, and for Sprints 2.4, 3.3, 5.3, 6.5.3, 7.2, 7.3.3, 8.

**Don't use it for** — fixing what it finds. It reports defects with reproduction steps and routes them to the owning agent.

**Requires the Playwright MCP server** — see setup below.

---

### `code-reviewer`

The guardrail against this PRD's two named failure modes: over-engineering (NFR-01) and inconsistency (NFR-05). Checks per-user data isolation, the dependency budget, single-quote and English-only rules, CBV preference, signal placement, the midnight and overlap edge cases, HTMX error status codes, and design-system drift.

**Use it for** — end of each sprint, and after any large change.

**Don't use it for** — implementation. Read-only by design; it has no `Write` or `Edit` tool.

---

## MCP servers

### Context7 — required by the three implementation agents

Already configured globally. `django-backend`, `django-frontend`, `htmx-interaction`, and `code-reviewer` must query it before writing or judging framework code. Pre-resolved library IDs:

| Stack | Library ID |
|---|---|
| Django 6.0 | `/websites/djangoproject_en_6_0` |
| Tailwind CSS | `/tailwindlabs/tailwindcss.com` |
| htmx | `/bigskysoftware/htmx` |

This matters more than usual here: the project runs **Django 6.0.7** and **Tailwind v4**, both newer than most model training data, and Tailwind v4 replaced the entire `tailwind.config.js` mechanism with CSS-first configuration.

### Playwright — required by `qa-tester`, not yet configured

```sh
claude mcp add playwright -- npx @playwright/mcp@latest
```

Node v20 and npx are present on this machine. Until this is added, `qa-tester` can write and run Django tests but cannot verify anything in a browser — it is instructed to stop and say so rather than guess.

---

## Suggested workflow per sprint

```
django-backend  ──►  django-frontend  ──►  htmx-interaction
                                                  │
                                                  ▼
                            qa-tester  ◄──►  code-reviewer
                                     │
                                     └──►  defects back to the owning agent
```

1. **Backend first** — models, views, and endpoints define the contract, including what context each fragment template receives.
2. **Frontend second** — templates and styling against that contract.
3. **Interaction third** — wire the swaps once real endpoints and real markup exist.
4. **QA and review last** — browser verification and standards audit before the sprint closes.

Steps 1–3 are sequential because each consumes the previous one's contract; running them in parallel produces invented endpoints and mismatched context variables. Step 4 can run in parallel.

---

## Two open discrepancies every agent is told to respect

**1. Django version.** The PRD says "Django 5.x"; the repo has **6.0.7** installed. The installed version wins. Agents verify APIs against 6.0 docs and report any PRD instruction that is deprecated there rather than following it silently.

**2. Directory layout collision.** PRD §8.1 specifies `config/` for the settings package and `apps/core/` for the shared app — but the repo already uses `core/` as the settings package (`ROOT_URLCONF = 'core.urls'`). The names collide. `django-backend` will not restructure unilaterally; it flags the conflict and, absent a decision, renames the settings package to `config/` to match the PRD, reporting the change.

---

## Conventions every agent inherits

From PRD §2 and NFR-02 — enforced, not suggested:

- PEP 8, **single quotes**, **English only** (code, comments, templates, UI copy).
- Class-Based Views wherever possible.
- Every model inherits `TimestampedModel` (`created_at`, `updated_at`).
- Signals only in `apps/<app>/signals.py`, registered in `AppConfig.ready()`.
- Fat models, thin views — so the deferred Sprint 8 tests stay cheap (risk R6).
- Dependencies via **uv** (`uv add`), never `pip install`. Budget: ≤ 5 runtime deps before the final sprints.
- No SPA framework, no DRF, no Celery, no third-party ORM, no JS component library.
