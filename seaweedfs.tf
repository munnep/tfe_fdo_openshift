# https://github.com/seaweedfs/seaweedfs?tab=readme-ov-file#quick-start-for-s3-api-on-docker

resource "kubernetes_config_map_v1" "seaweedfs_s3_config" {
  metadata {
    name      = "${var.tag_prefix}-seaweedfs-s3-config"
    namespace = kubernetes_namespace_v1.terraform_enterprise[var.dep_namespace].metadata.0.name
  }
  data = {
    "s3.json" = jsonencode({
      identities = [
        {
          name = "admin"
          credentials = [
            {
              accessKey = var.seaweedfs_access_key
              secretKey = var.seaweedfs_secret_key
            }
          ]
          actions = ["Admin", "Read", "Write"]
        }
      ]
    })
  }
}

resource "kubernetes_pod_v1" "seaweedfs" {
  metadata {
    name      = "${var.tag_prefix}-seaweedfs"
    namespace = kubernetes_namespace_v1.terraform_enterprise[var.dep_namespace].metadata.0.name
    labels    = { app = "seaweedfs" }
    annotations = {
      "openshift.io/scc" = "nonroot-v2"
    }
  }
  spec {
    security_context {
      run_as_non_root = true
      run_as_user     = 1000
      run_as_group    = 1000
      fs_group        = 1000
      seccomp_profile {
        type = "RuntimeDefault"
      }
    }

    container {
      name  = "seaweedfs"
      image = var.image_seaweedfs
      args  = ["server", "-s3", "-s3.config=/etc/seaweedfs/s3.json", "-filer", "-dir=/data"]

      security_context {
        allow_privilege_escalation = false
        capabilities {
          drop = ["ALL"]
        }
        run_as_non_root = true
        run_as_user     = 1000
        run_as_group    = 1000
        seccomp_profile {
          type = "RuntimeDefault"
        }
      }

      port { container_port = 8333 } # S3 API
      port { container_port = 9333 } # Master UI
      port { container_port = 8080 } # Volume server UI
      port { container_port = 8888 } # Filer UI

      resources {}

      volume_mount {
        name       = "seaweedfs-data"
        mount_path = "/data"
      }

      volume_mount {
        name       = "seaweedfs-s3-config"
        mount_path = "/etc/seaweedfs"
        read_only  = true
      }

      lifecycle {
        post_start {
          exec {
            command = ["/bin/sh", "-c", "sleep 30 && echo 's3.bucket.create -name ${var.tag_prefix}-bucket' | weed shell || true"]
          }
        }
      }
    }
    volume {
      name = "seaweedfs-data"
      empty_dir {}
    }
    volume {
      name = "seaweedfs-s3-config"
      config_map {
        name = kubernetes_config_map_v1.seaweedfs_s3_config.metadata.0.name
      }
    }
  }

  lifecycle {
    ignore_changes = [
      spec[0].security_context,
      metadata[0].annotations,
    ]
  }
}


resource "kubernetes_service_v1" "seaweedfs" {
  metadata {
    name      = "${var.tag_prefix}-seaweedfs"
    namespace = kubernetes_namespace_v1.terraform_enterprise[var.dep_namespace].metadata.0.name
  }
  spec {
    selector = {
      app = "seaweedfs"
    }
    port {
      name        = "s3-api"
      port        = 8333
      target_port = 8333
    }
    port {
      name        = "master-ui"
      port        = 9333
      target_port = 9333
    }
    port {
      name        = "volume-server-ui"
      port        = 8080
      target_port = 8080
    }
    port {
      name        = "filer-ui"
      port        = 8888
      target_port = 8888
    }
    type = "LoadBalancer"
  }
  wait_for_load_balancer = false
}

output "seaweedfs_filer_url" {
  value = "http://localhost:${kubernetes_service_v1.seaweedfs.spec[0].port[2].port}/"
}
