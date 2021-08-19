from cae.models import ingress


def traefik_operator():
    ingress.apply_service("cae-placeholder", {
        "servers": ["http://0.0.0.1:80"]
    })
