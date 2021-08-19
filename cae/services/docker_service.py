from cae.config import config
import docker


def get_docker_client() -> docker.DockerClient:
    return docker.DockerClient(**config.get("DOCKER_CLIENT_ARGS", {}))
