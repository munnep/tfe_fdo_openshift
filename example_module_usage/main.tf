module "tfe_fdo_openshift" {
  source        = "git::github.com/munnep/tfe_fdo_openshift"
  dns_subdomain = var.dns_subdomain
  dns_zone      = var.dns_zone
  cert_email    = var.cert_email

  cloudflare_account_id = var.cloudflare_account_id
  cloudflare_api_token  = var.cloudflare_api_token

  admin_email    = var.admin_email
  admin_password = var.admin_password
  admin_username = var.admin_username

  tfe_encryption_password = var.tfe_encryption_password
  release_sequence        = var.release_sequence

  tfe_raw_license = var.tfe_raw_license

  kubectl_context = var.kubectl_context
  replica_count   = var.replica_count
}


output "tfe_fdo_openshift" {
  value = module.tfe_fdo_openshift
}
