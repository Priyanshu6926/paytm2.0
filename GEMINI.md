<!-- GSD:project-start source:PROJECT.md -->

## Project

**Munim-AI (powered by KiranaOS)**

Munim-AI is a vernacular, voice-first and vision-first AI CFO & AI CMO mobile merchant partner for Indian kirana store owners using Paytm Soundbox and QR. Underneath the intuitive mobile UI sits KiranaOS, a deterministic append-only business memory engine ensuring 100% mathematical accuracy without LLM hallucinations. Built for the Paytm Build for India AI Hackathon (Track 1: Merchant Growth AI) by Team Code Apex.

**Core Value:** A closed-loop AI business partner that safeguards margins (AI CFO: invoice price-creep alerts, Paytm settlement waterfall explainer, cautious UPI reconciliation) and drives attributed footfall and recovery (AI CMO: vernacular voice udhaar recovery, break-even offer studio, 60s Diwali closing ritual) with 100% auditable deterministic arithmetic.

### Constraints

- **Tech Stack**: FastAPI (Python 3.11+), SQLite (8 append-only tables), React 18 + Vite + TypeScript + Tailwind CSS.
- **Law of Zero LLM Math**: LLM never computes arithmetic, margins, loan deductions, or stock calculations. All math lives in `backend/services/deterministic_engine.py`.
- **Law of Append-Only Immutability**: No `UPDATE` or `DELETE` on financial amounts. Adjustments are explicit `REVERSAL_ADJUSTMENT` entries.
- **Law of Demo-Day Survivability**: All external calls have 6s timeouts with instant high-fidelity local mock fallbacks (realistic synthetic base64 audio and OCR results).
- **Form Factor**: Strictly mobile-first interface adhering to Paytm Merchant design patterns.
- **Custom Invoices**: Support both built-in demo sample invoices and custom user image uploads.

<!-- GSD:project-end -->

<!-- GSD:stack-start source:STACK.md -->

## Technology Stack

Technology stack not yet documented. Will populate after codebase mapping or first phase.
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.agents/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-fast` for a trivial task inline, with no subagents and no PLAN.md
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
