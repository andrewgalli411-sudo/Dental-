# verifi-dental

AI-assisted dental insurance **eligibility verification** for independent,
single-location US dental practices.

**v1 is wizard-of-oz.** The software is the intake + verification workflow +
report layer. A human (the founder) is the eligibility engine for the first
1–3 pilot clients. The eligibility *source* is abstracted behind a clean
interface so v2 can swap the manual step for a clearinghouse **EDI 270/271**
integration with no rewrite.

> This system touches **PHI**. HIPAA applies. Encryption at rest + in transit,
> no PHI in logs, human sign-off before any report is released, BAAs with every
> vendor that touches PHI, and short-timer PHI purge are designed in, not bolted
> on. See `docs/` and the plan for the full compliance posture.

## Core loop

1. Practice uploads tomorrow's appointment list via a secure, tokenized link
   (no client accounts). Any format: CSV / Excel / PDF / screenshot.
2. The list is normalized into a reviewable table.
3. In the internal admin queue, the founder reviews/corrects the parsed rows and
   enters eligibility per patient (active?, payer/plan, effective date, annual
   max, remaining benefit, deductible total + met).
4. Founder approves → a clean report (web page + printable PDF) is generated and
   an email with a secure link (no PHI) goes to the practice by 7:00 AM local.
5. PHI is purged 7 days after delivery.

## The v1 → v2 seam

Everything hinges on `app.eligibility`:

- `EligibilityRequest` / `EligibilityResult` — the data contract (accepts the
  full field set an EDI 270 needs, even though v1 tolerates gaps).
- `EligibilitySource` — protocol. `submit(request) -> verification_id (pending)`.
  Resolution is **out-of-band**: v1 = human via admin UI; v2 = 271 parser.
- `ManualEligibilitySource` — v1 implementation.
- A future `ClearinghouseEligibilitySource` drops in behind the same protocol.

A contract test (`tests/test_eligibility_contract.py`) proves a fake
clearinghouse source swaps in unchanged.

## Layout

```
backend/
  app/
    main.py              FastAPI app + health check
    config.py            pydantic-settings; env-driven config
    logging_config.py    structured logging with a PHI-field scrubber
    db.py                SQLAlchemy engine/session
    models/              ORM: practice, tokens, batch, appointment, verification, report, audit
    eligibility/         the v1->v2 seam (types, source protocol, manual source)
    services/            (workflow services — filled in later phases)
  migrations/            Alembic
  tests/
```

Frontend (Next.js) is added in Phase 2 (`frontend/`).

## Status

All codeable v1 phases complete (1–5): intake + normalization, admin auth + MFA +
verification queue, human sign-off, report HTML/PDF + secure-link delivery, and
7-day PHI purge. Behind adapters (storage/OCR/email/eligibility) so real AWS drops
in at Phase 0. 32 tests passing.

**Not yet production-ready — Phase 0 is on the founder:** real AWS infra
(RDS/S3/KMS/SES/Textract), signed BAAs (AWS; Anthropic only if an LLM ever touches
PHI), secrets, deploy, and a Next.js frontend if desired (the API is ready for one).
Flip this repo **private** before any real credentials or PHI. See `CLAUDE.md`.
