import docker
from io import BytesIO
import io
from docker.models.containers import Container
from typing import List
from pretty_logging import pretty_logger

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


def check_container_sshd(container: Container) -> bool:
    try:
        bts, stat = container.get_archive("/var/run/sshd.pid")
        pretty_logger.info("{} sshd.pid {}".format(container.id, stat))
        if stat.get("size") < 1:
            raise Exception("container passwd file if none {}".format(container.id))
        return True
    except Exception as e:
        pretty_logger.error("{}".format(e))
        return False


if __name__ == "__main__":
    # add_cae_image("redis", "5.0.12")
    # instance_id = "16b61a3ba766473837646aecd6316879fe5f222f74c637b4f347b696ea2f8c9c"
    instance_id = "ea2b3bc99aa0ebaffaccc62f58c1769968ddffa9ccdfb23da24fd79f7a145816"
    dc = get_docker_client()
    cs: List[Container] = dc.containers.list(filters={
        "label": ["cae.app=true"],
        "id": instance_id
    })
    if not cs:
        raise Exception("not found instance {}".format(instance_id))
    container: Container = cs[0]
    check_container_sshd(container)
