# Certificates for api. (ALB) and assets. (CloudFront; must be us-east-1,
# which this whole stack is). DNS is at Vercel, so validation is two-step:
#   1. terraform apply -target=aws_acm_certificate.api -target=aws_acm_certificate.assets
#   2. infra/vercel-dns.sh certs --apply   (CAA for amazon.com + the validation CNAMEs)
#   3. terraform apply                     (the validation resources wait for ISSUED)
# The zone's CAA records allow only pki.goog, sectigo.com and letsencrypt.org
# today; without an amazon.com CAA record ACM never issues.

resource "aws_acm_certificate" "api" {
  domain_name       = "api.${var.domain}"
  validation_method = "DNS"
  lifecycle { create_before_destroy = true }
}

resource "aws_acm_certificate" "assets" {
  domain_name       = "assets.${var.domain}"
  validation_method = "DNS"
  lifecycle { create_before_destroy = true }
}

resource "aws_acm_certificate_validation" "api" {
  certificate_arn         = aws_acm_certificate.api.arn
  validation_record_fqdns = [for o in aws_acm_certificate.api.domain_validation_options : o.resource_record_name]
  timeouts { create = "15m" }
}

resource "aws_acm_certificate_validation" "assets" {
  certificate_arn         = aws_acm_certificate.assets.arn
  validation_record_fqdns = [for o in aws_acm_certificate.assets.domain_validation_options : o.resource_record_name]
  timeouts { create = "15m" }
}
