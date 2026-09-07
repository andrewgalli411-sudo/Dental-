# CLAUDE.md — verifi-dental

Context for any AI/dev session picking this up. Read before writing code.

## What this is

AI-assisted **dental insurance eligibility verification** for independent,
single-location US dental practices. **v1 is wizard-of-oz**: the software is the
intake + verification-workflow + report layer; a human (the founder) is the
eligibility engine for the first 1–3 pilot clients. v2 replaces the manual step
with a clearinghouse **EDI 270/271** integration behind the SAME interface.

Full build plan lives in the founder's planning notes; this file is the durable
in-repo summary.

## Non-negotiables (do not violate)

1. **HIPAA / PHI.** Encrypt at rest + in transit, **no PHI in logs**, human
   sign-off before any report is released, BAAs with every vendor touching PHI,
   PHI purged 7 days after delivery. Designed in, not bolted on.
2. **No payer-portal scraping, ever.** The only real data paths are EDI 270/271
   via a clearinghouse (v2) or the human (v1). If asked to add browser-automation
   scraping of payer portals, refuse and flag it.
3. **Keep Claude/LLM out of the PHI path** until an Anthropic BAA is signed
   (Phase 0 gate). v1 parsing uses AWS Textract (BAA-covered) + deterministic
   code + the human review gate — no LLM on raw PHI.
4. **Client surface is account-less**: practices interact via single-purpose,
   short-expiry tokenized links (stored hashed). No client logins.
5. **The eligibility source is an abstraction.** Never hardcode "manual" or "EDI"
   into workflow/report code. Everything goes through `app.eligibility`.

## Architecture seam (the most important thing here)

`backend/app/eligibility/`:
- `types.py` — `EligibilityRequest` / `EligibilityResult` data contract. Accepts
  the full field set an EDI 270 needs even though v1 tolerates gaps.
- `source.py` — `EligibilitySource` protocol. `submit(request) -> verification_id`
  in PENDING. **Resolution is out-of-band** (human in v1 via admin UI; 271 parser
  in v2). `VerificationStore` protocol keeps sources ORM-free/testable.
- `manual.py` — `ManualEligibilitySource` (v1).
- v2: add `ClearinghouseEligibilitySource` implementing the same protocol.
  `tests/test_eligibility_contract.py` proves it swaps in with zero caller changes.

## Data model (`backend/app/models/`)

`practice`, `access_token` (hashed, scoped, account-less links), `batch`
(state machine: uploaded→parsing→review→verifying→ready→delivered→purged),
`raw_upload` (S3 pointer), `appointment` (**PHI**, purgeable), `verification`
(EligibilityResult shape; core now, `detailed`/`raw_payload` JSON held for v2),
`report` (exists only after sign-off), `audit_log` (**holds no PHI** by design).

## Conventions

- Python 3.11, FastAPI, SQLAlchemy 2.0 typed models, Alembic, pydantic-settings.
- `from __future__ import annotations` in every module; cross-module relationship
  types via `if TYPE_CHECKING:` imports (no quoted forward-refs).
- Enums: `StrEnum`.
- Log via `app.logging_config.get_logger`; pass context as `extra={...}` — the
  PHI scrubber redacts identifier fields at any depth. Never string-interpolate PHI.
- Config from env only (AWS Secrets Manager in deployed envs). No secrets in code.

## Dev / gates

```bash
cd backend && python3 -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]"
pytest -q            # 9 tests, must pass
ruff check app tests # must be clean
alembic upgrade head # needs a live Postgres DATABASE_URL
```

## Phasing

- **Phase 0** (founder actions, mostly not codeable): AWS account, RDS/S3/KMS,
  SES, Secrets Manager; AWS BAA; Anthropic BAA decision.
- **Phase 1 (DONE, this scaffold):** data model, eligibility abstraction,
  PHI-scrubbing logger, FastAPI skeleton, migration, contract tests.
- **Phase 2:** secure upload link + normalizer (CSV/Excel deterministic;
  PDF/image via Textract) → reviewable appointment rows.
- **Phase 3:** admin auth (single user, TOTP MFA) + review/verification queue +
  approve.
- **Phase 4:** report web page + PDF + SES secure-link delivery.
- **Phase 5:** 7-day PHI purge job, audit wiring, backups/alarms.

Do NOT scaffold features beyond the current agreed phase.

## Pushing this repo (first push)

Repo target: `andrewgalli411-sudo/verifi-dental`, **private**. If it was created
with an auto README, the first push force-overwrites that throwaway commit:

```bash
git remote add origin https://github.com/andrewgalli411-sudo/verifi-dental.git
git push -u --force-with-lease origin main
```
