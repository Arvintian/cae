
"""
docker run --rm -ti --name dev-traefik -v /var/run/docker.sock:/var/run/docker.sock \
    --label cae.infra=traefik \
    --label traefik.http.routers.api.entrypoints=traefik \
    --label 'traefik.http.routers.api.rule=PathPrefix(`/api`)' \
    --label traefik.http.routers.api.service=api@internal \
    --label traefik.http.routers.dashboard.entrypoints=traefik \
    --label 'traefik.http.routers.dashboard.rule=PathPrefix(`/`)' \
    --label traefik.http.routers.dashboard.service=dashboard@internal \
    -p 80:80 -p 8080:8080 traefik:v2.4.8 \
    --accesslog=true \
    --api.dashboard=true \
    --api=true \
    --entrypoints.http80.address=:80 \
    --entrypoints.http80=true \
    --entrypoints.traefik.address=:8080 \
    --entrypoints.traefik=true \
    --log.level=info \
    --log=true \
    --providers.docker.constraints='Label(`cae.infra`,`traefik`)' \
    --providers.docker.endpoint=unix:///var/run/docker.sock \
    --providers.docker=true \
    --providers.redis.endpoints=172.17.0.2:6379 \
    --providers.redis.rootkey=cae/ingress \
    --providers.redis=true
"""
