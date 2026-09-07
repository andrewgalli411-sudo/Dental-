# SES domain identity for sending report links (links only — never PHI in email).
# Verification + DKIM require adding the output DNS records at your registrar.
# Created only when a sending domain is provided.

resource "aws_ses_domain_identity" "main" {
  count  = var.sending_domain == "" ? 0 : 1
  domain = var.sending_domain
}

resource "aws_ses_domain_dkim" "main" {
  count  = var.sending_domain == "" ? 0 : 1
  domain = aws_ses_domain_identity.main[0].domain
}
