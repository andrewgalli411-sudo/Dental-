# Deploying verifi-dental

Two targets, split on purpose so PHI never touches a non-BAA host:

| Piece | Host | Why |
|---|---|---|
| Marketing + sign-in site (`marketing/`) | **Vercel** | No PHI. Fast, cheap, easy. |
| App: Next admin console + FastAPI + DB + files (`frontend/`, `backend/`, `infra/`) | **AWS** | Handles PHI → needs a signed BAA. Standard Vercel can't. |

> **Standard Vercel does not sign a HIPAA BAA** (Enterprise only). Do not deploy
> the app, or proxy PHI, through Vercel.

## A. Marketing site → Vercel (5 minutes)

1. Vercel → **New Project** → import `andrewgalli411-sudo/verifi-dental`.
2. **Root Directory:** `marketing` · **Framework:** Other · no build command.
3. Deploy; add domain `www.verifidental.com`.
4. Edit `marketing/index.html` → set `APP_URL` to `https://app.verifidental.com`
   once the app (below) is live, so "Sign in" points to it.

## B. App → AWS

Prereqs: an AWS account with the **BAA signed** (AWS Artifact), the AWS CLI, Docker,
and Terraform.

### 1. Provision infra
Follow `infra/README.md` steps 0–1 (creates ECR, RDS, S3, KMS, secrets, VPC).

### 2. Build & push images
```bash
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
REGION=us-east-1
aws ecr get-login-password --region $REGION \
  | docker login --username AWS --password-stdin $ACCOUNT.dkr.ecr.$REGION.amazonaws.com

# Backend
docker build -t verifi-backend ./backend
docker tag verifi-backend:latest $(terraform -chdir=infra output -raw ecr_backend_url):v1
docker push $(terraform -chdir=infra output -raw ecr_backend_url):v1

# Frontend
docker build -t verifi-frontend ./frontend
docker tag verifi-frontend:latest $(terraform -chdir=infra output -raw ecr_frontend_url):v1
docker push $(terraform -chdir=infra output -raw ecr_frontend_url):v1
```

### 3. Create the services
Run `infra/README.md` step 3 with the `:v1` image URIs. The backend runs
`alembic upgrade head` on boot (see `backend/docker-entrypoint.sh`), so the DB
schema is created automatically.

### 4. Bootstrap the first admin
```bash
# One-off: exec the create-admin script against the deployed DB. Easiest is to run
# it locally with DATABASE_URL pointed at RDS through a bastion/SSM tunnel:
cd backend && python -m scripts.create_admin you@verifidental.com
# Save the printed otpauth:// URI into your authenticator app.
```

### 5. DNS + email
- Point `app.verifidental.com` at the frontend App Runner URL.
- Add the SES DKIM CNAMEs from `terraform output ses_dkim_tokens`; request SES
  production access.

### 6. Schedule the PHI purge
Create an EventBridge rule (daily) that runs `python -m scripts.purge_phi` — as a
scheduled ECS task using the backend image, or a small Lambda. Enforces the
7-day retention promise.

## Local development (no AWS)

```bash
# Backend
cd backend && python3 -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]"
cp .env.example .env && uvicorn app.main:app --reload
python -m scripts.create_admin you@example.com   # in another shell

# Frontend
cd frontend && npm install && cp .env.local.example .env.local && npm run dev
# open http://localhost:3000
```
