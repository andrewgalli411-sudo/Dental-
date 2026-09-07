# HANDOFF — verifi-dental

Everything a fresh session (human or AI) needs to continue this project. Start by
reading `CLAUDE.md`, then `DEPLOY.md`, then this file.

## Status snapshot

Built, tested, and on `main`:
- **backend/** — FastAPI. Intake (token upload + CSV/Excel/PDF normalizer), admin
  auth (argon2 + TOTP MFA + signed cookie + login lockout), verification workflow
  with human sign-off, report HTML+PDF, secure-link email delivery, 7-day PHI purge.
  36 tests. Alembic (3 migrations).
- **frontend/** — Next.js on the UI-kit tokens: /upload/[token], /login, /queue,
  /batches/[id]. `npm run build` passes.
- **marketing/** — static Vercel-ready marketing + sign-in site (no PHI).
- **infra/** — Terraform for a BAA-covered AWS home (VPC, private RDS, S3 SSE-KMS,
  KMS, Secrets, ECR, App Runner, SES) + scheduled PHI-purge (ECS Fargate) + basic
  CloudWatch alarms. Authored; run `terraform validate` on a machine with registry
  access (the sandbox that wrote it couldn't reach the TF registry).
- **.github/workflows/ci.yml** — backend tests+lint and frontend build on push/PR.
- Docker images + entrypoints for both apps.

Nothing is deployed yet. See "What's left".

## Non-negotiables (also in CLAUDE.md)
1. HIPAA: encrypt in transit + at rest, no PHI in logs, human sign-off before any
   report goes out, PHI purged after 7 days, BAAs with every vendor touching PHI.
2. No payer-portal scraping, ever.
3. No LLM in the PHI path until an Anthropic BAA is signed (v1 parses with Textract
   + deterministic code, not an LLM).
4. Standard Vercel has no BAA → PHI app runs on AWS; only marketing on Vercel.
5. All eligibility flows through `app.eligibility` (the v1→v2 EDI seam).
6. Account-less client surface (secure tokenized links); only the admin logs in.

## What's left

### Human-only (cannot be automated)
1. Make the GitHub repo private.
2. Sign the AWS BAA (AWS Artifact) before any real PHI.
3. Anthropic BAA — only if an LLM is ever put in the PHI path (default: not).
4. Sign a BAA with each pilot practice.
5. AWS account + credentials for deploy; domain + DNS; SES production access.
6. Land the first pilot practice (the real bottleneck).

### Agent/engineer tasks
- `terraform validate` + a `terraform plan` review on a machine with registry access.
- Deploy: follow `DEPLOY.md` (Vercel for marketing; AWS via `infra/` for the app),
  build/push images, bootstrap the first admin, wire DNS + SES.
- Product decision to confirm with the founder: split the single amber "Needs info"
  status into "missing data" vs "payer pending" (a 4th badge) — small change.
- When scaling past one backend instance, move the login limiter
  (`app/security/ratelimit.py`) to a shared store (Redis/DB); today it's in-memory.
- Frontend: continue the accessibility pass and richer error/loading states as the
  console grows.

## Local dev
```bash
cd backend && python3 -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]"
cp .env.example .env && uvicorn app.main:app --reload
python -m scripts.create_admin you@example.com   # another shell

cd frontend && npm install && cp .env.local.example .env.local && npm run dev
```
Gates before pushing: `cd backend && pytest -q && ruff check app tests scripts`,
`cd frontend && npm run build`.
