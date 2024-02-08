from cae.models import ingress


def traefik_operator():
    ingress.apply_service("cae-placeholder", {
        "servers": ["http://0.0.0.1:80"]
    })
    ingress.apply_config_middleware("https-redirect", "redirectScheme", {
        "permanent": "true",
        "scheme": "https"
    })
