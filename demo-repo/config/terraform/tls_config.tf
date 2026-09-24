
# WEAK: TLS 1.0 in Terraform
resource "aws_lb_listener" "frontend" {
  protocol              = "HTTPS"
  ssl_policy            = "ELBSecurityPolicy-TLS-1-0-2015-04"
  min_tls_version       = "1.0"
  tls_version           = "TLSv1.0"
}

# WEAK: TLS 1.1 in Terraform
resource "aws_lb_listener" "backend" {
  protocol              = "HTTPS"
  ssl_policy            = "ELBSecurityPolicy-TLS-1-1-2016-08"
  min_tls_version       = "1.1"
  tls_version           = "TLSv1.1"
}

# WEAK: RC4 ciphers in Terraform
resource "aws_lb_listener" "weak" {
  ssl_policy            = "ELBSecurityPolicy-TLS-1-0-2015-04"
  cipher_suites         = ["RC4-SHA", "DES-CBC3-SHA"]
}

# WEAK: RSA-1024 key
resource "aws_kms_key" "weak" {
  key_bits              = 1024
  key_type              = "SYMMETRIC_DEFAULT"
}

# WEAK: Certificate verification disabled
resource "aws_eks_cluster" "cluster" {
  insecure_skip_tls_verify = true
}

# OK: TLS 1.3 in Terraform
resource "aws_lb_listener" "strong" {
  protocol              = "HTTPS"
  ssl_policy            = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  min_tls_version       = "1.3"
  tls_version           = "TLSv1.3"
}
