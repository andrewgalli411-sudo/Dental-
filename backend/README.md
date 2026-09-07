# backend

FastAPI backend for verifi-dental. Phase 1 scaffold: data model, the eligibility
abstraction (v1 manual → v2 EDI seam), PHI-scrubbing logging, and migrations.

## Dev setup

```bash
cd backend
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env            # edit as needed
```

## Common commands

```bash
pytest -q                       # run tests (no DB required for Phase 1 tests)
ruff check app tests            # lint
alembic upgrade head            # apply migrations (needs a live DATABASE_URL)
uvicorn app.main:app --reload   # run the API (GET /healthz)
```

## Migrations

Models live in `app/models/`; `app/models/__init__.py` imports all of them so
Alembic autogenerate sees the full metadata.

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

The initial migration is dialect-neutral and targets Postgres in every deployed
environment. (You can apply it against a throwaway SQLite DB for a quick smoke
test, but Postgres is the source of truth — enum/uuid/json types differ.)

## Layout

- `app/eligibility/` — the v1→v2 seam. Start here. `types.py` is the data
  contract; `source.py` the protocol; `manual.py` the v1 human source. A future
  `ClearinghouseEligibilitySource` implements the same protocol.
- `app/models/` — ORM. `appointment.py` is PHI; `audit.py` intentionally holds none.
- `app/logging_config.py` — structured logs with a PHI-field scrubber (tested).
- `app/config.py`, `app/db.py`, `app/main.py` — settings, session, entrypoint.

## Not here yet (later phases)

Intake/upload endpoints + normalizer (Phase 2), admin auth + verification UI
(Phase 3), report generation + delivery (Phase 4), purge job + audit wiring
(Phase 5). No PHI-handling endpoints exist in this scaffold.
