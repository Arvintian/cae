import docker
from io import BytesIO

config = {
    "DOCKER_CLIENT_ARGS": {
        "base_url": "unix://var/run/docker.sock"
    }
}


def get_docker_client() -> docker.DockerClient:
    return docker.DockerClient(**config.get("DOCKER_CLIENT_ARGS", {}))


dockerfile_template = """
FROM {}:{}
LABEL "cae.image"="true"
"""


def add_cae_image(repo, tag):
    dc = get_docker_client()
    dockerfile = dockerfile_template.format(repo, tag)
    build_fd = BytesIO(dockerfile.encode('utf-8'))
    dc.images.build(fileobj=build_fd, tag="{}:{}".format(repo, tag))


if __name__ == "__main__":
    add_cae_image("redis", "5.0.12")
