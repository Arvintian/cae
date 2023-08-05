from cae.config import config
import docker
import os
import json

docker_root = "/var/lib/docker"


def get_docker_client() -> docker.DockerClient:
    return docker.DockerClient(**config.get("DOCKER_CLIENT_ARGS", {}))


def get_container_config(container_id: str) -> dict:
    container_home = os.path.join(docker_root, "containers", container_id)
    config_json = os.path.join(container_home, "config.v2.json")
    if not os.path.exists(config_json):
        config_json = os.path.join(container_home, "config.json")
    if not os.path.exists(config_json):
        raise Exception("can not find container config.json")
    with open(config_json, "r", encoding="utf-8") as fd:
        config_bts = fd.read()
        return json.loads(config_bts)


def put_container_config(container_id: str, cfg: dict) -> dict:
    container_home = os.path.join(docker_root, "containers", container_id)
    config_json = os.path.join(container_home, "config.v2.json")
    if not os.path.exists(config_json):
        config_json = os.path.join(container_home, "config.json")
    if not os.path.exists(config_json):
        raise Exception("can not find container config.json")
    with open(config_json, "w", encoding="utf-8") as fd:
        fd.write(json.dumps(cfg))
