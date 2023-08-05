from .env_utils import env

config = {
    "DEBUG": False,
    "PORT": 5000,
    "WORKERS": env("WORKERS", cast=int, default=2),
    "REDIS_URL": env("REDIS_URL", cast=str, default="redis://127.0.0.1:6379/0"),
    "REDIS_KEY_PREFIX":  env("REDIS_KEY_PREFIX", cast=str, default="cae"),
    "DOCKER_CLIENT_ARGS": {
        "base_url": "unix://var/run/docker.sock"
    },
    "DOCKER_NETWORK": env("DOCKER_NETWORK", cast=str, default="caenet"),
    "DOCKER_NETWORK_BLOCKS": env("DOCKER_NETWORK_BLOCKS", cast=str, default="172.28.2.0/24"),
    "middlewares": [
        "cae.middleware.panic.PanicMiddleware",
    ]
}

channel_config = {
    "BIND_HOST": "0.0.0.0",
    "SSHD_PORT": env("SSHD_PORT", cast=int, default=2222),
    "SSH_TIMEOUT": 15,
    "HOST_PRIVATE_KEY": "/channel/id_rsa",
    "HOST_PUBLIC_KEY": "/channel/id_rsa.pub",
}
