# General
variable "dns_zone" {
  description = "The domain used in the URL."
  type        = string
}

variable "dns_subdomain" {
  description = "the subdomain of the url"
  type        = string
}

variable "cert_email" {
  description = "Email address used to obtain ssl certificate."
  type        = string
}

variable "kubectl_config_path" {
  description = "Path to the kube config file."
  type        = string
  default     = "~/.kube/config"
}

variable "kubectl_context" {
  description = "The context to use within the kube config file."
  type        = string
  default     = "crc-admin"
}

variable "tfe_agent_image" {
  description = "Docker image for the TFE agent ."
  type        = string
  default     = "docker.io/patrickmunne3/custom-agent-openshift:v1.4"
}


variable "namespace" {
  description = "Kubernetes namespace to deploy resources into."
  type        = string
  default     = "terraform-enterprise"
}

variable "dep_namespace" {
  description = "Kubernetes namespace to deploy dependencies into."
  type        = string
  default     = "terraform-enterprise"
}

variable "tag_prefix" {
  description = "Prefix for naming Kubernetes resources."
  type        = string
  default     = "tfe"
}

# Cloudflare
variable "cloudflare_account_id" {
  description = "Cloudflare account ID."
  type        = string
}

variable "cloudflare_api_token" {
  description = "API token for Cloudflare DNS challenge."
  type        = string
}

# SeaweedFS
variable "seaweedfs_access_key" {
  description = "SeaweedFS access key."
  type        = string
  default = "admin"
}

variable "seaweedfs_secret_key" {
  description = "SeaweedFS secret key."
  type        = string
  default = "password"
}

variable "image_seaweedfs" {
  description = "SeaweedFS docker image."
  type        = string
  default = "docker.io/chrislusf/seaweedfs:4.09"
}

# Squid
variable "image_squid" {
  description = "Squid proxy docker image."
  type        = string
  default     = "docker.io/ubuntu/squid:latest"
}

variable "enable_proxy" {
  description = "Enable the Squid proxy server and configure TFE to use it."
  type        = bool
  default     = false
}


# Postgres
variable "postgres_user" {
  description = "Postgres username."
  type        = string
  default = "postgres"
}

variable "postgres_password" {
  description = "Postgres password."
  type        = string
  default     = "postgresql"
}

variable "postgres_db" {
  description = "Postgres database name."
  type        = string
  default     = "postgres"
}

variable "postgres_db_explorer" {
  description = "Second Postgres database name."
  type        = string
  default     = "tfe_explorer"
}

variable "image_postgres" {
  description = "Postgres docker image."
  type        = string
  default     = "docker.io/library/postgres:16"
}

# Redis
variable "image_redis" {
  description = "Redis docker image."
  type        = string
  default     = "docker.io/library/redis:7"
}


# TFE
variable "tfe_encryption_password" {
  description = "Password used to encrypt TFE data."
  type        = string
}

variable "admin_username" {
  description = "Username for the TFE admin account."
  type        = string
}

variable "admin_email" {
  description = "Email address for the TFE admin account."
  type        = string
}

variable "admin_password" {
  description = "Password for the TFE admin account."
  type        = string
}

variable "release_sequence" {
  description = "Release number of the TFE version you wish to install."
  type        = string
}

variable "registry_username" {
  description = "Username to download docker tfe image."
  type        = string
  default     = "terraform"
}

variable "registry_images_url" {
  description = "URL for the images registry to download docker tfe image."
  type        = string
  default     = "images.releases.hashicorp.com"
}

variable "tfe_raw_license" {
  description = "The raw TFE license string"
  type        = string
}

variable "tfe_helm_version" {
  description = "The helm TFE version string"
  type        = string
  default     = "1.6.8"
}

variable "replica_count" {
  description = "Number of replicas (pods)."
  type        = number
  default     = 1
}

variable "helm_timeout" {
  description = "timeout for helm"
  type        = number
  default     = 600
}

variable "acme_server_url" {
  description = "acme server url to use"
  type        = string
  default     = "https://acme-v02.api.letsencrypt.org/directory"
}
