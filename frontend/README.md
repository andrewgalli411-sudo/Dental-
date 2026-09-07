# frontend

Next.js (App Router, TypeScript, Tailwind) UI for verifi-dental, built on the
Verifi UI Kit tokens (`../design/ui-kit.html`).

## Surfaces

- **`/upload/[token]`** — public, account-less. A practice drops their appointment
  file; single-use token scopes it to their practice.
- **`/login`** — admin sign-in (password + TOTP).
- **`/queue`** — admin review queue (batches).
- **`/batches/[id]`** — review/correct parsed appointments, verify each patient,
  approve (sign-off), and send the report.

## How it talks to the backend

`next.config.mjs` rewrites `/api/*` to the FastAPI backend (`BACKEND_URL`). This
keeps the admin session cookie **first-party** (same origin as the app), which is
what makes the httponly + SameSite=Strict cookie work without CORS.

## Run

```bash
cp .env.local.example .env.local     # point BACKEND_URL at FastAPI
npm install
npm run dev                          # http://localhost:3000
```

Run the backend alongside it (`cd ../backend && uvicorn app.main:app --reload`)
and create an admin with `python -m scripts.create_admin you@example.com`.

## Checks

```bash
npm run typecheck
npm run build
```
