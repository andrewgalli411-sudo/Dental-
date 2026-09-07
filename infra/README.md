# infra — AWS (BAA-covered home for the PHI app)

Terraform for the environment the app runs in. **This is where PHI lives** — not
Vercel. Vercel hosts only the marketing site (`../marketing`).

## What it creates

- **VPC** (2 private + 2 public subnets, 1 NAT, S3 gateway endpoint)
- **RDS Postgres 16** — private only, KMS-encrypted, 14-day backups, deletion protection
- **S3** — `uploads` + `reports` buckets, SSE-KMS, public access blocked, 30-day lifecycle backstop
- **KMS** customer-managed key (rotated) for RDS/S3/Secrets
- **Secrets Manager** — app config (DB URL, session secret) injected at runtime
- **ECR** — backend + frontend image repos (scan on push, KMS-encrypted)
- **App Runner** — backend (in-VPC, reaches RDS) + frontend, with health checks
- **SES** domain identity + DKIM for report-link emails

## Order of operations

Terraform has a bootstrapping order because images must exist before App Runner
can run them.

```bash
# 0. One-time, by hand: create the state bucket + lock table, then fill in the
#    backend "s3" block in versions.tf.

# 1. Stand up everything except the App Runner services (images don't exist yet).
export TF_VAR_db_password='<a strong password>'
terraform init
terraform apply   # backend_image/frontend_image default "" → services skipped

# 2. Build & push images to the ECR repos from the outputs.
#    (see ../DEPLOY.md for the exact docker/ecr commands)

# 3. Re-apply with the pushed image tags to create the App Runner services.
terraform apply \
  -var="backend_image=<ecr_backend_url>:<tag>" \
  -var="frontend_image=<ecr_frontend_url>:<tag>" \
  -var="sending_domain=verifidental.com" \
  -var="app_public_url=https://app.verifidental.com"

# 4. Add the DNS records from `terraform output` (SES DKIM), point
#    app.<domain> at the frontend App Runner URL, and request SES production access.
```

## HIPAA / BAA checklist — do BEFORE any real patient data

- [ ] **Sign the AWS BAA** (AWS Artifact → Agreements). Covers RDS, S3, SES,
      Textract, App Runner, KMS, Secrets Manager — all used here.
- [ ] Confirm every service in use is in AWS's HIPAA-eligible list (all above are).
- [ ] **Anthropic BAA** — only if you ever route PHI through Claude. This build does
      not; keep it that way until that BAA is signed.
- [ ] Repo is **private**.
- [ ] Each pilot practice has a **signed BAA** with you.
- [ ] Verify RDS `publicly_accessible = false` and S3 public-access-block on (both set here).
- [ ] Turn on **CloudTrail** + GuardDuty in the account (not in this module — account-level).

## Cost note

Single-AZ RDS + one NAT + minimal App Runner ≈ low-tens of dollars/month idle.
Flip `multi_az = true` and per-AZ NAT before you depend on availability.
