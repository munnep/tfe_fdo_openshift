# Squid Proxy ConfigMap for squid.conf
resource "kubernetes_config_map_v1" "squid" {
  count = var.enable_proxy ? 1 : 0

  metadata {
    name      = "${var.tag_prefix}-squid-config"
    namespace = kubernetes_namespace_v1.terraform_enterprise[var.dep_namespace].metadata.0.name
  }
  data = {
    "squid.conf" = <<-EOF
      # Squid proxy configuration
      # Port configuration
      http_port 3128

      # Access control - allow all (restrict in production!)
      acl all src all
      http_access allow all

      # Allow CONNECT for HTTPS
      acl SSL_ports port 443
      acl CONNECT method CONNECT
      http_access allow CONNECT SSL_ports

      # Caching configuration
      cache_dir ufs /var/spool/squid 1000 16 256
      maximum_object_size 512 MB
      cache_mem 256 MB

      # DNS settings
      dns_nameservers 8.8.8.8 8.8.4.4

      # Logging
      access_log /var/log/squid/access.log squid
      cache_log /var/log/squid/cache.log
      cache_store_log /var/log/squid/store.log

      # Don't cache dynamic content
      acl dynamic urlpath_regex cgi-bin \?
      cache deny dynamic

      # Refresh patterns
      refresh_pattern ^ftp:           1440    20%     10080
      refresh_pattern ^gopher:        1440    0%      1440
      refresh_pattern -i (/cgi-bin/|\?) 0     0%      0
      refresh_pattern .               0       20%     4320

      # Preserve authentication headers (critical for AWS)
      request_header_access Authorization allow all
      request_header_access X-Amz-.* allow all
      request_header_access AWS.* allow all

      # Don't modify requests
      collapsed_forwarding off
    EOF
  }
}

resource "kubernetes_pod_v1" "squid" {
  count = var.enable_proxy ? 1 : 0

  metadata {
    name      = "${var.tag_prefix}-squid"
    namespace = kubernetes_namespace_v1.terraform_enterprise[var.dep_namespace].metadata.0.name
    labels    = { app = "squid" }
  }
  spec {
    container {
      name  = "squid"
      image = var.image_squid

      port { container_port = 3128 }

      readiness_probe {
        tcp_socket {
          port = 3128
        }
        initial_delay_seconds = 10
        period_seconds        = 5
      }
      liveness_probe {
        tcp_socket {
          port = 3128
        }
        initial_delay_seconds = 30
        period_seconds        = 10
      }

      resources {}

      volume_mount {
        name       = "squid-config"
        mount_path = "/etc/squid/squid.conf"
        sub_path   = "squid.conf"
        read_only  = true
      }
      volume_mount {
        name       = "squid-cache"
        mount_path = "/var/spool/squid"
      }
      volume_mount {
        name       = "squid-logs"
        mount_path = "/var/log/squid"
      }
    }
    volume {
      name = "squid-config"
      config_map {
        name = kubernetes_config_map_v1.squid[0].metadata[0].name
      }
    }
    volume {
      name = "squid-cache"
      empty_dir {}
    }
    volume {
      name = "squid-logs"
      empty_dir {}
    }
  }
}

resource "kubernetes_service_v1" "squid" {
  count = var.enable_proxy ? 1 : 0

  metadata {
    name      = "${var.tag_prefix}-squid"
    namespace = kubernetes_namespace_v1.terraform_enterprise[var.dep_namespace].metadata.0.name
  }
  spec {
    selector = { app = "squid" }
    port {
      name        = "squid"
      port        = 3128
      target_port = 3128
    }
    type = "LoadBalancer"
  }
  wait_for_load_balancer = false
}

