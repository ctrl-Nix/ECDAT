# terraform-vulnerable.tf — Terraform with weak crypto settings
# TEST FIXTURE for the ECDAT config engine.

resource "tls_private_key" "weak_key" {
  algorithm = "RSA"
  rsa_bits  = 1024
}

resource "tls_private_key" "medium_key" {
  algorithm = "RSA"
  rsa_bits  = 2048
}

resource "aws_lb_listener" "insecure" {
  load_balancer_arn = "arn:aws:elasticloadbalancing:us-east-1:123:loadbalancer/app/test/abc"
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS-1-0"

  default_action {
    type = "forward"
    target_group_arn = "arn:aws:elasticloadbalancing:us-east-1:123:targetgroup/test/abc"
  }
}

resource "aws_provider" "example" {
  insecure = true
}
