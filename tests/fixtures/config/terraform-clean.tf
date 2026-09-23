# terraform-clean.tf — Terraform with strong crypto settings
# TEST FIXTURE for the ECDAT config engine — no weak crypto.

resource "tls_private_key" "strong_key" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "aws_lb_listener" "secure" {
  load_balancer_arn = "arn:aws:elasticloadbalancing:us-east-1:123:loadbalancer/app/test/abc"
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"

  default_action {
    type = "forward"
    target_group_arn = "arn:aws:elasticloadbalancing:us-east-1:123:targetgroup/test/abc"
  }
}
