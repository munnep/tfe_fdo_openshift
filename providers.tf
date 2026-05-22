terraform {
  required_providers {
    acme = {
      source  = "vancluever/acme"
      version = "~> 2.36.0"
    }
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 5.11.0"
    }
  }
}
