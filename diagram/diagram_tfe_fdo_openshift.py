# diagram_tfe_fdo_openshift.py
# Requirements:
#   pip install diagrams
#   brew install graphviz  # on macOS
#
# Run:
#   source ../venv/bin/activate
#   python3 diagram_tfe_fdo_openshift.py
#
# Output:
#   diagram_tfe_fdo_openshift.png

from diagrams import Diagram, Cluster, Edge
from diagrams.k8s.compute import Pod
from diagrams.onprem.database import Postgresql
from diagrams.onprem.inmemory import Redis
from diagrams.aws.storage import S3
from diagrams.saas.cdn import Cloudflare
from diagrams.onprem.client import Users

with Diagram(
    "TFE FDO on OpenShift",
    show=False,
    filename="diagram_tfe_fdo_openshift",
    outformat="png",
    direction="LR",
):
    # External user
    external_user = Users("External User")
    
    # Cloudflare public service
    cloudflare_public = Cloudflare("Cloudflare\n(Public)")

    # OpenShift cluster with namespaces
    with Cluster("OpenShift Cluster"):
        # Two namespaces: one for TFE, one for dependencies
        with Cluster("TFE Namespace"):
            tfe_pods = [Pod(f"TFE Pod {i+1}\n(Helm deployed)") for i in range(2)]
        
        with Cluster("Dependencies Namespace"):
            cloudflared_pod = Pod("cloudflared\n(Cloudflare tunnel)")
            postgres_pod = Postgresql("PostgreSQL\n(database)")
            redis_pod = Redis("Redis\n(cache/session)")
            seaweedfs_pod = S3("SeaweedFS\n(S3-compatible)")

    # Relationships
    external_user >> Edge(label="HTTPS") >> cloudflare_public
    cloudflare_public >> Edge(label="tunnel") >> cloudflared_pod
    cloudflared_pod >> Edge(label="forwards") >> tfe_pods[0]
    
    # Internal pod relationships - TFE connects to dependencies
    for tfe_pod in tfe_pods:
        tfe_pod >> Edge(label="queries") >> postgres_pod
        tfe_pod >> Edge(label="stores") >> seaweedfs_pod
        tfe_pod >> Edge(label="caches") >> redis_pod
